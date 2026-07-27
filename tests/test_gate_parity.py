# Parity guard: pre-commit and CI must ENFORCE the same set of gate scripts, so
# enforcement can't silently diverge between the two points. Only actual invocations
# count (comment headers and `echo "Run: ..."` help-text are skipped), and the set
# spans every tools/ + literature/ gate — not just check_*.py. The corpus-dependent
# verify_quotes is the one declared local-only exception (CI has no corpus to re-hash).
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INVOKE_RE = re.compile(r"(?:tools|literature)/(\w+)\.py")
LOCAL_ONLY = {"verify_quotes"}   # needs the git-ignored corpus → pre-commit only

# The canonical enforced set. Pinning it catches a gate dropped from BOTH points, which
# the pre==CI parity check alone cannot see.
EXPECTED_GATES = {
    "verify_quotes", "check_citations", "check_manifest", "ledger_doctor",
    "check_structure", "check_assessment", "check_coverage", "check_attestation",
    "check_selection", "check_source_flow", "check_units", "check_synthesis", "lint_wiki",
}


def _invoked_gates(path):
    gates = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#") or "echo " in line:
            continue                       # skip comment headers and help-text echoes
        gates.update(INVOKE_RE.findall(line))
    return gates


def test_precommit_runs_exactly_the_canonical_gates():
    assert _invoked_gates(REPO_ROOT / ".githooks" / "pre-commit") == EXPECTED_GATES


def test_precommit_and_ci_enforce_the_same_gates():
    pre = _invoked_gates(REPO_ROOT / ".githooks" / "pre-commit")
    ci = _invoked_gates(REPO_ROOT / ".github" / "workflows" / "ci.yml")
    assert ci - pre == set(), f"gates in CI but not pre-commit: {sorted(ci - pre)}"
    assert pre - ci == LOCAL_ONLY, \
        f"pre-commit-only gates should be exactly {sorted(LOCAL_ONLY)}, got {sorted(pre - ci)}"


def test_no_gate_is_silently_bypassed():
    # Set-parity misses a NEUTRALISED gate — one swallowed by `|| true`/`|| :`, or a
    # pre-commit that no longer aborts on failure. Guard both.
    pre = (REPO_ROOT / ".githooks" / "pre-commit").read_text(encoding="utf-8")
    assert "|| true" not in pre and "|| :" not in pre, "a gate is neutralised with || true / || :"
    assert 'if [ "$fail" -ne 0 ]' in pre and "exit 1" in pre, \
        "pre-commit no longer aborts the commit on an accumulated gate failure"
