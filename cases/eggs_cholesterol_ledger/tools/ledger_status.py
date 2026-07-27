# === SCRIPT: Ledger status — the operator map (which guarantees are active?) ===
# The kit has several gates, modes, and postures that interact. This read-only tool
# answers, at a glance, "what is actually enforced here right now?": the project state +
# strictness, every posture and whether it BLOCKS or merely advises, the
# corpus/graph/assessment counts, and the semantic-review age. It changes nothing and
# always exits 0 — it is a dashboard, not a gate.
# INPUTS : ledger.config.md, literature/verified_claims/ (+ _runs/), content/.
# OUTPUTS: a status report on stdout; exit 0 always.
# Run    : python3 tools/ledger_status.py
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from check_citations import claim_mode, numeric_mode, parse_config
from check_manifest import provenance_mode, read_frontmatter
from check_structure import parse_inquiry_qids, structure_mode
from check_assessment import (ASSESSED_EDGE_TYPES, assessment_mode,
                              edge_assessment_mode, edge_assessment_problems,
                              load_records, valid_edge_coverage)
from check_coverage import coverage_mode
from check_attestation import attestation_mode
from check_selection import selection_mode, parse_register
from check_source_flow import parse_flow, source_flow_mode
from check_units import units_mode
from check_synthesis import synthesis_mode
from ledger_doctor import (diagnose, semantic_max_age, semantic_mode,
                           semantic_staleness_problems, strict_mode)
from postures import POSTURES, POSTURE_BLOCK
import claim_graph as cg

REPO_ROOT = Path(__file__).resolve().parents[1]


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def _blocking(mode: str, block_value: str = "required") -> str:
    """How a posture value reads operationally."""
    if mode in ("off", "ignore"):
        return "off"
    if mode == block_value:
        return "BLOCKING"
    return "advisory"


def _count_ledgers(claims_dir: Path) -> tuple[int, int]:
    """(ledgers, stamped) — a ledger is stamped if it carries a body_sha256."""
    if not claims_dir.is_dir():
        return 0, 0
    ledgers = [p for p in claims_dir.glob("*.md") if p.stem != "TEMPLATE"]
    stamped = sum(1 for p in ledgers if read_frontmatter(p).get("body_sha256"))
    return len(ledgers), stamped


def build_report(repo_root: Path) -> list[str]:
    config = parse_config(repo_root / "ledger.config.md")
    claims_dir = repo_root / "literature" / "verified_claims"
    runs_dir = claims_dir / "_runs"
    assess_dir = repo_root / "content" / "assessments"
    inquiry = repo_root / "content" / "inquiry.md"

    state, _problems = diagnose(config, repo_root)
    strict = strict_mode(config, repo_root)

    ledgers, stamped = _count_ledgers(claims_dir)
    run_records = len(list(runs_dir.glob("*.run.json"))) if runs_dir.is_dir() else 0
    signed = len(list(runs_dir.glob("*.run.json.sig"))) if runs_dir.is_dir() else 0
    edges = sum(1 for _ in cg.iter_edges(claims_dir))
    records = [r for _s, r, _e in load_records(assess_dir / "_records") if r]
    records_by_id = {str(r.get("id", "")).lower(): r for r in records}
    record_ids = set(records_by_id)
    graph_edges = list(cg.iter_edges(claims_dir))
    assessed_edge_count = sum(1 for e in graph_edges if e.edge_type in ASSESSED_EDGE_TYPES)
    unassessed_edge_count = len(edge_assessment_problems(
        claims_dir, record_ids, valid_edge_coverage(assess_dir / "_records", claims_dir)))
    faithfulness_records = sum(1 for r in records if r.get("kind") == "faithfulness")
    faithfulness_passes = sum(1 for r in records if r.get("kind") == "faithfulness-pass")
    disputed_records = {
        str(d).lower()
        for r in records
        for d in (r.get("disputes") or [])
    }
    calib = sum(1 for p in assess_dir.glob("*.md")
                if "calibrated_confidence" in read_frontmatter(p)) \
        if assess_dir.is_dir() else 0
    qids = len(parse_inquiry_qids(inquiry))
    reg = parse_register(repo_root / "content" / "source_register.md")
    flow = parse_flow(repo_root / "content" / "source_flow.md")

    sem_problems = semantic_staleness_problems(repo_root, config)
    sem_line = "stale/missing" if sem_problems else f"fresh (< {semantic_max_age(config)}d)"

    # Each posture key -> the callable that reads its current mode from config. The key
    # set + block-value come from the canonical registry (tools/postures.py), so the
    # dashboard can't drift out of sync with the config template or the judge pack.
    readers = {
        "claim_ids": claim_mode, "numeric_citations": numeric_mode,
        "provenance": provenance_mode, "structure_layer": structure_mode,
        "assessment_layer": assessment_mode, "graph_coverage": coverage_mode,
        "edge_assessments": edge_assessment_mode, "selection_audit": selection_mode,
        "source_flow": source_flow_mode, "units_layer": units_mode,
        "synthesis_claims": synthesis_mode, "semantic_health": semantic_mode,
        "attestation": attestation_mode,
    }
    postures = [(key, readers[key](config), POSTURE_BLOCK[key])
                for key, _label, _bv in POSTURES]

    out: list[str] = []
    out.append(f"Ledger status — {repo_root}")
    out.append(f"  project state : {state}")
    out.append(f"  strict mode   : {'strict (configured)' if strict else 'lenient'}")
    if state == "configured":
        out.append("  note          : configured ⟹ strict — the five strict "
                    "postures must be 'required'/'block' or every gate fails.")
    out.append("  postures:")
    width = max(len(k) for k, _v, _b in postures)
    for key, value, block_value in postures:
        out.append(f"    {key.ljust(width)} : {value}  [{_blocking(value, block_value)}]")
    out.append("  corpus / graph:")
    out.append(f"    ledgers            : {ledgers} ({stamped} stamped)")
    out.append(f"    run-records        : {run_records} ({signed} signed)")
    out.append(f"    claim-graph edges  : {edges}")
    out.append(f"    supports/rebuts    : {assessed_edge_count} "
               f"({unassessed_edge_count} lacking assessment record)")
    out.append(f"    judgement records  : {len(records)} ({calib} calibration note(s))")
    out.append(f"    faithfulness       : {faithfulness_records} dispute record(s), "
               f"{faithfulness_passes} pass record(s), "
               f"{len(disputed_records)} disputed judgement(s)")
    out.append(f"    sub-questions      : {qids}")
    out.append(f"    source register    : {len(reg['sources'])} source(s), "
               f"{len(reg['positions'])} position(s), {len(reg['gaps'])} known gap(s)")
    out.append(f"    source flow        : {len(flow['searches'])} search(es), "
               f"{len(flow['included'])} included, {len(flow['excluded'])} excluded, "
               f"{len(flow['unavailable'])} unavailable")
    out.append(f"    semantic review    : {sem_line}")
    blocking = [k for k, v, b in postures if _blocking(v, b) == "BLOCKING"]
    out.append("  blocking postures: " + (", ".join(blocking) or "(none — lenient)")
               + "  [+ citation-coverage always blocks]")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only Ledger status dashboard.")
    ap.add_argument("--repo-root", default=str(REPO_ROOT))
    args = ap.parse_args()
    for line in build_report(Path(args.repo_root)):
        log_info(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
