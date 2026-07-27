# === SCRIPT: Claim-graph resolver — the shared cross-ledger addressing core ===
# Purpose: the keystone the structure + assessment layers stand on. A claim is
#          addressed globally as <ledger_key>:<slug> (e.g.
#          andersen_2020:fcs-not-expected), composing the two primitives that
#          already exist — the ledger file stem and the claim's **ID:** slug. A
#          bare <slug> means "this ledger". This module owns ONE definition of:
#            - the small edge taxonomy (EDGE_LABELS) the graph is built from;
#            - how an in-band `**<EdgeType>:** <key:slug> (grounded by #<slug>)`
#              line parses into an Edge;
#            - how an address resolves to a ledger + a real claim in it.
#          check_structure.py, check_assessment.py and build_graph.py all import
#          from here, so the three gates and the builder can never drift on what
#          a claim address means (the "verify_quotes owns the stamp schema" pattern).
# INPUTS : literature/verified_claims/<key>.md ledgers (committed); their
#          `## Claim N` headers + `**ID:**` slugs supply the resolvable claim ids
#          (via check_citations.ledger_claim_id_sets).
# OUTPUTS: as a library, dataclasses (Address / Edge / Resolution). As a CLI, a
#          resolution report over every in-band edge: stdout [INFO]; stderr
#          [WARNING] for an unresolved endpoint/grounding. Exit 0 = all resolve
#          (or no edges); 1 = at least one endpoint or grounding does not resolve.
# Run    : python3 tools/claim_graph.py        # report over literature/verified_claims/
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

# tools/ is on sys.path[0] when run as a script (and conftest adds it for tests),
# so the sibling kernel checker is importable without a package layout.
from check_citations import ledger_claim_id_sets

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAIMS_DIR = REPO_ROOT / "literature" / "verified_claims"

# The taxonomy is deliberately small — taxonomy bloat is both a generalisability
# risk and a gaming surface. Key = canonical edge type (lower-case, as it appears
# in graph.json); value = the bolded in-band label authored in the ledger. The
# canonical type is exactly the label lower-cased, so parsing needs no second map.
EDGE_LABELS: dict[str, str] = {
    "supports": "Supports",        # inference structure
    "rebuts": "Rebuts",
    "depends-on": "Depends-on",
    "refines": "Refines",          # similar-but-not-identical
    "qualifies": "Qualifies",
    "restates": "Restates",        # same proposition, INDEPENDENT statement
    "duplicate-of": "Duplicate-of",  # same source re-logged → collapses to one node
    "supersedes": "Supersedes",    # over time
}

# An edge line, e.g.:
#   **Rebuts:** segreto_2021:fcs-implies-engineering (grounded by #not-from-known-backbone)
# The target is a key:slug address (or a bare slug = this ledger); the
# `(grounded by #<slug>)` clause is mandatory in a valid ledger but OPTIONAL in
# the parse, so a missing/malformed grounding surfaces as grounding=None for a
# gate to flag (like an unresolvable #ref) rather than silently dropping the edge.
_LABEL_ALT = "|".join(re.escape(label) for label in EDGE_LABELS.values())
EDGE_LINE_RE = re.compile(
    rf"^\*\*(?P<label>{_LABEL_ALT}):\*\*\s+"
    rf"(?P<target>[\w-]+(?::[\w-]+)?)"
    rf"(?:\s*\(grounded by\s+#(?P<grounding>[\w-]+)\))?",
    re.IGNORECASE,
)
# Optional `[rec: <id>]` clause: links an edge (or assessment marker) to a record.
REC_REF_RE = re.compile(r"\[rec:\s*(?P<id>[\w-]+)\]", re.IGNORECASE)


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_warning(msg: str) -> None:
    print(f"[WARNING] {msg}", file=sys.stderr)


@dataclass(frozen=True)
class Address:
    """A global claim address. key=None means 'this ledger' (a bare slug)."""
    key: str | None
    slug: str

    def render(self, default_key: str | None = None) -> str:
        key = self.key or default_key
        return f"{key}:{self.slug}" if key else self.slug


