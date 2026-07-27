# === SCRIPT: Build the verified-claim graph — derived, interrogable artifact ===
# Read-only emitter (like lint_wiki): it scans the in-band claim-graph edges, the
# inquiry question tree, and the judgement records, and emits content/graph.json —
# the single interrogable view of the argument (nodes, edges, sub-questions,
# assessments, and the DERIVED findings: double-count + superseded). `--mermaid`
# renders the same graph for a human. Both are DERIVED: never hand-edited, and
# git-ignored — a fresh clone rebuilds them. It changes no source of truth and
# exits 0 (a dashboard, not a gate); an empty graph yields empty arrays.
# INPUTS : literature/verified_claims/ (edges + qid refs + records via the gates),
#          content/inquiry.md, content/assessments/_records/.
# OUTPUTS: content/graph.json (default) or --stdout; --mermaid prints a diagram.
# Run    : python3 tools/build_graph.py            # write content/graph.json
#          python3 tools/build_graph.py --mermaid  # print a Mermaid diagram
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import claim_graph as cg
from check_structure import parse_inquiry_qids, parse_qid_refs
from check_assessment import (ASSESSED_EDGE_TYPES, covering_record,
                              double_count_findings, load_correlation_kinds,
                              load_records)
from assess_record import RECORDS_DIR_NAME

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAIMS_DIR = REPO_ROOT / "literature" / "verified_claims"
CONTENT_DIR = REPO_ROOT / "content"


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def build_graph(claims_dir: Path, inquiry_path: Path, assess_dir: Path) -> dict:
    """Assemble the derived graph dict from the three in-band sources."""
    nodes: set[str] = set()
    edges: list[dict] = []
    superseded: list[str] = []
    for e in cg.iter_edges(claims_dir):
        source = f"{e.originating_key}:{e.grounding}" if e.grounding else None
        target = e.target.render(e.originating_key)
        target_res = cg.resolve(e.target, e.originating_key, claims_dir)
        edges.append({
            "type": e.edge_type, "source": source, "target": target,
            "grounding": e.grounding, "target_resolved": target_res.exists,
            "rec": e.rec, "from_ledger": e.originating_key, "line": e.line_no,
        })
        if source:
            nodes.add(source)
        nodes.add(target)
        if e.edge_type == "supersedes":
            superseded.append(target)

    addresses = [{"ledger": r.origin, "field": r.field, "qid": r.qid}
                 for r in parse_qid_refs(claims_dir)]

    records = [rec for _stem, rec, _err in load_records(assess_dir / RECORDS_DIR_NAME)
               if rec]
    assessments = []
    for rec in records:
        subject = str(rec.get("subject", "")).lower()
        nodes.add(subject)
        assessments.append({
            "id": rec.get("id"), "kind": rec.get("kind"), "subject": subject,
            "grounding": rec.get("grounding", []), "disputes": rec.get("disputes", []),
            "reviews": rec.get("reviews", []),
        })

    return {
        "nodes": sorted(n for n in nodes if n),
        "edges": edges,
        "sub_questions": sorted(parse_inquiry_qids(inquiry_path)),
        "addresses": addresses,
        "assessments": assessments,
        "findings": {
            "double_count": [d.as_dict() for d in double_count_findings(
                claims_dir, assess_dir / "_records",
                load_correlation_kinds(assess_dir.parent)[0])],
            "superseded": sorted(set(superseded)),
        },
    }


def edge_record_id(edge: dict, edge_records: dict[tuple[str, str], set[str]]) -> str | None:
    """The record id covering a supports/rebuts graph-dict edge, or None — via the shared
    check_assessment.covering_record rule, so consumers match the gate. `edge_records`
    keyed (target, grounding) as edge_record_coverage produces it."""
    if edge.get("type") not in ASSESSED_EDGE_TYPES:
        return None
    target = str(edge.get("target", "")).lower()
    grounding = f'{edge.get("from_ledger")}:{edge.get("grounding") or "?"}'.lower()
    return covering_record(target, grounding, edge.get("rec"), edge_records)


def _mid(node: str) -> str:
    """A Mermaid-safe node id (alnum/underscore)."""
    return "n_" + "".join(ch if ch.isalnum() else "_" for ch in node)


def to_mermaid(graph: dict) -> str:
    """A Mermaid `graph TD` view: claim nodes + typed edges; superseded nodes and
    rebuttals are visually distinct. Derived, human-facing — not the source."""
    lines = ["graph TD"]
    superseded = set(graph["findings"]["superseded"])
    for node in graph["nodes"]:
        shape = f'(["{node}"])' if node in superseded else f'["{node}"]'
        lines.append(f"  {_mid(node)}{shape}")
    for e in graph["edges"]:
        if not e["source"]:
            continue
        arrow = "-.->|{}|".format(e["type"]) if e["type"] == "rebuts" \
            else "-->|{}|".format(e["type"])
        lines.append(f"  {_mid(e['source'])} {arrow} {_mid(e['target'])}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit the derived verified-claim graph.")
    ap.add_argument("--claims-dir", default=str(CLAIMS_DIR))
    ap.add_argument("--content-dir", default=str(CONTENT_DIR))
    ap.add_argument("--mermaid", action="store_true", help="print a Mermaid diagram instead")
    ap.add_argument("--stdout", action="store_true", help="print JSON instead of writing the file")
    args = ap.parse_args()

    content_dir = Path(args.content_dir)
    graph = build_graph(Path(args.claims_dir), content_dir / "inquiry.md",
                        content_dir / "assessments")

    if args.mermaid:
        print(to_mermaid(graph))
        return 0
    payload = json.dumps(graph, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.stdout:
        sys.stdout.write(payload)
        return 0
    out = content_dir / "graph.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(payload, encoding="utf-8")
    log_info(f"wrote {out} — {len(graph['nodes'])} node(s), {len(graph['edges'])} edge(s), "
             f"{len(graph['assessments'])} assessment(s); "
             f"{len(graph['findings']['double_count'])} double-count finding(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
