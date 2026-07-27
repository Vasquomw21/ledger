# === SCRIPT: Faithfulness probe — the adversarial-faithfulness worklist ===
# Purpose: the read-only half of the adversarial-faithfulness mechanism. The
#          verbatim gate proves a quote is real; it cannot prove the quote is used
#          FAITHFULLY (a real sentence can be read out of context to "support" an
#          inference it does not). This tool enumerates every supports/rebuts edge,
#          shows the grounding quote each rests on and the inference it asserts, and
#          reports whether that inference has been adversarially reviewed — i.e.
#          whether a `kind: faithfulness` record disputes the edge's aptness record.
#
#          It does NO judging itself (the kit ships no model — the adversarial read
#          is the agent/curate layer's job, kept agent-neutral). It prints the
#          worklist + the exact assess_record.py command to FILE a dispute, so a
#          reviewer (an LLM via skill-ledger-curate / AGENTS.md, or a human) drives
#          the actual judgement. ASSIST, never a gate: most edges are faithful, so
#          there is no posture that REQUIRES a dispute — a dispute is filed only
#          where a genuine gap is found.
# INPUTS : literature/verified_claims/*.md (edges + quotes);
#          content/assessments/_records/*.assess.json (existing faithfulness records).
# OUTPUTS: [INFO] worklist to stdout; always exit 0 (read-only, no verdict).
# Run    : python3 tools/faithfulness_probe.py
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import claim_graph as cg
from assess_record import CLAIMS_DIR, ASSESS_DIR, RECORDS_DIR_NAME
from check_assessment import (ASSESSED_EDGE_TYPES, covering_record,
                              load_records, valid_edge_coverage)


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def disputed_record_ids(records_dir: Path) -> set[str]:
    """Record ids that at least one faithfulness record contests."""
    disputed: set[str] = set()
    for _stem, rec, _err in load_records(records_dir):
        if rec and rec.get("kind") == "faithfulness":
            disputed.update(str(d).lower() for d in (rec.get("disputes") or []))
    return disputed


def passed_record_ids(records_dir: Path) -> set[str]:
    """Edge record ids that at least one faithfulness-pass record reviews."""
    passed: set[str] = set()
    for _stem, rec, _err in load_records(records_dir):
        if rec and rec.get("kind") == "faithfulness-pass":
            passed.update(str(r).lower() for r in (rec.get("reviews") or []))
    return passed


def _quote(claims_dir: Path, key: str, slug: str | None) -> str:
    if not slug:
        return ""
    ledger = cg.ledger_for_key(claims_dir, key)
    return cg.claim_quote(ledger, slug) if ledger else ""


def probe(claims_dir: Path, assess_dir: Path) -> int:
    edges = [e for e in cg.iter_edges(claims_dir)
             if e.edge_type in ASSESSED_EDGE_TYPES]
    if not edges:
        log_info("no supports/rebuts edges yet — nothing to adversarially review.")
        return 0
    disputed = disputed_record_ids(assess_dir / RECORDS_DIR_NAME)
    passed = passed_record_ids(assess_dir / RECORDS_DIR_NAME)
    external_edge_records = valid_edge_coverage(assess_dir / RECORDS_DIR_NAME, claims_dir)
    disputed_count = passed_count = unreviewed = 0
    log_info(f"adversarial-faithfulness worklist — {len(edges)} supports/rebuts "
             "edge(s). For each, ask: does the grounding QUOTE actually warrant "
             "this inference, or is it read out of context?\n")
    for e in edges:
        src = f"{e.originating_key}:{e.grounding or '?'}"
        tgt = e.target.render(e.originating_key)
        # Same covering rule as the gate — a dangling/wrong-kind [rec:] is not coverage.
        rec_id = covering_record(tgt, src, e.rec, external_edge_records)
        quote = _quote(claims_dir, e.originating_key, e.grounding)
        print(f"  {src} --{e.edge_type}--> {tgt}")
        if quote:
            print(f"    grounding quote: \"{quote}\"")
        if rec_id is None:
            print("    status: NO edge aptness record — file a kind=edge record "
                  "(edge_assessments) before it can be faithfulness-disputed.\n")
            continue
        if rec_id in disputed:
            disputed_count += 1
            print(f"    status: REVIEWED — a faithfulness record disputes [{rec_id}].\n")
        elif rec_id in passed:
            passed_count += 1
            print(f"    status: REVIEWED — a faithfulness-pass record reviews [{rec_id}].\n")
        else:
            unreviewed += 1
            print(f"    status: UNREVIEWED. If the quote does NOT warrant this "
                  f"{e.edge_type}, file a dispute:")
            print(f"      python3 tools/assess_record.py --write --kind faithfulness \\\n"
                  f"        --id {rec_id}-faithfulness --subject {tgt} \\\n"
                  f"        --grounding {src} --disputes {rec_id} \\\n"
                  f"        --span \"<verbatim substring read unfaithfully>\" --date YYYYMMDD\n")
    log_info(f"summary: {disputed_count} reviewed (disputed), {passed_count} reviewed "
             f"(pass), {unreviewed} with an aptness record but no adversarial review yet.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="List supports/rebuts edges and their faithfulness-review state.")
    ap.add_argument("--claims-dir", default=str(CLAIMS_DIR))
    ap.add_argument("--assess-dir", default=str(ASSESS_DIR))
    args = ap.parse_args()
    return probe(Path(args.claims_dir), Path(args.assess_dir))


if __name__ == "__main__":
    sys.exit(main())
