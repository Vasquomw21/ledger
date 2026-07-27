# Make the un-packaged kernel scripts importable as plain modules: the repo
# has no pyproject/installable layout by design (it is a starter kit), so the
# tests import literature/verify_quotes.py and tools/check_citations.py by
# putting their directories on sys.path.
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for subdir in ("literature", "tools"):
    sys.path.insert(0, str(REPO_ROOT / subdir))
