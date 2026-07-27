# === SCRIPT: Selection-audit gate — is the corpus registered, with no empty side? ===
# Guards a Layer 2 (selection/completeness) gap: a misleading but internally verified
# corpus can still pass every fidelity gate. This gate, OFF by default, asks of a
# configured project whether the corpus is accounted for — every source carries a
# registered reason and discovery trail, every claimed viewpoint is either covered by a
# source or explicitly flagged as a known gap. It enforces NO SILENT EMPTY SIDE among
# declared positions.
#
# Honesty boundary (same as structure/assessment): the gate proves the DECLARED position
# set has no empty side; it does NOT prove that set is COMPLETE. Whether a viewpoint is
# missing entirely is judgement — surfaced via `## Known gaps` and semantic health, never
# claimed as mechanically proven.
#
# Scope: the artefact is `content/source_register.md` (lightweight markdown, the same
# **Field:** idiom as the ledgers). The pristine invariant holds: default off, and with no
# ledgers + no register there is nothing to check.
# INPUTS : content/source_register.md; literature/verified_claims/ (stamped ledgers);
#          content/inquiry.md (qid validation); selection_audit: in config.
# OUTPUTS: [INFO]/[WARNING]/[ERROR]; exit 0 = ok or posture off/warn; 1 = a gap under
#          selection_audit: required.
# Run    : python3 tools/check_selection.py
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from check_citations import parse_config
from check_structure import parse_inquiry_qids
import claim_graph as cg
from check_manifest import read_frontmatter

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAIMS_DIR = REPO_ROOT / "literature" / "verified_claims"
REGISTER = REPO_ROOT / "content" / "source_register.md"
INQUIRY = REPO_ROOT / "content" / "inquiry.md"

