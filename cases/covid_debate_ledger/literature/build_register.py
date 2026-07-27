#!/usr/bin/env python3
# === SCRIPT: build_register.py ===
# Purpose: Build literature/REGISTER.tsv and REGISTER_review.md from the
#          contents of literature/. Also audits every file for a mismatch
#          between its filename-claimed author/year and the actual author/year
#          derived from the file's metadata (HTML meta tags, PDF /Title+/Author,
#          embedded DOI). Produces canonical symlinks so the citation hook can
#          resolve every paper by its canonical <author>_<year>[suffix].<ext>.
#
# Inputs:
#   - literature/*.pdf, *.html, *.xml (flat; verified_claims/ is skipped)
#   - literature/verified_claims/*.md (to mark status=verified where a claims
#     file already exists)
#
# Outputs:
#   - literature/REGISTER.tsv                 (authoritative paper index)
#   - literature/REGISTER_review.md           (human-readable triage report)
#   - literature/<author>_<year>.<ext>        (canonical symlinks, non-dry-run)
#
# Usage:
#   python3 build_register.py --dry-run      # discovery only; no symlinks
#   python3 build_register.py                # creates symlinks
#
# Never deletes or renames existing files. Unknown/mislabelled files stay in
# place with status flagged in REGISTER.tsv for manual resolution.

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader


def ascii_fold(s: str) -> str:
    """Strip diacritics and apostrophes; lowercase. Preserves hyphens and
    underscores so filename regex separators still work.
    'Barrón' → 'barron', 'Tørresen' → 'torresen', "O'Loughlin" → 'oloughlin'."""
    if not s:
        return ""
    n = unicodedata.normalize("NFKD", s)
    folded = "".join(c for c in n if not unicodedata.combining(c)).lower()
    folded = folded.replace("ø", "o").replace("ł", "l").replace("æ", "ae")
    for ch in ("'", "\u2019", "\u2018"):
        folded = folded.replace(ch, "")
    return folded


def surname_key(s: str) -> str:
    """Tightly normalised surname for equality comparison: drop hyphens too,
    so 'Smith-Jones' == 'smithjones', 'Van-Dijk' == 'vandijk'."""
    return ascii_fold(s).replace("-", "")


# --- Constants --------------------------------------------------------------

# Resolve project paths relative to THIS script's location (literature/build_register.py)
# so the pipeline is portable across machines/clones. PROJECT_ROOT = repo root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LITERATURE_DIR = PROJECT_ROOT / "literature"
CLAIMS_DIR = LITERATURE_DIR / "verified_claims"
# status=verified is driven solely by the presence of a
# verified_claims/<author>_<year>.md ledger.

REGISTER_TSV = LITERATURE_DIR / "REGISTER.tsv"
REGISTER_MD = LITERATURE_DIR / "REGISTER_review.md"
OVERRIDES_TSV = LITERATURE_DIR / "OVERRIDES.tsv"

KNOWN_EXTS = {".pdf", ".html", ".xml"}
SKIP_DIRS = {"verified_claims", "_archive"}

# Size floors below which a file cannot plausibly contain a full paper.
# Used to tag landing pages / Cloudflare challenges / PMC "restricted" HTMLs.
HTML_SIZE_FLOOR_BYTES = 20 * 1024     # 20 KB
PDF_SIZE_FLOOR_BYTES = 50 * 1024      # 50 KB
XML_SIZE_FLOOR_BYTES = 5 * 1024       # 5 KB (bibliographic XML can be small)

# Sentinel phrases that mark HTML as a landing page / access-blocked page
# rather than a real paper. Case-insensitive.
LANDING_PAGE_SENTINELS = re.compile(
    r"just a moment\.\.\."
    r"|enable javascript and cookies to continue"
    r"|access to this article is restricted"
    r"|you do not have access"
    r"|subscribe to (read|view)"
    r"|purchase (this )?article"
    r"|sign in to continue"
    r"|please log in"
    r"|cloudflare"
    r"|institutional login"
    r"|request access",
    re.IGNORECASE,
)