@dataclass(frozen=True)
class Edge:
    """One in-band edge line, attributed to the ledger it was authored in.
    The source node is <originating_key>:<grounding> — the grounding claim IS the
    verbatim quote where the relationship is asserted, so it is the natural source
    endpoint; the target is the claim the relationship points at. `rec` is the
    optional `[rec: <id>]` clause linking the edge to a judgement record (used by
    the edge_assessments coverage policy)."""
    edge_type: str
    target: Address
    grounding: str | None
    originating_key: str
    line_no: int
    raw: str
    rec: str | None = None


@dataclass(frozen=True)
class Resolution:
    """The outcome of resolving an Address against the corpus. exists is True only
    when the ledger file is present AND the slug names a real claim in it."""
    address: Address
    key: str
    ledger_path: Path | None
    exists: bool
    reason: str


def parse_address(text: str) -> Address:
    """Parse `key:slug` or a bare `slug` into an Address. Keys and slugs are
    lower-cased so matching is case-insensitive (ledger stems are lower-case by
    convention; ledger_claim_id_sets lower-cases slugs)."""
    text = text.strip()
    if ":" in text:
        raw_key, _, raw_slug = text.partition(":")
        return Address(raw_key.strip().lower() or None, raw_slug.strip().lower())
    return Address(None, text.lower())


def parse_edge_line(line: str, originating_key: str, line_no: int = 0) -> Edge | None:
    """Parse a single line into an Edge, or None if it is not an edge line."""
    m = EDGE_LINE_RE.match(line.strip())
    if not m:
        return None
    grounding = m.group("grounding")
    rec_m = REC_REF_RE.search(line)
    return Edge(
        edge_type=m.group("label").lower(),
        target=parse_address(m.group("target")),
        grounding=grounding.lower() if grounding else None,
        originating_key=originating_key.lower(),
        line_no=line_no,
        raw=line.rstrip(),
        rec=rec_m.group("id").lower() if rec_m else None,
    )


def parse_ledger_edges(ledger_path: Path) -> list[Edge]:
    """Every in-band edge authored in one ledger (the file stem is the key)."""
    key = ledger_path.stem.lower()
    edges: list[Edge] = []
    text = ledger_path.read_text(encoding="utf-8", errors="ignore")
    for line_no, line in enumerate(text.splitlines(), start=1):
        edge = parse_edge_line(line, key, line_no)
        if edge is not None:
            edges.append(edge)
    return edges


def iter_edges(claims_dir: Path) -> Iterator[Edge]:
    """Every edge across the corpus (TEMPLATE skipped)."""
    if not claims_dir.is_dir():
        return
    for ledger in sorted(claims_dir.glob("*.md")):
        if ledger.stem == "TEMPLATE":
            continue
        yield from parse_ledger_edges(ledger)


CLAIM_HEADER_RE = re.compile(r"^##\s+claim\b", re.IGNORECASE)
_ID_LINE_RE = re.compile(r"^\*\*ID:\*\*\s*([\w-]+)", re.IGNORECASE)
_DOUBLE_QUOTES = '"“”'


def claim_body(ledger_path: Path, slug: str) -> str | None:
    """The text of the one `## Claim` block in this ledger that the slug names —
    by `**ID:**` slug or by `cN` ordinal (header order). None if no block matches.
    Binding an assessment's body_sha256 to THIS (not the whole ledger) means an
    edit to an unrelated claim does not stale the judgement; an edit to the
    assessed claim does. Block = from its `## Claim` header to the next one (or EOF)."""
    slug = slug.lower()
    lines = ledger_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    headers = [i for i, ln in enumerate(lines) if CLAIM_HEADER_RE.match(ln.strip())]
    for n, start in enumerate(headers):
        end = headers[n + 1] if n + 1 < len(headers) else len(lines)
        block = lines[start:end]
        ordinal = f"c{n + 1}"
        slugs = {m.group(1).lower() for ln in block
                 if (m := _ID_LINE_RE.match(ln.strip()))}
        if slug == ordinal or slug in slugs:
            return "\n".join(block).rstrip() + "\n"
    return None


