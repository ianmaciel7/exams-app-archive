import hashlib
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from sys import path
path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from archive_index import ingest,search,images,recover,open_db,safe_path,safe_ref


def run(*cmd, cwd=None):
    return subprocess.run(cmd,cwd=cwd,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout


class ArchiveTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.work=self.root/'work';self.work.mkdir()
        run('git','init','-q','-b','main',str(self.work))
        run('git','config','user.email','archive@example.invalid',cwd=self.work)
        run('git','config','user.name','Archive Test',cwd=self.work)
        (self.work/'graph-history.png').write_bytes(b'\x89PNG\r\n\x1a\nOLD_SCREENSHOT')
        (self.work/'recall.ts').write_text('export function spacedRepetition() { return "FSRS"; }\n')
        run('git','add','.',cwd=self.work);run('git','commit','-qm','feat: initial graph screenshot and FSRS recall',cwd=self.work)
        self.ancestor=run('git','rev-parse','HEAD',cwd=self.work).decode().strip()
        run('git','checkout','-qb','old-visual',cwd=self.work)
        (self.work/'old-visual.md').write_text('Historical Capacities sidebar references')
        run('git','add','.',cwd=self.work);run('git','commit','-qm','docs: Capacities sidebar reference',cwd=self.work)
        run('git','checkout','-q','main',cwd=self.work)
        (self.work/'graph-history.png').unlink()
        run('git','add','-u',cwd=self.work);run('git','commit','-qm','remove old graph screenshot',cwd=self.work)
        self.removal=run('git','rev-parse','HEAD',cwd=self.work).decode().strip()
        self.bare=self.root/'source.git'
        run('git','clone','--mirror','-q',str(self.work),str(self.bare))
        self.conn=open_db(self.root/'index.sqlite')
        self.addCleanup(self.conn.close)

    def test_index_and_find_removed_image(self):
        info=ingest(self.bare,'example',self.conn)
        self.assertEqual(info['refs'],2)
        self.assertEqual(info['commits'],3)
        found=images(self.conn,deleted_only=True)
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]['path'],'graph-history.png')
        self.assertEqual(found[0]['commit_sha'],self.ancestor)
        output=self.root/'recovered.png'
        evidence=recover(self.bare,self.ancestor,'graph-history.png',output)
        self.assertTrue(output.read_bytes().startswith(b'\x89PNG'))
        self.assertEqual(evidence['sha256'],hashlib.sha256(output.read_bytes()).hexdigest())

    def test_search_and_branch_history(self):
        ingest(self.bare,'example',self.conn)
        hits=search(self.conn,'FSR')
        self.assertTrue(any('FSRS' in x['summary'] for x in hits))
        hits=search(self.conn,'recall')
        self.assertTrue(any(x['path']=='recall.ts' for x in hits))
        refs=self.conn.execute('SELECT name FROM refs').fetchall()
        self.assertIn(('refs/heads/old-visual',),refs)

    def test_reject_unsafe_paths(self):
        for path in ['../secret','/etc/passwd','x\\y',':oops','-flag']:
            with self.assertRaises(ValueError):safe_path(path)
        with self.assertRaises(ValueError):safe_ref('main')
        with self.assertRaises(FileExistsError):
            (self.root/'exists').write_text('data')
            recover(self.bare,self.ancestor,'recall.ts',self.root/'exists')

    def test_default_db_path_not_in_reports_and_no_tracked_sqlite(self):
        root=Path(__file__).resolve().parents[1]
        cli_help=run('python3',str(root/'scripts/archive_index.py'),'--help').decode('utf-8')
        self.assertNotIn('reports/archive-index.sqlite',cli_help)
        tracked=run('git','ls-files','reports/*.sqlite',cwd=root).decode('utf-8').strip()
        self.assertEqual(tracked,'')
        poc_wf=(root/'.github/workflows/archive-poc.yml').read_text(encoding='utf-8')
        self.assertNotIn('git add reports/POC.md reports/POC.json reports/archive-index.sqlite',poc_wf)

    def test_search_ranking_quota_dedup_and_compatibility(self):
        # Populate enough synthetic rows across commit, file, and image to test quota, ranking, and dedupe
        for idx in range(10):
            (self.work / 'sidebar.tsx').write_text(f'export const step = {idx};\n')
            run('git', 'add', 'sidebar.tsx', cwd=self.work)
            run('git', 'commit', '-qm', f'chore: update sidebar iteration {idx}', cwd=self.work)
        (self.work / 'sidebar-panel.png').write_bytes(b'\x89PNG\r\n\x1a\nSIDEBAR_IMG_A')
        (self.work / 'sidebar-extra.png').write_bytes(b'\x89PNG\r\n\x1a\nSIDEBAR_IMG_A')
        run('git', 'add', '.', cwd=self.work)
        run('git', 'commit', '-qm', 'feat: sidebar panel layout exact', cwd=self.work)
        exact_sha = run('git', 'rev-parse', 'HEAD', cwd=self.work).decode().strip()

        bare2 = self.root / 'source2.git'
        run('git', 'clone', '--mirror', '-q', str(self.work), str(bare2))
        ingest(bare2, 'example', self.conn)

        # Default search(conn, q, limit=...) remains backwards compatible and includes multiple types
        mixed = search(self.conn, 'sidebar', 6)
        self.assertEqual(len(mixed), 6)
        kinds = {item['kind'] for item in mixed}
        self.assertIn('commit', kinds)
        self.assertIn('file', kinds)
        self.assertIn('image', kinds)
        for item in mixed:
            self.assertTrue({'repository', 'kind', 'sha', 'path', 'summary'}.issubset(item.keys()))

        # File deduplication aggregates commits and preserves first/last SHA
        file_hits = search(self.conn, 'sidebar', 10, kind='file')
        paths = [(r['repository'], r['path']) for r in file_hits]
        self.assertEqual(len(paths), len(set(paths)))
        sidebar_file = next(r for r in file_hits if r['path'] == 'sidebar.tsx')
        self.assertEqual(sidebar_file['commits'], 10)
        self.assertNotEqual(sidebar_file['first_sha'], sidebar_file['last_sha'])

        # Image deduplication collapses identical blobs across paths
        img_hits = search(self.conn, 'sidebar', 10, kind='image')
        blobs = [r['blob'] for r in img_hits]
        self.assertEqual(len(blobs), len(set(blobs)))
        self.assertEqual(img_hits[0]['occurrences'], 2)

        # Phrase/AND-first returns exact match before falling back to OR
        and_hits = search(self.conn, 'sidebar panel', 10, kind='commit')
        self.assertEqual([h['sha'] for h in and_hits], [exact_sha])
        or_fallback = search(self.conn, 'sidebar nonexistentterm', 10, kind='commit')
        self.assertGreaterEqual(len(or_fallback), 10)

        # CLI backwards compatibility: search without --kind/--repo
        root = Path(__file__).resolve().parents[1]
        db_file = self.root / 'index.sqlite'
        cli_out = run('python3', str(root / 'scripts/archive_index.py'), '--db', str(db_file), 'search', 'sidebar', '--limit', '6').decode('utf-8')
        self.assertEqual(len(__import__('json').loads(cli_out)), 6)

if __name__=='__main__':unittest.main()