# Filename parse: optional leading junk, then <author_tokens>_year[suffix]
# Author group may contain multiple surnames joined by underscore/hyphen
# (e.g. "smith_jones", "lee-park"). We take the FIRST token as the canonical
# first-author surname.
FILENAME_PATTERN = re.compile(
    r"^([a-z][a-z_\-]+?)[_\-](\d{4})([a-z]?)(?:[_\-](.+))?$", re.IGNORECASE
)
# DOI extraction regex
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")


# --- Record dataclass-ish ---------------------------------------------------

def new_record(path: Path) -> dict:
    return {
        "path": path,
        "filename": path.name,
        "extension": path.suffix.lstrip(".").lower(),
        "size_kb": round(path.stat().st_size / 1024, 1),
        # Filename-claimed identity
        "fn_author": None,
        "fn_year": None,
        "fn_suffix": None,   # single letter if filename encodes a collision (2015a vs 2015b)
        # Metadata-derived identity
        "meta_author": None,
        "meta_year": None,
        "meta_title": None,
        "meta_journal": None,
        "meta_doi": None,
        # Status
        "is_landing_page": False,
        "mismatch": False,
        "parse_failed": False,
        "notes": [],
        # Final resolved identity (filled after all parsing)
        "author": None,
        "year": None,
        "key": None,
        "status": "unknown",
    }


# --- Filename parser --------------------------------------------------------

def parse_filename(rec: dict) -> None:
    stem = ascii_fold(rec["path"].stem)
    m = FILENAME_PATTERN.match(stem)
    if m:
        # Reduce compound author groups ("smith_jones") to first surname.
        first_author_token = re.split(r"[_\-]", m.group(1), maxsplit=1)[0]
        rec["fn_author"] = first_author_token
        rec["fn_year"] = m.group(2)
        rec["fn_suffix"] = m.group(3) or ""
        return
    # Fallback: try a year anywhere in stem; no author claim
    ym = YEAR_PATTERN.search(stem)
    if ym:
        rec["fn_year"] = ym.group(0)


# --- HTML parser ------------------------------------------------------------

def _meta_contents(soup: BeautifulSoup, name: str) -> list[str]:
    vals = []
    for m in soup.find_all("meta", attrs={"name": name}):
        c = (m.get("content") or "").strip()
        if c:
            vals.append(c)
    return vals


def parse_html(rec: dict) -> None:
    try:
        raw = rec["path"].read_text(errors="ignore", encoding="utf-8")
    except Exception as e:
        rec["parse_failed"] = True
        rec["notes"].append(f"read_error: {e}")
        return

    # Sentinel check on raw content first (BS-free is fine here)
    head_chunk = raw[:8000]
    if LANDING_PAGE_SENTINELS.search(head_chunk):
        rec["is_landing_page"] = True
        rec["notes"].append("sentinel_phrase_matched")

    # Very short HTML (< floor) also landing page by size
    if rec["path"].stat().st_size < HTML_SIZE_FLOOR_BYTES:
        rec["is_landing_page"] = True
        rec["notes"].append(f"html_below_size_floor_{HTML_SIZE_FLOOR_BYTES}_bytes")

    try:
        soup = BeautifulSoup(raw, "lxml")
    except Exception as e:
        rec["parse_failed"] = True
        rec["notes"].append(f"bs_parse_error: {e}")
        return

    # Title
    titles = _meta_contents(soup, "citation_title") or _meta_contents(soup, "DC.Title")
    if titles:
        rec["meta_title"] = titles[0]
    elif soup.title and soup.title.string:
        rec["meta_title"] = soup.title.string.strip()

    # First author
    authors = _meta_contents(soup, "citation_author") or _meta_contents(soup, "DC.Creator")
    if authors:
        first = authors[0]
        # Surname is typically the last space-separated token for "Given Surname"
        # or the first comma-separated token for "Surname, Given"
        if "," in first:
            rec["meta_author"] = ascii_fold(first.split(",", 1)[0].strip())
        else:
            parts = first.strip().split()
            rec["meta_author"] = ascii_fold(parts[-1]) if parts else None

    # Year
    dates = (_meta_contents(soup, "citation_publication_date")
             or _meta_contents(soup, "citation_date")
             or _meta_contents(soup, "DC.Date"))
    for d in dates:
        ym = YEAR_PATTERN.search(d)
        if ym:
            rec["meta_year"] = ym.group(0)
            break

    # DOI
    dois = _meta_contents(soup, "citation_doi") or _meta_contents(soup, "DC.Identifier")
    for d in dois:
        mm = DOI_PATTERN.search(d)
        if mm:
            rec["meta_doi"] = mm.group(0).lower()
            break

    # Journal
    jrn = _meta_contents(soup, "citation_journal_title")
    if jrn:
        rec["meta_journal"] = jrn[0]


