# Guard: no truly-personal identifier (the author's private email or home path) may
# ship in a tracked file. The GitHub *noreply* identity is public by design (it is in
# commit metadata and case attributions) and is deliberately NOT forbidden; the
# published spec example uses a neutral placeholder instead.
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Needles are assembled from fragments so the literal never appears in THIS file (no
# self-match) and can't partial-match unrelated text (e.g. the LHC-case "proton").
NEEDLES = [
    "van_songhai" + "@" + "proton.me",   # author's private email
    "/Users/" + "mw21",                   # author's home path
]

TEXT_EXTS = {".md", ".py", ".sh", ".json", ".yml", ".yaml", ".toml", ".txt", ".cfg"}


def _tracked_text_files():
    out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT,
                         capture_output=True, text=True, check=True).stdout.split()
    return [REPO_ROOT / f for f in out if Path(f).suffix in TEXT_EXTS]


def test_no_personal_identifiers_in_tracked_files():
    hits = []
    for path in _tracked_text_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for needle in NEEDLES:
            if needle in text:
                hits.append(f"{path.relative_to(REPO_ROOT)}: {needle}")
    assert not hits, "personal identifier(s) in tracked files:\n  " + "\n  ".join(hits)
