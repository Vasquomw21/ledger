# === SCRIPT: Judge dashboard — one static review surface for the ledger ===
# Read-only by default: emits a self-contained HTML report to stdout unless --out
# is given. It does not decide whether the project is good; it makes the evidence
# trail visible in one page and lets a judge navigate it: the argument graph, the
# full quote ledger, a dossier per source, the sealed judgement records, the
# development documents it was built from (inquiry, finding, source trail, config —
# rendered read-only), and the metrics. Every claim carries its verbatim quote (the
# FACT layer); every assessment
# — the rhetorical flags, double-counts, faithfulness disputes — is surfaced as a
# readable comment on the quote it judges (the MEASURE layer). Single file, inline
# CSS+JS, no CDN, no build — it opens offline in any browser, light or dark.
# INPUTS : ledger.config.md; content/inquiry.md; content/finding.md;
#          content/source_register.md; content/source_flow.md;
#          content/assessments/_records/; literature/verified_claims/.
# OUTPUTS: static HTML.
# Run    : python3 tools/judge_dashboard.py > /tmp/ledger_dashboard.html
from __future__ import annotations

import argparse
import html
import json
import re
import shlex
import sys
from collections import defaultdict
from pathlib import Path

from build_graph import build_graph, edge_record_id
from check_assessment import (ASSESSED_EDGE_TYPES, RECORDS_DIR_NAME,
                              double_count_findings, edge_assessment_problems,
                              load_correlation_kinds, load_records,
                              load_records_validated, resolve_rec_refs,
                              valid_edge_coverage)
from check_citations import gated_prefixes, parse_config
from check_selection import selection_problems
from check_source_flow import source_flow_problems
from check_manifest import (ledger_body, read_frontmatter, run_record_problems,
                            sha256_file, sha256_text, stamp_problems)
from ledger_status import build_report
import claim_graph as cg
import md_render

REPO_ROOT = Path(__file__).resolve().parents[1]


def _esc(text: object) -> str:
    return html.escape(str(text), quote=True)


# ---- verification state: what was proved, and what the reader can repeat ----

def _corpus_in_bundle(bundle_dir, stamped: list) -> bool:
    """Whether the READER holds the bytes: every stamped source present INSIDE the
    exported artefact, at the path its ledger records, hashing to the stamp.

    Verified, never declared. Bytes on the builder's disk are not bytes in the reader's
    hands, and the two are one confusion apart — a caller wiring this to the project's
    own corpus would restore the overclaim in a single line. A hash check cannot be
    satisfied by that mistake, or by shipping a source that no longer matches its stamp.
    """
    if bundle_dir is None or not stamped:
        return False
    for _key, fm in stamped:
        rel = (fm.get("file") or "").strip()
        if not rel:
            return False
        source = Path(bundle_dir) / rel
        if not source.is_file() or sha256_file(source) != fm.get("source_sha256", ""):
            return False
    return True


def verification_state(repo_root: Path, *, bundle_dir=None,
                       artefact: str = "export") -> dict:
    """Two facts a single 'verified' badge conflates: whether a verbatim proof was
    performed and recorded for these ledgers, and whether THIS artefact carries the
    source bytes a reader needs to repeat it. They come apart — raw sources are
    git-ignored, so a fully verified project exports to a reader who cannot re-prove
    a thing. Claiming a proof the reader cannot run is the failure this guards.

    bundle_dir is the exported artefact's root, or None for an export that is a single
    file. Attestation and body integrity are checkable from the exported ledgers alone;
    re-binding source_sha256 needs the corpus, so build-time bytes are reported only as
    a hash match. This never re-runs the quote scan, so it never says the quotes were
    re-proved here.
    """
    claims_dir = repo_root / "literature" / "verified_claims"
    keys = (sorted(p.stem for p in claims_dir.glob("*.md") if p.stem != "TEMPLATE")
            if claims_dir.is_dir() else [])

    stamped, unattested, sources_at_build, drifted = [], [], [], []
    for key in keys:
        ledger = claims_dir / f"{key}.md"
        fm = read_frontmatter(ledger)
        body = sha256_text(ledger_body(ledger))
        if (stamp_problems(fm, key) or body != fm.get("body_sha256", "")
                or run_record_problems(claims_dir, key, fm, body)):
            unattested.append(key)
            continue
        stamped.append((key, fm))
        source = repo_root / (fm.get("file") or "")
        if not (fm.get("file") and source.is_file()):
            continue
        sources_at_build.append(key)
        if sha256_file(source) != fm.get("source_sha256", ""):
            drifted.append(key)

    corpus_included = _corpus_in_bundle(bundle_dir, stamped)
    attested = len(keys) - len(unattested)
    if not keys:
        level = "empty"
    elif unattested or drifted:
        level = "unverified"
    elif corpus_included:
        level = "reproducible"
    else:
        level = "attested"

    return {
        "ledgers": len(keys),
        "attested": attested,
        "unattested": unattested,
        "sources_at_build": len(sources_at_build),
        "drifted": drifted,
        "corpus_included": corpus_included,
        "level": level,
        "quote_badge": QUOTE_BADGE[level],
        "ceiling": _ceiling(level, artefact, len(keys), attested, unattested, drifted),
        "build_note": ("Source bytes were on disk when this was generated and matched "
                       "every committed hash." if sources_at_build and not drifted else ""),
    }


QUOTE_BADGE = {"empty": "None", "unverified": "Unverified",
               "attested": "Attested", "reproducible": "Guaranteed"}


def _ceiling(level: str, artefact: str, ledgers: int, attested: int,
             unattested: list, drifted: list) -> str:
    if level == "empty":
        return "No sources are ingested yet, so there is nothing to verify."
    if level == "unverified":
        parts = []
        if unattested:
            parts.append(f"{len(unattested)} of {ledgers} ledger(s) carry no valid "
                         "verification record")
        if drifted:
            parts.append(f"{len(drifted)} source file(s) no longer match the hash they "
                         "were stamped against")
        return ("Quote verification: " + "; ".join(parts)
                + ". Treat the affected quotations as unverified.")
    if level == "reproducible":
        return (f"Quote verification: attested by {attested} committed verification "
                f"record(s), and the source corpus travels with this {artefact} — the "
                "quotations can be re-proved against source bytes here.")
    return (f"Quote verification: attested by {attested} committed verification "
            f"record(s). The source corpus is not included, so this {artefact} cannot "
            "re-prove quotations against source bytes.")


def _li(items: list[str], empty: str) -> str:
    if not items:
        return f"<p class=\"empty\">{_esc(empty)}</p>"
    return "<ul>" + "".join(f"<li>{_esc(item)}</li>" for item in items) + "</ul>"


def _metric(label: str, value: object, note: str = "", *,
            tab: str = "", scroll: str = "") -> str:
    """A metric tile. When `tab` or `scroll` is given it becomes a deep-link: `tab`
    switches to that tab; `scroll` jumps to a section (its detail lives lower in the
    Metrics tab). The delegated handler in _APP_JS acts on the data-* attributes."""
    note_html = f"<span>{_esc(note)}</span>" if note else ""
    body = f"<strong>{_esc(value)}</strong><label>{_esc(label)}</label>{note_html}"
    if tab or scroll:
        attrs = ' class="metric metric-link" role="link" tabindex="0"'
        if tab:
            attrs += f' data-tab="{_esc(tab)}"'
        if scroll:
            attrs += f' data-scroll="{_esc(scroll)}"'
        return f"<div{attrs}>{body}</div>"
    return f'<div class="metric">{body}</div>'


def _linkify_refs(text: str, node_ids: set, ledger_first: dict) -> str:
    """Turn the real identifiers a metrics/gap line names — key:slug claim ids, and
    bare ledger keys — into Board jump-links (data-goto). Only ids that resolve to a
    real node are linked; everything else stays plain escaped text. key:slug is
    matched before bare keys so the slug isn't split off its ledger."""
    out = _esc(text)
    for tid in sorted(node_ids, key=len, reverse=True):
        pat = re.compile(r"(?<![\w:-])" + re.escape(tid) + r"(?![\w:-])")
        out = pat.sub(lambda m, t=tid: f'<a class="jump" data-goto="{t}">{t}</a>', out)
    for lk in sorted(ledger_first, key=len, reverse=True):
        pat = re.compile(r"(?<![\w:-])" + re.escape(lk) + r"(?![\w:-])")
        out = pat.sub(lambda m, k=lk, dst=ledger_first[lk]: f'<a class="jump" data-goto="{dst}">{k}</a>', out)
    return out


def dashboard_model(repo_root: Path) -> dict:
    claims_dir = repo_root / "literature" / "verified_claims"
    records_dir = repo_root / "content" / "assessments" / "_records"
    record_rows = load_records(records_dir)
    records = [r for _stem, r, _err in record_rows if r]
    records_by_id = {str(r.get("id", "")).lower(): r for r in records}
    record_ids = set(records_by_id)
    edges = list(cg.iter_edges(claims_dir))
    assessed_edges = [e for e in edges if e.edge_type in ASSESSED_EDGE_TYPES]
    unassessed = edge_assessment_problems(
        claims_dir, record_ids, valid_edge_coverage(records_dir, claims_dir))
    faithfulness = [r for r in records if r.get("kind") == "faithfulness"]
    faithfulness_passes = [r for r in records if r.get("kind") == "faithfulness-pass"]
    disputed = {str(d).lower() for r in records for d in (r.get("disputes") or [])}
    double_counts = double_count_findings(
        claims_dir, repo_root / "content" / "assessments" / "_records",
        load_correlation_kinds(repo_root / "content")[0])
    selection_gaps = selection_problems(
        claims_dir, repo_root / "content" / "source_register.md", repo_root / "content" / "inquiry.md")
    source_flow_gaps = source_flow_problems(claims_dir, repo_root / "content" / "source_flow.md")

    return {
        "status": build_report(repo_root),
        "counts": {
            "ledgers": len([p for p in claims_dir.glob("*.md")
                            if claims_dir.is_dir() and p.stem != "TEMPLATE"]),
            "edges": len(edges),
            "assessed_edges": len(assessed_edges),
            "unassessed_edges": len(unassessed),
            "records": len(records),
            "faithfulness_records": len(faithfulness),
            "faithfulness_passes": len(faithfulness_passes),
            "disputed_records": len(disputed),
            "double_count_findings": len(double_counts),
            "selection_gaps": len(selection_gaps),
            "source_flow_gaps": len(source_flow_gaps),
        },
        "unassessed": unassessed,
        "double_counts": double_counts,
        "selection_gaps": selection_gaps,
        "source_flow_gaps": source_flow_gaps,
        "record_errors": [f"{stem}: {err}" for stem, rec, err in record_rows if rec is None],
    }


_LOCATION_RE = re.compile(r"^\*\*Location:\*\*\s*(.+)$", re.IGNORECASE)
# A double-count finding reads "<A> and <B> both support <target> but are
# In-band markers that carry a human "comment" on a claim but reach no other
# surface. The rhetorical assessment is the headline one — a quote-pinned span
# plus the reviewer's rationale; the rest are the premise/status/crux notes.
_MARKER_RE = re.compile(r"^\*\*(?P<label>[A-Za-z][\w-]*):\*\*\s*(?P<rest>.*)$")
_QUOTED_RE = re.compile(r'["“”]([^"“”]+)["“”]')
_BRACKET_NOTE_RE = re.compile(r"\[(?!rec:)([^\]]+)\]", re.IGNORECASE)
_GROUNDED_RE = re.compile(r"\(grounded by[^)]*\)", re.IGNORECASE)


def _claim_location(body: str) -> str:
    """The `**Location:**` reference of a claim block, or '' if none."""
    for line in (body or "").splitlines():
        m = _LOCATION_RE.match(line.strip())
        if m:
            return m.group(1).strip()
    return ""


def _clean_note(text: str) -> str:
    """Strip the `(grounded by …)` and `[rec: …]` machine clauses and dashes, so
    what's left is the human sentence."""
    text = _GROUNDED_RE.sub("", text)
    text = cg.REC_REF_RE.sub("", text)
    return text.strip(" \t—–-")


def claim_annotations(body: str) -> list[dict]:
    """The in-band human comments on a claim, parsed from its `## Claim` block.
    Each is {type, note, ...}: `rhetorical` carries the flagged span + the record
    id it seals to; `correlated`/`crux` carry the shared-premise / if-resolved
    note; `status` carries the settlement note. This prose lives only in the
    ledger markdown today — the dashboard is the first surface to render it."""
    out: list[dict] = []
    for raw in (body or "").splitlines():
        line = raw.strip()
        m = _MARKER_RE.match(line)
        if not m:
            continue
        label = m.group("label").lower()
        rest = m.group("rest").strip()
        rec_m = cg.REC_REF_RE.search(rest)
        rec = rec_m.group("id").lower() if rec_m else ""
        if label == "assess-rhetorical":
            span_m = _QUOTED_RE.search(rest)
            span = span_m.group(1) if span_m else ""
            note = _clean_note(_QUOTED_RE.sub("", rest, count=1))
            out.append({"type": "rhetorical", "span": span, "note": note, "rec": rec})
        elif label == "status":
            out.append({"type": "status", "note": _clean_note(rest), "rec": rec})
        elif label == "correlated-with":
            note_m = _BRACKET_NOTE_RE.search(rest)
            out.append({"type": "correlated", "target": rest.split()[0] if rest else "",
                        "note": note_m.group(1).strip() if note_m else "", "rec": rec})
        elif label == "crux-of":
            note_m = _BRACKET_NOTE_RE.search(rest)
            out.append({"type": "crux", "target": rest.split()[0] if rest else "",
                        "note": note_m.group(1).strip() if note_m else "", "rec": rec})
    return out


