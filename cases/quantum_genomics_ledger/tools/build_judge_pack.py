# === SCRIPT: build_judge_pack — the navigable, zero-install judge bundle ===
# Exports a Ledger project into a folder anyone opens offline (double-click index.html)
# and navigates: the system framed as INPUTS -> PROCESSES -> OUTPUTS (the Ingestion ->
# Structure -> Assessment stack), a flow infographic, a table of ingested documents that
# links to a rendered
# page per ledger, the active gates, the human-in-the-loop trail (who sealed each
# judgement, and that it is contestable), and the interactive argument graph. It is
# DERIVED output, not a source of truth; markdown is rendered with the in-kit
# dependency-free renderer (browsers do not render .md, and the kit ships no Node).
# Run: python3 tools/build_judge_pack.py [PROJECT_DIR] --out /tmp/judge_pack
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import md_render as md
from build_graph import build_graph, to_mermaid
from check_assessment import RECORDS_DIR_NAME
from check_citations import parse_config
from check_manifest import read_frontmatter
from judge_dashboard import (GRAPH_CSS, LAYER1_HEADING, LAYER2_HEADING, LAYER3_HEADING,
                             authored_interpretation, contest_command, dashboard_model,
                             derived_summary, evidence_trace, finding_lead,
                             graph_section_html, graphview_payload, recorded_judgements,
                             render_derived_layer, render_interpretation_layer,
                             render_judgements_layer, trace_anchor, verification_state)
from postures import POSTURES
import claim_graph as cg

REPO_ROOT = Path(__file__).resolve().parents[1]

# Postures whose 'required'/'block' value means a gate actually bites. Derived from the
# canonical registry so the checklist can't drift out of sync with the operator dashboard.
GATE_KEYS = [(key, label) for key, label, _bv in POSTURES]
_ENFORCED = {"required", "block"}


def _esc(text: object) -> str:
    return md.escape(text)


def _year(text: str) -> str:
    m = re.search(r"\b(19|20)\d{2}\b", text or "")
    return m.group(0) if m else ""


def _locator_html(fm: dict) -> str:
    if fm.get("doi"):
        return f'<a href="https://doi.org/{_esc(fm["doi"])}" target="_blank" rel="noopener">doi</a>'
    if fm.get("pmcid"):
        pid = str(fm["pmcid"]).replace("PMC", "")
        return (f'<a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC{_esc(pid)}/" '
                f'target="_blank" rel="noopener">PMC{_esc(pid)}</a>')
    if fm.get("url"):
        return f'<a href="{_esc(fm["url"])}" target="_blank" rel="noopener">source</a>'
    return "—"


def _verdict_badge(verdict: str) -> str:
    cls = "ok" if verdict == "pass" else ("bad" if verdict else "warn")
    return f'<span class="badge {cls}">{_esc(verdict or "unstamped")}</span>'


def _ledger_keys(claims_dir: Path) -> list[str]:
    if not claims_dir.is_dir():
        return []
    return sorted(p.stem.lower() for p in claims_dir.glob("*.md") if p.stem != "TEMPLATE")


def _claim_count(ledger_path: Path) -> int:
    return sum(1 for ln in ledger_path.read_text(encoding="utf-8", errors="ignore").splitlines()
               if cg.CLAIM_HEADER_RE.match(ln.strip()))


def _source_positions(register_path: Path) -> dict[str, str]:
    """ledger key -> declared position slug, parsed from source_register.md."""
    out: dict[str, str] = {}
    if not register_path.is_file():
        return out
    current: str | None = None
    for line in register_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"^\*\*Source:\*\*\s*(\S+)", line)
        if m:
            current = m.group(1).lower()
            continue
        m = re.match(r"^\*\*Position:\*\*\s*(.+)$", line)
        if m and current:
            out[current] = re.split(r"\s+[—-]\s+", m.group(1).strip())[0]
            current = None
    return out


def _linkify(html_str: str, keys: list[str], href, current: str | None = None) -> str:
    """Turn `key:slug` mentions into links to that ledger's page (href(key))."""
    if not keys:
        return html_str
    pat = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(keys, key=len, reverse=True))
                     + r"):([A-Za-z0-9][\w-]*)")

    def repl(m: re.Match) -> str:
        k = m.group(1).lower()
        if current and k == current:
            return m.group(0)
        return f'<a href="{href(k)}">{m.group(0)}</a>'

    return pat.sub(repl, html_str)


# `[rec: id]` is how an author addresses a sealed judgement in prose. Left raw it is
# machinery showing through — the reader sees an id and no way to reach what it names, so
# the sentence's own evidence stays out of reach. The wrapping brackets go with it: what
# remains is the record, linked.
_REC_IN_PROSE_RE = re.compile(r"\[rec:\s*([\w-]+)\s*\]")


def _link_rec_refs(html_str: str, record_ids: set, prefix: str = "") -> str:
    """Turn `[rec: id]` markers into links to that record's row in assessments.html.

    Only a known id is linked: an unknown one would send the reader to an anchor that is
    not there, and the gate already refuses to commit prose carrying one.
    """
    def repl(m: re.Match) -> str:
        rid = m.group(1)
        if rid.lower() not in record_ids:
            return m.group(0)
        return (f'<a class="recref" href="{prefix}assessments.html#rec-{_esc(rid)}">'
                f'{_esc(rid)}</a>')

    return _REC_IN_PROSE_RE.sub(repl, html_str)


# ---- page chrome -----------------------------------------------------------

# Theme: an early head script applies data-theme from localStorage BEFORE the
# stylesheet loads (no flash of the wrong theme); the toggle handler at end-of-body
# flips + persists it. Mirrors judge_dashboard's toggle, with a pack-scoped key.
_THEME_HEAD = ('<script>try{var t=localStorage.getItem("ledger-pack-theme");'
               'if(t)document.documentElement.setAttribute("data-theme",t);}catch(e){}</script>')

_THEME_JS = ('(function(){var root=document.documentElement,KEY="ledger-pack-theme";'
             'var b=document.getElementById("theme-toggle");if(!b)return;'
             'b.addEventListener("click",function(){'
             'var dark=root.getAttribute("data-theme")==="dark"||'
             '(!root.getAttribute("data-theme")&&window.matchMedia("(prefers-color-scheme: dark)").matches);'
             'var next=dark?"light":"dark";root.setAttribute("data-theme",next);'
             'try{localStorage.setItem(KEY,next);}catch(e){}});})();')


