#!/usr/bin/env python3
# === SCRIPT: regen_cases — propagate the kernel into every vendored case ===
# INPUTS : the repo root (kernel) and cases/<name>_ledger/ (build outputs)
# OUTPUTS: each case's kernel paths rewritten from the kit; a JSON drift artefact
#          on --json; nothing written under --check.
#
# Development edits the kernel, never a case. A case is a build output: change
# tools/, run this, and all five update identically. A hand-edit under a
# regenerated path is a defect this script overwrites.
#
# Run:
#   python3 dev/regen_cases.py --check          # report drift, write nothing, exit 1 if any
#   python3 dev/regen_cases.py                  # regenerate every case
#   python3 dev/regen_cases.py --json out.json  # machine-readable drift artefact
#
# tests/ is OPT-IN (--with-tests) and does not currently succeed: several kit tests
# assert kit-level facts that are false inside a case (the config template's posture
# list, the shipped-case inventory), so vendoring them ships failures. The portability
# filter is derived, not listed, but the residue needs per-test triage first.
#
# Repo hygiene, NOT one of the 13 integrity gates: it lives in dev/, ships to no
# subject project, and adds no enforcement.
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = REPO_ROOT / "cases"

# Machinery — identical in every case, regenerated from the kit.
KERNEL_DIRS = ("tools", "spec", ".githooks", ".github", ".claude")
KERNEL_FILES = ("AGENTS.md", "DEPENDENCIES.md", "environment.yml", ".gitignore")
# The intake scripts only; literature/verified_claims and literature/units are the
# case's own evidence and must never be written.
LITERATURE_GLOBS = ("literature/*.py", "literature/*.sh")

# Evidence and configuration — the case's own. A write here is a bug, so the guard
# is an assertion rather than a convention.
CASE_OWNED_PREFIXES = (
    "content/",
    "literature/verified_claims/",
    "literature/units/",
    "ledger.config.md",
    "README.md",
    "baseline_research_raw.md",
)

# Kit-level tools that no subject project runs: they build or inspect THIS repo's
# submission bundle, or drive verbs still unadvertised in the CLI. Vendoring them
# would ship machinery a case has no use for.
KIT_ONLY = frozenset({
    "tools/build_submission.py",
    "tools/corpus_manifest.py",
    "tools/config_edit.py",
    "tools/init_plan.py",
    "tools/init_apply.py",
})

# Modules that live at the kit root or in dev/, so a case cannot import them.
NON_VENDORED_MODULES = frozenset({"ledger_cli", "regen_cases", "check_comments"})

_IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_]\w*)", re.M)


def unportable_reason(test_path: Path, vendored: set[str]) -> str | None:
    """Why this kit test cannot run inside a case, or None if it can.

    Derived, not listed. A hand-maintained exclusion list goes stale the moment a
    tool moves in or out of KIT_ONLY, and the failure it lets through is a vendored
    test that cannot even be collected. `vendored` holds the module names the case
    will carry."""
    text = test_path.read_text(encoding="utf-8", errors="ignore")
    if "cases/" in text or "CASES_DIR" in text:
        return "reads cases/"
    for mod in _IMPORT_RE.findall(text):
        if mod in NON_VENDORED_MODULES:
            return f"imports {mod}"
        if mod in _kit_module_names() and mod not in vendored:
            return f"imports non-vendored {mod}"
    return None


def _kit_module_names() -> set[str]:
    """Importable module stems the kit ships under tools/ and literature/."""
    return {Path(p).stem for p in _version_controlled()
            if p.endswith(".py") and p.split("/", 1)[0] in ("tools", "literature")
            and p.count("/") == 1}


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_warning(msg: str) -> None:
    print(f"[WARNING] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def case_dirs() -> list[Path]:
    """Every vendored case, sorted. Empty when cases/ is absent."""
    if not CASES_DIR.is_dir():
        return []
    return sorted(p for p in CASES_DIR.iterdir() if p.is_dir() and (p / "ledger.config.md").is_file())


def _version_controlled() -> set[str]:
    """The repo's version-controlled paths, as posix strings.

    The kernel is what is committed, not what happens to sit on disk. Reading the
    filesystem instead would copy OS cruft (.DS_Store) and uncommitted in-flight
    work into all five cases at once."""
    out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT,
                         capture_output=True, text=True, check=True)
    return set(out.stdout.split())


def kernel_sources(include_tests: bool = True) -> list[Path]:
    """Kernel paths as repo-relative files, sorted; committed files only."""
    tracked = _version_controlled()
    wanted: set[str] = set()
    for path in tracked:
        if path in KIT_ONLY:
            continue
        head = path.split("/", 1)[0]
        if head in KERNEL_DIRS or path in KERNEL_FILES:
            wanted.add(path)
        elif path.startswith("literature/") and path.endswith((".py", ".sh")) \
                and path.count("/") == 1:
            wanted.add(path)
    if include_tests:
        # Tests are resolved after the tools, because portability is decided against
        # the module set the case will actually carry.
        vendored = {Path(p).stem for p in wanted if p.endswith(".py")}
        for path in sorted(tracked):
            if not (path.startswith("tests/") and path.endswith(".py")
                    and path.count("/") == 1):
                continue
            if unportable_reason(REPO_ROOT / path, vendored) is None:
                wanted.add(path)
    return sorted(Path(p) for p in wanted)


