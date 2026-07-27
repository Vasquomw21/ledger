# === SCRIPT: md_render — dependency-free Markdown -> HTML for the judge bundle ===
# Browsers do not render .md, and the kit ships no Node/CDN, so the judge bundle
# renders its ledgers and content pages with this small pure-stdlib converter. It
# handles the constrained subset the ledger actually uses: YAML frontmatter (as a
# provenance table), ATX headers, **bold**/*italic*, `> "blockquotes"`, lists, GFM
# tables, inline `code`/links, fenced code, and paragraphs. Everything is
# HTML-escaped first, so ledger text can never inject markup. Underscores are NOT
# treated as italics (claim addresses like andersen_2020:slug are full of them).
# INPUTS : a markdown string.
# OUTPUTS: an HTML fragment string (no <html>/<head> wrapper — the caller supplies
#          the shared page chrome).
from __future__ import annotations

import html
import re

_FM_LINE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
_HEADER = re.compile(r"^(#{1,6})\s+(.*)$")
_LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+\.)\s+(.*)$")
_TABLE_SEP = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")
_CODE_SPAN = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*(?!\*)([^*\n]+)\*(?!\*)")


def escape(text: object) -> str:
    return html.escape(str(text), quote=True)


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """(frontmatter dict, body) — empty dict + original text when no `---` block."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                fm: dict[str, str] = {}
                for ln in lines[1:j]:
                    m = _FM_LINE.match(ln)
                    if m:
                        fm[m.group(1)] = m.group(2).strip().strip('"')
                return fm, "\n".join(lines[j + 1:])
    return {}, text


def inline(text: str) -> str:
    """Inline formatting on one line. Escape first, then apply spans on safe text."""
    s = escape(text)
    s = _CODE_SPAN.sub(lambda m: f"<code>{m.group(1)}</code>", s)
    s = _LINK.sub(
        lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener">{m.group(1)}</a>', s)
    s = _WIKILINK.sub(lambda m: f"<code>{m.group(1)}</code>", s)  # no dangling cross-link
    s = _BOLD.sub(lambda m: f"<strong>{m.group(1)}</strong>", s)
    s = _ITALIC.sub(lambda m: f"<em>{m.group(1)}</em>", s)
    return s


def _fm_table(fm: dict[str, str]) -> str:
    rows = "".join(
        f"<tr><th>{escape(k)}</th><td>{inline(v)}</td></tr>" for k, v in fm.items())
    return f'<table class="fm">{rows}</table>'


def _fence(lines: list[str], i: int) -> tuple[int, str]:
    i += 1
    buf: list[str] = []
    while i < len(lines) and not lines[i].strip().startswith("```"):
        buf.append(lines[i])
        i += 1
    i += 1  # closing fence
    return i, f"<pre><code>{escape(chr(10).join(buf))}</code></pre>"


def _table(lines: list[str], i: int) -> tuple[int, str]:
    def cells(row: str) -> list[str]:
        return [c.strip() for c in row.strip().strip("|").split("|")]

    head = cells(lines[i])
    i += 2  # header + separator
    body: list[list[str]] = []
    while i < len(lines) and "|" in lines[i] and lines[i].strip():
        body.append(cells(lines[i]))
        i += 1
    thead = "".join(f"<th>{inline(c)}</th>" for c in head)
    trows = "".join(
        "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>" for row in body)
    return i, f"<table><thead><tr>{thead}</tr></thead><tbody>{trows}</tbody></table>"


def _blockquote(lines: list[str], i: int) -> tuple[int, str]:
    buf: list[str] = []
    while i < len(lines) and lines[i].lstrip().startswith(">"):
        buf.append(inline(lines[i].lstrip()[1:].lstrip()))
        i += 1
    return i, "<blockquote>" + "<br>".join(buf) + "</blockquote>"


def _list(lines: list[str], i: int) -> tuple[int, str]:
    ordered = bool(re.match(r"^\s*\d+\.\s", lines[i]))
    items: list[str] = []
    while i < len(lines):
        m = _LIST_ITEM.match(lines[i])
        if not m:
            break
        items.append(f"<li>{inline(m.group(3))}</li>")
        i += 1
    tag = "ol" if ordered else "ul"
    return i, f"<{tag}>{''.join(items)}</{tag}>"


def _paragraph(lines: list[str], i: int) -> tuple[int, str]:
    buf: list[str] = []
    while i < len(lines) and lines[i].strip() and not (
            _HEADER.match(lines[i]) or lines[i].lstrip().startswith((">", "```"))
            or _LIST_ITEM.match(lines[i])):
        buf.append(inline(lines[i].strip()))
        i += 1
    return i, "<p>" + "<br>".join(buf) + "</p>"


def render_markdown(text: str, frontmatter: str = "table") -> str:
    """Render a markdown string to an HTML fragment. `frontmatter`: 'table' renders
    the `---` block as a provenance table, 'drop' discards it, 'keep' leaves it as a
    paragraph."""
    fm, body = split_frontmatter(text)
    out: list[str] = []
    if fm and frontmatter == "table":
        out.append(_fm_table(fm))
    elif fm and frontmatter == "keep":
        body = text
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            i, frag = _fence(lines, i)
        elif not line.strip():
            i += 1
            continue
        elif _HEADER.match(line):
            m = _HEADER.match(line)
            level = len(m.group(1))
            frag = f"<h{level}>{inline(m.group(2))}</h{level}>"
            i += 1
        elif "|" in line and i + 1 < len(lines) and "-" in lines[i + 1] \
                and _TABLE_SEP.match(lines[i + 1]):
            i, frag = _table(lines, i)
        elif line.lstrip().startswith(">"):
            i, frag = _blockquote(lines, i)
        elif _LIST_ITEM.match(line):
            i, frag = _list(lines, i)
        else:
            i, frag = _paragraph(lines, i)
        out.append(frag)
    return "\n".join(out)