def _nav(prefix: str) -> str:
    items = [("Overview", "overview"), ("Inputs", "inputs"),
             ("Processes", "processes"), ("Collaboration", "hitl"), ("Outputs", "outputs")]
    links = "".join(
        f'<a href="{prefix}index.html#{anchor}">{label}</a>' for label, anchor in items)
    return (f'<nav><a class="brand" href="{prefix}index.html">Ledger · Judge Pack</a>'
            f'<span class="navlinks">{links}</span>'
            f'<button class="theme-toggle" id="theme-toggle" title="Toggle light/dark" '
            f'aria-label="Toggle light/dark">&#9681;</button></nav>')


def _page(title: str, body: str, prefix: str = "") -> str:
    return (f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{_esc(title)} — Ledger</title>\n'
            f'{_THEME_HEAD}\n'
            f'<link rel="stylesheet" href="{prefix}assets/ledger.css">\n</head>\n'
            f'<body>\n{_nav(prefix)}\n<main>\n{body}\n</main>\n'
            f'<script>{_THEME_JS}</script>\n</body>\n</html>\n')


# ---- the flow infographic (hand-authored, inline SVG) ----------------------

def _infographic(state: dict) -> str:
    # The ingestion chip tracks the reader's position, not the pipeline's: the gate is a
    # machine guarantee where it runs, but a green "guaranteed" beside a proof this reader
    # has no bytes to repeat claims the very thing the ceiling above denies.
    reproducible = state["level"] == "reproducible"
    stages = [
        ("Primary sources", "papers, reports, debates", "input",
         "the corpus a curator selects", ""),
        ("Ingestion", "fetch · verbatim-quote gate · stamp", "good",
         "machine-guaranteed" if reproducible else "verified upstream",
         "guaranteed" if reproducible else "attested"),
        ("Structure", "typed claim graph (edges)", "good",
         "machine-resolved, human-authored", "guaranteed"),
        ("Assessment", "rhetorical · double-count · faithfulness · calibration", "warn",
         "human-in-the-loop judgement", "judged"),
        ("Outputs", "navigable finding + graph", "input", "what a judge reads", ""),
    ]
    x, gap, w, h, y = 12, 18, 184, 116, 30
    boxes, arrows = [], []
    for i, (title, sub, kind, tag, chip) in enumerate(stages):
        bx = x + i * (w + gap)
        fill = {"good": "#eef6ef", "warn": "#fbf4e6", "input": "#eef1f6"}[kind]
        stroke = {"good": "#2e7d32", "warn": "#b8860b", "input": "#7a8794"}[kind]
        boxes.append(
            f'<g><rect x="{bx}" y="{y}" rx="8" width="{w}" height="{h}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1.4"/>'
            f'<text x="{bx + 12}" y="{y + 26}" class="ig-t">{_esc(title)}</text>'
            f'<text x="{bx + 12}" y="{y + 46}" class="ig-s">{_esc(sub)}</text>'
            f'<text x="{bx + 12}" y="{y + h - 28}" class="ig-tag">{_esc(tag)}</text>'
            + (f'<rect x="{bx + 12}" y="{y + h - 22}" rx="7" width="78" height="16" '
               f'fill="{stroke}"/><text x="{bx + 18}" y="{y + h - 10}" class="ig-chip">'
               f'{_esc(chip)}</text>' if chip else "")
            + "</g>")
        if i:
            ax = bx - gap - 1
            arrows.append(f'<path d="M{ax - 5} {y + h / 2} l{gap + 6} 0" stroke="#9aa6b2" '
                          f'stroke-width="1.6" marker-end="url(#ig-arw)"/>')
    return (
        '<svg class="infographic" viewBox="0 0 1010 180" role="img" '
        'aria-label="how the ledger works">'
        '<defs><marker id="ig-arw" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
        'fill="#9aa6b2"/></marker></defs>'
        + "".join(arrows) + "".join(boxes)
        + '<text x="12" y="166" class="ig-note">The machine guarantees the facts where the '
        'pipeline runs (verbatim quotes, content stamps, structural resolution); the human '
        'supplies the contestable judgement — and others with different beliefs can pick up '
        'where one left off.</text>'
        + "</svg>")


# ---- per-ledger pages ------------------------------------------------------

def _provenance_block(fm: dict) -> str:
    rows = []
    for label, key in [("Paper", "paper"), ("Title", "title"), ("Version", "source_version"),
                       ("Retrieved", "retrieved"), ("Verified by", "verified_by")]:
        if fm.get(key):
            rows.append(f"<tr><th>{label}</th><td>{md.inline(fm[key])}</td></tr>")
    rows.append(f"<tr><th>Source</th><td>{_locator_html(fm)}</td></tr>")
    rows.append(f"<tr><th>Verification</th><td>{_verdict_badge(fm.get('verified_verdict', ''))} "
                f"<span class=\"mono\">body {_esc(str(fm.get('body_sha256', ''))[:12])}…</span></td></tr>")
    return f'<table class="fm">{"".join(rows)}</table>'


def _ledger_page(key: str, claims_dir: Path, keys: list[str], record_ids: set) -> str:
    ledger = claims_dir / f"{key}.md"
    fm, body = md.split_frontmatter(ledger.read_text(encoding="utf-8", errors="ignore"))
    body_html = _linkify(md.render_markdown(body, frontmatter="drop"), keys,
                         lambda k: f"{k}.html", current=key)
    title = fm.get("paper") or key
    # This page is written one directory down, so every link out of it needs the prefix
    # the nav uses; a bare "index.html" resolves inside ledgers/ and 404s offline.
    prefix = "../"
    body_html = _link_rec_refs(body_html, record_ids, prefix=prefix)
    inner = (f'<p class="back"><a href="{prefix}index.html#inputs">← all documents</a></p>'
             f'<h1>{_esc(title)}</h1>{_provenance_block(fm)}'
             f'<section class="ledger-body">{body_html}</section>')
    return _page(title, inner, prefix=prefix)


# ---- content sub-pages -----------------------------------------------------

def _content_page(title: str, src: Path, keys: list[str], record_ids: set,
                  frontmatter: str = "table") -> str:
    body = _linkify(md.render_markdown(src.read_text(encoding="utf-8", errors="ignore"),
                                       frontmatter=frontmatter),
                    keys, lambda k: f"ledgers/{k}.html")
    body = _link_rec_refs(body, record_ids)
    inner = f'<p class="back"><a href="index.html">← index</a></p><h1>{_esc(title)}</h1>{body}'
    return _page(title, inner)


