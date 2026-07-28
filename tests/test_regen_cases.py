# Tests for dev/regen_cases.py — the kernel-to-case generator. A case is a build
# output, so the properties that matter are: it writes only kernel paths, it never
# writes a case's own evidence, and running it twice changes nothing.
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "dev"))
import regen_cases as rc  # noqa: E402


def test_kit_only_tools_are_not_kernel():
    """A tool that builds this repo's own submission bundle has no use in a case."""
    sources = {p.as_posix() for p in rc.kernel_sources()}
    assert not (sources & rc.KIT_ONLY)


def test_kernel_is_version_controlled_only():
    """OS cruft and uncommitted work must not reach five cases at once."""
    sources = {p.as_posix() for p in rc.kernel_sources()}
    tracked = rc._version_controlled()
    assert sources <= tracked
    assert not any(p.endswith(".DS_Store") for p in sources)


def test_case_owned_paths_are_never_kernel():
    """Evidence and configuration are the case's own; the generator must not
    produce a plan that would overwrite them."""
    for rel in rc.kernel_sources():
        assert not rc._is_case_owned(rel), rel


def test_unportable_tests_are_excluded():
    """A kit test that reads cases/, or imports a module the case will not carry,
    cannot even be collected inside a case."""
    vendored = {p.stem for p in rc.kernel_sources(include_tests=False) if p.suffix == ".py"}
    for path in rc.kernel_sources(include_tests=True):
        if path.parts[0] == "tests":
            assert rc.unportable_reason(REPO_ROOT / path, vendored) is None, path


def test_unportable_reason_catches_both_causes(tmp_path):
    """Derived, not listed: the rule must fire on a cases/ read and on an import of
    a kit-only module, since a list goes stale when a tool changes side."""
    vendored = {"repro", "postures"}
    reads_cases = tmp_path / "test_a.py"
    reads_cases.write_text("p = Path('cases/x')\n", encoding="utf-8")
    assert rc.unportable_reason(reads_cases, vendored) == "reads cases/"

    imports_root = tmp_path / "test_b.py"
    imports_root.write_text("import ledger_cli\n", encoding="utf-8")
    assert rc.unportable_reason(imports_root, vendored) == "imports ledger_cli"

    portable = tmp_path / "test_c.py"
    portable.write_text("import repro\n", encoding="utf-8")
    assert rc.unportable_reason(portable, vendored) is None


def test_no_tests_flag_drops_the_tests_tree():
    with_tests = {p for p in rc.kernel_sources(include_tests=True) if p.parts[0] == "tests"}
    without = {p for p in rc.kernel_sources(include_tests=False) if p.parts[0] == "tests"}
    assert with_tests and not without


def _fake_case(tmp_path: Path) -> Path:
    """A case carrying one stale kernel file and one file the generator must not touch."""
    case = tmp_path / "fake_ledger"
    (case / "tools").mkdir(parents=True)
    (case / "content").mkdir(parents=True)
    (case / "ledger.config.md").write_text("project_state: pristine\n", encoding="utf-8")
    (case / "tools" / "repro.py").write_text("stale\n", encoding="utf-8")
    (case / "content" / "inquiry.md").write_text("case evidence\n", encoding="utf-8")
    return case


def test_plan_classifies_create_update_and_same(tmp_path):
    case = _fake_case(tmp_path)
    sources = [Path("tools/repro.py"), Path("tools/postures.py")]
    plan = rc.plan_case(case, sources, scan_tests=False)
    assert "tools/repro.py" in plan["update"]      # present but stale
    assert "tools/postures.py" in plan["create"]   # absent
    assert plan["same"] == 0


def test_apply_writes_kernel_and_leaves_case_evidence_alone(tmp_path):
    case = _fake_case(tmp_path)
    before = (case / "content" / "inquiry.md").read_bytes()
    written = rc.apply_case(case, [Path("tools/repro.py")])
    assert written == [case / "tools" / "repro.py"]
    assert (case / "tools" / "repro.py").read_bytes() == \
        (REPO_ROOT / "tools" / "repro.py").read_bytes()
    assert (case / "content" / "inquiry.md").read_bytes() == before


def test_apply_is_idempotent(tmp_path):
    """A second run writes nothing — otherwise 'regenerate' would churn the diff."""
    case = _fake_case(tmp_path)
    sources = [Path("tools/repro.py"), Path("tools/postures.py")]
    assert rc.apply_case(case, sources)
    assert rc.apply_case(case, sources) == []
    assert rc.plan_case(case, sources, scan_tests=False)["same"] == len(sources)


def test_apply_refuses_a_case_owned_path(tmp_path):
    """The guard is an assertion, not a convention: a write here is a bug."""
    case = _fake_case(tmp_path)
    with pytest.raises(AssertionError):
        rc.apply_case(case, [Path("ledger.config.md")])


def test_orphans_are_reported_never_removed(tmp_path):
    """A file the kit no longer ships stays on disk and is named, so removal is the
    author's deliberate act."""
    case = _fake_case(tmp_path)
    stray = case / "tools" / "gone_from_kit.py"
    stray.write_text("x\n", encoding="utf-8")
    plan = rc.plan_case(case, [Path("tools/repro.py")], scan_tests=False)
    assert "tools/gone_from_kit.py" in plan["orphan"]
    rc.apply_case(case, [Path("tools/repro.py")])
    assert stray.is_file()
