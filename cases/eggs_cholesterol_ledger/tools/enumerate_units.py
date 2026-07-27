# === SCRIPT: enumerate_units — a source's deterministic coordinate system ===
# The keystone that makes EXTRACTION.md's determinism enforceable instead of
# aspirational. Given a RAW source + its source-type, it emits the canonical
# candidate list — every structural unit with an ABSOLUTE locus and its verbatim
# text — to a COMMITTED manifest literature/units/<key>.units.json. The manifest
# travels (the raw .html/.pdf is git-ignored), so the quote-within-unit check
# (tools/check_units.py) and the repro keep/drop measure run OFFLINE against it.
#
# It enumerates the candidate UNIVERSE only; it never applies the Anchor-B
# keep/drop filter — that one judgement stays the agent/curator's, and is the
# single thing the repro residual measures. Honesty boundary: enumeration is
# deterministic only to the degree the source is structurally parseable. Clean
# HTML enumerates fully; a collapsed-space PDF degrades to coarse page/paragraph
# loci and sets fully_enumerable=false, so the gate never blocks on it.
# INPUTS : literature/<key>.{html,pdf} (raw); source-type (CLI or inferred).
# OUTPUTS: literature/units/<key>.units.json ; stdout summary. --check re-emits
#          and asserts byte-identical (a determinism self-test), exit 1 on drift.
# Run    : python3 tools/enumerate_units.py --key daniel --source-type probabilistic-analysis
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# Reuse the verbatim verifier's normalisation + body hash so a unit's identity
# and the quote-within-unit check share ONE definition of "same text".
sys.path.insert(0, str(REPO_ROOT / "literature"))
from verify_quotes import norm, sha256_text  # noqa: E402

ENUMERATOR_VERSION = "1"
# Block elements that carry an asserting unit, in the order a reader meets them.
HTML_BLOCK_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote")
# A unit must have at least this many normalised chars to be addressable (matches
# verify_quotes MIN_SEGMENT_CHARS — shorter spans are not assertions worth a locus).
UNIT_MIN_CHARS = 25


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_warning(msg: str) -> None:
    print(f"[WARNING] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def manifest_digest(manifest: dict) -> str:
    """Canonical sha256 over the manifest EXCEPT manifest_sha256 — the internal
    seal a clone/CI recomputes corpus-free. Same canonicalisation discipline as
    verify_quotes.run_record_digest (sorted keys, UTF-8)."""
    payload = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    return sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False))


def enumerate_html(raw: str) -> list[dict]:
    """Leaf block elements in document order → units. A block with a nested block
    descendant is a container (skipped) so its text is not double-counted; only
    leaves (the actual paragraphs/items) become units. Deterministic: the order
    is the document's, the locus is the running ordinal over kept leaves."""
    from bs4 import BeautifulSoup  # intake-only; lazy so the stdlib tools + check_units
                                   # gate import without it (matches pypdf in enumerate_pdf)
    soup = BeautifulSoup(raw, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    units: list[dict] = []
    n = 0
    for el in soup.find_all(HTML_BLOCK_TAGS):
        if el.find(HTML_BLOCK_TAGS) is not None:
            continue  # container, not a leaf block
        text = el.get_text(" ", strip=True)
        if len(norm(text)) < UNIT_MIN_CHARS:
            continue
        n += 1
        units.append({"locus": f"p{n}", "text": text,
                      "unit_sha256": sha256_text(norm(text))})
    return units


def enumerate_pdf(raw_bytes: bytes) -> list[dict]:
    """Coarse page/paragraph units from a PDF. pypdf cannot recover reliable word
    or block boundaries (collapsed spacing), so this is an HONEST DEGRADE: loci
    are page<n>-p<m> over blank-line-split paragraphs, and the caller marks the
    manifest fully_enumerable=false so the gate treats it as advisory only."""
    from io import BytesIO

    from pypdf import PdfReader
    reader = PdfReader(BytesIO(raw_bytes))
    units: list[dict] = []
    for pi, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            text = ""
        paras = [p for p in text.split("\n\n") if len(norm(p)) >= UNIT_MIN_CHARS]
        for mi, para in enumerate(paras, start=1):
            units.append({"locus": f"page{pi}-p{mi}", "text": " ".join(para.split()),
                          "unit_sha256": sha256_text(norm(para))})
    return units


def choose_raw(lit_dir: Path, key: str) -> Path | None:
    """The raw source for <key>: .html preferred (clean structure), else .pdf."""
    for ext in ("html", "pdf"):
        p = lit_dir / f"{key}.{ext}"
        if p.is_file():
            return p
    return None


def build_manifest(lit_dir: Path, key: str, source_type: str,
                   enumerated_date: str) -> dict:
    """Enumerate <key> into a sealed manifest dict (does not write)."""
    raw_path = choose_raw(lit_dir, key)
    if raw_path is None:
        raise FileNotFoundError(f"no raw literature/{key}.html|pdf to enumerate")
    raw_bytes = raw_path.read_bytes()
    if raw_path.suffix == ".html":
        units = enumerate_html(raw_bytes.decode("utf-8", errors="ignore"))
        addressing, fully = "html-block", True
    else:
        units = enumerate_pdf(raw_bytes)
        addressing, fully = "pdf-page-para", False
    manifest = {
        "key": key,
        "source_type": source_type,
        "source_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "enumerator_version": ENUMERATOR_VERSION,
        "enumerated_date": enumerated_date,
        "addressing": addressing,
        "fully_enumerable": fully,
        "units": units,
    }
    manifest["manifest_sha256"] = manifest_digest(manifest)
    return manifest


def render(manifest: dict) -> str:
    """Canonical on-disk form (stable bytes so --check can assert determinism)."""
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Emit a source's committed candidate manifest (coordinate system).")
    ap.add_argument("--key", required=True, help="ledger/source key (e.g. daniel)")
    ap.add_argument("--source-type", required=True, help="EXTRACTION.md source-type row")
    ap.add_argument("--literature-dir", default=str(REPO_ROOT / "literature"),
                    help="override literature/ location (cases/tests)")
    ap.add_argument("--date", default="00000000",
                    help="enumerated_date stamp (caller supplies; no clock here)")
    ap.add_argument("--check", action="store_true",
                    help="re-enumerate and assert byte-identical to the committed manifest")
    args = ap.parse_args(argv)

    lit_dir = Path(args.literature_dir)
    out_dir = lit_dir / "units"
    out_path = out_dir / f"{args.key}.units.json"

    if args.check:
        if not out_path.is_file():
            log_error(f"--check: no committed manifest at {out_path}")
            return 1
        existing = json.loads(out_path.read_text(encoding="utf-8"))
        fresh = build_manifest(lit_dir, args.key, existing.get("source_type", args.source_type),
                               existing.get("enumerated_date", args.date))
        if render(fresh) == out_path.read_text(encoding="utf-8"):
            log_info(f"{args.key}: re-enumeration byte-identical — deterministic.")
            return 0
        log_error(f"{args.key}: re-enumeration DIFFERS from the committed manifest "
                  "(non-deterministic or raw source changed).")
        return 1

    manifest = build_manifest(lit_dir, args.key, args.source_type, args.date)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(manifest), encoding="utf-8")
    n = len(manifest["units"])
    flag = "" if manifest["fully_enumerable"] else " (fully_enumerable=false — coarse PDF)"
    log_info(f"{args.key}: {n} unit(s) via {manifest['addressing']} -> {out_path}{flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