def _assessments_page(repo_root: Path, keys: list[str], record_ids: set) -> str:
    records_dir = repo_root / "content" / "assessments" / "_records"
    rows = []
    for p in sorted(records_dir.glob("*.json")) if records_dir.is_dir() else []:
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        subj = str(r.get("subject", ""))
        subj_html = _linkify(_esc(subj), keys, lambda k: f"ledgers/{k}.html")
        # The row is the landing point for every [rec: id] in prose, so it carries the id
        # as an anchor: a marker names a judgement, and naming it has to reach it.
        rid = _esc(r.get("id", ""))
        rows.append(
            f"<tr id=\"rec-{rid}\"><td class=\"mono\">{rid}</td>"
            f"<td>{_esc(r.get('kind', ''))}</td><td class=\"mono\">{subj_html}</td>"
            f"<td>{_esc(', '.join(r.get('grounding', []) or []))}</td>"
            f"<td>{_esc(', '.join(r.get('disputes', []) or []))}</td>"
            f"<td>{_esc(r.get('assessor', ''))}</td><td>{_esc(r.get('assessed_date', ''))}</td></tr>")
    table = (
        '<table class="docs"><thead><tr><th>Record</th><th>Kind</th><th>Subject</th>'
        '<th>Grounding</th><th>Disputes</th><th>Assessor (human-in-the-loop)</th><th>Date</th>'
        '</tr></thead><tbody>' + ("".join(rows) or
        '<tr><td colspan="7" class="muted">No sealed judgement records.</td></tr>')
        + "</tbody></table>")
    prose = ""
    assess_dir = repo_root / "content" / "assessments"
    for p in sorted(assess_dir.glob("*.md")) if assess_dir.is_dir() else []:
        prose += _link_rec_refs(
            _linkify(md.render_markdown(p.read_text(encoding="utf-8", errors="ignore")),
                     keys, lambda k: f"ledgers/{k}.html"), record_ids)
    inner = (f'<p class="back"><a href="index.html#outputs">← index</a></p>'
             f'<h1>Assessment records</h1>'
             f'<p class="muted">Each record is sealed (hashed) and names its <strong>assessor</strong>'
             f' — the human-in-the-loop fingerprint. Any record is contestable: a faithfulness record'
             f' disputes another by id.</p>{table}{prose}')
    return _page("Assessment records", inner)


# ---- the evidence trace ----------------------------------------------------

def _record_chip(record: dict, label: str, cls: str) -> str:
    who = _esc(record.get("assessor", "")).split("@")[0]
    span = record.get("span") or ""
    span_html = (f'<div class="span">challenged span: &ldquo;{_esc(span)}&rdquo;</div>'
                 if span else "")
    return (f'<div class="rec {cls}"><span class="badge {cls}">{_esc(label)}</span> '
            f'<code>{_esc(record.get("id", ""))}</code> '
            f'<span class="muted">sealed by {who} · {_esc(record.get("assessed_date", ""))}</span>'
            f'{span_html}</div>')


def _edge_block(edge: dict, keys: list[str]) -> str:
    source = _esc(edge["source"])
    href = _ledger_href(edge["source"], keys)
    quote = (f'<blockquote>&ldquo;{_esc(edge["grounding_quote"])}&rdquo;</blockquote>'
             if edge["grounding_quote"] else
             '<p class="muted">No grounding quote resolved.</p>')
    if edge["contested_by"]:
        judgement = "".join(_record_chip(r, "disputed", "bad") for r in edge["contested_by"])
    elif edge["upheld_by"]:
        judgement = "".join(_record_chip(r, "reviewed — held", "ok") for r in edge["upheld_by"])
    elif edge["record_id"]:
        judgement = (f'<div class="rec neu"><span class="badge neu">assessed</span> '
                     f'<code>{_esc(edge["record_id"])}</code> '
                     '<span class="muted">no adversarial review yet</span></div>')
    else:
        judgement = ('<div class="rec neu"><span class="badge warn">unassessed</span> '
                     '<span class="muted">no sealed judgement of this inference</span></div>')
    return (f'<li class="edge"><div class="edge-h"><span class="etype">{_esc(edge["type"])}</span> '
            f'from {href} <span class="muted">{_esc(edge["source_paper"])}</span></div>'
            f'{quote}{judgement}</li>')


def _ledger_href(addr: str, keys: list[str]) -> str:
    key = addr.partition(":")[0]
    if key in keys:
        return f'<a href="ledgers/{_esc(key)}.html"><code>{_esc(addr)}</code></a>'
    return f'<code>{_esc(addr)}</code>'


def _reason_badges(reasons: list) -> str:
    return " ".join(f'<span class="badge neu">{_esc(r)}</span>' for r in reasons)


def _trace_page(trace: list[dict], keys: list[str], case: str,
                finding_present: bool) -> str:
    blocks = []
    for item in trace:
        node = item["node"] or {}
        quote = (f'<blockquote class="subject">&ldquo;{_esc(node.get("quote", ""))}&rdquo;</blockquote>'
                 if node.get("quote") else
                 '<p class="muted">No verbatim quote resolved for this claim.</p>')
        locus = " · ".join(filter(None, [_esc(node.get("source", "")),
                                         _esc(node.get("location", ""))]))
        warnings = "".join(
            f'<div class="warnbox">⚠ {_esc(w)}</div>' for w in item["warnings"])
        # A claim earns a place here by being warned about, judged, or cited — not by
        # being argued over: an untargeted subject is normal. "(0)" over an empty list
        # promises a list and then withholds it, so state the fact instead.
        if item["incoming"]:
            aimed = (f'<h3>What is aimed at this claim ({len(item["incoming"])})</h3>'
                     f'<ul class="edges">'
                     f'{"".join(_edge_block(e, keys) for e in item["incoming"])}</ul>')
        else:
            aimed = ('<p class="muted">No incoming argument edges target this claim.</p>')
        cited = ", ".join(f"<code>{_esc(c)}</code>" for c in item["cited_by"])
        cited_frag = f"cited by the finding via {cited}" if item["cited_by"] else ""
        meta = " · ".join(x for x in (locus, cited_frag) if x)
        meta_html = f'<p class="muted">{meta}</p>' if meta else ""
        anchor = trace_anchor(item["subject"])
        blocks.append(
            f'<section id="{anchor}" class="trace"><h2>{_ledger_href(item["subject"], keys)}</h2>'
            f'<p class="why">Why it appears: {_reason_badges(item.get("reasons", []))}</p>'
            f'{meta_html}{quote}{aimed}{warnings}</section>')
    finding_ref = ('the <a href="finding.html">finding</a>' if finding_present
                   else "an authored finding")
    return _page(f"Evidence trace — {case}", f"""
<header class="hero"><h1>Evidence trace</h1><div class="case">{_esc(case)}</div></header>
<p>Every claim a derived warning, a sealed record, or {finding_ref} puts in question — with its
verbatim quotation, everything aimed at it, and how each inference was judged. Each address here
resolved against the gates before this page was built.</p>
{"".join(blocks)}
<p class="boundary"><strong>The boundary:</strong> Ledger displays these judgements; it does not
settle them. A dispute shows that someone contested an inference, not that the inference is wrong;
a correlation warning shows possible dependence, not that two edges collapse into one.</p>
""")


