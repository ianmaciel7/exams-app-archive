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

if __name__=='__main__':unittest.main()