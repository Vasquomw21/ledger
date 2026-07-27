# === SCRIPT: check_units — the quote-within-unit gate (units_layer) ===
# The offline half of the coordinate-system guarantee (enumerate_units.py is the
# write-time half). For every ledger claim that carries a **Locus:**, it attests
# corpus-free that: (1) the locus resolves to a unit in the committed manifest
# literature/units/<key>.units.json; (2) the claim's quote is a verbatim span
# WITHIN that unit's text (norm-substring, the same normalisation as the verbatim
# gate); (3) the manifest's seal is internally consistent and its source_sha256
# matches the ledger's stamp (three-way bind raw<->manifest<->ledger).
#
# This makes the claim's address mechanical (slug = locus) and its span bounded
# (must fall inside the addressed unit) — collapsing two of EXTRACTION.md's three
# reader-judgement layers. It does NOT judge whether the unit SHOULD have been
# selected (Anchor-B keep/drop) — that judgement is named, not gated.
# Honesty boundary: a fully_enumerable=false manifest (coarse PDF) downgrades any
# required finding to a warning, so the gate never blocks on un-enumerable structure.
# INPUTS : literature/verified_claims/*.md (**Locus:** + quote); literature/units/*.units.json;
#          units_layer: in ledger.config.md.
# OUTPUTS: [INFO]/[WARNING]/[ERROR]; exit 0 = ok or posture off/warn; 1 = a required gap.
# Run    : python3 tools/check_units.py
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from check_citations import parse_config
from enumerate_units import manifest_digest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "literature"))
from verify_quotes import norm, read_frontmatter  # noqa: E402

CLAIMS_DIR = REPO_ROOT / "literature" / "verified_claims"
UNITS_DIR = REPO_ROOT / "literature" / "units"

LOCUS_RE = re.compile(r"^\*\*Locus:\*\*\s*([\w-]+)", re.M)
DOUBLE_QUOTES = "\"“”"


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_warning(msg: str) -> None:
    print(f"[WARNING] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def units_mode(config: dict[str, str]) -> str:
    """units_layer: off | warn | required (default off — opt-in)."""
    raw = config.get("units_layer", "").split("#", 1)[0].strip().lower()
    return raw if raw in ("off", "warn", "required") else "off"


def _block_quote(block: str) -> str | None:
    """First blockquote span in a claim block (text between first/last double-quote
    on a `>` line), or None."""
    for line in block.splitlines():
        s = line.lstrip()
        if not s.startswith(">"):
            continue
        body = s[1:].strip()
        idx = [i for i, ch in enumerate(body) if ch in DOUBLE_QUOTES]
        if len(idx) >= 2 and idx[-1] > idx[0]:
            return body[idx[0] + 1:idx[-1]]
    return None


def claim_loci(ledger_path: Path) -> list[tuple[str, str | None]]:
    """[(locus, quote)] for each claim block carrying a **Locus:**."""
    text = ledger_path.read_text(encoding="utf-8", errors="ignore")
    out: list[tuple[str, str | None]] = []
    for block in re.split(r"(?m)^## ", text)[1:]:
        m = LOCUS_RE.search(block)
        if m:
            out.append((m.group(1).lower(), _block_quote(block)))
    return out


def load_manifest(units_dir: Path, key: str) -> tuple[dict | None, str | None]:
    """(manifest, error). error names a seal/parse failure; manifest is None then."""
    path = units_dir / f"{key}.units.json"
    if not path.is_file():
        return None, f"no manifest literature/units/{key}.units.json (run enumerate_units.py)"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"manifest unreadable ({exc})"
    if manifest.get("manifest_sha256") != manifest_digest(manifest):
        return None, "manifest_sha256 inconsistent — edited after enumeration (re-enumerate)"
    return manifest, None


def unit_problems(claims_dir: Path, units_dir: Path) -> tuple[list[str], list[str]]:
    """(hard, soft): hard = required-blocking problems on fully-enumerable sources;
    soft = the same class on a fully_enumerable=false (coarse PDF) manifest, only
    ever a warning. A ledger with no **Locus:** is simply not yet on the grid."""
    hard: list[str] = []
    soft: list[str] = []
    for ledger in sorted(claims_dir.glob("*.md")):
        if ledger.stem == "TEMPLATE":
            continue
        loci = claim_loci(ledger)
        if not loci:
            continue
        key = ledger.stem
        manifest, err = load_manifest(units_dir, key)
        bucket = hard
        problems: list[str] = []
        if err:
            problems.append(f"{key}: {err}")
        else:
            if not manifest.get("fully_enumerable", True):
                bucket = soft
            by_locus = {u["locus"].lower(): u["text"] for u in manifest.get("units", [])}
            stamp = read_frontmatter(ledger).get("source_sha256", "")
            if stamp and manifest.get("source_sha256") and stamp != manifest["source_sha256"]:
                problems.append(f"{key}: manifest source_sha256 != ledger stamp "
                                "(manifest enumerated from different bytes)")
            for locus, quote in loci:
                if locus not in by_locus:
                    problems.append(f"{key}: **Locus:** {locus} not in manifest")
                    continue
                if quote is None:
                    problems.append(f"{key}: claim at {locus} has no quote to bind")
                    continue
                if norm(quote) not in norm(by_locus[locus]):
                    problems.append(f"{key}: quote at {locus} is not a span within that unit")
        bucket.extend(problems)
    return hard, soft


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Attest every located claim's quote falls within its addressed unit.")
    ap.add_argument("--claims-dir", default=str(CLAIMS_DIR))
    ap.add_argument("--units-dir", default=str(UNITS_DIR))
    ap.add_argument("--config", default=str(REPO_ROOT / "ledger.config.md"))
    ap.add_argument("--units", choices=("off", "warn", "required"), default=None,
                    help="override the posture (default: units_layer: in config)")
    args = ap.parse_args()

    mode = args.units or units_mode(parse_config(Path(args.config)))
    if mode == "off":
        log_info("units_layer: off — unit-manifest check skipped.")
        return 0

    hard, soft = unit_problems(Path(args.claims_dir), Path(args.units_dir))
    if soft:
        log_warning("unit checks on coarse (fully_enumerable=false) sources — advisory:\n  - "
                    + "\n  - ".join(soft))
    if not hard:
        log_info("units ok — every located claim's quote falls within its addressed unit.")
        return 0
    message = "unit-manifest problems:\n  - " + "\n  - ".join(hard)
    if mode == "required":
        log_error(message)
        return 1
    log_warning(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