# The three trust layers render from judge_dashboard's shared renderers (render_derived_
# _layer / render_judgements_layer / render_interpretation_layer) so pack and dashboard
# cannot drift in structure or wording. The pack passes its trace-page base for the focused
# "Inspect" links; the finding.html read-through is a pack-only affordance added in _index.


# ---- the index -------------------------------------------------------------

def _docs_table(repo_root: Path, claims_dir: Path, keys: list[str]) -> str:
    positions = _source_positions(repo_root / "content" / "source_register.md")
    rows = []
    for key in keys:
        ledger = claims_dir / f"{key}.md"
        fm = read_frontmatter(ledger)
        paper = fm.get("paper") or key
        rows.append(
            f'<tr><td><a href="ledgers/{key}.html">{_esc(paper)}</a></td>'
            f'<td>{_esc(_year(paper) or _year(fm.get("retrieved", "")))}</td>'
            f'<td>{_esc(fm.get("source_version", ""))}</td>'
            f'<td>{_esc(positions.get(key, ""))}</td>'
            f'<td class="num">{_claim_count(ledger)}</td>'
            f'<td>{_verdict_badge(fm.get("verified_verdict", ""))}</td>'
            f'<td>{_locator_html(fm)}</td></tr>')
    return (
        '<table class="docs"><thead><tr><th>Document</th><th>Year</th><th>Type</th>'
        '<th>Position</th><th class="num">Claims</th><th>Verified</th><th>Source</th></tr></thead>'
        '<tbody>' + "".join(rows) + "</tbody></table>")


def _gates_checklist(config: dict) -> str:
    items = []
    for key, label in GATE_KEYS:
        val = (config.get(key, "") or "").split("#", 1)[0].strip().lower()
        on = val in _ENFORCED
        mark = "✓" if on else "·"
        cls = "on" if on else "off"
        items.append(f'<li class="{cls}"><span class="mark">{mark}</span> {_esc(label)} '
                     f'<span class="mono">{_esc(val or "off")}</span></li>')
    return f'<ul class="gates">{"".join(items)}</ul>'


def _hitl_map(repo_root: Path, payload: dict, model: dict) -> str:
    """Every place a human judges, comments, or builds — each directly accessible with the
    exact command or file — plus the live 'awaiting judgement' frontier and the honest
    presentation-vs-production boundary. Mirrors the integrity layers of the system map."""
    c = model["counts"]
    idx = payload.get("records_index", {})
    kinds: dict[str, int] = {}
    assessors: set[str] = set()
    for r in idx.values():
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
        if r.get("assessor"):
            assessors.add(str(r["assessor"]))
    kind_str = ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())) or "none yet"
    who = ", ".join(sorted(assessors)) or "—"

    # A real, runnable contest command from the first assessed edge (every shipped case has one).
    contest = ""
    for e in payload.get("edges", []):
        if e.get("edge_record_id"):
            q = next((n["quote"] for n in payload["nodes"] if n["id"] == e["source"]), "")
            contest = contest_command(e["target"], e["source"], e["edge_record_id"], q)
            break
    contest = contest or ("python3 tools/assess_record.py --write --kind faithfulness "
                          "--disputes <edge-record-id> --subject <key:slug> "
                          "--grounding <key:slug> --span '…' --date YYYYMMDD")

    # Band 1 — every human touchpoint, by integrity layer (what · where · exact command · state).
    rows = [
        ("L1", "Write a verified-claim quote",
         "author reads + greps the source, writes the > \"…\" quote into "
         "literature/verified_claims/<key>.md, then stamps it",
         "literature/check.sh <author> <year>  →  literature/fetch_paper.sh --out … --pmcid …  →  "
         "python3 literature/extract_text.py <key>  →  edit ledger  →  "
         "python3 literature/verify_quotes.py --stamp",
         f'{c["ledgers"]} documents'),
        ("L1", "Contest a quote's faithful use",
         "argue a grounding quote does not warrant its inference; file a sealed faithfulness dispute",
         contest, f'{c["faithfulness_records"]} filed'),
        ("L2", "Declare source rationale & known gaps",
         "record why each source is in, and name viewpoints not yet covered",
         "edit content/source_register.md", f'{c["selection_gaps"]} open gaps'),
        ("L3", "Draw a claim-graph edge",
         "assert a typed, quote-grounded relationship between two claims",
         "edit the ledger:  **Supports:** key:slug (grounded by #slug)",
         f'{c["assessed_edges"]} supports/rebuts'),
        ("L4", "Assess edge / rhetorical / crux / double-count",
         "seal a judgement about a claim or an inference",
         "python3 tools/assess_record.py --write --kind <kind> --subject key:slug "
         "--grounding key:slug --span '…' --date YYYYMMDD",
         f'{c["records"]} records ({kind_str})'),
        ("L5", "Write & refine the prose",
         "draft the synthesis one section at a time; the bored-reader test gates readability",
         "the writing loop — AGENTS.md / skill-ledger-write → content/*.md", "—"),
        ("—", "Curate the base",
         "ingest a source, save a good answer as a note, run a health-check",
         "AGENTS.md / skill-ledger-curate", "—"),
    ]
    trows = "".join(
        f'<tr><td><span class="badge neu">{_esc(layer)}</span></td>'
        f'<td><strong>{_esc(what)}</strong><br><span class="muted">{_esc(where)}</span></td>'
        f'<td><pre class="cmd">{_esc(cmd)}</pre></td>'
        f'<td class="mono">{_esc(state)}</td></tr>'
        for layer, what, where, cmd, state in rows)
    band1 = ('<table class="hitl-map"><thead><tr><th>Layer</th><th>What the human does</th>'
             '<th>Direct access</th><th>This project</th></tr></thead>'
             f'<tbody>{trows}</tbody></table>')

    # Band 2 — awaiting judgement (live frontier).
    awaiting = payload.get("awaiting", [])
    if awaiting:
        items = "".join(
            f'<li><div class="await-edge mono">{_esc(a["source"])} '
            f'<span class="badge neu">{_esc(a["type"])}</span> {_esc(a["target"])}</div>'
            + (f'<blockquote>&ldquo;{_esc(a["grounding_quote"])}&rdquo;</blockquote>'
               if a["grounding_quote"] else "")
            + f'<pre class="cmd">{_esc(a["command"])}</pre></li>'
            for a in awaiting)
        band2 = ('<p>These inferences are drawn but not yet judged — the queue a reviewer works. '
                 'Run the command to seal the judgement; the gates re-check it.</p>'
                 f'<ul class="awaiting">{items}</ul>')
    else:
        band2 = ('<p class="empty muted">Every supports/rebuts edge in this project carries a sealed '
                 'judgement — nothing is awaiting review.</p>')

    # Band 3 — presentation vs production (honest boundary).
    band3 = ('<div class="hitl-note"><h4>Presentation vs production</h4>'
             '<p>This export is static. Every action above shows the command to run (fill in the '
             '&lt;placeholders&gt;), which runs '
             'against the repository and the CLI and persists there — nothing typed on this page is '
             'captured. A production reviewer server would instead take a dispute or assessment '
             'through a form, seal it with <code>assess_record.py</code>, re-run the gates and CI, '
             'update the graph live, and manage signer identity and attestation.</p></div>')

    return (
        '<p>The machine guarantees the <em>facts</em> (verbatim quotes, content stamps, structural '
        'resolution). A human supplies the <em>judgement</em> — which sources matter, which '
        'inferences are apt, which moves are rhetorical — sealed and contestable. '
        f'<strong>Sealed so far by:</strong> <span class="mono">{_esc(who)}</span>.</p>'
        f'<h3>Where a human judges, comments, and builds</h3>{band1}'
        f'<h3>Awaiting judgement</h3>{band2}'
        f'{band3}')


