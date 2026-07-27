# === SCRIPT: Structure gate — every claim-graph edge resolves + is grounded ===
# The structure layer's enforcement half (mirrors check_manifest.py for the
# provenance layer). It validates the in-band claim graph WITHOUT endorsing any
# judgement: for every authored edge it checks the target resolves cross-ledger,
# the (grounded by #slug) clause is present and resolves in the originating
# ledger, and no source/target pair carries contradictory edges (supports AND
# rebuts). It also checks every `**Addresses:**` / `**Crux-of:**` field names a
# real sub-question id in content/inquiry.md.
#
# What it does NOT check (the central, stated seam): whether the grounding quote
# TRULY rebuts/supports the target. Grounding RESOLVES is mechanical; grounding
# is APT is judgement (the assessment layer attests it, it is never proven).
#
# An empty graph is always valid — no posture forces edges to exist, so the
# pristine kit (no edges, no inquiry.md) passes under every mode.
# INPUTS : literature/verified_claims/*.md (edges + qid fields via claim_graph),
#          content/inquiry.md (sub-question ids), structure_layer: in config.
# OUTPUTS: [INFO]/[WARNING]/[ERROR]; exit 0 = ok or posture off/optional;
#          1 = a problem under structure_layer: required.
# Run    : python3 tools/check_structure.py
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from check_citations import parse_config
import claim_graph as cg

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAIMS_DIR = REPO_ROOT / "literature" / "verified_claims"
INQUIRY = REPO_ROOT / "content" / "inquiry.md"

# A sub-question in content/inquiry.md declares its id on an `**id:** <qid>` line
# (mirrors the ledger `**ID:**` convention). Claims point at one with
# `**Addresses:** <qid>` (structure) or `**Crux-of:** <qid> …` (assessment);
# both are validated here against the inquiry's declared ids.
QID_LINE_RE = re.compile(r"^\*\*id:\*\*\s*([\w-]+)", re.IGNORECASE)
QID_FIELD_RE = re.compile(r"^\*\*(?P<field>Addresses|Crux-of):\*\*\s*(?P<qid>[\w-]+)",
                          re.IGNORECASE)


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_warning(msg: str) -> None:
    print(f"[WARNING] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def structure_mode(config: dict[str, str]) -> str:
    """structure_layer: off | optional | required (default optional)."""
    raw = config.get("structure_layer", "").split("#", 1)[0].strip().lower()
    return raw if raw in ("off", "optional", "required") else "optional"


@dataclass(frozen=True)
class QidRef:
    """An in-band field referencing an inquiry sub-question id."""
    field: str
    qid: str
    origin: str
    line_no: int


def parse_inquiry_qids(inquiry_path: Path) -> set[str]:
    """The set of sub-question ids declared in inquiry.md (empty if absent — then
    any qid reference is dangling, which is the point)."""
    if not inquiry_path.is_file():
        return set()
    text = inquiry_path.read_text(encoding="utf-8", errors="ignore")
    return {m.group(1).lower() for line in text.splitlines()
            if (m := QID_LINE_RE.match(line.strip()))}


def parse_qid_refs(claims_dir: Path) -> list[QidRef]:
    """Every `**Addresses:**` / `**Crux-of:**` qid reference across the corpus."""
    refs: list[QidRef] = []
    if not claims_dir.is_dir():
        return refs
    for ledger in sorted(claims_dir.glob("*.md")):
        if ledger.stem == "TEMPLATE":
            continue
        text = ledger.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            m = QID_FIELD_RE.match(line.strip())
            if m:
                refs.append(QidRef(m.group("field").lower(), m.group("qid").lower(),
                                   ledger.stem, line_no))
    return refs


def _edge_label(edge: cg.Edge) -> str:
    src = f"{edge.originating_key}:{edge.grounding or '?'}"
    return f"{src} --{edge.edge_type}--> {edge.target.render(edge.originating_key)}"


def structure_problems(claims_dir: Path, inquiry_path: Path) -> list[str]:
    """All structural problems across the graph ([] = valid / empty graph)."""
    problems: list[str] = []
    qids = parse_inquiry_qids(inquiry_path)
    pair_types: dict[tuple[str, str], set[str]] = {}

    for edge in cg.iter_edges(claims_dir):
        label = _edge_label(edge)
        target, grounding = cg.resolve_edge(edge, claims_dir)
        if not target.exists:
            problems.append(f"{label}: target unresolved — {target.reason}")
        if edge.grounding is None:
            problems.append(f"{label}: missing (grounded by #slug) clause "
                            "— an edge must name the claim asserting the relationship")
        elif grounding is not None and not grounding.exists:
            problems.append(f"{label}: grounding unresolved — {grounding.reason}")
        # Contradiction is keyed on the precise (source claim, target) pair: the
        # same grounded claim cannot both support and rebut the same target.
        src = f"{edge.originating_key}:{edge.grounding}" if edge.grounding \
            else edge.originating_key
        pair_types.setdefault((src, edge.target.render(edge.originating_key)),
                              set()).add(edge.edge_type)

    for (src, tgt), types in sorted(pair_types.items()):
        if "supports" in types and "rebuts" in types:
            problems.append(f"{src} -> {tgt}: contradictory edges "
                            "(both supports and rebuts on one pair)")

    for ref in parse_qid_refs(claims_dir):
        if ref.qid not in qids:
            where = "no content/inquiry.md" if not qids else "not declared there"
            problems.append(f"{ref.origin}:{ref.line_no}: **{ref.field}:** "
                            f"'{ref.qid}' is not a sub-question id in inquiry.md ({where})")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Validate the in-band claim graph: edges resolve + are grounded.")
    ap.add_argument("--claims-dir", default=str(CLAIMS_DIR),
                    help="override verified_claims/ location (tests)")
    ap.add_argument("--inquiry", default=str(INQUIRY),
                    help="override content/inquiry.md location (tests)")
    ap.add_argument("--config", default=str(REPO_ROOT / "ledger.config.md"),
                    help="override ledger.config.md location (tests)")
    ap.add_argument("--structure", choices=("off", "optional", "required"), default=None,
                    help="override the posture (default: structure_layer: in config)")
    args = ap.parse_args()

    mode = args.structure or structure_mode(parse_config(Path(args.config)))
    if mode == "off":
        log_info("structure_layer: off — claim-graph validation skipped.")
        return 0

    claims_dir = Path(args.claims_dir)
    problems = structure_problems(claims_dir, Path(args.inquiry))
    if not problems:
        n = sum(1 for _ in cg.iter_edges(claims_dir))
        log_info(f"structure ok — {n} edge(s) resolve and are grounded.")
        return 0

    message = ("claim-graph structure problems "
               "(unresolved/ungrounded edge, contradiction, or bad qid):\n  - "
               + "\n  - ".join(problems))
    if mode == "required":
        log_error(message)
        return 1
    log_warning(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