# --- PDF parser -------------------------------------------------------------

def parse_pdf(rec: dict) -> None:
    if rec["path"].stat().st_size < PDF_SIZE_FLOOR_BYTES:
        rec["is_landing_page"] = True
        rec["notes"].append(f"pdf_below_size_floor_{PDF_SIZE_FLOOR_BYTES}_bytes")

    # Sniff header: some files ending in .pdf are actually HTML error pages
    try:
        with rec["path"].open("rb") as fh:
            head = fh.read(16)
    except Exception as e:
        rec["parse_failed"] = True
        rec["notes"].append(f"pdf_header_read_error: {e}")
        return
    if not head.startswith(b"%PDF"):
        rec["is_landing_page"] = True
        rec["notes"].append("pdf_extension_but_non_pdf_content")
        # Fall through to HTML parsing as best-effort
        parse_html(rec)
        return

    try:
        reader = PdfReader(str(rec["path"]))
    except Exception as e:
        rec["parse_failed"] = True
        rec["notes"].append(f"pdf_read_error: {e}")
        return

    meta = reader.metadata or {}
    title = str(meta.get("/Title") or "").strip()
    author = str(meta.get("/Author") or "").strip()

    if title and len(title) > 4 and "PII:" not in title:
        rec["meta_title"] = title
    if author:
        # Author metadata varies: "Surname, Given" or "Given Surname" or CSV of authors
        first_author = author.split(",")[0].strip() if "," in author else author.split(";")[0].split(" and ")[0].strip()
        # Surname heuristic: if there's a comma, it's "Surname, Given"; else last token
        if "," in author.split(";")[0]:
            raw = author.split(",", 1)[0].strip()
            rec["meta_author"] = ascii_fold(raw.split()[-1]) if raw else None
        else:
            parts = first_author.split()
            rec["meta_author"] = ascii_fold(parts[-1]) if parts else None

    # DOI + year from first 3 pages of text
    text = ""
    for pg in reader.pages[:3]:
        try:
            text += (pg.extract_text() or "")[:4000]
        except Exception:
            continue

    if text:
        mm = DOI_PATTERN.search(text)
        if mm:
            rec["meta_doi"] = mm.group(0).rstrip(".").lower()
        ym = YEAR_PATTERN.search(text)
        if ym:
            rec["meta_year"] = ym.group(0)

    # CreationDate as fallback year
    if not rec["meta_year"]:
        cd = str(meta.get("/CreationDate") or "")
        ym = YEAR_PATTERN.search(cd)
        if ym:
            rec["meta_year"] = ym.group(0)
            rec["notes"].append("year_from_creation_date_only")


# --- XML parser -------------------------------------------------------------