QUOTE_MEANING = {
    "empty": "No sources are ingested yet, so there is no quote to check.",
    "unverified": "At least one ledger's verification record is missing or no longer "
                  "matches its source — read the note above before trusting a quote.",
    "attested": "Each quote was proved verbatim against its source when the ledger was "
                "stamped. That record travels; the source bytes do not.",
    "reproducible": "Each quote re-proves byte-for-byte against the source corpus "
                    "shipped alongside.",
}
_BADGE_CLASS = {"Guaranteed": "ok", "Attested": "neu", "Unverified": "bad", "None": "neu"}


def _trust_table(state: dict) -> str:
    """Three things a reader must not conflate: what this bundle enforces in their own
    hands, what was verified upstream and only attested here, and what is a human's
    judgement. Only the first is checkable from the bundle alone, so only the first may
    read as a guarantee while the corpus is absent."""
    quotes = ("Verbatim quotes", state["quote_badge"], _BADGE_CLASS[state["quote_badge"]],
              QUOTE_MEANING[state["level"]])
    rows = [
        ("Graph structure", "Enforced here", "ok",
         "Every edge resolves to a real claim cross-ledger and carries its grounding "
         "quote — checkable from the graph.json in this folder."),
        ("Ledger body integrity", "Enforced here", "ok",
         "Each ledger's body hash is bound into its stamp, so a quote edited after "
         "stamping is caught without the corpus."),
        quotes,
        ("Source provenance", "Attested", "neu",
         "Source and extract hashes were bound when the ledger was stamped; re-binding "
         "them to bytes needs the raw corpus."),
        ("Double-count / correlation", "Mechanical", "neu",
         "Derived from the declared correlated-with edges — flagged, not adjudicated."),
        ("Assessments / faithfulness", "Judged", "warn",
         "A human's tamper-evident, contestable judgement — shown, never claimed "
         "proven, and its assessor recorded as claimed, not authenticated."),
    ]
    body = "".join(f'<tr><td>{_esc(what)}</td><td><span class="badge {cls}">{_esc(status)}'
                   f'</span></td><td>{_esc(meaning)}</td></tr>'
                   for what, status, cls, meaning in rows)
    return ('<table class="trust"><thead><tr><th>What</th><th>Status</th><th>Meaning</th></tr>'
            f'</thead><tbody>{body}</tbody></table>')


def _layers_table() -> str:
    """The five integrity layers (foundation → delivery) and how strongly a failure in
    each can be caught — the map behind the guaranteed-vs-judged boundary. Mirrors
    DEMO.md §5 / docs/integrity_framework.md; the badge encodes the dominant strength
    (ok = Guarantee, neu = Structural, warn = Judged)."""
    rows = [
        ("1 · Fidelity", "fabricated quote · wrong paper · quote out of context", "ok",
         "Fabrication is blocked mechanically; wrong-paper is structural; out-of-context "
         "use is measured + assisted (a detection rate on a labelled benchmark)."),
        ("2 · Completeness", "selection bias · missing source", "neu",
         "Structural + assisted — a floor against a silent empty position, not a "
         "representativeness proof."),
        ("3 · Coherence", "broken or absent links · contradiction · stale claim", "neu",
         "Structural (every edge resolves + is grounded) plus an assisted semantic pass "
         "for meaning."),
        ("4 · Validity", "the conclusion doesn't follow · cherry-picking", "warn",
         "Judged — ledger analyze assists (load-bearing claims, dependency closure, "
         "double-counts). This is the frontier."),
        ("5 · Clarity", "opacity · undefined jargon", "warn",
         "Judged — enforced in the writing loop by the bored-reader test."),
    ]
    label = {"ok": "Guarantee", "neu": "Structural", "warn": "Judged"}
    body = "".join(
        f'<tr><td>{_esc(layer)}</td><td>{_esc(fail)}</td>'
        f'<td><span class="badge {cls}">{_esc(label[cls])}</span> {_esc(status)}</td></tr>'
        for layer, fail, cls, status in rows)
    return ('<table class="trust"><thead><tr><th>Integrity layer</th>'
            '<th>Failure it targets</th><th>How strongly it is caught</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')


# A sub-page is written only where its source file exists, so prose that names one has to
# be built from the same `present` map rather than assuming the full set: a project without
# a source register is a project whose index must not offer that page.
def _links_present(present: dict[str, bool], items: list[tuple]) -> list[str]:
    return [f'<a href="{name}.html">{label}</a>'
            for name, label in items if present.get(name)]


def _trail_sentence(present: dict[str, bool]) -> str:
    links = _links_present(present, [("source_register", "source register"),
                                     ("source_flow", "source flow")])
    if not links:
        return ""
    return f' Positions and the search/known-gaps trail are in the {" and ".join(links)}.'


def _aside_links(present: dict[str, bool]) -> str:
    links = _links_present(present, [("log", "Activity log")])
    if present.get("semantic_health"):
        links.append('<a href="semantic_health.html">Semantic-health review</a> '
                     '(contradictions / missing perspectives)')
    return f'<p class="muted">{" · ".join(links)}.</p>' if links else ""


