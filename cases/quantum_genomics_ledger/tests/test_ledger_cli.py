# Tests for the ledger CLI dispatcher (ergonomics). No subprocess: we exercise the
# pure routing/profile/demo-wiring logic and assert the dispatch table is consistent
# with the tools actually on disk.
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import ledger_cli as lc


def test_usage_on_no_args(capsys):
    assert lc.main([]) == 0
    assert "ledger" in capsys.readouterr().out


def test_unknown_command_errors():
    assert lc.main(["definitely-not-a-command"]) == 2


def test_dispatch_targets_all_exist():
    # Every subcommand maps to a real tool file in the kit.
    missing = [rel for rel in lc.DISPATCH.values() if not (REPO_ROOT / rel).is_file()]
    assert missing == []


def test_demo_steps_reference_known_commands():
    assert all(cmd in lc.DISPATCH for _label, cmd, _extra in lc.DEMO_STEPS)


def test_profiles_list(capsys):
    assert lc.main(["profiles"]) == 0
    out = capsys.readouterr().out
    assert "submission" in out and "pristine" in out


def test_profiles_named_prints_postures(capsys):
    assert lc.main(["profiles", "submission"]) == 0
    out = capsys.readouterr().out
    assert "selection_audit" in out and "required" in out


def test_profiles_unknown_errors():
    assert lc.main(["profiles", "no-such-profile"]) == 2


def test_every_profile_sets_the_same_postures():
    keys = [set(p) for p in lc.PROFILES.values()]
    assert all(k == keys[0] for k in keys)      # no profile silently omits a posture