def parse_xml(rec: dict) -> None:
    try:
        raw = rec["path"].read_text(errors="ignore", encoding="utf-8")
    except Exception as e:
        rec["parse_failed"] = True
        rec["notes"].append(f"xml_read_error: {e}")
        return

    try:
        soup = BeautifulSoup(raw, "lxml-xml")
    except Exception:
        try:
            soup = BeautifulSoup(raw, "xml")
        except Exception as e:
            rec["parse_failed"] = True
            rec["notes"].append(f"xml_parse_error: {e}")
            return

    # PubMed XML shapes
    t = soup.find("ArticleTitle") or soup.find("article-title")
    if t and t.get_text(strip=True):
        rec["meta_title"] = t.get_text(strip=True)[:300]

    a = soup.find("LastName") or soup.find("surname")
    if a and a.get_text(strip=True):
        rec["meta_author"] = ascii_fold(a.get_text(strip=True))

    y = soup.find("Year") or soup.find("year")
    if y and y.get_text(strip=True):
        ym = YEAR_PATTERN.search(y.get_text())
        if ym:
            rec["meta_year"] = ym.group(0)

    # DOI
    for tag in soup.find_all(["ArticleId", "ELocationID", "article-id"]):
        s = tag.get_text() or ""
        mm = DOI_PATTERN.search(s)
        if mm:
            rec["meta_doi"] = mm.group(0).lower()
            break


# --- Resolve canonical identity --------------------------------------------

def resolve_identity(rec: dict) -> None:
    """Decide on final (author, year) using precedence: metadata > filename."""
    rec["author"] = rec["meta_author"] or rec["fn_author"]
    rec["year"] = rec["meta_year"] or rec["fn_year"]

    # Mismatch check uses surname_key (hyphen-insensitive) and tolerates a
    # ±1 year difference to accept the common "online vs print year" split.
    fn_a = surname_key(rec["fn_author"]) if rec["fn_author"] else ""
    mt_a = surname_key(rec["meta_author"]) if rec["meta_author"] else ""
    if fn_a and mt_a and fn_a != mt_a:
        # Accept if one is a prefix of the other with ≥5 shared chars (handles a
        # compound surname in the filename vs a single surname in the metadata,
        # e.g. "Smith-Jones" → "smith", "Van-der-Berg" → "van der berg").
        if not (len(fn_a) >= 5 and len(mt_a) >= 5 and (fn_a.startswith(mt_a) or mt_a.startswith(fn_a))):
            rec["mismatch"] = True
            rec["notes"].append(
                f"filename_says_{rec['fn_author']}_but_metadata_says_{rec['meta_author']}"
            )

    if rec["fn_year"] and rec["meta_year"]:
        try:
            dy = abs(int(rec["fn_year"]) - int(rec["meta_year"]))
        except ValueError:
            dy = 99
        if dy > 1:
            rec["mismatch"] = True
            rec["notes"].append(
                f"filename_says_{rec['fn_year']}_but_metadata_says_{rec['meta_year']}"
            )


# --- OVERRIDES.tsv ----------------------------------------------------------
#
# Force-resolves records that auto-parsing classifies wrongly because of a
# corrupt PDF /CreationDate, a reference-section DOI, or similar metadata bug.
# Rows override filename-claimed and metadata-derived identity. Only filenames
# whose *content* is confirmed correct belong here (usual evidence: an
# existing verified_claims/<author>_<year>.md file).


def load_overrides() -> dict[str, dict]:
    """Return {filename: {author, year, status, reason}}. Empty dict if the
       file is absent. Comment lines (beginning with '#') and blank lines are
       skipped. Unknown columns are ignored."""
    if not OVERRIDES_TSV.exists():
        return {}
    out: dict[str, dict] = {}
    with OVERRIDES_TSV.open() as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            fn = (row.get("filename") or "").strip()
            if not fn or fn.startswith("#"):
                continue
            out[fn] = {
                "author": ascii_fold((row.get("author") or "").strip()) or None,
                "year": (row.get("year") or "").strip() or None,
                "status": (row.get("status") or "").strip() or None,
                "reason": (row.get("reason") or "").strip(),
            }
    return out


