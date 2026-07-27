# Fixtures for dev/check_comments.py, and the sweep that makes the rule repository-wide
# rather than one agent's habit.
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "dev" / "check_comments.py"
sys.path.insert(0, str(REPO_ROOT / "dev"))

import check_comments as cc

PLAN_REFERENCES = [
    "# M5.3 de-vendors four cases.",
    "# Re-vendoring to make this file pass during M5.3 would undo M5.3.",
    "# C6b builds the plan; this module writes it.",
    "# --- C1: the step registry ---",
    "# Phase 2 promotes these to stable cause codes.",
    "# The roadmap defers this to a later pass.",
    "# Deferred to the next milestone.",
    "# The point of C2: gates are reachable through inspect.",
    "# Read-only boundary: mutation arrives in C5 behind --dry-run.",
    "# C4 adds the config namespace.",
    "# Step 2 of the handoff adds the postures.",
    "# Fixed in (Issue 214).",
    "# Kept after the second-pass review.",
]

CONTRACTS = [
    "# Full-kernel cases must match the root kernel; content-only cases carry no kernel.",
    "# An atomic replace swaps the directory ENTRY: a symlinked target would become a\n"
    "# regular file and be lost.",
    "# Enter finishes the list; Ctrl-C abandons the command.",
    "# The temp is a SIBLING so the replace stays on one filesystem.",
    "# 3+ authors, with or without the Oxford comma - MUST precede the two-author pattern",
    "# Mirrors tools/postures.py rather than importing it: the CLI must not depend on the\n"
    "# TARGET project's kernel, which may be an older vendored copy.",
    "# Broken projects remain lenient even when project_state says configured.",
]


def _findings(text, python=True):
    return cc.findings(text, python=python)


def test_every_plan_reference_is_caught():
    missed = [text for text in PLAN_REFERENCES if not _findings(text)]
    assert not missed, missed


def test_no_contract_is_flagged():
    flagged = [text for text in CONTRACTS if _findings(text)]
    assert not flagged, flagged


def test_code_is_never_read_only_comments_and_docstrings():
    # The whole reason for tokenize: these words are legitimate in identifiers, strings and
    # data, and a raw-text scanner would fail every one of them.
    code = (
        'roadmap = load("roadmap.md")\n'
        'MILESTONE_HEADING = "## Phase 2"\n'
        'def milestone_for(c6b):\n'
        '    return {"roadmap": c6b, "m5.3": "M5.3"}\n'
    )
    assert _findings(code) == []


def test_a_docstring_naming_a_plan_is_caught():
    assert _findings('def f():\n    """Superseded by M5.3."""\n')


def test_a_comment_naming_a_plan_is_caught_inside_real_code():
    assert _findings('def f():\n    # C6b builds the plan.\n    return 1\n')


def test_a_fragment_that_cannot_parse_still_reads_its_comments():
    # What the write-time hook passes: an edit's replacement text, not a whole module.
    fragment = "    # M5.3 de-vendors four cases.\n        return x)\n"
    assert _findings(fragment)


def test_shell_comments_are_read():
    assert _findings("# Phase 2 adds the gate.\necho hi\n", python=False)
    assert _findings('echo "the roadmap says so"\n', python=False) == []


def test_the_checker_does_not_police_its_own_watchlist():
    assert cc.exempt("dev/check_comments.py")
    assert cc.exempt(REPO_ROOT / "tests" / "test_comment_discipline.py")
    assert not cc.exempt("tools/init_plan.py")


def _run(*args, stdin=None):
    return subprocess.run([sys.executable, str(CHECKER), *args], input=stdin,
                          cwd=REPO_ROOT, capture_output=True, text=True)


def test_the_command_exits_1_on_a_finding(tmp_path):
    # The exit code is the ONLY thing pre-commit and the write-time hook read: a checker
    # that found everything and still exited 0 would leave both dead while these pass.
    bad = tmp_path / "bad.py"
    bad.write_text("# C6b builds the plan.\n", encoding="utf-8")
    result = _run(str(bad))
    assert result.returncode == 1
    assert "bad.py:1" in result.stdout


def test_the_command_exits_0_on_a_clean_file(tmp_path):
    good = tmp_path / "good.py"
    good.write_text("# The temp is a SIBLING so the replace stays on one filesystem.\n",
                    encoding="utf-8")
    assert _run(str(good)).returncode == 0


def test_the_stdin_fragment_path_exits_1_on_a_finding():
    assert _run("--stdin", "--python", stdin="# M5.3 will de-vendor four cases.\n"
                ).returncode == 1
    assert _run("--stdin", "--python", stdin="x = 1\n").returncode == 0


def test_the_tracked_tree_is_clean():
    # The point of an agent-neutral checker: this fails for anyone — Claude, Codex, a
    # human, CI — not only at one editor's write-time hook.
    tracked = subprocess.run(["git", "ls-files", "*.py", "*.sh"], cwd=REPO_ROOT,
                             capture_output=True, text=True, check=True).stdout.split()
    result = _run(*tracked)
    assert result.returncode == 0, result.stdout
