# === SCRIPT: Mechanical wiki health-check for a Ledger knowledge base ===
# Purpose: the MECHANICAL half of the Ledger health-check. The semantic half —
#          contradictions between notes, claims a newer source overturned — is the
#          LLM pass in skill-ledger-curate; this script catches what code can catch:
#            - dead wikilinks       [[target]] with no matching note on disk
#            - orphan notes         a note with no inbound [[link]] from any other note
#            - uncatalogued notes   a concept note / review absent from crosswalk.md
#          Read-only: it prints a report and never edits the knowledge base.
# INPUTS : a content directory (default ./content) of Markdown notes using [[wikilink]]s.
# OUTPUTS: stdout report. Exit 0 (advisory) unless --strict and issues exist (then 1).
# Run    : python3 tools/lint_wiki.py [content_dir] [--strict]
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# [[target]], [[target|alias]], [[target#anchor]] → capture the bare target name.
WIKILINK_RE = re.compile(r"\[\[\s*([^\]|#]+?)\s*(?:[#|][^\]]*)?\]\]")

# Notes that are entry points / indices, so a missing inbound link is not an orphan.
# inquiry.md is the discourse-structure root of the claim graph; source_register.md,
# source_flow.md and correlation_kinds.md are Layer-2 / metadata audit artefacts — entry
# points, not orphans, even before any note links to them.
ENTRYPOINT_STEMS = {
    "index", "crosswalk", "log", "readme", "inquiry", "source_register", "source_flow",
    "finding", "baseline_comparison", "correlation_kinds",
}

# Subdirectories whose notes are expected to be catalogued in crosswalk.md.
CATALOGUED_SUBDIRS = ("concept_notes", "literature_reviews")


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_warning(msg: str) -> None:
    print(f"[WARNING] {msg}", file=sys.stderr)


def find_notes(content_dir: Path) -> list[Path]:
    """Every .md note under content_dir, excluding the per-project _ledger config."""
    return sorted(
        p for p in content_dir.rglob("*.md")
        if "_ledger" not in p.parts
    )


def outbound_links(note: Path) -> set[str]:
    """The set of wikilink targets (bare names, lowercased) a note points to."""
    text = note.read_text(encoding="utf-8", errors="ignore")
    return {m.group(1).strip().lower() for m in WIKILINK_RE.finditer(text)}


def lint(content_dir: Path) -> tuple[list[str], list[str], list[str]]:
    """Return (dead_links, orphans, uncatalogued) as human-readable lines."""
    notes = find_notes(content_dir)
    stems = {p.stem.lower() for p in notes}

    inbound: dict[str, int] = {s: 0 for s in stems}
    dead_links: list[str] = []

    for note in notes:
        for target in outbound_links(note):
            if target in stems:
                inbound[target] += 1
            else:
                rel = note.relative_to(content_dir)
                if "/" in target:
                    dead_links.append(f"{rel}: [[{target}]] → path-style link; use the bare note name")
                else:
                    dead_links.append(f"{rel}: [[{target}]] → no such note")

    orphans = [
        str(p.relative_to(content_dir))
        for p in notes
        if p.stem.lower() not in ENTRYPOINT_STEMS and inbound[p.stem.lower()] == 0
    ]

    # Uncatalogued: a concept note / review whose stem never appears in crosswalk.md.
    uncatalogued: list[str] = []
    crosswalk = content_dir / "crosswalk.md"
    if crosswalk.exists():
        catalogue_text = crosswalk.read_text(encoding="utf-8", errors="ignore").lower()
        for p in notes:
            if any(sub in p.parts for sub in CATALOGUED_SUBDIRS):
                if p.stem.lower() not in catalogue_text:
                    uncatalogued.append(str(p.relative_to(content_dir)))

    return dead_links, orphans, uncatalogued


def main() -> int:
    parser = argparse.ArgumentParser(description="Mechanical health-check for a Ledger wiki.")
    parser.add_argument("content_dir", nargs="?", default="content",
                        help="path to the knowledge-base content directory (default: content)")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 if any issue is found (for CI); default is advisory exit 0")
    args = parser.parse_args()

    content_dir = Path(args.content_dir).resolve()
    if not content_dir.is_dir():
        log_warning(f"content dir not found: {content_dir}")
        return 2

    log_info(f"linting {content_dir}")
    dead_links, orphans, uncatalogued = lint(content_dir)

    def report(title: str, items: list[str]) -> None:
        if items:
            log_warning(f"{title} ({len(items)}):")
            for it in items:
                print(f"    - {it}")
        else:
            log_info(f"{title}: none")

    report("Dead wikilinks", dead_links)
    report("Orphan notes (no inbound links)", orphans)
    report("Uncatalogued notes (absent from crosswalk.md)", uncatalogued)

    total = len(dead_links) + len(orphans) + len(uncatalogued)
    log_info(f"done — {total} mechanical issue(s). "
             f"Semantic checks (contradictions / stale claims) are skill-ledger-curate's LLM pass.")
    return 1 if (args.strict and total) else 0


if __name__ == "__main__":
    sys.exit(main())
