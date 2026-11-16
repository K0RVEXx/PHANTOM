"""Modified-copy check.

Every release ships `app/integrity.json` with the SHA-256 of each program file.
On start the files are compared with that list. If something was changed, the
user is reminded what the license allows. This is a reminder, not a lock: the
license lets people change the software for themselves, it only forbids
publishing, sharing or presenting it as their own.
"""
import hashlib
import json
import os

from . import BASE_DIR

MANIFEST = os.path.join(BASE_DIR, "integrity.json")
PACKAGE = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
EXTRA = ("setup/install-python.ps1",)   # files outside the package to cover (relative to BASE_DIR)


def tracked_files():
    """Program files covered by the check, as paths relative to BASE_DIR (forward slashes)."""
    files = []
    pkg = os.path.join(BASE_DIR, PACKAGE)
    for name in sorted(os.listdir(pkg)):
        if name.endswith(".py"):
            files.append(f"{PACKAGE}/{name}")
    files.append(f"{PACKAGE}.py")
    files.extend(EXTRA)
    return files


def file_hash(rel):
    with open(os.path.join(BASE_DIR, rel), "rb") as f:
        data = f.read()
    # Git may check files out with Windows (CRLF) or Unix (LF) line endings;
    # both count as the same file.
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def current():
    return {rel: file_hash(rel) for rel in tracked_files() if os.path.isfile(os.path.join(BASE_DIR, rel))}


def write_manifest(version):
    data = {"version": version, "files": current()}
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1, sort_keys=True)
        f.write("\n")
    return data


def check():
    """Returns a dict: {"status": "ok"|"modified"|"no-manifest", "changed": [...],
    "missing": [...], "added": [...], "fingerprint": <hash of the current state>}"""
    now = current()
    fingerprint = hashlib.sha256(json.dumps(now, sort_keys=True).encode()).hexdigest()[:16]
    try:
        with open(MANIFEST, encoding="utf-8") as f:
            expected = json.load(f).get("files", {})
    except (OSError, ValueError):
        return {"status": "no-manifest", "changed": [], "missing": [], "added": [], "fingerprint": fingerprint}
    changed = sorted(r for r in now if r in expected and now[r] != expected[r])
    missing = sorted(r for r in expected if r not in now)
    added = sorted(r for r in now if r not in expected)
    status = "modified" if (changed or missing or added) else "ok"
    return {"status": status, "changed": changed, "missing": missing, "added": added, "fingerprint": fingerprint}
