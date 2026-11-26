"""Bounded local recovery of an exact historical Git blob; no network or public output."""
from pathlib import Path
import hashlib
import subprocess
import re

SHA = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")

def recover_blob(repo_dir, commit, path, expected_blob, *, max_bytes=2_000_000):
    """Caller supplies an authorized local repository. Ref/path and hash must match.
    No mutable ref fallback, no clone, no automatic writing or image interpretation.
    """
    if not SHA.fullmatch(commit) or not SHA.fullmatch(expected_blob):
        raise ValueError("Full immutable commit and blob IDs required")
    if not path or path.startswith(("/", "-")) or "\\" in path or ":" in path or "\x00" in path or any(p in ("", ".", "..") for p in path.split("/")):
        raise ValueError("Invalid historical path")
    if not 1 <= max_bytes <= 16_000_000:
        raise ValueError("Invalid maximum size")
    root = Path(repo_dir).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Local Git repository directory required")
    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args],
                              check=True, capture_output=True, timeout=20).stdout
    if git("cat-file", "-t", commit).strip() != b"commit":
        raise ValueError("Commit is not a commit object")
    object_id = git("rev-parse", "--verify", commit + ":" + path).decode("ascii").strip()
    if object_id != expected_blob or git("cat-file", "-t", object_id).strip() != b"blob":
        raise ValueError("Pinned blob does not match the historical path")
    size = int(git("cat-file", "-s", object_id))
    if size > max_bytes:
        raise ValueError("Blob exceeds byte budget")
    data = git("cat-file", "blob", object_id)
    if len(data) != size:
        raise ValueError("Blob size mismatch")
    algorithm = "sha1" if len(object_id) == 40 else "sha256"
    actual = hashlib.new(algorithm, f"blob {size}\x00".encode() + data).hexdigest()
    if actual != expected_blob:
        raise ValueError("Blob checksum mismatch")
    return data, {"commit_sha":commit,"path":path,"blob_sha":actual,
                  "sha256":hashlib.sha256(data).hexdigest(),"bytes":size,
                  "retrieval_method":"local_git_object","visual_inspection":"not_performed"}
