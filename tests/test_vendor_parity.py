# Full-kernel cases must match the root kernel; content-only cases must contain no kernel.
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KIT_TOOLS = REPO_ROOT / "tools"
CASES_DIR = REPO_ROOT / "cases"

FULL_KERNEL_CASES = {
    "covid_debate_ledger",
    "covid_origins_ledger",
    "eggs_cholesterol_ledger",
    "lhc_safety_ledger",
    "quantum_genomics_ledger",
}
CONTENT_ONLY_CASES: set = set()

# Kit tools no case vendors: the CLI's own support modules (no case ships a ledger_cli.py,
# and no vendored tool imports them), the kit-level bundle builder, and untracked local work.
CLI_ONLY = {"config_edit.py", "init_plan.py", "init_apply.py", "audit_pack.py",
            "build_submission.py", "corpus_manifest.py"}


def _cases():
    return sorted(p.name for p in CASES_DIR.iterdir() if p.is_dir())


def _kernel(case: str):
    return sorted((CASES_DIR / case / "tools").glob("*.py"))


def test_every_case_is_declared_full_kernel_or_content_only():
    assert set(_cases()) == FULL_KERNEL_CASES | CONTENT_ONLY_CASES
    assert not (FULL_KERNEL_CASES & CONTENT_ONLY_CASES)


def test_full_kernel_cases_match_root():
    drifted = []
    for case in sorted(FULL_KERNEL_CASES):
        for tool in _kernel(case):
            root = KIT_TOOLS / tool.name
            here = tool.relative_to(REPO_ROOT)
            if not root.is_file():
                drifted.append(f"{here}: the kit has no such tool")
            elif root.read_bytes() != tool.read_bytes():
                drifted.append(f"{here}: differs from tools/{tool.name} — "
                               f"`cp tools/{tool.name} {here}`")
    assert not drifted, drifted


def test_full_kernel_cases_carry_every_kit_tool():
    expected = {t.name for t in KIT_TOOLS.glob("*.py")} - CLI_ONLY
    missing = {case: sorted(expected - {t.name for t in _kernel(case)})
               for case in sorted(FULL_KERNEL_CASES)}
    assert not any(missing.values()), {k: v for k, v in missing.items() if v}


def test_content_only_cases_vendor_no_kernel():
    carried = {case: sorted(t.name for t in _kernel(case))
               for case in sorted(CONTENT_ONLY_CASES)}
    assert not any(carried.values()), {k: v for k, v in carried.items() if v}
