"""Write evidence/code_manifest.json: sha256 of every source, test, tool, schema and data file.

The combined digest is used as the 'code revision' in the review packet because this folder is not a git repository.
"""
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDERS = ["src", "tests", "tools", "schemas", "data"]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


files = {}
for folder in FOLDERS:
    for base, _, names in os.walk(os.path.join(ROOT, folder)):
        if "__pycache__" in base:
            continue
        for n in sorted(names):
            p = os.path.join(base, n)
            files[os.path.relpath(p, ROOT)] = sha(p)

combined = hashlib.sha256("\n".join(f"{k} {v}" for k, v in sorted(files.items())).encode()).hexdigest()
out = {"note": "Not a git repository; combined_sha256 stands in for a code revision.",
       "combined_sha256": combined, "file_count": len(files), "files": dict(sorted(files.items()))}
with open(os.path.join(ROOT, "evidence", "code_manifest.json"), "w") as fh:
    json.dump(out, fh, indent=2)
    fh.write("\n")
print("code revision (combined sha256):", combined, f"({len(files)} files)")