def _index(repo_root: Path, claims_dir: Path, keys: list[str], config: dict,
           present: dict[str, bool], state: dict) -> str:
    model = dashboard_model(repo_root)
    payload = graphview_payload(repo_root)
    summary = derived_summary(repo_root)
    records = recorded_judgements(repo_root)
    interp = authored_interpretation(repo_root)
    c = model["counts"]
    case = config.get("project_name") or repo_root.name
    metrics = "".join(
        f'<div class="metric"><strong>{v}</strong><label>{_esc(lab)}</label></div>'
        for lab, v in [
            ("Documents", c["ledgers"]), ("Graph edges", c["edges"]),
            ("Unassessed edges", c["unassessed_edges"]), ("Judgement records", c["records"]),
            ("Faithfulness disputes", c["faithfulness_records"]),
            ("Double-count findings", c["double_count_findings"])])

    def out_link(label: str, page: str, key: str) -> str:
        return f'<li><a href="{page}">{_esc(label)}</a></li>' if present.get(key) else ""

    output_links = "".join([
        out_link("Headline finding", "finding.html", "finding"),
        out_link("Inquiry — sub-questions & cruxes", "inquiry.html", "inquiry"),
        '<li><a href="assessments.html">Assessment records</a></li>',
        out_link("Baseline comparison", "baseline.html", "baseline")])

    return _page(case, f"""
<header class="hero"><h1>Ledger — Judge Pack</h1>
<div class="case">{_esc(case)}</div></header>

<section id="overview"><h2>Overview</h2>
<p>This is a navigable read of a contested question. Each claim below is a
<strong>verbatim quote</strong> carrying the record of its proof against a primary source; the
relationships between claims form an argument graph; and a human's tamper-evident, contestable
judgement sits on top. Start here, then follow <a href="#inputs">Inputs</a> →
<a href="#processes">Processes</a> → <a href="#outputs">Outputs</a>. This page <em>shows the trail
and the trust boundary; it does not adjudicate the truth.</em></p>
<p class="ceiling">{_esc(state["ceiling"])}{" " + _esc(state["build_note"]) if state["build_note"] else ""}</p>
{_trust_table(state)}</section>

<section id="derived"><h2>{LAYER1_HEADING}</h2>
{render_derived_layer(summary, "trace.html#")}</section>

<section id="judgements"><h2>{LAYER2_HEADING}</h2>
{render_judgements_layer(records, "trace.html#")}</section>

<section id="interpretation"><h2>{LAYER3_HEADING}</h2>
{render_interpretation_layer(interp)}
{'<p class="muted">Read it in full: <a href="finding.html">the finding</a>.</p>' if interp["present"] else ""}</section>

<section id="how"><h2>How the Ledger works</h2>{_infographic(state)}</section>

<section id="inputs"><h2>Inputs — the corpus</h2>
<p class="muted">The primary sources ingested for this question. Each row opens the rendered ledger:
its provenance, stamps, and every verbatim claim.{_trail_sentence(present)}</p>
{_docs_table(repo_root, claims_dir, keys)}</section>

<section id="processes"><h2>Processes — how it is built</h2>
<p>Each source travels one pipeline: <strong>check</strong> (already on disk?) →
<strong>fetch</strong> → <strong>verify</strong> (every quote proved byte-for-byte against the
fetched source) → <strong>stamp</strong> (hashes bound) → <strong>structure</strong> (typed edges
resolve cross-ledger) → <strong>assess</strong> (human judgement, sealed). The verify step runs
where the corpus lives — in the project, at every commit.</p>
<p>That pipeline is one instrument in a <strong>five-layer integrity stack</strong> — the distinct
ways knowledge work fails, ordered foundation → delivery, crossed with how strongly Ledger catches a
failure in each. Enforcement strength falls as you climb: the foundation is a mechanical guarantee,
the top is disciplined judgement. This is the map behind the
<a href="#overview">guaranteed-vs-judged boundary</a>.</p>
{_layers_table()}
<p>The gates below are what <em>this</em> project actually enforces:</p>
{_gates_checklist(config)}
<p class="muted">Where humans judge, comment, and build — every touchpoint with its exact command:
see <a href="#hitl">Human-in-the-loop</a>.</p>
{_aside_links(present)}</section>

<section id="hitl"><h2>Human-in-the-loop — the collaboration</h2>
{_hitl_map(repo_root, payload, model)}</section>

<section id="outputs"><h2>Outputs — what it produces</h2>
<div class="metrics">{metrics}</div>
{graph_section_html(payload)}
<ul class="outlinks">{output_links}</ul></section>
""")


# ---- orchestration ---------------------------------------------------------

