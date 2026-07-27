# === SCRIPT: Extract greppable text layers from fetched papers ===
# Purpose: build literature/extracted/<key>.txt for each paper so direct quotes
#          can be mechanically grep-verified (literature/verify_quotes.py) against
#          the primary source. Also prints a first-text snippet for an identity
#          check (right paper, not a landing-page wrapper).
#
#          The extract MUST come from the version the ledger actually cites: a
#          paper may have both a published .html (version of record) and a
#          preprint .pdf whose wording differs, so a quote verified against one
#          version would FAIL against the other. So for each key the source is
#          chosen by the ledger's `file:` frontmatter extension; absent a
#          ledger, .pdf is preferred, else .html.
# INPUTS : literature/<key>.{pdf,html} (keys passed as argv, or all on disk)
# OUTPUTS: literature/extracted/<key>.txt ; stdout identity report
from __future__ import annotations  # PEP 604 `str | None` on the 3.9 intake interpreter

import re
import sys
from pathlib import Path

from pypdf import PdfReader
from bs4 import BeautifulSoup

LIT = Path(__file__).resolve().parent
OUT = LIT / "extracted"
LEDGERS = LIT / "verified_claims"
OUT.mkdir(exist_ok=True)

# Pull the cited file extension out of a ledger's `file:` frontmatter line.
LEDGER_FILE_RE = re.compile(r'^file:\s*"?[^"\n]*\.(pdf|html|xml)"?\s*$', re.M)


def cited_extension(key: str) -> str | None:
    """Return 'pdf'/'html'/'xml' that the ledger for <key> cites, or None."""
    ledger = LEDGERS / f"{key}.md"
    if not ledger.exists():
        return None
    m = LEDGER_FILE_RE.search(ledger.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def choose_source(key: str) -> Path | None:
    """Pick the source file to extract: the ledger-cited version if present,
    else .pdf, else .html."""
    ext = cited_extension(key)
    if ext:
        cited = LIT / f"{key}.{ext}"
        if cited.exists():
            return cited
        print(f"[WARNING] {key}: ledger cites .{ext} but file missing; falling back")
    for fallback in (f"{key}.pdf", f"{key}.html"):
        p = LIT / fallback
        if p.exists():
            return p
    return None


def extract_pdf(path: Path) -> tuple[str, str]:
    """Return (full_text, identity_snippet) for a PDF."""
    reader = PdfReader(str(path))
    pages = []
    for pg in reader.pages:
        try:
            pages.append(pg.extract_text() or "")
        except Exception:  # noqa: BLE001
            pages.append("")
    full = "\n\n".join(pages)
    snippet = " ".join(pages[0].split())[:1400] if pages else ""
    return full, f"pdf pages={len(reader.pages)} chars={len(full)}"


def extract_html(path: Path) -> tuple[str, str]:
    """Return (full_text, identity_snippet) for an HTML file. Drops script/style
    so only rendered prose enters the grep layer."""
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    full = soup.get_text(" ")
    return full, f"html chars={len(full)}"


def main() -> int:
    keys = sys.argv[1:]
    if not keys:
        keys = sorted({p.stem for p in LIT.glob("*.pdf")} |
                      {p.stem for p in LIT.glob("*.html")})

    n_ok = 0
    for key in keys:
        src = choose_source(key)
        if src is None:
            print(f"[ERROR] {key}: no .pdf/.html source on disk")
            continue
        try:
            full, ident = (extract_pdf(src) if src.suffix == ".pdf"
                           else extract_html(src))
        except Exception as e:  # noqa: BLE001
            print(f"[ERROR] {key}: cannot parse {src.name} ({e})")
            continue
        (OUT / f"{key}.txt").write_text(full, encoding="utf-8")
        snippet = " ".join(full.split())[:600]
        print(f"=== {key} | {src.name} | {ident} ===")
        print(snippet)
        print()
        n_ok += 1

    print(f"[SUMMARY] extracted {n_ok}/{len(keys)} key(s) -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