def apply_overrides(records: list[dict], overrides: dict[str, dict]) -> int:
    """Mutate records in place: force-set author/year, clear mismatch flag,
       stash an optional forced status for _finalise_cluster to honour.
       Returns count of records overridden."""
    if not overrides:
        return 0
    n = 0
    for rec in records:
        ov = overrides.get(rec["filename"])
        if not ov:
            continue
        if ov["author"]:
            rec["author"] = ov["author"]
            rec["meta_author"] = ov["author"]
        if ov["year"]:
            rec["year"] = ov["year"]
            rec["meta_year"] = ov["year"]
        rec["mismatch"] = False
        # Drop prior mismatch notes — they no longer apply
        rec["notes"] = [s for s in rec["notes"]
                        if not s.startswith("filename_says_")]
        rec["notes"].append(f"override_applied: {ov['reason']}")
        if ov["status"]:
            rec["_force_status"] = ov["status"]
        n += 1
    return n


# --- Verified-claims cross-reference ----------------------------------------

def load_verified_keys() -> set[str]:
    """Keys (author_year) with a verified_claims file already."""
    if not CLAIMS_DIR.exists():
        return set()
    keys = set()
    for p in CLAIMS_DIR.iterdir():
        if p.suffix == ".md" and p.stem != "TEMPLATE":
            # Strip any trailing _keyword so bare "<author>_<year>" and
            # "<author>_<year>_topic" both canonicalise to author_year.
            stem = p.stem.lower()
            m = re.match(r"^([a-z][a-z\-_]*?)_(\d{4})([a-z]?)", stem)
            if m:
                keys.add(f"{m.group(1)}_{m.group(2)}{m.group(3)}")
    return keys


# --- Ledger frontmatter as identity authority -------------------------------

def load_ledger_records() -> dict[str, dict]:
    """Per key, the source-identity a ledger frontmatter records — the identity
    authority over the filename/metadata heuristics. Carries the durable locators
    (doi/pmcid/url) and the source file alongside source_sha256 so the register
    can flag a ledger that names its bytes but no durable source."""
    from verify_quotes import read_frontmatter
    out: dict[str, dict] = {}
    if not CLAIMS_DIR.exists():
        return out
    for p in CLAIMS_DIR.iterdir():
        if p.suffix != ".md" or p.stem == "TEMPLATE":
            continue
        m = re.match(r"^([a-z][a-z\-_]*?)_(\d{4})([a-z]?)", p.stem.lower())
        if not m:
            continue
        key = f"{m.group(1)}_{m.group(2)}{m.group(3)}"
        fm = read_frontmatter(p)
        out[key] = {"doi": (fm.get("doi") or "").lower().strip(),
                    "pmcid": (fm.get("pmcid") or "").strip(),
                    "url": (fm.get("url") or "").strip(),
                    "file": (fm.get("file") or "").strip(),
                    "source_sha256": (fm.get("source_sha256") or "").strip()}
    return out


def flag_ledger_divergence(records: list[dict]) -> int:
    """Flag any canonical file whose DOI or source bytes disagree with the ledger
    attesting its key (status=mismatch, so it is excluded from canonical
    symlinks). The ledger frontmatter wins. Returns the count flagged."""
    from verify_quotes import sha256_file
    ledgers = load_ledger_records()
    if not ledgers:
        return 0
    hex64 = re.compile(r"^[0-9a-f]{64}$")
    flagged = 0
    for rec in records:
        key = rec.get("key")
        if not key or rec["status"].startswith("duplicate_of:"):
            continue
        lr = ledgers.get(key)
        if not lr:
            continue
        diverged = False
        ledger_doi, file_doi = lr["doi"], (rec.get("meta_doi") or "").lower()
        if ledger_doi and file_doi and ledger_doi not in file_doi and file_doi not in ledger_doi:
            rec["notes"].append(f"doi_differs_from_ledger: file={file_doi} ledger={ledger_doi}")
            diverged = True
        if hex64.match(lr["source_sha256"]):
            try:
                actual = sha256_file(rec["path"])
            except OSError:
                actual = ""
            if actual and actual != lr["source_sha256"]:
                rec["notes"].append("source_bytes_differ_from_ledger_hash")
                diverged = True
        if diverged:
            rec["status"] = "mismatch"
            flagged += 1
    return flagged