def _bundle_css() -> str:
    base = """:root {
  color-scheme: light dark;
  --ink: #17202a; --muted: #5d6975; --line: #d8dee6; --bg: #f6f8fb; --panel: #ffffff;
  --panel-2: #eef2f7; --accent: #1769aa; --accent-ink: #12557f;
  --good: #2e7d32; --warn: #b8860b; --bad: #c0392b;
  /* --*-ink is the readable text on a tint of its own token, and --on-accent the label
     on an accent fill. A token picked to carry a 3px border is too light to read at
     11px against 16% of itself, so text must not reuse it. */
  --good-ink: #29702d; --warn-ink: #815e08; --bad-ink: #ad3327; --on-accent: #ffffff;
  --graph-bg: #fcfdfe; --exhibit-bg: #f1f7f3; --label-halo: #ffffff;
  --mono: ui-monospace, SFMono-Regular, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --ink: #e6eaf0; --muted: #98a2b3; --line: #232c39; --bg: #0f141b; --panel: #161d27;
  --panel-2: #1c2531; --accent: #6bb0f0; --accent-ink: #9fcdf5;
  --good: #45c07a; --warn: #e0a94a; --bad: #ec6a6a;
  --good-ink: #45c07a; --warn-ink: #e0a94a; --bad-ink: #ee7979; --on-accent: #0f141b;
  --graph-bg: #10161e; --exhibit-bg: #16241d; --label-halo: #0f141b;
} }
:root[data-theme="dark"] {
  --ink: #e6eaf0; --muted: #98a2b3; --line: #232c39; --bg: #0f141b; --panel: #161d27;
  --panel-2: #1c2531; --accent: #6bb0f0; --accent-ink: #9fcdf5;
  --good: #45c07a; --warn: #e0a94a; --bad: #ec6a6a;
  --good-ink: #45c07a; --warn-ink: #e0a94a; --bad-ink: #ee7979; --on-accent: #0f141b;
  --graph-bg: #10161e; --exhibit-bg: #16241d; --label-halo: #0f141b;
}
* { box-sizing: border-box; }
body { margin: 0; font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--ink); background: var(--bg); }
nav { position: sticky; top: 0; z-index: 10; display: flex; gap: 18px; align-items: center; padding: 11px 22px; background: var(--panel); border-bottom: 1px solid var(--line); }
nav .brand { font-weight: 700; color: var(--ink); text-decoration: none; }
nav .navlinks { display: flex; gap: 16px; margin-left: auto; }
nav a { color: var(--accent); text-decoration: none; font-size: 14px; }
.theme-toggle { width: 32px; height: 32px; padding: 0; border-radius: 8px; border: 1px solid var(--line); background: var(--panel); color: var(--ink); cursor: pointer; font-size: 15px; line-height: 1; }
.theme-toggle:hover { background: var(--panel-2); }
main { max-width: 1120px; margin: 0 auto; padding: 22px 20px 48px; }
.hero { padding: 8px 0 4px; } .hero h1 { margin: 0; font-size: 28px; } .hero .case { color: var(--muted); }
h1 { font-size: 26px; } h2 { font-size: 20px; margin: 0 0 12px; } h3 { font-size: 16px; margin: 16px 0 8px; }
section { padding: 20px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); margin-top: 16px; scroll-margin-top: 60px; }
a { color: var(--accent); }
p { margin: 0 0 10px; } .muted { color: var(--muted); font-size: 14px; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }
.back { margin: 0 0 6px; font-size: 14px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 4px; font-size: 14px; }
th, td { border: 1px solid var(--line); padding: 7px 9px; text-align: left; vertical-align: top; }
thead th { background: var(--panel-2); }
td.num, th.num, td.mono { font-variant-numeric: tabular-nums; }
table.fm { width: auto; } table.fm th { background: var(--panel-2); white-space: nowrap; }
.docs tbody tr:hover { background: var(--panel-2); }
.trust td:first-child { font-weight: 600; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; margin-bottom: 14px; }
.metric { padding: 12px 14px; border: 1px solid var(--line); border-radius: 6px; background: var(--panel-2); }
.metric strong { display: block; font-size: 24px; color: var(--accent); }
.metric label { display: block; font-weight: 600; font-size: 13px; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 650; }
.badge.ok { background: color-mix(in srgb, var(--good) 16%, var(--panel)); color: var(--good-ink); }
.badge.warn { background: color-mix(in srgb, var(--warn) 18%, var(--panel)); color: var(--warn-ink); }
.badge.bad { background: color-mix(in srgb, var(--bad) 16%, var(--panel)); color: var(--bad-ink); }
.badge.neu { background: var(--panel-2); color: var(--muted); }
.ceiling { border-left: 3px solid var(--warn); background: var(--panel-2); margin: 14px 0;
           padding: 10px 14px; font-size: 14px; border-radius: 0 6px 6px 0; }
.gates { list-style: none; padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 4px 16px; }
.gates li { font-size: 14px; } .gates .mark { display: inline-block; width: 16px; font-weight: 700; }
.gates li.on .mark { color: var(--good); } .gates li.off { color: var(--muted); }
.hitl { border-left: 3px solid var(--warn); padding: 4px 0 4px 14px; margin: 12px 0; }
.hitl-map td:nth-child(3) { padding: 0; width: 46%; }
pre.cmd { white-space: pre-wrap; word-break: break-word; margin: 0; padding: 8px 10px; background: var(--panel-2); border-radius: 6px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11.5px; color: var(--ink); }
ul.awaiting { list-style: none; padding: 0; margin: 10px 0; display: grid; gap: 10px; }
ul.awaiting > li { border: 1px solid var(--line); border-left: 3px solid var(--warn); border-radius: 0 8px 8px 0; padding: 10px 14px; background: var(--bg); }
.await-edge { margin-bottom: 6px; }
ul.awaiting blockquote { margin: 6px 0; padding: 6px 12px; border-left: 3px solid var(--good); background: var(--exhibit-bg); border-radius: 0 6px 6px 0; }
.empty { color: var(--muted); }
.hitl-note { border-left: 3px solid var(--accent); padding: 8px 0 4px 14px; margin: 14px 0 0; }
.hitl-note h4 { margin: 0 0 4px; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .9em; background: var(--panel-2); border-radius: 4px; padding: 0 4px; }
.infographic { width: 100%; height: auto; }
/* The infographic boxes have hard-coded light fills, so their inner text is pinned
   dark (not var(--ink)) to stay readable when the page is dark; .ig-note sits on the
   page background and follows the theme. */
.ig-t { font: 700 14px sans-serif; fill: #17202a; } .ig-s { font: 12px sans-serif; fill: #5d6975; }
.ig-tag { font: 11px sans-serif; fill: #5d6975; } .ig-chip { font: 700 10px sans-serif; fill: #fff; }
.ig-note { font: italic 12px sans-serif; fill: var(--muted); }
.ledger-body blockquote { margin: 0 0 10px; padding: 8px 12px; border-left: 3px solid var(--good); background: var(--exhibit-bg); }
.ledger-body h2 { font-size: 17px; border-top: 1px solid var(--line); padding-top: 12px; margin-top: 16px; }
.outlinks { margin: 6px 0 0; }
section.trace { border-top: 1px solid var(--line); padding-top: 14px; margin-top: 22px; }
blockquote.subject { margin: 8px 0; padding: 10px 14px; border-left: 3px solid var(--good);
  background: var(--exhibit-bg); border-radius: 0 6px 6px 0; font-size: 15px; }
ul.edges { list-style: none; padding: 0; display: grid; gap: 12px; }
li.edge { border: 1px solid var(--line); border-radius: 8px; padding: 10px 14px; background: var(--bg); }
li.edge blockquote { margin: 6px 0; padding: 6px 12px; border-left: 3px solid var(--line);
  background: var(--panel-2); border-radius: 0 6px 6px 0; font-size: 13.5px; }
.edge-h { font-size: 13.5px; margin-bottom: 2px; }
.etype { font-weight: 700; color: var(--accent); }
.rec { font-size: 12.5px; margin-top: 6px; }
.rec .span { margin-top: 4px; padding-left: 10px; border-left: 2px solid var(--bad); color: var(--muted); }
.warnbox { margin-top: 10px; padding: 8px 12px; border-left: 3px solid var(--warn);
  background: var(--panel-2); border-radius: 0 6px 6px 0; font-size: 13px; }
.boundary { margin-top: 26px; padding: 10px 14px; border-left: 3px solid var(--accent);
  background: var(--panel-2); border-radius: 0 6px 6px 0; font-size: 13.5px; }
.action { display: inline-block; margin: 10px 0; padding: 9px 16px; border-radius: 8px;
  background: var(--accent); color: var(--on-accent); font-weight: 650; text-decoration: none; }
.action:hover { background: var(--accent-ink); }
.no-finding { border-left: 3px solid var(--line); padding: 10px 14px; margin: 12px 0;
  background: var(--panel-2); border-radius: 0 6px 6px 0; color: var(--muted); font-size: 14px; }
/* The three trust layers. Neutral throughout: a dependence warning carries the amber warn
   accent (it IS a warning); a judgement and a declared cause never get green success fills.
   The provenance distinction is text (.prov / .badge), never colour alone. */
.layer-note { color: var(--muted); font-size: 13.5px; border-left: 3px solid var(--line);
  background: var(--panel-2); padding: 8px 12px; border-radius: 0 6px 6px 0; margin: 0 0 12px; }
.warn-card, .rec-card { border: 1px solid var(--line); border-radius: 0 8px 8px 0;
  padding: 12px 14px; margin: 10px 0; background: var(--bg); }
.warn-card { border-left: 3px solid var(--warn); } .rec-card { border-left: 3px solid var(--line); }
.warn-h, .rec-h { display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  font-weight: 700; margin-bottom: 8px; }
.warn-card .row, .rec-card .row { display: grid; grid-template-columns: 150px 1fr auto;
  gap: 8px; align-items: baseline; padding: 4px 0; font-size: 13.5px;
  border-top: 1px solid var(--line); }
.warn-card .row:first-of-type, .rec-card .row:first-of-type { border-top: 0; }
.row .k { color: var(--muted); font-weight: 600; } .row .v { word-break: break-word; }
.prov { font-size: 11px; color: var(--muted); background: var(--panel-2);
  border: 1px solid var(--line); border-radius: 999px; padding: 1px 8px; white-space: nowrap; }
.row .prov { justify-self: end; } .warn-h .prov, .rec-h .prov { margin-left: auto; }
.more-recs { margin-top: 10px; }
.more-recs summary { cursor: pointer; color: var(--accent); font-size: 14px; }
.prov-strip { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 13px;
  color: var(--muted); background: var(--panel-2); border: 1px solid var(--line);
  border-radius: 8px; padding: 8px 12px; margin-bottom: 8px; }
.why { font-size: 13px; margin: 2px 0 6px; }
/* The evidence path is walked by keyboard, so the ring sits outside the element: on an
   accent-filled .action an inset ring would be drawn against its own background. */
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }
"""
    # GRAPH_CSS (appended after `base`) re-declares .badge.ok/.warn/.bad with light
    # hard-coded hexes; re-assert the theme-aware versions AFTER it so the pack pages
    # theme correctly in dark mode too (mirrors judge_dashboard's GRAPHCSS trailer).
    trailer = (
        ".badge.ok { background: color-mix(in srgb, var(--good) 16%, var(--panel)); color: var(--good-ink); }\n"
        ".badge.warn { background: color-mix(in srgb, var(--warn) 18%, var(--panel)); color: var(--warn-ink); }\n"
        ".badge.bad { background: color-mix(in srgb, var(--bad) 16%, var(--panel)); color: var(--bad-ink); }\n")
    return base + "\n" + GRAPH_CSS.replace("    ", "") + "\n" + trailer


