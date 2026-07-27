# Regression test for the write-time hook's Layer-3 size floor (dogfood fix a).
# The bug: the 500-char floor measured the edit FRAGMENT (.new_string), so a small
# in-band edit (adding one marker line) to an existing real ledger false-positived.
# The fix measures the RESULTING FILE — for an Edit, the file already on disk.
# These tests drive the actual shipped hook via subprocess.
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / ".claude" / "hooks" / "verify-citations.sh"

pytestmark = pytest.mark.skipif(
    not HOOK.exists() or shutil.which("jq") is None,
    reason="hook or jq not available")


def _run(payload: dict) -> int:
    proc = subprocess.run(["bash", str(HOOK)], input=json.dumps(payload),
                          text=True, capture_output=True)
    return proc.returncode


def test_small_edit_to_existing_ledger_allowed(tmp_path):
    # A real, substantial ledger already on disk under literature/verified_claims/.
    ledger = tmp_path / "literature" / "verified_claims" / "foo_2020.md"
    ledger.parent.mkdir(parents=True)
    ledger.write_text("# Verified Claims — Foo (2020)\n\n" + ("body line. " * 80)
                      + "\n\n**ID:** c1\n", encoding="utf-8")
    # An Edit that adds one short marker line — the fragment is far below 500 chars.
    payload = {"tool_name": "Edit", "tool_input": {
        "file_path": str(ledger),
        "old_string": "**ID:** c1",
        "new_string": "**ID:** c1\n**Crux-of:** q1 (grounded by #c1)"}}
    assert _run(payload) == 0          # fixed: measured on the on-disk file, not the fragment


def test_tiny_new_stub_still_blocked(tmp_path):
    # A brand-new verified_claims file whose whole content is a tiny stub.
    stub = tmp_path / "literature" / "verified_claims" / "bar_2021.md"
    stub.parent.mkdir(parents=True)
    payload = {"tool_name": "Write", "tool_input": {
        "file_path": str(stub),
        "content": "# Bar 2021\nstub.\n"}}
    assert _run(payload) == 2          # still blocked: a new file's content is the file
