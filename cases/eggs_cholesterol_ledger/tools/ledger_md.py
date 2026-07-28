#!/usr/bin/env python3
# === SCRIPT: ledger_md — the one reader of a document's marker blocks ===
# INPUTS : a ledger Markdown file (the grammar of spec/INTERCHANGE.md §2), or any
#          Markdown document declaring fields under `## ` headings (inquiry.md).
# OUTPUT : MarkdownBlock records; every marker parser in the kit resolves fields
#          through these rather than scanning the file itself.
#
# A ledger contains prose ABOUT its own markers as well as markers carrying data:
# a header sentence beginning `**Locus:**` describing the convention, a fenced
# example showing `**ID:**`, a quoted span that mentions a field inline. A scan of
# the whole file cannot tell the two apart, counts the documentation as data, and
# fails silently — an inflated claim-id set makes a bogus `#slug` citation resolve,
# and an inflated locus set inflates every convergence score computed from it.
#
# So field lookup is defined once, here, and every consumer routes through it. Two
# tools reading one field with two different scopes is the defect this prevents.
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

CLAIM_HEADER_RE = re.compile(r"^##\s+claim\b", re.IGNORECASE)
CLAIM_NUMBER_RE = re.compile(r"^##\s+claim\s+(\d+)\b", re.IGNORECASE)
# Exactly two hashes: a `###` sub-heading stays inside its parent's block.
SECTION_HEADER_RE = re.compile(r"^##\s+\S")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")


@dataclass(frozen=True)
class MarkdownBlock:
    """One `## ` section. `text` keeps the block verbatim (quotes intact) for
    quote extraction; `marker_lines` is the subset a field may be read from."""

    ordinal: int
    header: str
    text: str
    marker_lines: tuple[str, ...]

    def field(self, pattern: re.Pattern[str]) -> re.Match[str] | None:
        """First match of a `**Field:**` pattern among this block's marker lines."""
        for line in self.marker_lines:
            m = pattern.match(line)
            if m:
                return m
        return None

    def fields(self, pattern: re.Pattern[str]) -> list[re.Match[str]]:
        """Every match, for fields a claim may carry more than once."""
        return [m for line in self.marker_lines if (m := pattern.match(line))]


def _strip_fences(lines: list[str]) -> list[bool]:
    """Per-line flag: True where the line sits inside a fenced code region.

    Fences are stripped before headers are found, so a `## Claim` shown inside a
    documentation example never opens a block and never shifts the ordinals that
    positional `#cN` refs resolve through."""
    inside = False
    out: list[bool] = []
    for line in lines:
        if _FENCE_RE.match(line):
            inside = not inside
            out.append(True)
            continue
        out.append(inside)
    return out


def _blocks(source: Path | str, header_re: re.Pattern[str]) -> list[MarkdownBlock]:
    """Every section opened by `header_re`, in header order (ordinals are 1-based).

    Accepts a path or the text itself. Text before the first header is the
    document's preamble — where a file explains its own conventions — and is never
    returned, so documentation of a field cannot be read as a use of it.
    """
    text = source.read_text(encoding="utf-8", errors="ignore") \
        if isinstance(source, Path) else source
    lines = text.splitlines()
    fenced = _strip_fences(lines)

    starts = [i for i, line in enumerate(lines)
              if not fenced[i] and header_re.match(line.strip())]
    blocks: list[MarkdownBlock] = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        body = lines[start:end]
        marker_lines = tuple(
            line.strip() for i, line in enumerate(body, start=start)
            # A field never appears inside a fence or on a quoted line: the fence is
            # an example and the `>` line is the source's words, not the author's.
            if not fenced[i] and not line.lstrip().startswith(">")
        )
        blocks.append(MarkdownBlock(ordinal=n + 1, header=lines[start].strip(),
                                    text="\n".join(body).rstrip() + "\n",
                                    marker_lines=marker_lines))
    return blocks


def claim_blocks(source: Path | str) -> list[MarkdownBlock]:
    """Every `## Claim` block in a ledger, in header order."""
    return _blocks(source, CLAIM_HEADER_RE)


def heading_blocks(source: Path | str) -> list[MarkdownBlock]:
    """Every `## ` section, for a document that carries fields without claim
    blocks — content/inquiry.md declares a sub-question id under each heading."""
    return _blocks(source, SECTION_HEADER_RE)


def claim_numbers(source: Path | str) -> list[int]:
    """The authored `## Claim N` numbers, in order; unnumbered claims are skipped."""
    return [int(m.group(1)) for b in claim_blocks(source)
            if (m := CLAIM_NUMBER_RE.match(b.header))]
