#!/usr/bin/env python3
"""Inventory every case source from committed ledger provenance and triage its
redistribution status by DOI registrant / host.

The raw source bytes are git-ignored and ship with no bundle, so this manifest is
documentary: it records what each source is, where it came from, and whether its
publisher's DEFAULT terms permit redistribution. Two honesty constraints hold by
construction:

* a status is the publisher/repository DEFAULT keyed off the DOI registrant or
  host, never a fetched per-article licence — an OA-paid exception at a closed
  publisher is NOT resolved here, so a 'restricted' row means "no open licence
  established", not "redistribution refused";
* a source is marked includable only when its bytes are present on disk AND its
  status is positively redistributable. This kit carries no source bytes, so no
  row is ever includable — an honest empty corpus, not a cleared one withheld.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

CASES = ("covid_origins", "eggs_cholesterol", "lhc_safety", "quantum_genomics",
         "covid_debate")

COLUMNS = ("case", "source_key", "title", "locator", "local_filename",
    "expected_sha256", "corpus_present", "included_in_submission",
    "redistribution_status", "licence_or_basis", "evidence_for_status",
    "acquisition_command_or_instructions", "verification_mode", "notes")

# Redistribution states permitted by the interchange contract.
CLEARED = {"cleared", "public-domain", "permissive-licence",
           "competition-supplied-cleared"}

# DOI registrant prefix -> (publisher, default status, basis). Conservative:
# a uniformly-CC publisher is permissive; a closed publisher's default is
# 'restricted' (no open licence established); a preprint's is 'unknown'. Any
# prefix not listed falls through to 'unknown'.
DOI_REGISTRANTS = {
    "10.1371": ("PLOS", "permissive-licence",
                "PLOS journals publish every article under CC-BY 4.0"),
    "10.1038": ("Springer Nature", "restricted",
                "closed-access publisher default; per-article open licence not established"),
    "10.1126": ("AAAS (Science)", "restricted",
                "closed-access publisher default; per-article open licence not established"),
    "10.1016": ("Elsevier", "restricted",
                "closed-access publisher default; per-article open licence not established"),
    "10.1103": ("APS", "restricted",
                "closed-access publisher default; per-article open licence not established"),
    "10.1073": ("PNAS", "unknown",
                "PNAS mixes open and closed access; per-article licence not established"),
    "10.1101": ("Cold Spring Harbor / bioRxiv", "unknown",
                "preprint or CSHL journal; author-selected licence not established"),
    "10.48550": ("arXiv", "unknown",
                 "arXiv's non-exclusive distribution licence does not by default permit third-party redistribution"),
    "10.1080": ("Taylor & Francis", "restricted",
                "closed-access publisher default; per-article open licence not established"),
    "10.1093": ("Oxford University Press", "restricted",
                "closed-access publisher default; per-article open licence not established"),
    "10.3390": ("MDPI", "permissive-licence",
                "MDPI journals publish every article under CC-BY 4.0"),
    "10.22331": ("Quantum", "permissive-licence",
                 "the journal Quantum publishes every article under CC-BY 4.0"),
    "10.3389": ("Frontiers", "permissive-licence",
                "Frontiers journals publish every article under CC-BY 4.0"),
    "10.6028": ("NIST", "public-domain",
                "NIST publications are US Government works (17 U.S.C. §105), public domain"),
    "10.1001": ("JAMA Network", "restricted",
                "closed-access publisher default; per-article open licence not established"),
    "10.1002": ("Wiley", "restricted",
                "closed-access publisher default; per-article open licence not established"),
    "10.1007": ("Springer", "restricted",
                "closed-access publisher default; per-article open licence not established"),
    "10.1088": ("IOP Publishing", "restricted",
                "closed-access publisher default; per-article open licence not established"),
    "10.1109": ("IEEE", "restricted",
                "closed-access publisher default; per-article open licence not established"),
    "10.1136": ("BMJ", "restricted",
                "closed-access default; the BMJ Open subset is CC-BY but this item's licence is not established"),
    "10.1137": ("SIAM", "restricted",
                "closed-access publisher default; per-article open licence not established"),
    "10.1145": ("ACM", "restricted",
                "closed-access publisher default; per-article open licence not established"),
    "10.1161": ("AHA journals", "restricted",
                "closed-access publisher default; per-article open licence not established"),
}

_FIELD_RE = re.compile(r'^([a-z_]+):\s*"?(.*?)"?\s*$')


def _frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    fields = {}
    for line in text[3:end if end != -1 else None].splitlines():
        m = _FIELD_RE.match(line.strip())
        if m:
            fields[m.group(1)] = m.group(2)
    return fields


def _ledgers(case_root: Path):
    claims = case_root / "literature" / "verified_claims"
    return sorted(p for p in claims.glob("*.md")) if claims.is_dir() else []


def _is_template(stem: str, fm: dict) -> bool:
    """A scaffolding ledger, not a real source: named TEMPLATE / underscore-led,
    or carrying placeholder provenance like doi: "<DOI>"."""
    if stem.upper() in ("TEMPLATE", "_TEMPLATE") or stem.startswith("_"):
        return True
    return any(fm.get(k, "").startswith(("<", "["))
               for k in ("doi", "title", "file", "url"))


def _doi_prefix(doi: str) -> str:
    return doi.split("/", 1)[0].strip() if doi else ""


def _triage(fm: dict) -> tuple[str, str, str]:
    """Return (status, licence_or_basis, evidence_for_status)."""
    doi = fm.get("doi", "")
    prefix = _doi_prefix(doi)
    if prefix in DOI_REGISTRANTS:
        publisher, status, basis = DOI_REGISTRANTS[prefix]
        return status, basis, f"DOI registrant {prefix} = {publisher}"
    if doi:
        return "unknown", "publisher default not established for this DOI registrant", \
            f"DOI registrant {prefix} not in the triage table"
    if fm.get("pmcid"):
        return "unknown", "PMC hosting does not establish an item-level redistribution licence", \
            "pmcid present, no DOI"
    return "unknown", "no DOI or repository licence established", \
        "no DOI / pmcid in provenance"


def build_rows(repo_root: Path) -> list[dict]:
    rows = []
    for name in CASES:
        case_root = repo_root / "cases" / f"{name}_ledger"
        for ledger in _ledgers(case_root):
            fm = _frontmatter(ledger.read_text(encoding="utf-8"))
            if _is_template(ledger.stem, fm):
                continue
            local = fm.get("file", "")
            present = bool(local) and (case_root / local).exists()
            status, basis, evidence = _triage(fm)
            locator = fm.get("doi") or fm.get("pmcid") or fm.get("url") or ""
            acquire = (f"https://doi.org/{fm['doi']}" if fm.get("doi")
                       else fm.get("url", ""))
            included = present and status in CLEARED
            rows.append({
                "case": name,
                "source_key": ledger.stem,
                "title": fm.get("title") or fm.get("paper", ""),
                "locator": locator,
                "local_filename": local,
                "expected_sha256": fm.get("source_sha256", ""),
                "corpus_present": "yes" if present else "no",
                "included_in_submission": "yes" if included else "no",
                "redistribution_status": status,
                "licence_or_basis": basis,
                "evidence_for_status": evidence,
                "acquisition_command_or_instructions": acquire,
                "verification_mode": "attested",
                "notes": "" if present else "source bytes not on disk (git-ignored)",
            })
    return rows


def render_tsv(rows: list[dict]) -> str:
    out = ["\t".join(COLUMNS)]
    for r in rows:
        out.append("\t".join(str(r[c]).replace("\t", " ") for c in COLUMNS))
    return "\n".join(out) + "\n"


def summary(rows: list[dict]) -> dict:
    counts = {}
    for r in rows:
        counts[r["redistribution_status"]] = counts.get(r["redistribution_status"], 0) + 1
    return {"sources": len(rows),
            "included": sum(1 for r in rows if r["included_in_submission"] == "yes"),
            "present": sum(1 for r in rows if r["corpus_present"] == "yes"),
            "by_status": counts}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Inventory + licence-triage every case source.")
    ap.add_argument("repo_root", nargs="?", default=str(REPO))
    ap.add_argument("--out", help="write the TSV here (default: stdout)")
    ap.add_argument("--summary", action="store_true",
                    help="print a status summary to stderr")
    args = ap.parse_args(argv)
    rows = build_rows(Path(args.repo_root).resolve())
    tsv = render_tsv(rows)
    if args.out:
        Path(args.out).write_text(tsv, encoding="utf-8")
    else:
        sys.stdout.write(tsv)
    if args.summary:
        s = summary(rows)
        print(f"[INFO] {s['sources']} sources, {s['present']} present on disk, "
              f"{s['included']} includable; by status: {s['by_status']}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