def _double_count_ledgers(findings: list[dict]) -> set[str]:
    """Ledger keys named as the correlated supporters in double-count findings — the two
    sources, not the shared target, so the amber ring lands on them, not the claim they
    both point at. Reads the typed finding dicts build_graph now emits."""
    out: set[str] = set()
    for f in findings:
        out.add(str(f["a"]).split(":")[0].lower())
        out.add(str(f["b"]).split(":")[0].lower())
    return out


_HEADING_RE = re.compile(r"^#\s+(.+)$")
_SUBHEAD_RE = re.compile(r"^##\s+(.+)$")
_QPREFIX_RE = re.compile(r"^Q\d+\s*[—–-]\s*", re.IGNORECASE)
_INQUIRY_PREFIX_RE = re.compile(r"^Inquiry\s*[—–-]\s*", re.IGNORECASE)
_QID_RE = re.compile(r"^\*\*id:\*\*\s*([\w-]+)", re.IGNORECASE)


def _case_context(content_dir: Path, fallback: str) -> dict:
    """The hero copy: the case title + the sub-questions being adjudicated (the
    thesis of the page), plus a one-line verdict from finding.md if present."""
    title, questions, verdict = "", [], ""
    inquiry = content_dir / "inquiry.md"
    if inquiry.is_file():
        lines = inquiry.read_text(encoding="utf-8", errors="ignore").splitlines()
        for i, ln in enumerate(lines):
            s = ln.strip()
            h = _HEADING_RE.match(s)
            if h and not title:
                title = _INQUIRY_PREFIX_RE.sub("", h.group(1).strip())
                continue
            sh = _SUBHEAD_RE.match(s)
            if sh:
                qid = ""
                for ln2 in lines[i + 1:]:
                    if ln2.strip().startswith("#"):
                        break
                    qm = _QID_RE.match(ln2.strip())
                    if qm:
                        qid = qm.group(1).lower()
                        break
                questions.append({"qid": qid, "text": _QPREFIX_RE.sub("", sh.group(1).strip())})
    verdict = finding_lead(content_dir / "finding.md")[:320]
    return {"title": title or fallback, "questions": questions, "verdict": verdict}


_MD_NOISE_RE = re.compile(r"\*\*|\*|`|\[\[|\]\]")
# A `[rec: id]` marker addresses a sealed judgement; the pack's own pages link it, but the
# lead is one sentence with nowhere to land a link, and an unresolvable-looking id is worse
# than none. The reference stays in the finding, which the lead sits one click from.
_REC_MARKER_IN_LEAD_RE = re.compile(r"\s*\[rec:\s*[^\]]*\]")


def finding_lead(path: Path) -> str:
    """The finding's opening paragraph — after the title, before the first section
    heading — as plain text.

    One reader for both surfaces: the hero and the pack's first screen must quote the
    same authored sentence rather than two guesses at it. Stopping at the first heading
    is the protocol — a finding states its lesson first — and it is why this cannot be
    a search for a known heading, which would impose one template on cases whose whole
    value is that each shows something different. Summarising here would be the machine
    writing the one thing that must be human-approved, so a finding that opens with a
    heading simply has no lead.
    """
    if not path.is_file():
        return ""
    lines = path.read_text(encoding="utf-8", errors="ignore").split("\n")
    # Skip a leading YAML frontmatter block so provenance metadata (author/date) never
    # becomes the lead — the lead is the first authored PROSE, after any frontmatter.
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is not None:
            lines = lines[end + 1:]
    paragraph: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if stripped.startswith(("# ", "---")):
            continue
        if not stripped:
            if paragraph:
                break
            continue
        paragraph.append(stripped)
    lead = _REC_MARKER_IN_LEAD_RE.sub("", " ".join(paragraph))
    return _MD_NOISE_RE.sub("", lead)


def _slug(text: str) -> str:
    """Lowercase, non-alphanumeric runs collapsed to a single hyphen (for suggested ids)."""
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def _suggest_edge_id(source: str, target: str, etype: str) -> str:
    """A deterministic, unique-per-edge suggested record id, e.g. worobey-supports-nolab-apt.
    Only a suggestion — the id merely has to be unique when the reviewer writes it."""
    src = source.split(":", 1)[0].split("_")[0]      # from_ledger:grounding -> surname
    tgt = target.split(":", 1)[-1]                    # key:slug -> slug
    return _slug(f"{src}-{etype}-{tgt}-apt")


def _span_arg(quote: str) -> str:
    """A shell-safe --span from a grounding quote: whitespace-normalised, length-capped,
    single-quote escaped so embedded quotes/backticks/$ are inert on paste."""
    span = " ".join(str(quote).split())[:140]
    return shlex.quote(span or "quote-pinned span")


def assess_command(target: str, source: str, suggested_id: str, quote: str) -> str:
    """The exact command a reviewer runs to judge a supports/rebuts edge apt.
    subject = the edge's target claim, grounding = the claim it is grounded by."""
    return ("python3 tools/assess_record.py --write --kind edge "
            f"--id {suggested_id} --subject {target} --grounding {source} "
            f"--span {_span_arg(quote)} --date YYYYMMDD")


def contest_command(target: str, source: str, edge_record_id: str, quote: str) -> str:
    """The exact command to contest an assessed edge (file a faithfulness dispute).
    Empty when the edge carries no record id to dispute."""
    if not edge_record_id:
        return ""
    return ("python3 tools/assess_record.py --write --kind faithfulness "
            f"--disputes {edge_record_id} --subject {target} --grounding {source} "
            f"--span {_span_arg(quote)} --date YYYYMMDD")