# --- Grouping & key assignment ---------------------------------------------

def _best_file_sort_key(rec: dict) -> tuple:
    """Lower tuple = preferred as canonical file for a key."""
    ext_rank = {"pdf": 0, "html": 1, "xml": 2}.get(rec["extension"], 3)
    landing_penalty = 1 if rec["is_landing_page"] else 0
    # Larger size is better → negate
    size_pref = -rec["size_kb"]
    # Simpler filename (starts with author_year, no extra suffix) preferred
    simplicity = 0 if re.fullmatch(r"[a-z]+_\d{4}[a-z]?\.\w+", rec["filename"].lower()) else 1
    return (landing_penalty, ext_rank, simplicity, size_pref, rec["filename"])


def assign_keys_and_status(records: list[dict],
                           verified_claims_keys: set[str]) -> None:
    # Group by (author, year, meta_doi-if-present). If DOIs differ within the
    # same (author, year), they are genuinely different papers → suffix a/b.
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for rec in records:
        if not rec["author"] or not rec["year"]:
            continue
        groups[(rec["author"], rec["year"])].append(rec)

    for (author, year), recs in groups.items():
        # Split within the group by DOI; files lacking a DOI cluster together
        doi_clusters: dict[str, list[dict]] = defaultdict(list)
        for rec in recs:
            doi_clusters[rec["meta_doi"] or "_nodoi"].append(rec)

        # Assign suffixes if >1 distinct DOI (ignoring the nodoi bucket unless
        # it is the only bucket)
        real_dois = [d for d in doi_clusters if d != "_nodoi"]
        if len(real_dois) <= 1:
            # Single paper (plus possibly some unlabelled copies merged in)
            key = f"{author}_{year}"
            cluster = sum(doi_clusters.values(), [])
            _finalise_cluster(cluster, key, verified_claims_keys)
        else:
            # Multiple distinct DOIs → a, b, c by DOI alpha sort (deterministic)
            for i, doi in enumerate(sorted(real_dois)):
                suf = chr(ord("a") + i)
                key = f"{author}_{year}{suf}"
                _finalise_cluster(doi_clusters[doi], key, verified_claims_keys)
            # Unlabelled DOI-less files left as status=unknown in this group
            for rec in doi_clusters.get("_nodoi", []):
                rec["key"] = f"{author}_{year}?"
                rec["status"] = "unknown"
                rec["notes"].append("could_not_assign_to_a_b_suffix_without_doi")


def _finalise_cluster(cluster: list[dict], key: str,
                      verified_claims_keys: set[str]) -> None:
    cluster_sorted = sorted(cluster, key=_best_file_sort_key)
    canonical = cluster_sorted[0]
    canonical["key"] = key

    # OVERRIDES.tsv wins over all auto-classification
    forced = canonical.get("_force_status")
    if forced:
        canonical["status"] = forced
    elif canonical["is_landing_page"]:
        canonical["status"] = "landing_page"
    elif canonical["mismatch"]:
        canonical["status"] = "mismatch"
    elif key in verified_claims_keys:
        canonical["status"] = "verified"
    else:
        canonical["status"] = "downloaded"

    for other in cluster_sorted[1:]:
        other["key"] = key
        other["status"] = f"duplicate_of:{key}"


# --- Output writers --------------------------------------------------------

REGISTER_COLUMNS = [
    "key", "filename", "extension", "title", "doi", "journal",
    "year", "first_author", "status", "size_kb", "added_on", "notes",
]