# A structured **Field:** value line (the ledger idiom, reused here).
FIELD_RE = re.compile(r"^\*\*([A-Za-z][\w-]*):\*\*\s*(.+?)\s*$")
REQUIRED_SOURCE_FIELDS = ("discovery", "rationale", "position")


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_warning(msg: str) -> None:
    print(f"[WARNING] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def selection_mode(config: dict[str, str]) -> str:
    """selection_audit: off | warn | required (default off — opt-in)."""
    raw = config.get("selection_audit", "").split("#", 1)[0].strip().lower()
    return raw if raw in ("off", "warn", "required") else "off"


def _first_token(value: str) -> str:
    """The leading slug of a field value, e.g. 'natural-origin — desc' -> 'natural-origin'."""
    return value.strip().split()[0].strip(" —-:.,").lower() if value.strip() else ""


def parse_register(register_path: Path) -> dict:
    """Parse source_register.md into {positions, sources, gaps}.

    positions: {slug: description}
    sources  : [{heading, fields}] where fields maps lowercased field -> list[str]
    gaps     : [raw gap text] (leading token treated as an optional position slug)
    """
    positions: dict[str, str] = {}
    sources: list[dict] = []
    gaps: list[str] = []
    if not register_path.is_file():
        return {"positions": positions, "sources": sources, "gaps": gaps}

    section = None            # "positions" | "sources" | "gaps" | None
    current: dict | None = None
    in_comment = False
    for raw in register_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.rstrip()
        if in_comment:                       # skip HTML-comment example blocks
            if "-->" in line:
                in_comment = False
            continue
        if line.lstrip().startswith("<!--") and "-->" not in line:
            in_comment = True
            continue
        if line.startswith("## "):
            title = line[3:].strip().lower()
            section = ("positions" if title.startswith("position")
                       else "sources" if title.startswith("source")
                       else "gaps" if "gap" in title else None)
            current = None
            continue
        if section == "sources" and line.startswith("### "):
            current = {"heading": line[4:].strip(), "fields": {}}
            sources.append(current)
            continue
        m = FIELD_RE.match(line)
        if not m:
            continue
        field, value = m.group(1).lower(), m.group(2).strip()
        if section == "positions" and field == "position":
            positions[_first_token(value)] = value
        elif section == "sources" and current is not None:
            current["fields"].setdefault(field, []).append(value)
        elif section == "gaps" and field == "gap":
            gaps.append(value)
    return {"positions": positions, "sources": sources, "gaps": gaps}


def _stamped_ledger_keys(claims_dir: Path) -> set[str]:
    """Keys of ledgers carrying a body_sha256 (the registered-corpus floor)."""
    if not claims_dir.is_dir():
        return set()
    keys = set()
    for p in claims_dir.glob("*.md"):
        if p.stem == "TEMPLATE":
            continue
        if read_frontmatter(p).get("body_sha256"):
            keys.add(p.stem.lower())
    return keys


def selection_problems(claims_dir: Path, register_path: Path,
                       inquiry_path: Path) -> list[str]:
    """Selection-audit problems: unregistered sources, missing fields, phantom or
    orphan-positioned sources, declared positions with no source and no gap, orphan qids."""
    stamped = _stamped_ledger_keys(claims_dir)
    reg = parse_register(register_path)
    positions: dict[str, str] = reg["positions"]
    sources: list[dict] = reg["sources"]
    gaps: list[str] = reg["gaps"]

    problems: list[str] = []

    # If there is nothing to audit, pass (pristine invariant).
    if not stamped and not sources and not positions:
        return problems

    registered_keys: set[str] = set()
    covered_positions: set[str] = set()
    qids = parse_inquiry_qids(inquiry_path) if inquiry_path.is_file() else set()

    for src in sources:
        fields = src["fields"]
        head = src["heading"] or "(unnamed source)"
        key_vals = fields.get("source", [])
        key = key_vals[0].strip().lower() if key_vals else ""
        if not key:
            problems.append(f"source '{head}': no **Source:** ledger key")
        else:
            registered_keys.add(key)
            if cg.ledger_for_key(claims_dir, key) is None:
                problems.append(f"source '{head}': **Source:** {key} resolves to no "
                                f"ledger in {claims_dir.name}/ (phantom source)")
        for req in REQUIRED_SOURCE_FIELDS:
            if not fields.get(req):
                problems.append(f"source '{head}': missing **{req.capitalize()}:**")
        for pos in fields.get("position", []):
            slug = _first_token(pos)
            covered_positions.add(slug)
            if slug not in positions:
                problems.append(f"source '{head}': **Position:** {slug} is not a declared "
                                "position in ## Positions (orphan position)")
        for qid in fields.get("addresses", []):
            q = _first_token(qid)
            if qids and q not in qids:
                problems.append(f"source '{head}': **Addresses:** {q} resolves to no "
                                "sub-question in inquiry.md")

    # Core invariant: every DECLARED position is covered by a source or named by a gap.
    gap_blob = "\n".join(gaps).lower()
    for slug in positions:
        if slug in covered_positions:
            continue
        if re.search(rf"(?<![\w-]){re.escape(slug)}(?![\w-])", gap_blob):
            continue
        problems.append(f"position '{slug}': no source carries it and no ## Known gaps "
                        "entry names it (silent empty side) — add a source or a gap")

    # Coverage: every stamped ledger is registered.
    for key in sorted(stamped - registered_keys):
        problems.append(f"ledger '{key}' is stamped but has no **Source:** entry in "
                        "source_register.md (unregistered source)")

    return problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Selection audit: the corpus is registered, with no silent empty side.")
    ap.add_argument("--claims-dir", default=str(CLAIMS_DIR))
    ap.add_argument("--register", default=str(REGISTER))
    ap.add_argument("--inquiry", default=str(INQUIRY))
    ap.add_argument("--config", default=str(REPO_ROOT / "ledger.config.md"))
    ap.add_argument("--selection", choices=("off", "warn", "required"), default=None,
                    help="override the posture (default: selection_audit: in config)")
    args = ap.parse_args()

    config = parse_config(Path(args.config))
    mode = args.selection or selection_mode(config)
    if mode == "off":
        log_info("selection_audit: off — selection-audit check skipped.")
        return 0

    problems = selection_problems(Path(args.claims_dir), Path(args.register),
                                  Path(args.inquiry))
    if not problems:
        log_info("selection audit ok — corpus registered, no declared position left empty.")
        return 0
    message = "selection-audit problems:\n  - " + "\n  - ".join(problems)
    if mode == "required":
        log_error(message)
        return 1
    log_warning(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