def claim_aliases(ledger_path: Path, slug: str) -> set[str]:
    """Every address of the ONE claim that `slug` names: its `cN` ordinal plus any
    `**ID:**` slugs in the same block ({} if none matches). Lets a consumer treat a
    `#c1` ordinal cite and the claim's slug as the same node (coverage)."""
    slug = slug.lower()
    lines = ledger_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    headers = [i for i, ln in enumerate(lines) if CLAIM_HEADER_RE.match(ln.strip())]
    for n, start in enumerate(headers):
        end = headers[n + 1] if n + 1 < len(headers) else len(lines)
        block = lines[start:end]
        ordinal = f"c{n + 1}"
        slugs = {m.group(1).lower() for ln in block
                 if (m := _ID_LINE_RE.match(ln.strip()))}
        if slug == ordinal or slug in slugs:
            return {ordinal} | slugs
    return set()


def claim_quote(ledger_path: Path, slug: str) -> str:
    """The verbatim quote text of a claim — the content between the first and last
    double-quote on its `> "…"` blockquote lines, space-joined. "" if the claim or
    a quote is absent. Used to pin a rhetorical-assessment span to a real quote."""
    body = claim_body(ledger_path, slug)
    if body is None:
        return ""
    quotes: list[str] = []
    for line in body.splitlines():
        stripped = line.lstrip()
        if not stripped.startswith(">"):
            continue
        idx = [i for i, ch in enumerate(stripped) if ch in _DOUBLE_QUOTES]
        if len(idx) >= 2 and idx[-1] > idx[0]:
            quotes.append(stripped[idx[0] + 1:idx[-1]])
    return " ".join(quotes)


def ledger_for_key(claims_dir: Path, key: str) -> Path | None:
    """The ledger file for a key is its exact stem: verified_claims/<key>.md.
    Exact (not glob) so a global address is unambiguous; a renamed ledger surfaces
    as a dangling reference rather than silently re-resolving to a near-match."""
    candidate = claims_dir / f"{key.lower()}.md"
    return candidate if candidate.is_file() else None


def resolve(address: Address, originating_key: str, claims_dir: Path) -> Resolution:
    """Resolve an address to a ledger + a real claim in it. A bare slug resolves
    within originating_key. exists is False (with a reason) if the ledger is
    missing or the slug names no claim — the single predicate every gate reads."""
    key = address.key or originating_key.lower()
    ledger = ledger_for_key(claims_dir, key)
    if ledger is None:
        return Resolution(address, key, None, False, f"no ledger '{key}.md'")
    ordinals, slugs = ledger_claim_id_sets(ledger)
    if address.slug not in (ordinals | slugs):
        return Resolution(address, key, ledger, False,
                          f"no claim '{address.slug}' in {key}.md")
    return Resolution(address, key, ledger, True, "")


def resolve_edge(edge: Edge, claims_dir: Path) -> tuple[Resolution, Resolution | None]:
    """(target resolution, grounding resolution|None). The grounding is resolved
    within the originating ledger; None means the edge carried no grounding clause
    at all — a distinct failure from a grounding that resolves to nothing."""
    target = resolve(edge.target, edge.originating_key, claims_dir)
    grounding = (resolve(Address(None, edge.grounding), edge.originating_key, claims_dir)
                 if edge.grounding else None)
    return target, grounding


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Resolution report over every in-band claim-graph edge.")
    ap.add_argument("--claims-dir", default=str(CLAIMS_DIR),
                    help="override verified_claims/ location (tests)")
    args = ap.parse_args()

    claims_dir = Path(args.claims_dir)
    edges = list(iter_edges(claims_dir))
    if not edges:
        log_info("no claim-graph edges — nothing to resolve.")
        return 0

    unresolved = 0
    for edge in edges:
        target, grounding = resolve_edge(edge, claims_dir)
        src = f"{edge.originating_key}:{edge.grounding or '?'}"
        line = f"{src} --{edge.edge_type}--> {edge.target.render(edge.originating_key)}"
        if not target.exists:
            log_warning(f"{line}: target unresolved — {target.reason}")
            unresolved += 1
        if edge.grounding is None:
            log_warning(f"{line}: no (grounded by #slug) clause")
            unresolved += 1
        elif grounding is not None and not grounding.exists:
            log_warning(f"{line}: grounding unresolved — {grounding.reason}")
            unresolved += 1
        if target.exists and grounding is not None and grounding.exists:
            log_info(line)
    if unresolved:
        log_warning(f"{unresolved} unresolved endpoint(s)/grounding(s) across "
                    f"{len(edges)} edge(s).")
        return 1
    log_info(f"all {len(edges)} edge(s) resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
