# === SCRIPT: Analyze the verified-claim graph — validity ASSISTANCE, not a gate ===
# A set of read-only queries over the claim graph that surface its structure for human
# judgement WITHOUT pretending to decide validity. This tool answers:
#   - which claims are doing the most work (load-bearing by graph degree);
#   - what a given conclusion rests on (its dependency closure);
#   - which supports/rebuts edges carry no judgement record (unassessed);
#   - which apparently-independent supporters share a premise (double-count);
#   - which claim, if removed, would sever a conclusion from its support (articulation).
# HONEST LIMIT: every output is a STRUCTURAL pointer for a human, never a verdict. The
# graph resolving and being grounded (the gates) does not make an inference valid; this
# tool only shows where the argument's weight sits. It changes nothing and exits 0.
# INPUTS : literature/verified_claims/, content/inquiry.md, content/assessments/.
# OUTPUTS: a report on stdout (or --json); exit 0 always.
# Run    : python3 tools/analyze_graph.py
#          python3 tools/analyze_graph.py --target andersen_2020:fcs-natural-process
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from build_graph import build_graph, edge_record_id
from check_assessment import (ASSESSED_EDGE_TYPES, double_count_findings,
                              edge_record_coverage, load_correlation_kinds,
                              valid_edge_coverage)

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAIMS_DIR = REPO_ROOT / "literature" / "verified_claims"
CONTENT_DIR = REPO_ROOT / "content"

# Edge types that mean "the source claim underpins the target claim".
SUPPORT_TYPES = ("supports", "depends-on")


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def _underpins(graph: dict) -> dict[str, set[str]]:
    """U -> {C, …}: U underpins C. `supports` runs source→target; `depends-on` runs the
    other way (a claim depends on its target), so the target underpins the source."""
    adj: dict[str, set[str]] = defaultdict(set)
    for e in graph["edges"]:
        src, tgt, typ = e["source"], e["target"], e["type"]
        if not src or not tgt:
            continue
        if typ == "supports":
            adj[src].add(tgt)
        elif typ == "depends-on":
            adj[tgt].add(src)
    return adj


def _ancestors(adj: dict[str, set[str]], target: str,
               blocked: str | None = None) -> set[str]:
    """All claims that reach `target` through underpins-edges (its support base),
    optionally with one node removed (to test what `blocked` is holding up)."""
    reverse: dict[str, set[str]] = defaultdict(set)
    for u, cs in adj.items():
        for c in cs:
            reverse[c].add(u)
    seen: set[str] = set()
    stack = [target]
    while stack:
        node = stack.pop()
        for parent in reverse.get(node, ()):
            if parent == blocked or parent in seen:
                continue
            seen.add(parent)
            stack.append(parent)
    return seen


def load_bearing(graph: dict) -> list[dict]:
    """Rank nodes by how much argumentative weight rests on them: in-degree (how many
    edges target the claim) + grounding-degree (how many edges it is the source of)."""
    in_deg: dict[str, int] = defaultdict(int)
    grounds: dict[str, int] = defaultdict(int)
    for e in graph["edges"]:
        if e["target"]:
            in_deg[e["target"]] += 1
        if e["source"]:
            grounds[e["source"]] += 1
    rows = [{"node": n, "in_degree": in_deg[n], "grounds": grounds[n],
             "total": in_deg[n] + grounds[n]} for n in graph["nodes"]]
    rows = [r for r in rows if r["total"] > 0]
    rows.sort(key=lambda r: (-r["total"], r["node"]))
    return rows


def dependency_closure(graph: dict, target: str) -> list[str]:
    """Everything `target` transitively rests on (its support ancestors)."""
    return sorted(_ancestors(_underpins(graph), target))


def unassessed_edges(graph: dict, edge_records=None) -> list[dict]:
    """supports/rebuts edges with no valid covering record. Pass edge_records (the gate's
    valid coverage) to match enforcement; else derive it from the graph's assessments."""
    if edge_records is None:
        edge_records = edge_record_coverage(
            {str(a.get("id", "")).lower(): a for a in graph.get("assessments", [])})
    return [e for e in graph["edges"]
            if e["type"] in ASSESSED_EDGE_TYPES
            and edge_record_id(e, edge_records) is None]