def graphview_payload(repo_root: Path) -> dict:
    """The enriched client-side model, shared by the single-file dashboard and the
    judge pack's embedded graph. Every node carries its verbatim quote + locus +
    source locator (the FACT layer), the sealed judgement records that touch it,
    and the in-band rhetorical/premise comments (the MEASURE layer); every edge
    carries its grounding quote, the record that judged it apt, and whether it has
    been judged. Derived from graph.json's structure + the verified-claims quotes —
    embedded straight into the HTML so it opens with no server."""
    claims_dir = repo_root / "literature" / "verified_claims"
    content_dir = repo_root / "content"
    graph = build_graph(claims_dir, content_dir / "inquiry.md", content_dir / "assessments")

    records = [r for _s, r, _e in load_records(content_dir / "assessments" / "_records") if r]
    records_by_id = {str(r.get("id", "")).lower(): r for r in records}
    record_ids = set(records_by_id)
    edge_records = valid_edge_coverage(content_dir / "assessments" / "_records", claims_dir)

    records_by_subject: dict[str, list[dict]] = defaultdict(list)
    records_index: dict[str, dict] = {}
    for r in records:
        rid = str(r.get("id", "")).lower()
        subj = str(r.get("subject", "")).lower()
        slim = {
            "id": rid, "kind": r.get("kind", ""), "subject": subj,
            "span": r.get("span", ""), "grounding": r.get("grounding", []) or [],
            "disputes": [str(d).lower() for d in (r.get("disputes") or [])],
            "reviews": [str(d).lower() for d in (r.get("reviews") or [])],
            "assessor": r.get("assessor", ""), "date": r.get("assessed_date", ""),
        }
        records_by_subject[subj].append(slim)
        records_index[rid] = slim

    ledger_qids: dict[str, set] = {}
    for a in graph["addresses"]:
        ledger_qids.setdefault(a["ledger"], set()).add(a["qid"])

    # A node is contested when some record disputes a record whose subject is it.
    contested: set[str] = set()
    for r in records:
        for d in (r.get("disputes") or []):
            target = records_by_id.get(str(d).lower())
            if target and target.get("subject"):
                contested.add(str(target["subject"]).lower())

    kinds_by_node: dict[str, set] = {}
    for a in graph["assessments"]:
        kinds_by_node.setdefault(str(a["subject"]).lower(), set()).add(a["kind"])

    dc_findings = graph["findings"]["double_count"]
    dc_ledgers = _double_count_ledgers(dc_findings)
    fm_cache: dict[str, dict] = {}

    def _fm(key: str) -> dict:
        if key not in fm_cache:
            led = cg.ledger_for_key(claims_dir, key)
            fm_cache[key] = read_frontmatter(led) if led else {}
        return fm_cache[key]

    nodes = []
    for addr in graph["nodes"]:
        key, _, slug = addr.partition(":")
        led = cg.ledger_for_key(claims_dir, key)
        quote = cg.claim_quote(led, slug) if led else ""
        body = cg.claim_body(led, slug) if led else None
        fm = _fm(key)
        nodes.append({
            "id": addr,
            "ledger": key,
            "slug": slug,
            "quote": quote,
            "location": _claim_location(body or ""),
            "locator": {"doi": fm.get("doi", ""), "pmcid": fm.get("pmcid", ""),
                        "url": fm.get("url", "")},
            "source": fm.get("paper", "") or fm.get("title", ""),
            "qids": sorted(ledger_qids.get(key, set())),
            "kinds": sorted(kinds_by_node.get(addr, set())),
            "contested": addr in contested,
            "double_count": (key in dc_ledgers) if dc_ledgers
                            else any(addr in f for f in dc_findings),
            "resolved": bool(led) and bool(quote),
            "records": records_by_subject.get(addr, []),
            "annotations": claim_annotations(body or ""),
        })

    by_id = {n["id"]: n for n in nodes}
    edges = []
    for e in graph["edges"]:
        if not e["source"]:
            continue
        # supports/rebuts carry an assessment; every other edge type is always "assessed"
        # (nothing to judge). One shared predicate (build_graph.edge_record_id).
        rec_id = edge_record_id(e, edge_records)
        assessed = rec_id is not None if e["type"] in ASSESSED_EDGE_TYPES else True
        edges.append({
            "source": e["source"], "target": e["target"], "type": e["type"],
            "assessed": assessed, "grounding": e.get("grounding"), "rec": e.get("rec"),
            "edge_record_id": rec_id,
            "from_ledger": e.get("from_ledger"), "line": e.get("line"),
            "target_resolved": e.get("target_resolved", True),
        })

    # The supports/rebuts edges with no sealed judgement yet — the live frontier where a
    # human still has to decide. Each carries the grounding quote that must warrant the
    # inference and the exact command to seal that judgement.
    awaiting = []
    for e in edges:
        if e["type"] not in ASSESSED_EDGE_TYPES or e["assessed"]:
            continue
        grounding_quote = (by_id.get(e["source"]) or {}).get("quote", "")
        if not grounding_quote and e["from_ledger"] and e["grounding"]:
            led = cg.ledger_for_key(claims_dir, e["from_ledger"])
            grounding_quote = cg.claim_quote(led, e["grounding"]) if led else ""
        sid = _suggest_edge_id(e["source"], e["target"], e["type"])
        awaiting.append({
            "source": e["source"], "target": e["target"], "type": e["type"],
            "grounding": e["grounding"], "from_ledger": e["from_ledger"],
            "target_resolved": e["target_resolved"],
            "subject_quote": (by_id.get(e["target"]) or {}).get("quote", ""),
            "grounding_quote": grounding_quote,
            "suggested_id": sid,
            "command": assess_command(e["target"], e["source"], sid, grounding_quote),
        })

    sources = []
    for key in sorted({n["ledger"] for n in nodes}):
        fm = _fm(key)
        sources.append({
            "key": key, "paper": fm.get("paper", "") or fm.get("title", "") or key,
            "title": fm.get("title", ""), "doi": fm.get("doi", ""),
            "pmcid": fm.get("pmcid", ""), "url": fm.get("url", ""),
            "verified_verdict": fm.get("verified_verdict", ""),
            "verified_date": fm.get("verified_date", ""),
            "body_sha256": fm.get("body_sha256", ""),
            "source_version": fm.get("source_version", ""),
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "sub_questions": graph["sub_questions"],
        "double_count": dc_findings,
        "ledgers": sorted({n["ledger"] for n in nodes}),
        "sources": sources,
        "records_index": records_index,
        "awaiting": awaiting,
        "case": _case_context(content_dir, repo_root.name),
    }


# ---- the evidence trace a finding's references open -------------------------

def trace_anchor(addr: str) -> str:
    """The trace-section id for a claim address — shared so every 'Inspect' link, in pack
    or dashboard, lands on the exact section rather than the page top."""
    return re.sub(r"[^a-z0-9]+", "-", str(addr).lower()).strip("-")


# Why a claim earns a place in the trace. The three are independent: an entry survives on
# any one of them, so removing the finding drops only TRACE_AUTHORED reasons.
TRACE_DERIVED = "derived warning"
TRACE_JUDGED = "recorded judgement"
TRACE_AUTHORED = "authored reference"


def evidence_trace(repo_root: Path) -> list[dict]:
    """Every claim a derived warning, a sealed record, or an authored finding puts in
    question: its verbatim quote, every edge aimed at it, and the judgements on those
    edges. Each entry carries WHY it appears.

    The subject set is the UNION of the three sources, so the trace stands without a
    finding — dropping content/finding.md removes only the 'authored reference' reasons,
    never an entry a warning or a record also justifies. Every subject is still a resolved
    address (a warning target and a record subject are real claims); nothing is drawn from
    prose parsing, so an address the gate would reject cannot reach the page.
    """
    claims_dir = repo_root / "literature" / "verified_claims"
    content_dir = repo_root / "content"
    records_dir = content_dir / "assessments" / RECORDS_DIR_NAME
    config = parse_config(repo_root / "ledger.config.md")

    _all, valid, _ids, _problems = load_records_validated(records_dir, claims_dir)
    payload = graphview_payload(repo_root)
    by_id = {n["id"]: n for n in payload["nodes"]}
    findings = double_count_findings(claims_dir, records_dir, load_correlation_kinds(content_dir)[0])
    cited = [r for r in resolve_rec_refs(content_dir, records_dir, claims_dir,
                                         gated_prefixes(config), root=repo_root)
             if r.resolved]

    # subject -> reasons, first-seen order: derived warnings, then records, then finding
    # references. That order also drives which entries lead the trace page.
    reasons: dict[str, list[str]] = {}

    def _want(addr: str, why: str) -> None:
        key = str(addr).strip().lower()
        if not key:
            return
        bucket = reasons.setdefault(key, [])
        if why not in bucket:
            bucket.append(why)

    for finding in findings:
        _want(finding.target, TRACE_DERIVED)
    for record in valid.values():
        _want(record.get("subject", ""), TRACE_JUDGED)
    for ref in cited:
        _want(ref.record.get("subject", ""), TRACE_AUTHORED)

    contests: dict[str, list] = defaultdict(list)
    upholds: dict[str, list] = defaultdict(list)
    for record in valid.values():
        for target in record.get("disputes") or []:
            contests[str(target).lower()].append(record)
        for target in record.get("reviews") or []:
            upholds[str(target).lower()].append(record)

    trace = []
    for subject, why in reasons.items():
        incoming = []
        for edge in payload["edges"]:
            if edge["target"].lower() != subject:
                continue
            rec_id = (edge.get("edge_record_id") or "").lower()
            source = by_id.get(edge["source"]) or {}
            incoming.append({
                "source": edge["source"],
                "type": edge["type"],
                "grounding_quote": source.get("quote", ""),
                "source_paper": source.get("source", ""),
                "record_id": edge.get("edge_record_id"),
                "contested_by": contests.get(rec_id, []),
                "upheld_by": upholds.get(rec_id, []),
            })
        trace.append({
            "subject": subject,
            "node": by_id.get(subject),
            "incoming": incoming,
            "warnings": [f.summary for f in findings if f.target.lower() == subject],
            "reasons": why,
            "cited_by": [r.ref_id for r in cited
                         if str(r.record.get("subject", "")).lower() == subject],
        })
    return trace


def derived_summary(repo_root: Path) -> dict:
    """Layer 1 — what Ledger DERIVES from the committed records, with each fact's
    provenance kept: mechanically-computed (the warning fired, which pair, the counts),
    author-declared (the correlation's kind + basis), and assessment present/absent (a
    sealed correlated-with record backs the pair, or it is declared-only).

    Deterministic — same files, same output — but never a claim of established truth: the
    kind is carried as `declared`, the count as a count, and nothing here reads a finding.
    """
    claims_dir = repo_root / "literature" / "verified_claims"
    content_dir = repo_root / "content"
    records_dir = content_dir / "assessments" / RECORDS_DIR_NAME
    graph = build_graph(claims_dir, content_dir / "inquiry.md",
                        content_dir / "assessments")

    def _warning(w) -> dict:
        return {
            "a": w.a, "b": w.b, "target": w.target,
            "kind": w.kind, "kind_label": w.kind_label, "basis": w.basis,
            "sealed_record": w.sealed_record,
            "judgement_status": ("sealed assessment present" if w.sealed_record
                                 else "declared only; no sealed assessment"),
        }

    warnings = [_warning(w) for w in double_count_findings(claims_dir, records_dir, load_correlation_kinds(content_dir)[0])]

    # Principal-claim targeting is in-degree over every edge type; aptness below
    # counts only supports/rebuts, the edges an assessment can hold apt. The two
    # edge sets differ on purpose — do not unify them.
    incoming: dict[str, int] = defaultdict(int)
    for edge in graph["edges"]:
        incoming[edge["target"]] += 1
    principal = [{"claim": t, "incoming": n}
                 for t, n in sorted(incoming.items(), key=lambda kv: (-kv[1], kv[0]))]

    edge_cov = valid_edge_coverage(records_dir, claims_dir)
    assessed = [e for e in graph["edges"] if e["type"] in ASSESSED_EDGE_TYPES]
    reviewed = sum(1 for e in assessed if edge_record_id(e, edge_cov) is not None)
    return {
        "warnings": warnings,
        "principal_claims": principal,
        "aptness": {"reviewed": reviewed, "total": len(assessed)},
    }


# Layer 2 — a record's label states its ROLE, never its correctness: a faithfulness
# dispute reads "disputed", its upholding pass "reviewed — held", anything else "sealed
# record". Never "confirmed"/"proved"/"valid".
_RECORD_LABELS = {"faithfulness": "disputed", "faithfulness-pass": "reviewed — held"}


def recorded_judgements(repo_root: Path) -> list[dict]:
    """Layer 2 — the tamper-evident judgements, relevant-first. Integrity is
    membership in the validated set (the coverage the gate blocks on), reported as a
    fact about the record's grounding and seal — never that the judgement is correct
    or that its assessor is authenticated (only `attestation` signs).
    The pair a Layer-1 warning names is 'relevant'; those records lead the list."""
    claims_dir = repo_root / "literature" / "verified_claims"
    content_dir = repo_root / "content"
    records_dir = content_dir / "assessments" / RECORDS_DIR_NAME
    all_by_id, valid, _ids, _problems = load_records_validated(records_dir, claims_dir)

    relevant_keys: set[str] = set()
    for w in double_count_findings(claims_dir, records_dir, load_correlation_kinds(content_dir)[0]):
        relevant_keys.update({w.a, w.b, cg.parse_address(w.target).key})

    def _touches(record: dict) -> bool:
        addrs = [record.get("subject", ""), *(record.get("grounding") or [])]
        keys = {cg.parse_address(str(a)).key for a in addrs if a}
        return bool(keys & relevant_keys)

    out = []
    for rid, record in all_by_id.items():
        out.append({
            "id": record.get("id", rid),
            "kind": record.get("kind", ""),
            "assessor": record.get("assessor", ""),
            "date": record.get("assessed_date", ""),
            "subject": record.get("subject", ""),
            "grounding": list(record.get("grounding") or []),
            "span": record.get("span", ""),
            "disputes": list(record.get("disputes") or []),
            "reviews": list(record.get("reviews") or []),
            "integrity": "verified" if rid in valid else "unverified",
            "label": _RECORD_LABELS.get(record.get("kind", ""), "sealed record"),
            "trace_anchor": trace_anchor(record.get("subject", "")),
            "relevant": _touches(record),
        })
    out.sort(key=lambda r: (not r["relevant"], r["date"], r["id"]))
    return out


def authored_interpretation(repo_root: Path) -> dict:
    """Layer 3 — the optional finding.md. Provenance is read from the finding's OWN
    frontmatter, never git: an absent author/date is reported absent, an absent finding
    is reported absent. Nothing here is generated or endorsed."""
    path = repo_root / "content" / "finding.md"
    if not path.is_file():
        return {"present": False, "lead": "", "author": "", "date": "",
                "has_provenance": False}
    fm = read_frontmatter(path)
    author = str(fm.get("author") or fm.get("curator") or "").strip()
    date = str(fm.get("date") or fm.get("authored") or "").strip()
    return {"present": True, "lead": finding_lead(path), "author": author,
            "date": date, "has_provenance": bool(author or date)}


# ---- the three trust layers, rendered once for both surfaces ----------------
# Headings and boundary sentences are shared constants so pack and dashboard cannot drift
# in terminology. Each renderer reads only the shared model (derived_summary /
# recorded_judgements / authored_interpretation); the sole surface difference is the trace
# link: the pack passes its trace-page base, the dashboard passes none (its board is the
# exploration surface). Persistent text labels carry provenance; colour never does.

LAYER1_HEADING = "What Ledger derived from committed records"
LAYER2_HEADING = "Recorded judgements"
LAYER3_HEADING = "Authored interpretation"
LAYER1_NOTE = ("Computed from the committed ledgers and records — deterministic, each "
               "fact keeping its provenance. A declared cause is the author’s "
               "classification, not a machine-established fact; a count is a count; "
               "nothing here reads the authored interpretation below.")
LAYER2_BOUNDARY = ("These are tamper-evident assessments supplied by people or agents. "
                   "Ledger verifies their integrity, grounding and freshness. The seal is "
                   "an unkeyed digest: the assessor and date are recorded as claimed, not "
                   "authenticated, and sealing does not establish that a judgement is "
                   "correct.")
LAYER3_BOUNDARY = ("Ledger validates the cited claim and record addresses. The "
                   "interpretation and conclusion remain the author’s judgement.")
LAYER3_EMPTY = "No case-level interpretation has been authored."


def _prov(label: str) -> str:
    return f'<span class="prov">{_esc(label)}</span>'


def _rows_html(rows: list) -> str:
    return "".join(
        f'<div class="row"><span class="k">{_esc(k)}</span>'
        f'<span class="v">{v}</span>{_prov(tag) if tag else ""}</div>'
        for k, v, tag in rows)


def _warn_card(w: dict, trace_base: str | None) -> str:
    status_tag = "record available" if w["sealed_record"] else "no record"
    basis = _esc(w["basis"]) or '<span class="muted">no basis declared</span>'
    body = _rows_html([
        ("Pair", f'<code>{_esc(w["a"])}</code> ↔ <code>{_esc(w["b"])}</code>', ""),
        ("Target", f'<code>{_esc(w["target"])}</code>', ""),
        ("Declared cause", _esc(w["kind_label"]), "author-declared"),
        ("Declared basis", basis, "author-declared"),
        ("Judgement status", _esc(w["judgement_status"]), status_tag)])
    action = (f'<a class="action" href="{trace_base}{trace_anchor(w["target"])}">'
              'Inspect basis and grounding</a>' if trace_base else "")
    return (f'<div class="warn-card"><div class="warn-h">Dependence warning detected'
            f'{_prov("mechanically derived")}</div>{body}{action}</div>')


def render_derived_layer(summary: dict, trace_base: str | None = None) -> str:
    warns = summary["warnings"]
    if warns:
        dep = '<h4>Dependence warnings</h4>' + "".join(
            _warn_card(w, trace_base) for w in warns)
    else:
        dep = ('<h4>Dependence warnings</h4><p class="muted">None: no two supporters of '
               'one claim are declared correlated with each other.</p>')
    principal = [p for p in summary["principal_claims"] if p["incoming"] >= 2]
    if principal:
        rows = "".join(f'<tr><td><code>{_esc(p["claim"])}</code></td>'
                       f'<td class="num">{p["incoming"]}</td></tr>' for p in principal)
        targeting = ('<h4>Claim targeting</h4>'
                     '<p class="muted">Conclusions targeted by two or more edges — a '
                     'structural in-degree count, not a measure of how well-supported a '
                     'claim is.</p><table class="layer-tbl"><thead><tr><th>Conclusion</th>'
                     '<th class="num">Incoming edges</th></tr></thead><tbody>'
                     f'{rows}</tbody></table>')
    else:
        targeting = ('<h4>Claim targeting</h4><p class="muted">No conclusion is targeted '
                     'by more than one edge.</p>')
    apt = summary["aptness"]
    gap = apt["total"] - apt["reviewed"]
    coverage = ('<h4>Review coverage</h4><p>'
                f'{apt["reviewed"]} of {apt["total"]} supports/rebuts edges carry a sealed '
                'assessment' + (f'; {gap} remain unreviewed.' if gap else '.') + '</p>')
    return f'<p class="layer-note">{_esc(LAYER1_NOTE)}</p>{dep}{targeting}{coverage}'


def _rec_card(r: dict, trace_base: str | None) -> str:
    who = " · ".join(filter(None, [_esc(str(r["assessor"]).split("@")[0]),
                                        _esc(r["date"])]))
    grounding = (", ".join(f'<code>{_esc(g)}</code>' for g in r["grounding"])
                 or '<span class="muted">none</span>')
    rows = [("Kind", _esc(r["kind"]), ""), ("Assessor", who, ""),
            ("Subject", f'<code>{_esc(r["subject"])}</code>', ""),
            ("Grounding", grounding, "")]
    if r["disputes"]:
        rows.append(("Disputes", ", ".join(f'<code>{_esc(d)}</code>' for d in r["disputes"]), ""))
    if r["reviews"]:
        rows.append(("Reviews", ", ".join(f'<code>{_esc(d)}</code>' for d in r["reviews"]), ""))
    rows.append(("Integrity", f'{_esc(r["integrity"])} — grounding and seal checked; '
                              'this does not establish the judgement is correct', ""))
    action = (f'<a class="action" href="{trace_base}{_esc(r["trace_anchor"])}">'
              'Inspect judgement evidence</a>' if trace_base else "")
    return (f'<div class="rec-card"><div class="rec-h"><span class="badge neu">'
            f'{_esc(r["label"])}</span> <code>{_esc(r["id"])}</code>'
            f'{_prov("sealed judgement")}</div>{_rows_html(rows)}{action}</div>')


def render_judgements_layer(records: list, trace_base: str | None = None) -> str:
    boundary = f'<p class="boundary">{_esc(LAYER2_BOUNDARY)}</p>'
    if not records:
        return boundary + ('<p class="muted">No sealed judgements have been recorded for '
                           'this case.</p>')
    relevant = [r for r in records if r["relevant"]]
    other = [r for r in records if not r["relevant"]]
    # Relevant records (those a warning names) stay open and JS-free; when nothing is
    # flagged relevant, every record is shown open. Only the surplus folds into <details>.
    lead, rest = (relevant, other) if relevant else (other, [])
    rest_html = ""
    if rest:
        rest_html = ('<details class="more-recs"><summary>'
                     f'{len(rest)} further sealed record(s)</summary>'
                     + "".join(_rec_card(r, trace_base) for r in rest) + '</details>')
    return boundary + "".join(_rec_card(r, trace_base) for r in lead) + rest_html


def render_interpretation_layer(interp: dict) -> str:
    tag = _prov("authored interpretation")
    if not interp["present"]:
        return (f'<div class="no-finding">{tag} <strong>{_esc(LAYER3_EMPTY)}</strong> '
                'The derived results and recorded judgements above stand on their own.'
                '</div>')
    if interp["has_provenance"]:
        strip = " · ".join(filter(None, [
            f'Author/curator: {_esc(interp["author"])}' if interp["author"] else "",
            f'Date: {_esc(interp["date"])}' if interp["date"] else "",
            "Status: references mechanically validated"]))
    else:
        strip = "Authorship not recorded · Status: references mechanically validated"
    lead = interp["lead"]
    return (f'<div class="prov-strip">{tag} {strip}</div>'
            f'<p class="boundary">{_esc(LAYER3_BOUNDARY)}</p>'
            + (f'<p>{_esc(lead)}</p>' if lead else ""))


# ---- the tabs (server-rendered static HTML off the enriched payload) --------

def _flag_badges(n: dict) -> str:
    out = ""
    if n.get("contested"):
        out += '<span class="badge bad">faithfulness-disputed</span>'
    if n.get("double_count"):
        out += '<span class="badge warn">double-count</span>'
    for kd in n.get("kinds", []):
        if kd not in ("faithfulness", "faithfulness-pass"):
            out += f'<span class="badge ok">{_esc(kd)}</span>'
    return out


def _locator_link(loc: dict) -> str:
    if loc.get("doi"):
        return f'<a href="https://doi.org/{_esc(loc["doi"])}" target="_blank" rel="noopener" class="mono">doi:{_esc(loc["doi"])}</a>'
    if loc.get("pmcid"):
        pid = str(loc["pmcid"]).replace("PMC", "")
        return (f'<a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC{_esc(pid)}/" '
                f'target="_blank" rel="noopener" class="mono">PMC{_esc(pid)}</a>')
    if loc.get("url"):
        return f'<a href="{_esc(loc["url"])}" target="_blank" rel="noopener" class="mono">source</a>'
    return '<span class="muted">—</span>'


def _quotes_tab(payload: dict) -> str:
    rows = []
    for n in payload["nodes"]:
        if not n["quote"]:
            continue
        qchips = "".join(f'<span class="chip-sm">{_esc(q)}</span>' for q in n["qids"])
        rows.append(
            '<tr data-text="{txt}">'
            '<td>{src}<div class="mono muted">{slug}</div></td>'
            '<td class="quote">&ldquo;{quote}&rdquo;</td>'
            '<td>{qchips}</td><td>{flags}</td></tr>'.format(
                txt=_esc((n["source"] + " " + n["slug"] + " " + n["quote"]).lower()),
                src=_esc(n["source"] or n["ledger"]), slug=_esc(n["id"]),
                quote=_esc(n["quote"]), qchips=qchips or '<span class="muted">—</span>',
                flags=_flag_badges(n) or '<span class="muted">—</span>'))
    if not rows:
        return '<p class="empty">No verbatim quotes yet — this ledger has no claims.</p>'
    return (
        '<div class="toolbar"><input type="search" class="filter" data-target="quotes-table" '
        'placeholder="filter quotes by source or text…" autocomplete="off" spellcheck="false">'
        f'<span class="muted">{len(rows)} verbatim quotes</span></div>'
        '<table class="ledger-table" id="quotes-table"><thead><tr>'
        '<th>Source</th><th>Verbatim quote</th><th>Sub-question</th><th>Flags</th>'
        '</tr></thead><tbody>' + "".join(rows) + '</tbody></table>')


def _sources_tab(payload: dict) -> str:
    by_ledger: dict[str, list[dict]] = defaultdict(list)
    for n in payload["nodes"]:
        by_ledger[n["ledger"]].append(n)
    edges = payload["edges"]
    if not payload["sources"]:
        return '<p class="empty">No sources ingested yet.</p>'
    cards = []
    for s in payload["sources"]:
        key = s["key"]
        claims = by_ledger.get(key, [])
        verdict = s["verified_verdict"]
        vcls = "ok" if verdict == "pass" else ("bad" if verdict else "warn")
        fp = str(s["body_sha256"])[:12]
        prov = (
            f'<div class="prov"><span class="badge {vcls}">verified: {_esc(verdict or "unstamped")}</span>'
            + (f'<span class="mono muted"> body {_esc(fp)}…</span>' if fp else "")
            + (f'<span class="mono muted"> · {_esc(s["verified_date"])}</span>' if s["verified_date"] else "")
            + f' · {_locator_link(s)}</div>')
        claim_html = "".join(
            f'<li><span class="mono muted">{_esc(c["slug"])}</span> &ldquo;{_esc(c["quote"])}&rdquo; {_flag_badges(c)}</li>'
            for c in claims if c["quote"]) or '<li class="muted">no resolved quotes</li>'
        outgoing = [e for e in edges if (e["from_ledger"] or "") == key]
        incoming = [e for e in edges if str(e["target"]).split(":")[0] == key and (e["from_ledger"] or "") != key]
        rel_html = ""
        for e in outgoing:
            rel_html += (f'<li><span class="etag {_esc(e["type"])}">{_esc(e["type"])}</span> '
                         f'&rarr; <span class="mono">{_esc(e["target"])}</span>'
                         + ('' if e["assessed"] else ' <em class="muted">(unassessed)</em>') + '</li>')
        for e in incoming:
            rel_html += (f'<li><span class="mono">{_esc(e["source"])}</span> '
                         f'<span class="etag {_esc(e["type"])}">{_esc(e["type"])}</span> &rarr; here</li>')
        rel_block = f'<div class="src-rel"><h4>Relations</h4><ul class="tight">{rel_html}</ul></div>' if rel_html else ""
        cards.append(
            f'<article class="dossier"><header><h3>{_esc(s["paper"])}</h3>'
            + (f'<p class="muted">{_esc(s["title"])}</p>' if s["title"] and s["title"] != s["paper"] else "")
            + f'{prov}</header>'
            f'<div class="src-claims"><h4>Claims ({len(claims)})</h4><ul class="tight">{claim_html}</ul></div>'
            f'{rel_block}</article>')
    return f'<div class="dossiers">{"".join(cards)}</div>'


def _assessments_tab(payload: dict, model: dict) -> str:
    idx = payload["records_index"]
    rows = []
    dash = '<span class="muted">—</span>'
    for rid in sorted(idx):
        r = idx[rid]
        if r["disputes"]:
            thread = "disputes " + ", ".join(f'<span class="mono">{_esc(d)}</span>' for d in r["disputes"])
        elif r["reviews"]:
            thread = "reviews " + ", ".join(f'<span class="mono">{_esc(d)}</span>' for d in r["reviews"])
        else:
            thread = dash
        span_cell = f'&ldquo;{_esc(r["span"])}&rdquo;' if r["span"] else dash
        rows.append(
            f'<tr data-text="{_esc((rid + " " + r["kind"] + " " + r["subject"]).lower())}">'
            f'<td class="mono">{_esc(rid)}</td><td><span class="badge ok">{_esc(r["kind"])}</span></td>'
            f'<td class="mono">{_esc(r["subject"])}</td>'
            f'<td>{span_cell}</td><td>{thread}</td>'
            f'<td class="mono muted">{_esc(r["assessor"])}<br>{_esc(r["date"])}</td></tr>')
    table = (
        '<table class="ledger-table" id="records-table"><thead><tr><th>Record</th><th>Kind</th>'
        '<th>Subject claim</th><th>Flagged span</th><th>Thread</th><th>Assessor</th></tr></thead>'
        '<tbody>' + ("".join(rows) or '<tr><td colspan="6" class="muted">No sealed judgement records.</td></tr>')
        + '</tbody></table>')
    # The in-band rhetorical / premise comments — the human prose the records seal.
    notes = []
    for n in payload["nodes"]:
        for a in n["annotations"]:
            if not a.get("note"):
                continue
            label = {"rhetorical": "rhetorical", "correlated": "shared-premise",
                     "crux": "crux", "status": "status"}.get(a["type"], a["type"])
            span = f'&ldquo;{_esc(a["span"])}&rdquo; — ' if a.get("span") else ""
            rec = f' <a class="mono" href="#" data-rec="{_esc(a["rec"])}">[{_esc(a["rec"])}]</a>' if a.get("rec") else ""
            notes.append(
                f'<li><span class="etag {_esc(a["type"])}">{label}</span> '
                f'<span class="mono muted">{_esc(n["id"])}</span> — {span}{_esc(a["note"])}{rec}</li>')
    notes_block = (f'<h3>Reviewer comments</h3><ul class="comments">{"".join(notes)}</ul>'
                   if notes else "")
    intro = ('<p class="lead">Every judgement is <strong>sealed</strong> (self-hashed) and names its '
             '<strong>assessor</strong> — the human-in-the-loop fingerprint. A faithfulness record '
             'disputes another by id; nothing here is claimed proven, only shown and made contestable.</p>')
    return f'{intro}<div class="toolbar"><input type="search" class="filter" data-target="records-table" placeholder="filter records…" autocomplete="off"></div>{table}{notes_block}'


def _awaiting_html(awaiting: list, node_ids: set, ledger_first: dict) -> str:
    """The supports/rebuts edges with no sealed judgement yet — each with its grounding
    quote and the exact command a reviewer runs to judge it. Empty = every edge judged."""
    if not awaiting:
        return ('<p class="empty">Every supports/rebuts edge carries a sealed judgement — '
                'nothing is awaiting review.</p>')
    items = []
    for a in awaiting:
        rel = _linkify_refs(f'{a["source"]} {a["type"]} {a["target"]}', node_ids, ledger_first)
        quote = (f'<blockquote>&ldquo;{_esc(a["grounding_quote"])}&rdquo;</blockquote>'
                 if a["grounding_quote"] else "")
        items.append(f'<li><div class="await-edge">{rel}</div>{quote}'
                     f'<pre class="cmd">{_esc(a["command"])}</pre></li>')
    return ('<p class="lead">These inferences are drawn but not yet judged. Run the command to '
            'file the judgement — it seals to the repo and the gates re-check it.</p>'
            f'<ul class="awaiting">{"".join(items)}</ul>')


def _metrics_tab(model: dict, payload: dict) -> str:
    c = model["counts"]
    node_ids = {n["id"] for n in payload["nodes"]}
    ledger_first: dict = {}
    for n in payload["nodes"]:
        ledger_first.setdefault(n["ledger"], n["id"])

    def li(items: list, empty: str) -> str:
        if not items:
            return f'<p class="empty">{_esc(empty)}</p>'
        return "<ul>" + "".join(
            f"<li>{_linkify_refs(it, node_ids, ledger_first)}</li>" for it in items) + "</ul>"

    metrics = "".join([
        _metric("Sources", c["ledgers"], tab="sources"),
        _metric("Graph edges", c["edges"], tab="board"),
        _metric("Supports/rebuts edges", c["assessed_edges"], tab="board"),
        _metric("Awaiting judgement", c["unassessed_edges"],
                "supports/rebuts edges not yet judged — the human's queue",
                scroll="#sec-unassessed"),
        _metric("Judgement records", c["records"], tab="assessments"),
        _metric("Faithfulness disputes", c["faithfulness_records"], tab="assessments"),
        _metric("Faithfulness passes", c["faithfulness_passes"], tab="assessments"),
        _metric("Disputed records", c["disputed_records"], tab="assessments"),
        _metric("Double-count findings", c["double_count_findings"], scroll="#sec-double-count"),
        _metric("Selection gaps", c["selection_gaps"], scroll="#sec-selection"),
        _metric("Source-flow gaps", c["source_flow_gaps"], scroll="#sec-source-flow"),
    ])
    sections = "\n".join([
        f'<section id="sec-unassessed"><h3>Awaiting human judgement</h3>{_awaiting_html(payload.get("awaiting", []), node_ids, ledger_first)}</section>',
        f'<section id="sec-source-flow"><h3>Source-flow gaps</h3>{li(model["source_flow_gaps"], "No source-flow gaps detected.")}</section>',
        f'<section id="sec-selection"><h3>Selection gaps</h3>{li(model["selection_gaps"], "No selection-audit gaps detected.")}</section>',
        f'<section id="sec-double-count"><h3>Double-count findings</h3>{li(model["double_counts"], "No double-count findings detected.")}</section>',
        f'<section id="sec-record-errors"><h3>Record parse errors</h3>{li(model["record_errors"], "No unreadable judgement records.")}</section>',
    ])
    return (f'<div class="metrics">{metrics}</div>'
            f'<section><h3>Operator status</h3><pre>{_esc(chr(10).join(model["status"]))}</pre></section>'
            f'{sections}')


# The source-of-truth markdown behind a case — surfaced read-only so a judge can
# read the documents the ledger was built from, not just the claims extracted from
# them. Order is narrative: what we asked → what we found → how sources got in →
# the review → the postures the gates ran under.
_DOC_SPECS = [
    ("content/inquiry.md", "The inquiry — the question tree (Anchor B)"),
    ("content/finding.md", "The finding — the verdict"),
    ("content/source_flow.md", "Source flow — discovery & screening trail"),
    ("content/source_register.md", "Source register — selection audit"),
    ("content/_ledger/semantic_health.md", "Semantic-health review"),
    ("ledger.config.md", "Project config — gate postures"),
]


def _inquiry_provenance_badges(text: str) -> str:
    """Surface who drafted the inquiry (AI vs human) and whether a human reviewed
    it — the one unmechanised, framing-setting input, made visible."""
    fm, _ = md_render.split_frontmatter(text)
    who = fm.get("authored_by", "")
    if not who:
        return ""
    ok = who == "human"
    out = (f'<span class="badge {"ok" if ok else "warn"}">'
           f'{"human-authored" if ok else "AI-drafted"}</span>')
    status = fm.get("status", "")
    if status:
        out += f'<span class="badge muted">{_esc(status)}</span>'
    return out


def _docs_tab(repo_root: Path) -> str:
    blocks = []
    for i, (rel, role) in enumerate(_DOC_SPECS):
        path = repo_root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        badges = _inquiry_provenance_badges(text) if rel.endswith("inquiry.md") else ""
        body = md_render.render_markdown(text, frontmatter="table")
        opened = " open" if not blocks else ""  # first present doc open
        blocks.append(
            f'<details class="doc-item"{opened}>'
            f'<summary><code>{_esc(rel)}</code>'
            f'<span class="doc-role">{_esc(role)}</span>{badges}</summary>'
            f'<div class="doc">{body}</div></details>')
    if not blocks:
        return ('<section><p class="lead">No development documents found for this '
                'case yet — the inquiry, finding, and source trail live here once written.</p></section>')
    intro = ('<section class="doc-intro"><h3>Development documents</h3>'
             '<p class="lead">The source-of-truth markdown this ledger was built from — the '
             'inquiry that frames it, the finding, the source-discovery trail, the review, and '
             'the gate postures. Rendered read-only; the AI-drafted inquiry is flagged as such.</p>'
             '</section>')
    return intro + "".join(blocks)


def render_html(repo_root: Path) -> str:
    model = dashboard_model(repo_root)
    payload = graphview_payload(repo_root)
    c = model["counts"]
    case = payload["case"]
    n_quotes = sum(1 for n in payload["nodes"] if n["quote"])
    n_flags = c["faithfulness_records"] + c["double_count_findings"]

    eyebrow = f'LEDGER · {_esc(repo_root.name)}'
    questions = "".join(
        f'<li>{_esc(q["text"])}</li>' for q in case["questions"]) if case["questions"] else ""
    questions_html = f'<ul class="questions">{questions}</ul>' if questions else ""
    verdict_html = f'<p class="verdict">{_esc(case["verdict"])}</p>' if case["verdict"] else ""
    integrity = " · ".join([
        f'<b>{c["ledgers"]}</b> sources', f'<b>{n_quotes}</b> verbatim quotes',
        f'<b>{c["edges"]}</b> relations', f'<b>{n_flags}</b> flags',
    ])
    # One HTML file has no bundle to carry a corpus in, so the reader can never re-prove
    # from it: no bundle_dir exists to pass.
    state = verification_state(repo_root, artefact="page")
    ceiling = (f'<p class="ceiling">{_esc(state["ceiling"])}</p>'
               if state["level"] != "empty" else "")

    # The three trust layers, stacked and always visible (not tabs) — same shared model and
    # wording as the pack. The dashboard passes no trace base: its board is the exploration
    # surface, so the cards carry no cross-page 'Inspect' link.
    layers = (
        f'<section class="layer" id="derived"><h2>{_esc(LAYER1_HEADING)}</h2>'
        f'{render_derived_layer(derived_summary(repo_root))}</section>'
        f'<section class="layer" id="judgements"><h2>{_esc(LAYER2_HEADING)}</h2>'
        f'{render_judgements_layer(recorded_judgements(repo_root))}</section>'
        f'<section class="layer" id="interpretation"><h2>{_esc(LAYER3_HEADING)}</h2>'
        f'{render_interpretation_layer(authored_interpretation(repo_root))}</section>')

    tabs = [("board", "Board"), ("quotes", "Quotes"), ("sources", "Sources"),
            ("assessments", "Assessments"), ("docs", "Docs"), ("metrics", "Metrics")]
    tab_nav = "".join(
        f'<button class="tab{" active" if i == 0 else ""}" role="tab" '
        f'aria-selected="{"true" if i == 0 else "false"}" data-tab="{t}">{_esc(lab)}</button>'
        for i, (t, lab) in enumerate(tabs))

    panels = {
        "board": graph_section_html(payload),
        "quotes": _quotes_tab(payload),
        "sources": _sources_tab(payload),
        "assessments": _assessments_tab(payload, model),
        "docs": _docs_tab(repo_root),
        "metrics": _metrics_tab(model, payload),
    }
    panels_html = "".join(
        f'<div class="tabpanel" data-panel="{t}"{"" if i == 0 else " hidden"}>{panels[t]}</div>'
        for i, (t, _lab) in enumerate(tabs))

    return (_PAGE
            .replace("__GRAPHCSS__", GRAPH_CSS)
            .replace("__EYEBROW__", eyebrow)
            .replace("__CASE_TITLE__", _esc(case["title"]))
            .replace("__QUESTIONS__", questions_html)
            .replace("__VERDICT__", verdict_html)
            .replace("__INTEGRITY__", integrity)
            .replace("__CEILING__", ceiling)
            .replace("__TABS__", tab_nav)
            .replace("__LAYERS__", layers)
            .replace("__PANELS__", panels_html)
            .replace("__APPJS__", _APP_JS))


_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ledger Judge Dashboard</title>
  <style>
    :root {
      color-scheme: light dark;
      --canvas: #f7f8fa; --panel: #ffffff; --panel-2: #f1f3f6;
      --ink: #1a2230; --muted: #5b6675; --line: #e4e8ee;
      --accent: #0e7c7b; --accent-ink: #0a5a59;
      --bg: var(--panel-2);
      --good: #2e9e5b; --warn: #c98a2b; --bad: #d64545;
      /* --*-ink is the readable text on a tint of its own token, and --on-accent the
         label on an accent fill. A token picked to carry a 3px border or a graph edge
         is too light to read at 11px against 16% of itself. */
      --good-ink: #1c5f37; --warn-ink: #79521a; --bad-ink: #802929; --on-accent: #ffffff;
      --e-supports: #2e9e5b; --e-rebuts: #d64545; --e-qualifies: #c98a2b;
      --e-depends: #3e6ddb; --e-neutral: #6b7686; --e-supersedes: #8a5cd1;
      --graph-bg: #fcfdfe; --exhibit-bg: #f1f7f3; --label-halo: #ffffff;
      --flag-bg: #fdf0f0; --shadow: 0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.06);
      --serif: "Iowan Old Style", "Charter", "Palatino", Georgia, serif;
      --sans: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      --mono: ui-monospace, "SF Mono", SFMono-Regular, Menlo, "Cascadia Code", monospace;
    }
    @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
      --canvas: #0f141b; --panel: #161d27; --panel-2: #1c2531;
      --ink: #e6eaf0; --muted: #98a2b3; --line: #232c39;
      --accent: #2fb3b0; --accent-ink: #7fe3e0;
      --good: #45c07a; --warn: #e0a94a; --bad: #ec6a6a;
      --good-ink: #45c07a; --warn-ink: #e0a94a; --bad-ink: #ed7171; --on-accent: #0f141b;
      --e-supports: #45c07a; --e-rebuts: #ec6a6a; --e-qualifies: #e0a94a;
      --e-depends: #6e92f0; --e-neutral: #8a96a6; --e-supersedes: #a985e0;
      --graph-bg: #10161e; --exhibit-bg: #16241d; --label-halo: #0f141b;
      --flag-bg: #2a1a1c; --shadow: 0 1px 2px rgba(0,0,0,.3);
    } }
    :root[data-theme="dark"] {
      --canvas: #0f141b; --panel: #161d27; --panel-2: #1c2531;
      --ink: #e6eaf0; --muted: #98a2b3; --line: #232c39;
      --accent: #2fb3b0; --accent-ink: #7fe3e0;
      --good: #45c07a; --warn: #e0a94a; --bad: #ec6a6a;
      --good-ink: #45c07a; --warn-ink: #e0a94a; --bad-ink: #ed7171; --on-accent: #0f141b;
      --e-supports: #45c07a; --e-rebuts: #ec6a6a; --e-qualifies: #e0a94a;
      --e-depends: #6e92f0; --e-neutral: #8a96a6; --e-supersedes: #a985e0;
      --graph-bg: #10161e; --exhibit-bg: #16241d; --label-halo: #0f141b;
      --flag-bg: #2a1a1c; --shadow: 0 1px 2px rgba(0,0,0,.3);
    }
    * { box-sizing: border-box; }
    body { margin: 0; font: 15px/1.5 var(--sans); color: var(--ink); background: var(--canvas); -webkit-font-smoothing: antialiased; }
    a { color: var(--accent-ink); }
    .mono { font-family: var(--mono); font-size: .82em; }
    .muted { color: var(--muted); }
    .empty { color: var(--muted); margin: 6px 0; }

    /* --- top bar / hero --- */
    .topbar { position: sticky; top: 0; z-index: 20; background: color-mix(in srgb, var(--panel) 88%, transparent);
      backdrop-filter: saturate(1.4) blur(8px); border-bottom: 1px solid var(--line); padding: 18px 26px 0; }
    .topwrap { max-width: 1200px; margin: 0 auto; }
    .eyebrow { font-family: var(--mono); font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); }
    .case-q { font-family: var(--serif); font-weight: 600; font-size: clamp(21px, 3vw, 30px); line-height: 1.15; margin: 6px 0 8px; letter-spacing: -.01em; }
    .questions { list-style: none; margin: 0 0 10px; padding: 0; display: flex; flex-wrap: wrap; gap: 6px 10px; }
    .questions li { font-size: 13px; color: var(--muted); padding-left: 15px; position: relative; max-width: 560px; }
    .questions li::before { content: "?"; position: absolute; left: 0; color: var(--accent); font-family: var(--serif); font-weight: 700; }
    .verdict { font-size: 14px; color: var(--ink); border-left: 2px solid var(--accent); padding-left: 12px; margin: 0 0 12px; max-width: 760px; }
    .integrity { font-size: 13px; color: var(--muted); margin-bottom: 12px; }
    .integrity b { color: var(--ink); font-variant-numeric: tabular-nums; }
    .ceiling { font-size: 13px; color: var(--muted); margin: 0 0 12px; padding: 8px 12px;
               border-left: 3px solid var(--warn); background: var(--panel-2);
               border-radius: 0 5px 5px 0; max-width: 78ch; }
    .tabs { display: flex; gap: 2px; flex-wrap: wrap; }
    .tab { font: 600 14px/1 var(--sans); color: var(--muted); background: none; border: 0; border-bottom: 2px solid transparent;
      padding: 12px 14px; cursor: pointer; }
    .tab:hover { color: var(--ink); }
    .tab.active { color: var(--accent-ink); border-bottom-color: var(--accent); }
    .theme-toggle { position: absolute; top: 16px; right: 22px; width: 34px; height: 34px; border-radius: 8px;
      border: 1px solid var(--line); background: var(--panel); color: var(--ink); cursor: pointer; font-size: 15px; }

    main { max-width: 1200px; margin: 0 auto; padding: 22px 22px 60px; }
    .tabpanel[hidden] { display: none; }
    h2 { font-family: var(--serif); font-weight: 600; font-size: 20px; margin: 0 0 12px; }
    h3 { font-size: 15px; margin: 18px 0 8px; }
    h4 { font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin: 12px 0 6px; }
    section { padding: 18px; border: 1px solid var(--line); border-radius: 10px; background: var(--panel); margin-top: 14px; box-shadow: var(--shadow); }
    pre { white-space: pre-wrap; margin: 0; font-family: var(--mono); font-size: 12px; color: var(--ink); }

    /* --- metric tiles --- */
    .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; }
    .metric { padding: 14px; border: 1px solid var(--line); border-radius: 10px; background: var(--panel); box-shadow: var(--shadow); }
    .metric strong { display: block; font-size: 26px; font-variant-numeric: tabular-nums; color: var(--accent-ink); }
    .metric label { display: block; font-weight: 600; margin-top: 2px; }
    .metric span { display: block; color: var(--muted); font-size: 12px; margin-top: 5px; }
    .metric-link { cursor: pointer; position: relative; transition: border-color .12s ease, background .12s ease, transform .12s ease; }
    .metric-link:hover { border-color: color-mix(in srgb, var(--accent) 45%, var(--line)); background: color-mix(in srgb, var(--accent) 5%, var(--panel)); }
    .metric-link:active { transform: translateY(1px); }
    .metric-link::after { content: "→"; position: absolute; top: 12px; right: 12px; color: var(--muted); font-size: 13px; opacity: .5; }
    .metric-link:hover::after { opacity: 1; color: var(--accent-ink); }

    /* --- tables --- */
    .toolbar { display: flex; gap: 12px; align-items: center; margin: 4px 0 12px; flex-wrap: wrap; }
    .filter { padding: 8px 12px; border: 1px solid var(--line); border-radius: 8px; font: inherit; min-width: 240px; background: var(--panel); color: var(--ink); }
    .lead { color: var(--muted); max-width: 760px; }
    ul.awaiting { list-style: none; padding: 0; margin: 10px 0; display: grid; gap: 10px; }
    ul.awaiting > li { border: 1px solid var(--line); border-left: 3px solid var(--warn); border-radius: 0 8px 8px 0; padding: 10px 14px; background: var(--panel); }
    .await-edge { font-family: var(--mono); font-size: 12.5px; margin-bottom: 6px; }
    ul.awaiting blockquote { margin: 6px 0; padding: 6px 12px; border-left: 3px solid var(--good); background: color-mix(in srgb, var(--good) 6%, transparent); border-radius: 0 6px 6px 0; color: var(--ink); }
    pre.cmd { margin-top: 8px; padding: 8px 10px; background: var(--panel-2); border: 1px solid var(--line); border-radius: 6px; font-size: 11.5px; overflow-x: auto; }
    table.ledger-table { border-collapse: collapse; width: 100%; font-size: 14px; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
    .ledger-table th, .ledger-table td { border-bottom: 1px solid var(--line); padding: 10px 12px; text-align: left; vertical-align: top; }
    .ledger-table thead th { background: var(--panel-2); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
    .ledger-table tbody tr:hover { background: color-mix(in srgb, var(--accent) 6%, transparent); }
    .ledger-table td.quote { max-width: 620px; }
    .chip-sm { display: inline-block; font-family: var(--mono); font-size: 11px; background: var(--panel-2); border: 1px solid var(--line); border-radius: 999px; padding: 1px 8px; margin: 1px 2px 1px 0; }

    /* --- source dossiers --- */
    .dossiers { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 14px; }
    .dossier { border: 1px solid var(--line); border-radius: 12px; background: var(--panel); padding: 16px; box-shadow: var(--shadow); }
    .dossier h3 { margin: 0 0 2px; font-size: 15px; }
    .dossier .prov { font-size: 12px; margin-top: 6px; }
    .dossier ul.tight { margin: 4px 0 0; padding-left: 16px; }
    .dossier ul.tight li { margin: 4px 0; font-size: 13px; }
    .src-rel, .src-claims { margin-top: 6px; }

    /* --- badges / edge tags --- */
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 650; margin: 0 3px 3px 0; }
    .badge.ok { background: color-mix(in srgb, var(--good) 16%, var(--panel)); color: var(--good-ink); }
    .badge.warn { background: color-mix(in srgb, var(--warn) 18%, var(--panel)); color: var(--warn-ink); }
    .badge.bad { background: color-mix(in srgb, var(--bad) 16%, var(--panel)); color: var(--bad-ink); }
    .badge.muted { background: var(--panel-2); color: var(--muted); border: 1px solid var(--line); }
    a.jump { color: var(--accent-ink); cursor: pointer; text-decoration: none; font-family: var(--mono); font-size: .95em;
      border-bottom: 1px dotted color-mix(in srgb, var(--accent) 55%, transparent); }
    a.jump:hover { border-bottom-style: solid; background: color-mix(in srgb, var(--accent) 8%, transparent); }

    /* --- development documents (rendered markdown) --- */
    .doc-intro { margin-bottom: 4px; }
    details.doc-item { border: 1px solid var(--line); border-radius: 10px; background: var(--panel); margin-top: 12px; box-shadow: var(--shadow); overflow: hidden; }
    details.doc-item > summary { cursor: pointer; list-style: none; padding: 14px 18px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    details.doc-item > summary::-webkit-details-marker { display: none; }
    details.doc-item > summary::before { content: "▸"; color: var(--muted); font-size: 12px; transition: transform .15s ease; }
    details.doc-item[open] > summary::before { transform: rotate(90deg); }
    details.doc-item > summary > code { font-size: 13px; color: var(--ink); background: var(--panel-2); border: 1px solid var(--line); border-radius: 6px; padding: 1px 8px; }
    .doc-role { color: var(--muted); font-size: 13px; }
    .doc { padding: 4px 22px 20px; border-top: 1px solid var(--line); max-width: 860px; line-height: 1.62; }
    .doc h1 { font-family: var(--serif); font-size: 22px; margin: 18px 0 6px; }
    .doc h2 { font-family: var(--serif); font-size: 18px; margin: 20px 0 6px; }
    .doc h3 { font-size: 15px; margin: 16px 0 4px; }
    .doc p { margin: 8px 0; }
    .doc ul, .doc ol { padding-left: 22px; }
    .doc li { margin: 4px 0; }
    .doc code { font-family: var(--mono); font-size: 12.5px; background: var(--panel-2); border-radius: 4px; padding: 0 4px; }
    .doc pre { background: var(--panel-2); border: 1px solid var(--line); border-radius: 8px; padding: 12px; overflow-x: auto; }
    .doc pre code { background: none; padding: 0; }
    .doc blockquote { margin: 10px 0; padding: 6px 14px; border-left: 3px solid var(--accent); color: var(--ink); background: color-mix(in srgb, var(--accent) 5%, transparent); border-radius: 0 6px 6px 0; }
    .doc table { border-collapse: collapse; font-size: 13px; margin: 10px 0; display: block; overflow-x: auto; }
    .doc table th, .doc table td { border: 1px solid var(--line); padding: 6px 10px; text-align: left; vertical-align: top; }
    .doc table.fm { font-family: var(--mono); font-size: 12px; }
    .doc table.fm th { color: var(--muted); font-weight: 600; background: var(--panel-2); }
    .etag { display: inline-block; font-family: var(--mono); font-size: 11px; padding: 1px 7px; border-radius: 5px; font-weight: 600;
      background: var(--panel-2); color: var(--muted); border: 1px solid var(--line); }
    .etag.supports { color: var(--e-supports); border-color: color-mix(in srgb, var(--e-supports) 40%, var(--line)); }
    .etag.rebuts { color: var(--e-rebuts); border-color: color-mix(in srgb, var(--e-rebuts) 40%, var(--line)); }
    .etag.qualifies { color: var(--e-qualifies); border-color: color-mix(in srgb, var(--e-qualifies) 40%, var(--line)); }
    .etag.crux, .etag.correlated { color: var(--e-supersedes); }
    .etag.rhetorical { color: var(--bad); }
    ul.comments { list-style: none; padding: 0; }
    ul.comments li { padding: 8px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
    mark.flagged { background: color-mix(in srgb, var(--bad) 22%, transparent); color: inherit; border-radius: 2px; padding: 0 1px; }

__GRAPHCSS__
    /* theme-aware refinements layered OVER the shared GRAPH_CSS (which ships light
       defaults for the pack); these re-assert the variable-driven badges so dark
       mode is correct in the dashboard. */
    .detail { background: var(--panel); }
    .badge.ok { background: color-mix(in srgb, var(--good) 16%, var(--panel)); color: var(--good-ink); }
    .badge.warn { background: color-mix(in srgb, var(--warn) 18%, var(--panel)); color: var(--warn-ink); }
    .badge.bad { background: color-mix(in srgb, var(--bad) 16%, var(--panel)); color: var(--bad-ink); }
    /* The three stacked trust layers (always visible, never a tab). Neutral throughout: a
       dependence warning carries the amber warn accent; a judgement and a declared cause
       never get green success fills. Provenance is text (.prov / .badge), never colour. */
    .layer { background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
      padding: 18px 20px; margin: 0 0 16px; box-shadow: var(--shadow); }
    .layer h2 { margin: 0 0 10px; font-size: 19px; } .layer h4 { margin: 14px 0 6px; font-size: 15px; }
    .layer-note { color: var(--muted); font-size: 13.5px; border-left: 3px solid var(--line);
      background: var(--panel-2); padding: 8px 12px; border-radius: 0 6px 6px 0; margin: 0 0 12px; }
    .warn-card, .rec-card { border: 1px solid var(--line); border-radius: 0 8px 8px 0;
      padding: 12px 14px; margin: 10px 0; background: var(--panel-2); }
    .warn-card { border-left: 3px solid var(--warn); } .rec-card { border-left: 3px solid var(--line); }
    .warn-h, .rec-h { display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
      font-weight: 700; margin-bottom: 8px; }
    .warn-card .row, .rec-card .row { display: grid; grid-template-columns: 150px 1fr auto;
      gap: 8px; align-items: baseline; padding: 4px 0; font-size: 13.5px; border-top: 1px solid var(--line); }
    .warn-card .row:first-of-type, .rec-card .row:first-of-type { border-top: 0; }
    .row .k { color: var(--muted); font-weight: 600; } .row .v { word-break: break-word; }
    .prov { font-size: 11px; color: var(--muted); background: var(--panel);
      border: 1px solid var(--line); border-radius: 999px; padding: 1px 8px; white-space: nowrap; }
    .row .prov { justify-self: end; } .warn-h .prov, .rec-h .prov { margin-left: auto; }
    .more-recs { margin-top: 10px; } .more-recs summary { cursor: pointer; color: var(--accent); font-size: 14px; }
    .prov-strip { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 13px;
      color: var(--muted); background: var(--panel-2); border: 1px solid var(--line);
      border-radius: 8px; padding: 8px 12px; margin-bottom: 8px; }
    .boundary { margin: 10px 0; padding: 10px 14px; border-left: 3px solid var(--accent);
      background: var(--panel-2); border-radius: 0 6px 6px 0; font-size: 13.5px; }
    .no-finding { border-left: 3px solid var(--line); padding: 10px 14px; background: var(--panel-2);
      border-radius: 0 6px 6px 0; color: var(--muted); font-size: 14px; }
    .layer-tbl { border-collapse: collapse; width: 100%; margin: 6px 0; font-size: 14px; }
    .layer-tbl th, .layer-tbl td { border: 1px solid var(--line); padding: 6px 9px; text-align: left; }
    .layer-tbl thead th { background: var(--panel-2); }
    .layer-tbl .num { text-align: right; font-variant-numeric: tabular-nums; }
    @media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto; } }
    :focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  </style>
</head>
<body>
  <header class="topbar">
    <button class="theme-toggle" id="theme-toggle" title="Toggle light/dark" aria-label="Toggle light/dark">&#9681;</button>
    <div class="topwrap">
      <div class="eyebrow">__EYEBROW__</div>
      <h1 class="case-q">__CASE_TITLE__</h1>
      __QUESTIONS__
      __VERDICT__
      <div class="integrity">__INTEGRITY__</div>
      __CEILING__
      <nav class="tabs" role="tablist">__TABS__</nav>
    </div>
  </header>
  <main>
    __LAYERS__
    __PANELS__</main>
  <script>
__APPJS__
  </script>
</body>
</html>
"""


# The graph section markup, reused by the single-file dashboard (Board tab) and the
# judge bundle's Outputs page. The data + script are appended by graph_section_html.
_GRAPH_SECTION = """<section class="graph-section">
      <p class="hint">Nodes are claims (fill colour = source). Edges are typed relations. Click a claim for its verbatim quote, the reviewer comments on it, and its provenance. A red ring marks a faithfulness-disputed claim; an amber ring marks a possible double-count; a dashed edge is an unassessed support/rebuttal. Drag to reposition, scroll to zoom, drag the background to pan.</p>
      <div class="graph-controls">
        <input id="search" type="search" placeholder="filter claims by text…" autocomplete="off" spellcheck="false">
        <span id="qfilters" class="qfilters"></span>
        <span class="legend" id="legend"></span>
      </div>
      <div class="graph-wrap">
        <svg id="graph" role="img" aria-label="argument graph"></svg>
        <aside id="detail" class="detail"><p class="empty">Click a claim to inspect its verbatim quote, the comments on it, and its provenance.</p></aside>
      </div>
    </section>"""


# The graph CSS, shared by the single-file dashboard (inline) and the judge bundle
# (written into assets/ledger.css) so the two surfaces never drift. Theme-sensitive
# colours are CSS variables WITH a light fallback, so the pack (which does not
# define them) renders exactly as before, while the dashboard themes them.
GRAPH_CSS = """    .hint { color: var(--muted); margin: 0 0 12px; font-size: 13px; }
    .graph-controls { display: flex; flex-wrap: wrap; gap: 10px 14px; align-items: center; margin-bottom: 10px; }
    .graph-controls input[type=search] { padding: 6px 10px; border: 1px solid var(--line); border-radius: 5px; font: inherit; min-width: 200px; background: var(--panel); color: var(--ink); }
    .qfilters { display: flex; flex-wrap: wrap; gap: 6px; }
    .chip { border: 1px solid var(--line); background: var(--bg); border-radius: 999px; padding: 3px 10px; font-size: 12px; cursor: pointer; user-select: none; color: var(--ink); }
    .chip.active { background: var(--accent); color: var(--on-accent, #fff); border-color: var(--accent); }
    .legend { display: flex; flex-wrap: wrap; gap: 10px; margin-left: auto; font-size: 12px; color: var(--muted); }
    .legend i { display: inline-block; width: 22px; height: 0; border-top: 3px solid #999; vertical-align: middle; margin-right: 4px; }
    .legend .ring { width: 12px; height: 12px; border-radius: 999px; border: 2px solid #999; }
    .graph-wrap { display: flex; gap: 14px; align-items: stretch; }
    #graph { flex: 1 1 auto; min-width: 0; height: 580px; border: 1px solid var(--line); border-radius: 10px; background: var(--graph-bg, #fbfdff); touch-action: none; }
    .detail { flex: 0 0 340px; max-height: 580px; overflow: auto; border: 1px solid var(--line); border-radius: 10px; background: var(--panel); padding: 16px; font-size: 14px; }
    .detail h3 { margin: 0 0 4px; font-size: 15px; word-break: break-word; }
    .detail .sub { color: var(--muted); font-size: 12px; margin-bottom: 10px; }
    .detail blockquote { margin: 0 0 10px; padding: 10px 12px; border-left: 3px solid var(--good); background: var(--exhibit-bg, #f3f8f4); border-radius: 0 6px 6px 0; font-size: 14px; }
    .detail .loc { color: var(--muted); font-size: 12px; margin-bottom: 6px; }
    .detail .loc .mono { color: var(--muted); }
    .detail a { color: var(--accent-ink); }
    .detail .comment { border-left: 2px solid var(--warn); padding: 4px 0 4px 10px; margin: 8px 0; font-size: 13px; }
    .detail .comment.rhetorical { border-left-color: var(--bad); }
    .detail .rec { font-family: var(--mono); font-size: 11px; color: var(--muted); }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 650; margin: 0 4px 4px 0; }
    .badge.warn { background: #fbf1dc; color: #8a6300; }
    .badge.bad { background: #fbe3e0; color: #a02414; }
    .badge.ok { background: #e7f3ea; color: #1f5b2b; }
    .detail ul.edges { padding-left: 16px; margin: 4px 0; }
    .detail ul.edges li { font-size: 12px; margin: 4px 0; }
    .detail ul.edges a { cursor: pointer; }
    .node-label { font-size: 10px; fill: var(--ink); pointer-events: none; paint-order: stroke; stroke: var(--label-halo, #ffffff); stroke-width: 2.5px; stroke-linejoin: round; }
    @media (max-width: 760px) { .graph-wrap { flex-direction: column; } .detail { flex-basis: auto; } }"""


def graph_section_html(payload: dict, heading: str = "Argument graph") -> str:
    """The full graph section: markup + embedded data + the renderer script. Reused
    by render_html (single-file) and the judge bundle's Outputs page."""
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return (_GRAPH_SECTION
            + f'\n<script id="ledger-data" type="application/json">{data}</script>'
            + f'\n<script>\n{_GRAPH_JS}\n</script>')


# Hand-rolled, dependency-free force-directed renderer. No CDN, no library — the
# whole point is a single file that opens offline. O(n^2) repulsion is fine for the
# tens-to-low-hundreds of claims a ledger holds.
_GRAPH_JS = r"""
(function () {
  var data = JSON.parse(document.getElementById('ledger-data').textContent);
  var svg = document.getElementById('graph');
  if (!svg) return;
  var NS = 'http://www.w3.org/2000/svg';
  var W = 1000, H = 580;
  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function cssVar(name, fallback) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }
  var EDGE_VARS = { supports: '--e-supports', rebuts: '--e-rebuts', qualifies: '--e-qualifies',
    'depends-on': '--e-depends', refines: '--e-neutral', restates: '--e-neutral',
    'duplicate-of': '--e-neutral', supersedes: '--e-supersedes' };
  function edgeColour(t) { return cssVar(EDGE_VARS[t] || '--e-neutral', '#6b7785'); }
  function ledgerHue(s) { var h = 0; for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 360; return h; }
  function ledgerColour(l) { return 'hsl(' + ledgerHue(l) + ', 55%, 55%)'; }

  var recIndex = data.records_index || {};

  // --- model ---
  var nodes = data.nodes.map(function (n, i) {
    var a = 2 * Math.PI * i / Math.max(1, data.nodes.length);
    var R = Math.min(W, H) * 0.34;
    return Object.assign({}, n, { x: W / 2 + R * Math.cos(a), y: H / 2 + R * Math.sin(a),
      vx: 0, vy: 0, fixed: false });
  });
  var byId = {}; nodes.forEach(function (n) { byId[n.id] = n; });
  var links = data.edges.filter(function (e) { return byId[e.source] && byId[e.target]; })
    .map(function (e) { return Object.assign({}, e, { s: byId[e.source], t: byId[e.target] }); });
  var adj = {}; nodes.forEach(function (n) { adj[n.id] = {}; });
  links.forEach(function (l) { adj[l.s.id][l.t.id] = 1; adj[l.t.id][l.s.id] = 1; });

  // --- defs: one arrowhead marker per edge colour ---
  var defs = document.createElementNS(NS, 'defs');
  var colours = {}; links.forEach(function (l) { colours[edgeColour(l.type)] = 1; });
  Object.keys(colours).forEach(function (col) {
    var m = document.createElementNS(NS, 'marker');
    m.setAttribute('id', 'arw-' + col.replace(/[^a-z0-9]/gi, ''));
    m.setAttribute('viewBox', '0 0 10 10'); m.setAttribute('refX', '9'); m.setAttribute('refY', '5');
    m.setAttribute('markerWidth', '7'); m.setAttribute('markerHeight', '7'); m.setAttribute('orient', 'auto-start-reverse');
    var p = document.createElementNS(NS, 'path'); p.setAttribute('d', 'M0,0 L10,5 L0,10 z'); p.setAttribute('fill', col);
    m.appendChild(p); defs.appendChild(m);
  });
  svg.appendChild(defs);

  var scene = document.createElementNS(NS, 'g'); svg.appendChild(scene);
  var linkLayer = document.createElementNS(NS, 'g'); scene.appendChild(linkLayer);
  var nodeLayer = document.createElementNS(NS, 'g'); scene.appendChild(nodeLayer);

  // --- elements ---
  links.forEach(function (l) {
    var col = edgeColour(l.type);
    l.el = document.createElementNS(NS, 'line');
    l.el.setAttribute('stroke', col);
    l.el.setAttribute('stroke-width', '1.7');
    l.el.setAttribute('marker-end', 'url(#arw-' + col.replace(/[^a-z0-9]/gi, '') + ')');
    if (l.type === 'rebuts') l.el.setAttribute('stroke-dasharray', '6 4');
    if (l.assessed === false) { l.el.setAttribute('stroke-dasharray', '2 4'); l.el.setAttribute('opacity', '0.7'); }
    var ttl = document.createElementNS(NS, 'title');
    ttl.textContent = l.type + (l.assessed === false ? ' (unassessed)' : '');
    l.el.appendChild(ttl);
    linkLayer.appendChild(l.el);
  });
  nodes.forEach(function (n) {
    n.g = document.createElementNS(NS, 'g'); n.g.setAttribute('class', 'node'); n.g.style.cursor = 'pointer';
    n.c = document.createElementNS(NS, 'circle');
    n.c.setAttribute('r', '10');
    n.c.setAttribute('fill', n.resolved ? ledgerColour(n.ledger) : '#cfd6de');
    n.c.setAttribute('stroke', n.contested ? cssVar('--bad', '#c0392b') : (n.double_count ? cssVar('--warn', '#b8860b') : cssVar('--line', '#33414d')));
    n.c.setAttribute('stroke-width', (n.contested || n.double_count) ? '3' : '1.2');
    var ttl = document.createElementNS(NS, 'title'); ttl.textContent = n.id; n.c.appendChild(ttl);
    n.t = document.createElementNS(NS, 'text'); n.t.setAttribute('class', 'node-label');
    n.t.setAttribute('x', '13'); n.t.setAttribute('y', '4'); n.t.textContent = n.slug || n.id;
    n.g.appendChild(n.c); n.g.appendChild(n.t); nodeLayer.appendChild(n.g);
    n.g.addEventListener('pointerdown', function (ev) { startDrag(ev, n); });
  });

  // --- force simulation ---
  var alpha = 1.0;
  function step() {
    var i, j, a, b, dx, dy, d2, d, f;
    for (i = 0; i < nodes.length; i++) {
      a = nodes[i];
      for (j = i + 1; j < nodes.length; j++) {
        b = nodes[j];
        dx = a.x - b.x; dy = a.y - b.y; d2 = dx * dx + dy * dy || 0.01; d = Math.sqrt(d2);
        f = 9000 / d2; var ux = dx / d, uy = dy / d;
        a.vx += ux * f; a.vy += uy * f; b.vx -= ux * f; b.vy -= uy * f;
      }
    }
    links.forEach(function (l) {
      dx = l.t.x - l.s.x; dy = l.t.y - l.s.y; d = Math.sqrt(dx * dx + dy * dy) || 0.01;
      f = (d - 150) * 0.05; var ux = dx / d, uy = dy / d;
      l.s.vx += ux * f; l.s.vy += uy * f; l.t.vx -= ux * f; l.t.vy -= uy * f;
    });
    nodes.forEach(function (n) {
      n.vx += (W / 2 - n.x) * 0.004; n.vy += (H / 2 - n.y) * 0.004;
      if (n.fixed) { n.vx = 0; n.vy = 0; return; }
      n.vx *= 0.86; n.vy *= 0.86;
      n.x += n.vx * alpha; n.y += n.vy * alpha;
      n.x = Math.max(16, Math.min(W - 16, n.x)); n.y = Math.max(16, Math.min(H - 16, n.y));
    });
    render();
  }
  function render() {
    links.forEach(function (l) {
      l.el.setAttribute('x1', l.s.x); l.el.setAttribute('y1', l.s.y);
      l.el.setAttribute('x2', l.t.x); l.el.setAttribute('y2', l.t.y);
    });
    nodes.forEach(function (n) { n.g.setAttribute('transform', 'translate(' + n.x + ',' + n.y + ')'); });
  }
  var ticks = 0, fitted = false, LIMIT = reduce ? 120 : 600;
  function loop() {
    step(); ticks++;
    alpha = Math.max(0.02, alpha * 0.992);
    if (ticks < LIMIT) requestAnimationFrame(loop);
    else if (!fitted) { fitView(); fitted = true; }
  }
  loop();

  // --- pan / zoom (transform on the scene group) ---
  var tx = 0, ty = 0, k = 1;
  function applyTransform() { scene.setAttribute('transform', 'translate(' + tx + ',' + ty + ') scale(' + k + ')'); }
  function fitView() {
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    nodes.forEach(function (n) { minX = Math.min(minX, n.x); maxX = Math.max(maxX, n.x); minY = Math.min(minY, n.y); maxY = Math.max(maxY, n.y); });
    if (!isFinite(minX)) return;
    var pad = 70, gw = Math.max(1, maxX - minX + pad * 2), gh = Math.max(1, maxY - minY + pad * 2);
    k = Math.max(0.3, Math.min(1.4, Math.min(W / gw, H / gh)));
    tx = (W - (minX + maxX) * k) / 2; ty = (H - (minY + maxY) * k) / 2; applyTransform();
  }
  function ptr(ev) { var r = svg.getBoundingClientRect(); return { x: (ev.clientX - r.left) * W / r.width, y: (ev.clientY - r.top) * H / r.height }; }
  svg.addEventListener('wheel', function (ev) {
    ev.preventDefault();
    var p = ptr(ev), s = ev.deltaY < 0 ? 1.1 : 1 / 1.1, nk = Math.max(0.3, Math.min(4, k * s));
    tx = p.x - (p.x - tx) * (nk / k); ty = p.y - (p.y - ty) * (nk / k); k = nk; applyTransform();
  }, { passive: false });

  // Click-vs-drag is decided here, in the pointer handlers, NOT via the derived
  // `click` event: setting pointer capture for the drag makes some browsers route
  // click to the SVG, so a node click would otherwise deselect. A pointerup that
  // never moved past the threshold IS a click → select; a moved one is a drag.
  var drag = null, pan = null, MOVE = 4;
  function startDrag(ev, n) { ev.preventDefault(); ev.stopPropagation(); drag = { n: n, x0: ev.clientX, y0: ev.clientY, moved: false }; svg.setPointerCapture(ev.pointerId); }
  svg.addEventListener('pointerdown', function (ev) { if (!drag) { pan = { x: ev.clientX, y: ev.clientY, tx: tx, ty: ty, moved: false }; svg.setPointerCapture(ev.pointerId); } });
  svg.addEventListener('pointermove', function (ev) {
    if (drag) {
      if (!drag.moved && Math.abs(ev.clientX - drag.x0) + Math.abs(ev.clientY - drag.y0) > MOVE) { drag.moved = true; drag.n.fixed = true; }
      if (drag.moved) { var p = ptr(ev); drag.n.x = (p.x - tx) / k; drag.n.y = (p.y - ty) / k; render(); alpha = Math.max(alpha, 0.25); }
    } else if (pan) {
      if (Math.abs(ev.clientX - pan.x) + Math.abs(ev.clientY - pan.y) > MOVE) pan.moved = true;
      var r = svg.getBoundingClientRect(); tx = pan.tx + (ev.clientX - pan.x) * W / r.width; ty = pan.ty + (ev.clientY - pan.y) * H / r.height; applyTransform();
    }
  });
  function endPtr() {
    if (drag) {
      if (!drag.moved) select(drag.n);                 // a click → inspect the claim
      else if (ticks >= LIMIT) { ticks = Math.max(0, LIMIT - 200); loop(); }
    } else if (pan && !pan.moved) { select(null); }    // a background click → deselect
    drag = null; pan = null;
  }
  svg.addEventListener('pointerup', endPtr);
  svg.addEventListener('pointercancel', endPtr);

  // --- detail panel (the annotated exhibit) ---
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function locatorHtml(loc) {
    if (!loc) return '';
    if (loc.doi) return '<a href="https://doi.org/' + esc(loc.doi) + '" target="_blank" rel="noopener" class="mono">doi:' + esc(loc.doi) + '</a>';
    if (loc.pmcid) { var id = String(loc.pmcid).replace(/^PMC/i, ''); return '<a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC' + esc(id) + '/" target="_blank" rel="noopener" class="mono">PMC' + esc(id) + '</a>'; }
    if (loc.url) return '<a href="' + esc(loc.url) + '" target="_blank" rel="noopener" class="mono">source</a>';
    return '';
  }
  function highlightQuote(q, anns) {
    var out = esc(q);
    (anns || []).forEach(function (a) {
      if (a.type === 'rhetorical' && a.span) {
        var s = esc(a.span);
        out = out.split(s).join('<mark class="flagged">' + s + '</mark>');
      }
    });
    return out;
  }
  var detail = document.getElementById('detail');
  function focusNeighborhood(n) {
    nodes.forEach(function (m) {
      var near = !n || m === n || adj[n.id][m.id];
      m.g.setAttribute('opacity', near ? '1' : '0.15');
    });
    links.forEach(function (l) {
      var on = !n || l.s.id === n.id || l.t.id === n.id;
      l.el.setAttribute('opacity', on ? (l.assessed === false ? '0.7' : '1') : '0.08');
    });
  }
  function select(n) {
    nodes.forEach(function (m) { m.c.setAttribute('stroke-width', (m === n) ? '4' : ((m.contested || m.double_count) ? '3' : '1.2')); });
    focusNeighborhood(n);
    if (!n) { detail.innerHTML = '<p class="empty">Click a claim to inspect its verbatim quote, the comments on it, and its provenance.</p>'; return; }
    var h = '<h3>' + esc(n.slug) + '</h3>';
    h += '<div class="sub">' + esc(n.source || n.ledger) + '</div>';
    h += n.quote ? '<blockquote>&ldquo;' + highlightQuote(n.quote, n.annotations) + '&rdquo;</blockquote>'
                 : '<p class="empty">No verbatim quote resolved for this node.</p>';
    if (n.location) h += '<div class="loc">Location: ' + esc(n.location) + '</div>';
    var lh = locatorHtml(n.locator); if (lh) h += '<div class="loc">Source: ' + lh + '</div>';
    var badges = '';
    if (n.contested) badges += '<span class="badge bad">faithfulness-disputed</span>';
    if (n.double_count) badges += '<span class="badge warn">possible double-count</span>';
    if (badges) h += '<div>' + badges + '</div>';
    // reviewer comments (the in-band prose)
    (n.annotations || []).forEach(function (a) {
      if (!a.note && !a.span) return;
      var cls = a.type === 'rhetorical' ? 'comment rhetorical' : 'comment';
      var label = { rhetorical: 'Rhetorical', correlated: 'Shared premise', crux: 'Crux', status: 'Status' }[a.type] || a.type;
      var span = a.span ? '&ldquo;' + esc(a.span) + '&rdquo; — ' : '';
      var rec = a.rec ? ' <a class="rec" data-rec="' + esc(a.rec) + '">[' + esc(a.rec) + ']</a>' : '';
      h += '<div class="' + cls + '"><strong>' + esc(label) + '.</strong> ' + span + esc(a.note) + rec + '</div>';
    });
    // sealed judgement records on this claim
    (n.records || []).forEach(function (r) {
      var thread = '';
      if (r.disputes && r.disputes.length) thread = ' disputes ' + r.disputes.map(function (d) { return '<a class="rec" data-rec="' + esc(d) + '">' + esc(d) + '</a>'; }).join(', ');
      else if (r.reviews && r.reviews.length) thread = ' reviews ' + r.reviews.map(function (d) { return '<a class="rec" data-rec="' + esc(d) + '">' + esc(d) + '</a>'; }).join(', ');
      h += '<div class="comment"><span class="badge ok">' + esc(r.kind) + '</span> <span class="rec">' + esc(r.id) + '</span>' + thread + '</div>';
    });
    var touch = links.filter(function (l) { return l.s.id === n.id || l.t.id === n.id; });
    if (touch.length) {
      h += '<p style="margin:12px 0 4px;font-weight:650;">Relations</p><ul class="edges">';
      touch.forEach(function (l) {
        var other = (l.s.id === n.id) ? l.t : l.s;
        var dir = (l.s.id === n.id) ? '&rarr;' : '&larr;';
        var grd = l.grounding ? ' <span class="rec">(grounded by #' + esc(l.grounding) + ')</span>' : '';
        h += '<li><span class="etag ' + esc(l.type) + '">' + esc(l.type) + '</span> ' + dir +
             ' <a data-goto="' + esc(other.id) + '">' + esc(other.slug) + '</a>' +
             (l.assessed === false ? ' <em class="muted">(unassessed)</em>' : '') + grd + '</li>';
      });
      h += '</ul>';
    }
    detail.innerHTML = h;
  }
  // expose Board navigation so a jump-link anywhere (Metrics, Docs, the exhibit
  // itself) can select a claim here. The delegated click handler lives in the app
  // chrome; these just do the selection and report whether the id resolved.
  window.__ledgerGoto = function (id) { if (byId[id]) { select(byId[id]); return true; } return false; };
  window.__ledgerRec = function (rec) {
    if (rec && recIndex[rec] && byId[recIndex[rec].subject]) { select(byId[recIndex[rec].subject]); return true; }
    return false;
  };

  // --- sub-question filters + search ---
  var activeQ = null, searchTerm = '';
  function dimmed(n) {
    if (activeQ && (n.qids || []).indexOf(activeQ) < 0) return true;
    if (searchTerm && (n.id + ' ' + (n.quote || '')).toLowerCase().indexOf(searchTerm) < 0) return true;
    return false;
  }
  function applyFilter() {
    nodes.forEach(function (n) { n.g.setAttribute('opacity', dimmed(n) ? '0.12' : '1'); });
    links.forEach(function (l) { l.el.setAttribute('opacity', (dimmed(l.s) || dimmed(l.t)) ? '0.06' : (l.assessed === false ? '0.7' : '1')); });
  }
  var qbox = document.getElementById('qfilters');
  function mkChip(label, q) {
    var el = document.createElement('span'); el.className = 'chip' + (q === activeQ ? ' active' : ''); el.textContent = label;
    el.addEventListener('click', function () { activeQ = (activeQ === q) ? null : q; Array.prototype.forEach.call(qbox.children, function (ch, i) { ch.className = 'chip' + ((i === 0 ? null : data.sub_questions[i - 1]) === activeQ ? ' active' : ''); }); applyFilter(); });
    return el;
  }
  if (data.sub_questions.length) {
    qbox.appendChild(mkChip('all', null));
    data.sub_questions.forEach(function (q) { qbox.appendChild(mkChip(q, q)); });
  }
  var searchBox = document.getElementById('search');
  if (searchBox) searchBox.addEventListener('input', function (ev) { searchTerm = ev.target.value.trim().toLowerCase(); applyFilter(); });

  // --- legend (edge types + ring meanings) ---
  var legend = document.getElementById('legend');
  [['supports', 'supports'], ['rebuts', 'rebuts'], ['qualifies', 'qualifies'], ['depends-on', 'depends-on']].forEach(function (p) {
    var s = document.createElement('span'); s.innerHTML = '<i style="border-top-color:' + edgeColour(p[0]) + (p[0] === 'rebuts' ? ';border-top-style:dashed' : '') + '"></i>' + p[1]; legend.appendChild(s);
  });
  var r1 = document.createElement('span'); r1.innerHTML = '<span class="ring" style="border-color:' + cssVar('--bad', '#c0392b') + '"></span>disputed'; legend.appendChild(r1);
  var r2 = document.createElement('span'); r2.innerHTML = '<span class="ring" style="border-color:' + cssVar('--warn', '#b8860b') + '"></span>double-count'; legend.appendChild(r2);
})();
"""


# App chrome: tab switching, theme toggle, table filtering. Kept tiny and framework-free.
_APP_JS = r"""
(function () {
  // theme toggle (persisted; defaults to the OS preference)
  var root = document.documentElement, KEY = 'ledger-theme';
  try { var saved = localStorage.getItem(KEY); if (saved) root.setAttribute('data-theme', saved); } catch (e) {}
  var tbtn = document.getElementById('theme-toggle');
  if (tbtn) tbtn.addEventListener('click', function () {
    var dark = root.getAttribute('data-theme') === 'dark'
      || (!root.getAttribute('data-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
    var next = dark ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem(KEY, next); } catch (e) {}
  });

  // tabs
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.tab'));
  var panels = Array.prototype.slice.call(document.querySelectorAll('.tabpanel'));
  function activate(name) {
    tabs.forEach(function (t) { var on = t.getAttribute('data-tab') === name; t.classList.toggle('active', on); t.setAttribute('aria-selected', on ? 'true' : 'false'); });
    panels.forEach(function (p) { p.hidden = p.getAttribute('data-panel') !== name; });
  }
  // one delegated navigator for everything that navigates: the tab bar, the metric
  // tiles (data-tab / data-scroll deep-links), and the jump-links in the Metrics
  // lists / Docs / Board exhibit (data-goto a claim, data-rec a record).
  var NAV = '[data-goto],[data-rec],[data-tab],[data-scroll]';
  function navTarget(el) { return el && el.closest ? el.closest(NAV) : null; }
  function doNav(a, ev) {
    var goto = a.getAttribute('data-goto'), rec = a.getAttribute('data-rec');
    if (goto || rec) {
      var ok = goto ? (window.__ledgerGoto && window.__ledgerGoto(goto))
                    : (window.__ledgerRec && window.__ledgerRec(rec));
      if (ok) {
        if (ev) ev.preventDefault();
        activate('board');
        var d = document.getElementById('detail');
        if (d && d.scrollIntoView) d.scrollIntoView({ block: 'nearest' });
      }
      return;
    }
    var tab = a.getAttribute('data-tab');
    if (tab) { if (ev) ev.preventDefault(); activate(tab); }
    var scroll = a.getAttribute('data-scroll');
    if (scroll) {
      var t = document.querySelector(scroll);
      if (t && t.scrollIntoView) { if (ev) ev.preventDefault(); t.scrollIntoView({ block: 'start' }); }
    }
  }
  document.addEventListener('click', function (ev) { var a = navTarget(ev.target); if (a) doNav(a, ev); });
  // keyboard access for the non-button tiles (role=link tabindex=0); native tab
  // buttons already synthesize a click on Enter/Space, so skip those here.
  document.addEventListener('keydown', function (ev) {
    if (ev.key !== 'Enter' && ev.key !== ' ') return;
    var a = navTarget(ev.target);
    if (a && a.getAttribute('tabindex') !== null) { doNav(a, ev); }
  });

  // table filters
  document.querySelectorAll('.filter').forEach(function (inp) {
    inp.addEventListener('input', function () {
      var term = inp.value.trim().toLowerCase();
      var table = document.getElementById(inp.getAttribute('data-target'));
      if (!table) return;
      table.querySelectorAll('tbody tr').forEach(function (tr) {
        var t = tr.getAttribute('data-text') || tr.textContent.toLowerCase();
        tr.style.display = (!term || t.indexOf(term) >= 0) ? '' : 'none';
      });
    });
  });
})();
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit a static HTML Ledger judge dashboard.")
    ap.add_argument("--repo-root", default=str(REPO_ROOT))
    ap.add_argument("--out", default="",
                    help="write HTML to this path instead of stdout")
    args = ap.parse_args()

    repo_root = Path(args.repo_root)
    if not (repo_root / "ledger.config.md").is_file():
        print(f"[ledger] {repo_root} is not a Ledger project (no ledger.config.md).",
              file=sys.stderr)
        return 2
    html_text = render_html(repo_root)
    if args.out:
        Path(args.out).write_text(html_text, encoding="utf-8")
    else:
        sys.stdout.write(html_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
