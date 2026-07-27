# === SCRIPT: Coverage gate — cited claims are situated in the argument graph ===
# Addresses the "mechanically green but never modelled" gap: a project can pass every
# gate with an EMPTY graph — citing many claims while never recording a single edge,
# Addresses link, or assessment. This gate,
# OFF by default, asks of a configured project: does each claim a piece of prose
# actually leans on (a cite carrying a #claim ref) have at least one role in the
# argument graph? A claim is "situated" if it is the source (grounding) or target
# of an edge, opts into a sub-question (**Addresses:**), or is the subject/grounding
# of a judgement record. A used claim with NONE of these is logged.
#
# Scope is deliberate: only CLAIM-level cites (Author YEAR #slug) are checked —
# bare cites are about a paper, not a claim — so coverage pairs naturally with
# claim_ids: required (which a configured project already adopts). The pristine
# invariant holds: default off, and with no gated prose there is nothing to check.
# INPUTS : gated prose under content/ (gated_paths:); literature/verified_claims/;
#          content/assessments/_records/; graph_coverage: in config.
# OUTPUTS: [INFO]/[WARNING]/[ERROR]; exit 0 = ok or posture off/warn; 1 = a gap
#          under graph_coverage: required.
# Run    : python3 tools/check_coverage.py
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from check_citations import (extract_citations, gated_prefixes, is_gated,
                             citation_aliases, ledger_path_for, parse_config)
import claim_graph as cg
from assess_record import ASSESS_DIR, RECORDS_DIR_NAME
from check_assessment import load_records

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAIMS_DIR = REPO_ROOT / "literature" / "verified_claims"
CONTENT_DIR = REPO_ROOT / "content"


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_warning(msg: str) -> None:
    print(f"[WARNING] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def coverage_mode(config: dict[str, str]) -> str:
    """graph_coverage: off | warn | required (default off — opt-in)."""
    raw = config.get("graph_coverage", "").split("#", 1)[0].strip().lower()
    return raw if raw in ("off", "warn", "required") else "off"


def situated_nodes(claims_dir: Path, assess_dir: Path) -> set[str]:
    """Every claim node (key:slug) that has a role in the graph: an edge endpoint
    (target or grounding/source), or a judgement record's subject/grounding."""
    nodes: set[str] = set()
    for edge in cg.iter_edges(claims_dir):
        nodes.add(edge.target.render(edge.originating_key))
        if edge.grounding:
            nodes.add(f"{edge.originating_key}:{edge.grounding}")
    for _stem, record, _err in load_records(assess_dir / RECORDS_DIR_NAME):
        if record is None:
            continue
        nodes.add(str(record.get("subject", "")).lower())
        for g in record.get("grounding", []):
            nodes.add(str(g).lower())
    return {n for n in nodes if n}


def gated_prose(content_dir: Path, prefixes: list[str]) -> list[tuple[str, str]]:
    """(path, text) for each gated .md note under content_dir."""
    if not content_dir.is_dir():
        return []
    out: list[tuple[str, str]] = []
    for md in sorted(content_dir.rglob("*.md")):
        if is_gated(str(md.resolve()), prefixes):
            out.append((str(md), md.read_text(encoding="utf-8", errors="ignore")))
    return out


def coverage_problems(claims_dir: Path, content_dir: Path,
                      prefixes: list[str], assess_dir: Path,
                      citation_aliases: dict[str, str] | None = None) -> list[str]:
    """Cited claims (a #claim ref) that resolve but have no role in the graph."""
    situated = situated_nodes(claims_dir, assess_dir)
    seen: set[str] = set()
    problems: list[str] = []
    for path, text in gated_prose(content_dir, prefixes):
        for author, year, claim_id in extract_citations(text):
            if claim_id is None:
                continue                      # bare cite: about the paper, not a claim
            # Two unrelated kinds of alias meet here: a CITE -> ledger map (project-wide,
            # constant) and the addresses of one CLAIM (per cite). They were both called
            # `aliases`, so the second silently replaced the first after the first
            # resolved cite — every later aliased cite then hit a set with no .get().
            ledger = ledger_path_for(claims_dir, author, year, citation_aliases)
            if ledger is None:
                continue                      # missing ledger is check_citations' job
            claim_ids = cg.claim_aliases(ledger, claim_id)
            if not claim_ids:
                continue                      # bad #ref is check_citations Layer 2b's job
            key = ledger.stem.lower()
            nodes = {f"{key}:{a}" for a in claim_ids}
            block = cg.claim_body(ledger, claim_id) or ""
            if nodes & situated or "**Addresses:**" in block:
                continue
            marker = f"{key}:{claim_id}"
            if marker in seen:
                continue
            seen.add(marker)
            problems.append(f"{path}: ({author} {year} #{claim_id}) is cited but the "
                            "claim has no graph role (no edge, **Addresses:**, or "
                            "assessment) — situate it or drop the dependence on it")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Coverage: every cited claim has a role in the argument graph.")
    ap.add_argument("--claims-dir", default=str(CLAIMS_DIR))
    ap.add_argument("--content-dir", default=str(CONTENT_DIR))
    ap.add_argument("--assess-dir", default=str(ASSESS_DIR))
    ap.add_argument("--config", default=str(REPO_ROOT / "ledger.config.md"))
    ap.add_argument("--coverage", choices=("off", "warn", "required"), default=None,
                    help="override the posture (default: graph_coverage: in config)")
    args = ap.parse_args()

    config = parse_config(Path(args.config))
    mode = args.coverage or coverage_mode(config)
    if mode == "off":
        log_info("graph_coverage: off — claim-coverage check skipped.")
        return 0

    problems = coverage_problems(Path(args.claims_dir), Path(args.content_dir),
                                 gated_prefixes(config), Path(args.assess_dir),
                                 citation_aliases(config))
    if not problems:
        log_info("coverage ok — every cited claim has a role in the argument graph.")
        return 0
    message = ("cited claims with no role in the argument graph:\n  - "
               + "\n  - ".join(problems))
    if mode == "required":
        log_error(message)
        return 1
    log_warning(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