def shared_premises(claims_dir: Path, records_dir: Path | None = None):
    """Apparently-independent supporters that share a premise (possible double-count)."""
    content_dir = records_dir.parent.parent if records_dir else None
    return double_count_findings(claims_dir, records_dir,
                                 load_correlation_kinds(content_dir)[0])


def load_bearing_cuts(graph: dict, target: str) -> list[str]:
    """Claims whose removal would sever some OTHER supporter from `target` — the
    articulation points of its support base. A structural proxy for 'what, if it fell,
    would take the conclusion's support with it'. (A sole direct supporter is surfaced by
    load_bearing, not here — this is specifically about disconnecting other support.)"""
    adj = _underpins(graph)
    full = _ancestors(adj, target)
    cuts: list[str] = []
    for cand in sorted(full):
        remaining = _ancestors(adj, target, blocked=cand)
        # Did removing `cand` strand any OTHER ancestor that was holding up the target?
        if (full - {cand}) - remaining:
            cuts.append(cand)
    return cuts


def report(graph: dict, claims_dir: Path, target: str | None, edge_records=None,
           records_dir: Path | None = None) -> list[str]:
    out: list[str] = []
    out.append("ASSISTED analysis — structural pointers for human judgement; it proves")
    out.append("NOTHING about whether an inference is valid. Weight, not verdict.")
    out.append("")
    lb = load_bearing(graph)
    out.append(f"Load-bearing claims (by graph degree) — {len(lb)}:")
    for r in lb[:10]:
        out.append(f"  {r['node']}  (targeted {r['in_degree']}x, grounds {r['grounds']} edge(s))")
    if not lb:
        out.append("  (none — no edges yet)")

    ua = unassessed_edges(graph, edge_records)
    out.append(f"Unassessed supports/rebuts edges — {len(ua)}:")
    for e in ua:
        out.append(f"  {e['source']} -[{e['type']}]-> {e['target']}  (no [rec:])")
    if not ua:
        out.append("  (none)")

    sp = shared_premises(claims_dir, records_dir)
    out.append(f"Shared-premise / possible double-counts — {len(sp)}:")
    for s in sp:
        seal = f"sealed:{s.sealed_record}" if s.sealed_record else "declared-only"
        out.append(f"  [{s.kind_label}; {seal}] {s.summary}")
    if not sp:
        out.append("  (none)")

    if target:
        closure = dependency_closure(graph, target)
        out.append(f"Dependency closure of {target} — rests on {len(closure)}:")
        for n in closure:
            out.append(f"  {n}")
        if not closure:
            out.append("  (nothing — it is a leaf / unsupported claim)")
        cuts = load_bearing_cuts(graph, target)
        out.append(f"Articulation claims for {target} (removal severs other support) — {len(cuts)}:")
        for n in cuts:
            out.append(f"  {n}")
        if not cuts:
            out.append("  (none — no single claim is a sole conduit)")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only validity-assistance over the claim graph.")
    ap.add_argument("--claims-dir", default=str(CLAIMS_DIR))
    ap.add_argument("--content-dir", default=str(CONTENT_DIR))
    ap.add_argument("--target", default=None, help="a key:slug claim to trace dependencies of")
    ap.add_argument("--json", action="store_true", help="emit the raw analysis as JSON")
    args = ap.parse_args()

    claims_dir = Path(args.claims_dir)
    content_dir = Path(args.content_dir)
    records_dir = content_dir / "assessments" / "_records"
    graph = build_graph(claims_dir, content_dir / "inquiry.md", content_dir / "assessments")
    edge_records = valid_edge_coverage(records_dir, claims_dir)

    if args.json:
        payload = {
            "load_bearing": load_bearing(graph),
            "unassessed_edges": unassessed_edges(graph, edge_records),
            "shared_premises": [s.as_dict() for s in shared_premises(claims_dir, records_dir)],
        }
        if args.target:
            payload["dependency_closure"] = dependency_closure(graph, args.target)
            payload["articulation_claims"] = load_bearing_cuts(graph, args.target)
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        return 0

    for line in report(graph, claims_dir, args.target, edge_records, records_dir):
        log_info(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
