#!/usr/bin/env python3
# === SCRIPT: ledger repro — measure extraction convergence between two runs ===
# INPUTS : two ledger dirs (verified_claims/-shaped) produced by EXTRACTION.md over
#          the SAME source(s).
# OUTPUT : claim-set agreement (Jaccard over key:slug), sub-question coverage match,
#          attribution match, and the residual (claims in exactly one run).
# This is the MEASURED side of EXTRACTION.md's near-determinism claim — a number with
# its residual, never an assertion. Read-only; reuses the existing ledger parsers.
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))
from check_citations import ledger_claim_id_sets   # (ordinals, **ID:** slugs) per ledger
from check_structure import parse_qid_refs          # **Addresses:**/**Crux-of:** qids
from ledger_md import claim_blocks                  # the one reader of claim blocks


def _ledgers(d: Path) -> list[Path]:
    return [p for p in sorted(d.glob("*.md")) if p.stem != "TEMPLATE"]


def run_facts(run_dir: Path) -> tuple[set[str], dict[str, set[str]], set[str]]:
    """For one run dir: (addresses, slug→keys, addressed qids).
    addresses = {"key:slug"}; slug→keys maps a bare slug to the ledger keys it
    appears under (so a unit routed to the wrong voice is detectable)."""
    addresses: set[str] = set()
    slug_keys: dict[str, set[str]] = {}
    for led in _ledgers(run_dir):
        _, slugs = ledger_claim_id_sets(led)
        for slug in slugs:
            addresses.add(f"{led.stem}:{slug}")
            slug_keys.setdefault(slug, set()).add(led.stem)
    qids = {ref.qid for ref in parse_qid_refs(run_dir)}
    return addresses, slug_keys, qids


def _jaccard(a: set[str], b: set[str]) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 1.0


# A blockquote line in a ledger claim: `> "the verbatim span"`.
_QUOTE_LINE = re.compile(r"^\s*>\s?(.*)$")
# A claim's coordinate address, when the source has a committed unit manifest.
_LOCUS_LINE = re.compile(r"^\*\*Locus:\*\*\s*([\w-]+)", re.M)


def _norm_quote(s: str) -> str:
    """Normalise a quote the way the verbatim gate does — NFKD-decompose, casefold,
    drop every non-alphanumeric (so spacing, punctuation, ligatures, and smart quotes
    don't matter). Two runs that lifted the SAME span normalise identically."""
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", s).casefold())


def run_quotes(run_dir: Path) -> set[str]:
    """{"key:normquote"} over every blockquote span in the run.

    This is the SELECTION signal, independent of slug naming: a claim's true locus is
    the span it lifted, not the slug a reader chose for it. Consecutive `>` lines are
    joined into one span (a multi-line blockquote is one quote)."""
    quotes: set[str] = set()
    for led in _ledgers(run_dir):
        buf: list[str] = []
        spans: list[str] = []
        for line in led.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = _QUOTE_LINE.match(line)
            if m:
                buf.append(m.group(1))
            elif buf:
                spans.append(" ".join(buf))
                buf = []
        if buf:
            spans.append(" ".join(buf))
        for span in spans:
            nq = _norm_quote(span)
            if nq:
                quotes.add(f"{led.stem}:{nq}")
    return quotes


def run_loci(run_dir: Path) -> set[str]:
    """{"key:locus"} over every claim carrying a **Locus:** — the canonical
    coordinate address from the source's unit manifest. This is the strongest
    selection signal: the locus is deterministic, so two runs that keep the same
    unit produce the same address regardless of slug or span choice. Empty when
    no source on the grid yet."""
    loci: set[str] = set()
    for led in _ledgers(run_dir):
        for block in claim_blocks(led):
            if (m := block.field(_LOCUS_LINE)):
                loci.add(f"{led.stem}:{m.group(1).lower()}")
    return loci


def compare(dir_a: Path, dir_b: Path) -> dict:
    addr_a, slug_a, qid_a = run_facts(dir_a)
    addr_b, slug_b, qid_b = run_facts(dir_b)
    shared_slugs = set(slug_a) & set(slug_b)
    attribution = (sum(slug_a[s] == slug_b[s] for s in shared_slugs) / len(shared_slugs)
                   if shared_slugs else 1.0)
    quo_a, quo_b = run_quotes(dir_a), run_quotes(dir_b)
    loci_a, loci_b = run_loci(dir_a), run_loci(dir_b)
    # locus_agreement is the strongest measure, available only once the source has a
    # committed unit manifest (claims carry **Locus:**): the address is mechanical, so
    # this isolates the one irreducible judgement — keep/drop. None when nothing is on
    # the grid yet, so it never masquerades as 1.0 for un-addressed corpora.
    locus_agreement = round(_jaccard(loci_a, loci_b), 3) if (loci_a or loci_b) else None
    return {
        # The hierarchy, coarse -> fine: coverage_match (same sub-questions) >=
        # selection_agreement (same spans, naming-independent) >= claim_agreement (same
        # spans AND same slug). locus_agreement, when present, supersedes them all: same
        # canonical coordinate, so only keep/drop can differ.
        "locus_agreement": locus_agreement,
        "selection_agreement": round(_jaccard(quo_a, quo_b), 3),
        "claim_agreement": round(_jaccard(addr_a, addr_b), 3),
        "coverage_match": round(_jaccard(qid_a, qid_b), 3),
        "attribution_match": round(attribution, 3),
        "shared_loci": len(loci_a & loci_b),
        "shared_spans": len(quo_a & quo_b),
        "shared_claims": len(addr_a & addr_b),
        "total_claims": len(addr_a | addr_b),
        "residual": sorted(addr_a ^ addr_b),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Measure extraction convergence between two ledger dirs.")
    ap.add_argument("run_a", help="ledger dir for run A")
    ap.add_argument("run_b", help="ledger dir for run B")
    ap.add_argument("--json", action="store_true", help="emit the metrics as JSON")
    args = ap.parse_args(argv)

    a, b = Path(args.run_a), Path(args.run_b)
    if not a.is_dir() or not b.is_dir():
        print(f"[ERROR] both runs must be directories: {a} {b}", file=sys.stderr)
        return 2
    m = compare(a, b)
    if args.json:
        print(json.dumps(m, indent=2))
        return 0
    locus = "n/a" if m["locus_agreement"] is None else m["locus_agreement"]
    print(f"[INFO] repro: locus {locus} · selection {m['selection_agreement']} · "
          f"claim-agreement {m['claim_agreement']} · coverage {m['coverage_match']} · "
          f"attribution {m['attribution_match']} · "
          f"residual {len(m['residual'])}/{m['total_claims']}")
    for addr in m["residual"]:
        print(f"  residual: {addr}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
