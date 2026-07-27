# === SCRIPT: Source-flow gate — discovery and screening trail for the corpus ===
# Layer 2 can say a source is registered; this gate asks how it entered the corpus.
# It is deliberately PRISMA-like without pretending to be a full systematic-review
# engine: searches carry database/query/date/counts, included sources resolve to
# committed ledgers, and every stamped ledger must appear in the flow. It proves
# "no source without a declared path in"; it does not prove the search strategy is
# complete.
# INPUTS : content/source_flow.md; literature/verified_claims/; source_flow: in config.
# OUTPUTS: [INFO]/[WARNING]/[ERROR]; exit 0 = ok or posture off/warn; 1 = gap under
#          source_flow: required.
# Run    : python3 tools/check_source_flow.py
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from check_citations import parse_config
from check_manifest import read_frontmatter
import claim_graph as cg

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAIMS_DIR = REPO_ROOT / "literature" / "verified_claims"
FLOW = REPO_ROOT / "content" / "source_flow.md"

FIELD_RE = re.compile(r"^\*\*([A-Za-z][\w-]*):\*\*\s*(.+?)\s*$")
REQUIRED_OVERVIEW_FIELDS = (
    "review-question", "inclusion-criteria", "exclusion-criteria",
    "update-procedure", "last-updated",
)
REQUIRED_SEARCH_FIELDS = ("database", "query", "date", "records-found", "included")
REQUIRED_INCLUDED_FIELDS = ("source", "reason")


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_warning(msg: str) -> None:
    print(f"[WARNING] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def source_flow_mode(config: dict[str, str]) -> str:
    """source_flow: off | warn | required (default off — opt-in)."""
    raw = config.get("source_flow", "").split("#", 1)[0].strip().lower()
    return raw if raw in ("off", "warn", "required") else "off"


def _normalise_key(value: str) -> str:
    return value.strip().split()[0].strip(" —-:.,").lower() if value.strip() else ""


def _split_keys(value: str) -> list[str]:
    return [k for k in (_normalise_key(part) for part in value.split(",")) if k]


def _parse_count(value: str) -> int | None:
    raw = value.replace(",", "").strip()
    return int(raw) if raw.isdigit() else None


def _stamped_ledger_keys(claims_dir: Path) -> set[str]:
    """Keys of ledgers carrying a body_sha256 (the corpus floor this gate covers)."""
    if not claims_dir.is_dir():
        return set()
    keys: set[str] = set()
    for p in claims_dir.glob("*.md"):
        if p.stem == "TEMPLATE":
            continue
        if read_frontmatter(p).get("body_sha256"):
            keys.add(p.stem.lower())
    return keys


def parse_flow(flow_path: Path) -> dict[str, list[dict] | dict[str, list[str]]]:
    """Parse source_flow.md into overview / search / included / excluded / unavailable.

    The parser accepts the ledger's lightweight markdown idiom:
      ## Overview
      **Review-question:** ...
      **Inclusion-criteria:** ...

      ## Searches
      ### PubMed 2026-06-15
      **Database:** PubMed
      **Query:** ...

      ## Included sources
      ### smith_2020
      **Source:** smith_2020
      **Reason:** ...
    """
    buckets: dict[str, list[dict] | dict[str, list[str]]] = {
        "overview": {},
        "searches": [],
        "included": [],
        "excluded": [],
        "unavailable": [],
    }
    if not flow_path.is_file():
        return buckets

    section: str | None = None
    current: dict | None = None
    in_comment = False
    for raw in flow_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.rstrip()
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if line.lstrip().startswith("<!--") and "-->" not in line:
            in_comment = True
            continue
        if line.startswith("## "):
            title = line[3:].strip().lower()
            if "overview" in title or "protocol" in title:
                section = "overview"
            elif "search" in title:
                section = "searches"
            elif "included" in title:
                section = "included"
            elif "excluded" in title:
                section = "excluded"
            elif "unavailable" in title or "inaccessible" in title:
                section = "unavailable"
            else:
                section = None
            current = None
            continue
        if section and section != "overview" and line.startswith("### "):
            current = {"heading": line[4:].strip(), "fields": {}}
            buckets[section].append(current)  # type: ignore[index, union-attr]
            continue
        m = FIELD_RE.match(line)
        if not m or not section:
            continue
        if section == "overview":
            field, value = m.group(1).lower(), m.group(2).strip()
            overview = buckets["overview"]
            overview.setdefault(field, []).append(value)  # type: ignore[union-attr]
            continue
        if current is None:
            current = {"heading": "(section entry)", "fields": {}}
            buckets[section].append(current)  # type: ignore[index, union-attr]
        field, value = m.group(1).lower(), m.group(2).strip()
        current["fields"].setdefault(field, []).append(value)
    return buckets


def source_flow_problems(claims_dir: Path, flow_path: Path) -> list[str]:
    """All source-flow problems. Empty starter projects pass."""
    stamped = _stamped_ledger_keys(claims_dir)
    flow = parse_flow(flow_path)
    overview = flow["overview"]
    searches = flow["searches"]
    included = flow["included"]
    excluded = flow["excluded"]
    unavailable = flow["unavailable"]
    problems: list[str] = []

    if not stamped and not searches and not included and not excluded and not unavailable:
        return problems
    if stamped and not flow_path.is_file():
        return ["stamped ledgers exist but content/source_flow.md is missing"]
    if stamped:
        for req in REQUIRED_OVERVIEW_FIELDS:
            if not overview.get(req):  # type: ignore[union-attr]
                problems.append(f"overview: missing **{req.capitalize()}:**")
    if stamped and not searches:
        problems.append("no ## Searches entries — the corpus has no discovery trail")
    if stamped and not included:
        problems.append("no ## Included sources entries — ledgers have no screening trail")

    search_included_keys: set[str] = set()
    for item in searches:
        fields = item["fields"]
        head = item["heading"] or "(unnamed search)"
        for req in REQUIRED_SEARCH_FIELDS:
            if not fields.get(req):
                problems.append(f"search '{head}': missing **{req.capitalize()}:**")
        if not (fields.get("records-screened") or fields.get("included")):
            problems.append(f"search '{head}': missing **Records-screened:** or **Included:**")
        found_vals = fields.get("records-found", [])
        screened_vals = fields.get("records-screened", [])
        found = _parse_count(found_vals[0]) if found_vals else None
        screened = _parse_count(screened_vals[0]) if screened_vals else None
        if found_vals and found is None:
            problems.append(f"search '{head}': **Records-found:** must be a non-negative integer")
        if screened_vals and screened is None:
            problems.append(f"search '{head}': **Records-screened:** must be a non-negative integer")
        if found is not None and screened is not None and screened > found:
            problems.append(f"search '{head}': records-screened exceeds records-found")
        for value in fields.get("included", []):
            search_included_keys.update(_split_keys(value))

    included_keys: set[str] = set()
    for item in included:
        fields = item["fields"]
        head = item["heading"] or "(unnamed included source)"
        for req in REQUIRED_INCLUDED_FIELDS:
            if not fields.get(req):
                problems.append(f"included source '{head}': missing **{req.capitalize()}:**")
        source_vals = fields.get("source", [])
        key = _normalise_key(source_vals[0]) if source_vals else ""
        if key:
            included_keys.add(key)
            if cg.ledger_for_key(claims_dir, key) is None:
                problems.append(f"included source '{head}': **Source:** {key} resolves to no "
                                f"ledger in {claims_dir.name}/")

    for key in sorted(stamped - included_keys):
        problems.append(f"ledger '{key}' is stamped but absent from ## Included sources "
                        "in source_flow.md")
    for key in sorted(included_keys - stamped):
        ledger = cg.ledger_for_key(claims_dir, key)
        if ledger is not None:
            problems.append(f"included source '{key}' resolves to a ledger but that ledger has "
                            "no body_sha256 stamp")
    if stamped:
        for key in sorted(included_keys - search_included_keys):
            problems.append(f"included source '{key}' is absent from all search **Included:** "
                            "lists")
        for key in sorted(search_included_keys - included_keys):
            problems.append(f"search **Included:** names '{key}' but ## Included sources has "
                            "no matching entry")

    for bucket_name, bucket in (("excluded", excluded), ("unavailable", unavailable)):
        for item in bucket:
            fields = item["fields"]
            head = item["heading"] or f"(unnamed {bucket_name} record)"
            if not (fields.get("record") or fields.get("source")):
                problems.append(f"{bucket_name} entry '{head}': missing **Record:** or **Source:**")
            if not fields.get("reason"):
                problems.append(f"{bucket_name} entry '{head}': missing **Reason:**")

    return problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Source flow: discovery/screening trail for every included ledger.")
    ap.add_argument("--claims-dir", default=str(CLAIMS_DIR))
    ap.add_argument("--flow", default=str(FLOW))
    ap.add_argument("--config", default=str(REPO_ROOT / "ledger.config.md"))
    ap.add_argument("--source-flow", choices=("off", "warn", "required"), default=None,
                    help="override the posture (default: source_flow: in config)")
    args = ap.parse_args()

    mode = args.source_flow or source_flow_mode(parse_config(Path(args.config)))
    if mode == "off":
        log_info("source_flow: off — source-flow check skipped.")
        return 0

    problems = source_flow_problems(Path(args.claims_dir), Path(args.flow))
    if not problems:
        log_info("source flow ok — included ledgers have a discovery/screening trail.")
        return 0
    message = "source-flow problems:\n  - " + "\n  - ".join(problems)
    if mode == "required":
        log_error(message)
        return 1
    log_warning(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