def _is_case_owned(rel: Path) -> bool:
    s = rel.as_posix()
    return any(s == p.rstrip("/") or s.startswith(p) for p in CASE_OWNED_PREFIXES)


def plan_case(case: Path, sources: list[Path], scan_tests: bool = True) -> dict:
    """What regenerating this case would do, without touching disk.

    Returns {"create": [...], "update": [...], "same": n, "orphan": [...]}.
    An orphan is a file under a kernel directory in the case with no kit
    counterpart; it is reported, never removed — this script only ever writes."""
    create: list[str] = []
    update: list[str] = []
    same = 0
    for rel in sources:
        assert not _is_case_owned(rel), f"kernel path collides with case-owned: {rel}"
        src, dst = REPO_ROOT / rel, case / rel
        if not dst.exists():
            create.append(rel.as_posix())
        elif src.read_bytes() != dst.read_bytes():
            update.append(rel.as_posix())
        else:
            same += 1

    expected = {r.as_posix() for r in sources}
    orphan: list[str] = []
    # Only scan directories this run actually owns; scanning tests/ while leaving it
    # alone would report every one of the case's tests as an orphan.
    for d in KERNEL_DIRS + (("tests",) if scan_tests else ()):
        root = case / d
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*")):
            if not p.is_file() or "__pycache__" in p.parts:
                continue
            rel = p.relative_to(case).as_posix()
            if rel not in expected:
                orphan.append(rel)
    return {"case": case.name, "create": create, "update": update,
            "same": same, "orphan": orphan}


def apply_case(case: Path, sources: list[Path]) -> list[Path]:
    """Write every kernel file into the case. Returns the paths written.

    Only ever creates or overwrites a kernel path; nothing is removed, so a file
    the kit no longer ships stays put and is reported as an orphan instead."""
    written: list[Path] = []
    for rel in sources:
        assert not _is_case_owned(rel), f"refusing to write case-owned path: {rel}"
        src, dst = REPO_ROOT / rel, case / rel
        if dst.exists() and src.read_bytes() == dst.read_bytes():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        written.append(dst)
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Propagate the kernel into every vendored case.")
    ap.add_argument("--check", action="store_true",
                    help="report drift, write nothing, exit 1 if any case is stale")
    ap.add_argument("--json", metavar="PATH", help="write the drift artefact as JSON")
    ap.add_argument("--with-tests", action="store_true",
                    help="also regenerate each case's tests/ (see the caveat below)")
    args = ap.parse_args(argv)

    cases = case_dirs()
    if not cases:
        log_error("no cases found under cases/ — nothing to regenerate")
        return 2

    sources = kernel_sources(include_tests=args.with_tests)
    log_info(f"kernel: {len(sources)} file(s) · cases: {len(cases)}")
    if args.with_tests:
        log_info(f"tests/: {len(TESTS_NOT_PORTABLE)} kit-only test(s) excluded (they read cases/)")

    plans = [plan_case(c, sources, scan_tests=args.with_tests) for c in cases]
    drift = 0
    for p in plans:
        n = len(p["create"]) + len(p["update"])
        drift += n
        log_info(f"{p['case']}: {len(p['create'])} new · {len(p['update'])} changed · "
                 f"{p['same']} identical · {len(p['orphan'])} orphan")
        for rel in p["create"][:10]:
            log_info(f"    new     {rel}")
        for rel in p["update"][:10]:
            log_info(f"    changed {rel}")
        if p["orphan"]:
            log_warning(f"{p['case']}: {len(p['orphan'])} file(s) under a kernel path with no kit "
                        f"counterpart — reported, never removed: {p['orphan'][:5]}")

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"kernel_files": len(sources), "cases": plans},
                                  indent=2, sort_keys=True) + "\n", encoding="utf-8")
        log_info(f"wrote {out.resolve()}")

    if args.check:
        if drift:
            log_error(f"{drift} file(s) stale across {len(cases)} case(s) — run "
                      f"python3 dev/regen_cases.py")
            return 1
        log_info("every case matches the kernel")
        return 0

    total: list[Path] = []
    for case in cases:
        total += apply_case(case, sources)
    if total:
        log_info(f"wrote {len(total)} file(s):")
        for p in total[:20]:
            log_info(f"    {p.resolve()}")
        if len(total) > 20:
            log_info(f"    … and {len(total) - 20} more")
    else:
        log_info("nothing to write — every case already matches the kernel")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
