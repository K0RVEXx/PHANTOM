"""Refresh app/integrity.json after changing program files.

Run before committing:  python tools/update_integrity.py
(The test suite fails if the list is out of date.)
"""
import os
import sys

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP)

from phantom import VERSION, integrity  # noqa: E402

data = integrity.write_manifest(VERSION)
print(f"integrity.json updated: {len(data['files'])} files, version {VERSION}")
