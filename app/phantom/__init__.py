"""PHANTOM - Proxy Rotation System."""
import os

VERSION = "1.0.1"
TERMS_VERSION = "1"   # bump when the terms of use change -> users are asked again
NAME = "PHANTOM"
SLOGAN = "Bláthy On Top"     # shown under the name - Bláthy is the author's school
SCHOOL = "Bláthy"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # PHANTOM/app
ROOT_DIR = os.path.dirname(BASE_DIR)                                       # PHANTOM
PROXY_DIR = os.path.join(ROOT_DIR, "proxies")                              # proxy lists