def build_pack(repo_root: Path, out_dir: Path) -> list[str]:
    repo_root, out_dir = repo_root.resolve(), out_dir.resolve()
    claims_dir = repo_root / "literature" / "verified_claims"
    content = repo_root / "content"
    keys = _ledger_keys(claims_dir)
    config = parse_config(repo_root / "ledger.config.md")
    # The bundle, not the project: inclusion is read from the bytes that will travel, so
    # nothing below copying a corpus is what makes this read 'attested' — not a promise
    # made here. Ship the sources into out_dir and the page re-reads itself.
    state = verification_state(repo_root, artefact="pack", bundle_dir=out_dir)

    sub = {
        "finding": (content / "finding.md", "Headline finding", "table"),
        "inquiry": (content / "inquiry.md", "Inquiry — sub-questions & cruxes", "table"),
        "source_register": (content / "source_register.md", "Source register", "table"),
        "source_flow": (content / "source_flow.md", "Source flow", "table"),
        "log": (content / "log.md", "Activity log", "drop"),
        "semantic_health": (content / "_ledger" / "semantic_health.md", "Semantic-health review", "table"),
        "baseline": (content / "baseline_comparison.md", "Baseline comparison", "drop"),
    }
    present = {name: src.is_file() for name, (src, _t, _f) in sub.items()}

    written: list[str] = []

    def write(rel: str, text: str) -> None:
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(rel)

    trace = evidence_trace(repo_root)
    record_ids = {p.stem.split(".")[0].lower()
                  for p in (content / "assessments" / RECORDS_DIR_NAME).glob("*.json")}
    out_dir.mkdir(parents=True, exist_ok=True)
    write("assets/ledger.css", _bundle_css())
    write("index.html", _index(repo_root, claims_dir, keys, config, present, state))
    for key in keys:
        write(f"ledgers/{key}.html", _ledger_page(key, claims_dir, keys, record_ids))
    for name, (src, title, fmmode) in sub.items():
        if present[name]:
            write(f"{name}.html", _content_page(title, src, keys, record_ids, frontmatter=fmmode))
    write("assessments.html", _assessments_page(repo_root, keys, record_ids))

    if trace:
        write("trace.html",
              _trace_page(trace, keys, config.get("project_name") or repo_root.name,
                          present.get("finding", False)))

    graph = build_graph(claims_dir, content / "inquiry.md", content / "assessments")
    write("graph.json", json.dumps(graph, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    write("graph.mmd", to_mermaid(graph) + "\n")
    write("README.md", "\n".join([
        "# Ledger — Judge Pack", "",
        f"Project: `{repo_root.name}`", "",
        "Open `index.html` in any browser (no install, no server). It is organised",
        "Inputs → Processes → Outputs; the docs table links to a rendered page per",
        "ingested document. This folder is derived output — edit the Ledger project,",
        "not the pack.", ""]))
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a navigable Ledger judge bundle.")
    ap.add_argument("repo_root", nargs="?", default=str(REPO_ROOT),
                    help="Ledger project to package (default: current kit root)")
    ap.add_argument("--out", required=True, help="output directory for the bundle")
    args = ap.parse_args()
    repo_root = Path(args.repo_root)
    if not (repo_root / "ledger.config.md").is_file():
        print(f"[ledger] {repo_root} is not a Ledger project (no ledger.config.md).",
              file=sys.stderr)
        return 2
    written = build_pack(repo_root, Path(args.out))
    print(f"[INFO] wrote judge pack to {Path(args.out).resolve()} ({len(written)} file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