def write_register_tsv(records: list[dict]) -> None:
    today = dt.date.today().isoformat()
    with REGISTER_TSV.open("w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        w.writerow(REGISTER_COLUMNS)
        for rec in sorted(records, key=lambda r: (r.get("key") or "~", r["filename"])):
            w.writerow([
                rec.get("key") or "",
                rec["filename"],
                rec["extension"],
                (rec["meta_title"] or "").replace("\t", " ").replace("\n", " ")[:300],
                rec.get("meta_doi") or "",
                (rec.get("meta_journal") or "").replace("\t", " "),
                rec.get("year") or "",
                rec.get("author") or "",
                rec["status"],
                rec["size_kb"],
                today,
                "; ".join(rec["notes"]),
            ])
    print(f"[INFO] wrote {REGISTER_TSV} ({len(records)} rows)")


def write_review_md(records: list[dict]) -> None:
    n = len(records)
    keys_seen = {r["key"] for r in records if r.get("key") and not r["status"].startswith("duplicate_of:")}
    n_keys = len(keys_seen)

    by_status: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        by_status[rec["status"].split(":")[0]].append(rec)

    lines: list[str] = []
    lines.append(f"# Literature Register — Review Report")
    lines.append("")
    lines.append(f"Generated: {dt.date.today().isoformat()}")
    lines.append(f"Files inspected: **{n}**")
    lines.append(f"Unique canonical papers: **{n_keys}**")
    lines.append("")
    lines.append("## Status counts")
    lines.append("")
    for status in ["verified", "downloaded", "mismatch", "landing_page", "duplicate_of", "unknown"]:
        lines.append(f"- `{status}`: {len(by_status.get(status, []))}")
    lines.append("")

    # Mismatches first — most urgent (mislabelled files are an integrity issue)
    if by_status.get("mismatch"):
        lines.append("## Filename ↔ metadata mismatches (review manually)")
        lines.append("")
        lines.append("The filename claims one paper but the embedded metadata (HTML meta tags / PDF /Title+/Author / embedded DOI) describes a different paper. These files MUST NOT be cited under their filename-claimed identity.")
        lines.append("")
        lines.append("| filename | filename claims | metadata says | DOI | title |")
        lines.append("|---|---|---|---|---|")
        for rec in sorted(by_status["mismatch"], key=lambda r: r["filename"]):
            fn_id = f"{rec['fn_author'] or '?'}_{rec['fn_year'] or '?'}"
            mt_id = f"{rec['meta_author'] or '?'}_{rec['meta_year'] or '?'}"
            lines.append(
                f"| `{rec['filename']}` | {fn_id} | {mt_id} | "
                f"{rec.get('meta_doi') or ''} | {(rec['meta_title'] or '')[:80]} |"
            )
        lines.append("")

    # Landing pages
    if by_status.get("landing_page"):
        lines.append("## Landing pages / access-blocked HTMLs (must be re-downloaded)")
        lines.append("")
        lines.append("Files that are below the size floor or contain Cloudflare/PMC access-denial markers. They are kept in place but must not be used as evidence. Re-download the underlying paper; then re-run this script.")
        lines.append("")
        lines.append("| filename | size KB | claimed | reason |")
        lines.append("|---|---|---|---|")
        for rec in sorted(by_status["landing_page"], key=lambda r: r["size_kb"]):
            claim = f"{rec['author'] or '?'}_{rec['year'] or '?'}"
            reason = "; ".join(n for n in rec["notes"] if "sentinel" in n or "below_size_floor" in n)
            lines.append(f"| `{rec['filename']}` | {rec['size_kb']} | {claim} | {reason} |")
        lines.append("")

    # Unknowns
    if by_status.get("unknown"):
        lines.append("## Could not identify author + year")
        lines.append("")
        lines.append("| filename | size KB | notes |")
        lines.append("|---|---|---|")
        for rec in sorted(by_status["unknown"], key=lambda r: r["filename"]):
            lines.append(f"| `{rec['filename']}` | {rec['size_kb']} | {'; '.join(rec['notes'])} |")
        lines.append("")

    # Duplicate summary (top 20 keys with most duplicates)
    dup_groups: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        if rec["status"].startswith("duplicate_of:"):
            tgt = rec["status"].split(":", 1)[1]
            dup_groups[tgt].append(rec)
    if dup_groups:
        lines.append("## Duplicate clusters (top 20)")
        lines.append("")
        lines.append("Canonical file for each key is kept; duplicates are recorded but not moved.")
        lines.append("")
        top = sorted(dup_groups.items(), key=lambda kv: -len(kv[1]))[:20]
        lines.append("| key | n duplicates | example filenames |")
        lines.append("|---|---|---|")
        for key, dups in top:
            examples = ", ".join(f"`{r['filename']}`" for r in dups[:3])
            lines.append(f"| `{key}` | {len(dups)} | {examples} |")
        lines.append("")

    REGISTER_MD.write_text("\n".join(lines))
    print(f"[INFO] wrote {REGISTER_MD}")


# --- Symlink creator --------------------------------------------------------

def create_canonical_symlinks(records: list[dict], dry_run: bool) -> list[tuple[str, str]]:
    """Create literature/<key>.<ext> → literature/<filename> for canonical
       records whose filename is not already canonical. Returns list of
       (symlink_name, target_name) pairs, dry-run or not."""
    planned: list[tuple[str, str]] = []
    for rec in records:
        if not rec.get("key"):
            continue
        if rec["status"] in {"unknown", "landing_page", "mismatch"}:
            continue
        if rec["status"].startswith("duplicate_of:"):
            continue
        # Canonical filename for this key
        canonical_name = f"{rec['key']}.{rec['extension']}"
        if rec["filename"] == canonical_name:
            continue
        link_path = LITERATURE_DIR / canonical_name
        # Do not clobber an existing file or symlink
        if link_path.exists() or link_path.is_symlink():
            continue
        planned.append((canonical_name, rec["filename"]))
        if not dry_run:
            os.symlink(rec["filename"], link_path)
    return planned


# --- Main -------------------------------------------------------------------

def collect_files() -> list[Path]:
    paths: list[Path] = []
    for p in LITERATURE_DIR.iterdir():
        if p.is_dir() and p.name in SKIP_DIRS:
            continue
        if p.is_dir():
            continue
        if p.name.startswith("."):
            continue
        if p.is_symlink() and not p.exists():
            print(f"[WARNING] skipping broken symlink: {p.name}")
            continue
        if p.name in {"REGISTER.tsv", "REGISTER_review.md", "check.sh"}:
            continue
        if p.suffix.lower() not in KNOWN_EXTS:
            continue
        paths.append(p)
    return sorted(paths)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Discovery only; emit REGISTER.tsv and REGISTER_review.md but create no symlinks.")
    args = ap.parse_args()

    print(f"[INFO] literature dir: {LITERATURE_DIR}")
    paths = collect_files()
    print(f"[INFO] {len(paths)} files to inspect")

    records: list[dict] = []
    for i, p in enumerate(paths, 1):
        if i % 25 == 0:
            print(f"[INFO]   processed {i}/{len(paths)}")
        rec = new_record(p)
        parse_filename(rec)
        ext = rec["extension"]
        if ext == "html":
            parse_html(rec)
        elif ext == "pdf":
            parse_pdf(rec)
        elif ext == "xml":
            parse_xml(rec)
        resolve_identity(rec)
        records.append(rec)

    overrides = load_overrides()
    n_overridden = apply_overrides(records, overrides)
    print(f"[INFO] OVERRIDES.tsv entries: {len(overrides)}; applied to {n_overridden} records")

    verified_claims_keys = load_verified_keys()
    print(f"[INFO] verified_claims keys: {len(verified_claims_keys)}")

    assign_keys_and_status(records, verified_claims_keys)

    n_diverged = flag_ledger_divergence(records)
    if n_diverged:
        print(f"[WARNING] {n_diverged} file(s) diverge from their ledger's "
              "attested identity (DOI/source hash) — flagged status=mismatch")

    write_register_tsv(records)
    write_review_md(records)

    planned_links = create_canonical_symlinks(records, dry_run=args.dry_run)
    verb = "would create" if args.dry_run else "created"
    print(f"[INFO] {verb} {len(planned_links)} canonical symlinks")
    for name, target in planned_links[:15]:
        print(f"[INFO]   {name} -> {target}")
    if len(planned_links) > 15:
        print(f"[INFO]   ... and {len(planned_links) - 15} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())
