# === SCRIPT: Assessment gate — judgement records are sealed, grounded, fresh ===
# The assessment layer's enforcement half (mirrors check_manifest.run_record_problems
# for run-records). It attests, corpus-free, that every committed judgement record
# in content/assessments/_records/ is well-formed, internally sealed
# (record_sha256), grounded in claims that resolve, and bound to the SUBJECT
# claim's CURRENT body (a stale body_sha256 = the assessed claim was edited after
# the judgement, caught like provenance staleness). It also checks: a rhetorical
# record's span is a substring of its grounding quote (the flag is quote-pinned);
# every in-band `[rec: id]` names a real record; a `**Status:** performed-settling`
# claim points at an open `**Crux-of:**`; calibration notes carry the discount
# shape (calibrated ≤ inside_view). The derived DOUBLE-COUNT finding (two
# correlated supporters of one claim) is surfaced as a WARNING even under required
# — it is a heuristic, not a proof.
#
# What it does NOT do (the stated seam): prove a judgement is CORRECT. It makes a
# judgement attributable, tamper-evident, grounded and re-judgeable — never right.
# An empty layer (no records, no markers, no calibration notes) passes every mode.
# INPUTS : content/assessments/_records/*.assess.json; in-band markers + edges in
#          literature/verified_claims/*.md; content/assessments/*.md (calibration);
#          assessment_layer: in config.
# OUTPUTS: [INFO]/[WARNING]/[ERROR]; exit 0 = ok or posture off/optional;
#          1 = a hard problem under assessment_layer: required.
# Run    : python3 tools/check_assessment.py
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from check_citations import gated_prefixes, is_gated, parse_config
import claim_graph as cg
import schema_check
from assess_record import (ASSESS_DIR, ASSESS_KINDS, CLAIMS_DIR, RECORDS_DIR_NAME,
                           REQUIRED_FIELDS, subject_body_sha256)

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "literature"))
from verify_quotes import read_frontmatter, run_record_digest  # noqa: E402

# In-band assessment markers (authored under a claim, like edges).
REC_REF_RE = re.compile(r"\[rec:\s*([\w-]+)\]")
STATUS_PERFORMED_RE = re.compile(r"^\*\*Status:\*\*\s*performed-settling", re.IGNORECASE)
CRUXOF_RE = re.compile(r"^\*\*Crux-of:\*\*", re.IGNORECASE)
CORRELATED_RE = re.compile(r"^\*\*Correlated-with:\*\*\s*([\w-]+(?::[\w-]+)?)",
                           re.IGNORECASE)

# The typed causes a declared correlation can carry, slug -> reader label. The distinction
# between exact cohort reuse and a broader overlapping-pool relationship is a judgement the
# curator records on the annotation, so the renderer can state it deterministically instead
# of re-deciding it from prose. An untyped correlation is `other-declared-dependence` — the
# default states only that a dependence was declared, never a stronger kind.
CORRELATION_KINDS = {
    "exact-cohort-reuse": "exact cohort reuse",
    "overlapping-pools": "overlapping pools",
    "shared-evidence": "shared evidence",
    "other-declared-dependence": "other declared dependence",
}
_CORR_BRACKET_RE = re.compile(r"\[([^\]]*)\]")
_CORR_KIND_RE = re.compile(r"^\s*kind:\s*([\w-]+)\s*[;—-]?\s*(.*)$",
                           re.IGNORECASE | re.DOTALL)


def parse_correlation_cause(line: str) -> tuple[str, str]:
    """(kind, basis) from a `Correlated-with:` annotation's bracket.

    A bracket may open `kind: <slug>` to type the dependence; the rest is the authored
    basis. An unrecognised or absent kind falls back to `other-declared-dependence` with
    the whole bracket as basis — a typo is never silently promoted to a stronger kind.
    """
    bracket = _CORR_BRACKET_RE.search(line)
    inner = bracket.group(1).strip() if bracket else ""
    m = _CORR_KIND_RE.match(inner)
    if m and m.group(1).lower() in CORRELATION_KINDS:
        return m.group(1).lower(), m.group(2).strip()
    return "other-declared-dependence", inner


@dataclass(frozen=True)
class DoubleCount:
    """A derived possible-dependence warning: two sources that each support the same claim
    and are declared correlated-with each other. `kind`/`basis` are read from the
    correlation annotation; `sealed_record` names a correlated-with assessment record that
    backs the pair, or None when the dependence is declared but not sealed."""
    a: str
    b: str
    target: str
    kind: str
    basis: str
    sealed_record: str | None

    @property
    def summary(self) -> str:
        return (f"{self.a} and {self.b} both support {self.target} but are "
                "correlated-with each other (possible double-count)")

    @property
    def kind_label(self) -> str:
        return CORRELATION_KINDS.get(self.kind, self.kind)

    def as_dict(self) -> dict:
        return {"a": self.a, "b": self.b, "target": self.target, "kind": self.kind,
                "basis": self.basis, "sealed_record": self.sealed_record}


# The author-declared correlation-kinds surface. A kind is authored epistemic metadata, so
# it lives in this committed, validated file — NEVER in a stamped ledger body, where a
# classification-only edit would restale the quote stamp, run record, and any sealed
# assessment bound to the edited claim. The ledger's Correlated-with bracket is untouched;
# it carries only the DECLARED basis (authored, not source-verified).
CORRELATION_KINDS_FILE = "correlation_kinds.md"
_PAIR_HEAD_RE = re.compile(r"^##\s+(\S+)\s*↔\s*(\S+)\s*$")
_KIND_LINE_RE = re.compile(r"^-\s*kind:\s*([\w-]+)\s*$", re.IGNORECASE)
_CORR_PROV_FIELDS = ("authored_by", "last_updated", "status")


def _declared_correlation_pairs(claims_dir: Path) -> set[frozenset]:
    """Every {ledger-key pair} a `Correlated-with:` line declares — the edges a
    classification may name. Read corpus-free from the ledgers, order-independent."""
    pairs: set[frozenset] = set()
    if not claims_dir.is_dir():
        return pairs
    for ledger in sorted(claims_dir.glob("*.md")):
        if ledger.stem == "TEMPLATE":
            continue
        for line in ledger.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = CORRELATED_RE.match(line.strip())
            if m:
                tgt = cg.parse_address(m.group(1))
                pairs.add(frozenset({ledger.stem.lower(),
                                     tgt.key or ledger.stem.lower()}))
    return pairs


def load_correlation_kinds(content_dir: Path | None):
    """Parse content/correlation_kinds.md → (kinds, provenance, entries).

    `kinds` maps frozenset({keyA, keyB}) -> kind_slug for every entry naming an allowed
    kind; `provenance` is the frontmatter (authored_by / last_updated / status); `entries`
    is the raw ordered list [(keyA, keyB, kind, line_no)] so the validator can catch
    duplicate and orphan classifications. Absent file / missing pair → the caller defaults
    to other-declared-dependence."""
    kinds: dict[frozenset, str] = {}
    entries: list[tuple[str, str, str, int]] = []
    if not content_dir:
        return kinds, {}, entries
    path = Path(content_dir) / CORRELATION_KINDS_FILE
    if not path.is_file():
        return kinds, {}, entries
    prov = read_frontmatter(path)
    pending: tuple[str, str] | None = None
    for i, raw in enumerate(
            path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        head = _PAIR_HEAD_RE.match(raw.strip())
        if head:
            pending = (head.group(1).lower(), head.group(2).lower())
            continue
        km = _KIND_LINE_RE.match(raw.strip())
        if km and pending:
            a, b = pending
            kind = km.group(1).lower()
            entries.append((a, b, kind, i))
            if kind in CORRELATION_KINDS:
                kinds[frozenset({a, b})] = kind
            pending = None
    return kinds, prov, entries


def correlation_kinds_problems(content_dir: Path | None,
                               claims_dir: Path) -> list[str]:
    """Validate the author-declared correlation-kinds file ([] = valid or absent). Enforces
    provenance fields, an allowed kind, one entry per unordered pair, and that each pair
    names a real declared correlated-with edge (no orphans). It classifies; it never seals,
    so it cannot change any pair's sealed-vs-declared status."""
    path = Path(content_dir) / CORRELATION_KINDS_FILE if content_dir else None
    if not path or not path.is_file():
        return []
    _kinds, prov, entries = load_correlation_kinds(content_dir)
    problems: list[str] = []
    for field in _CORR_PROV_FIELDS:
        if not str(prov.get(field, "")).strip():
            problems.append(f"{CORRELATION_KINDS_FILE}: missing provenance field '{field}'")
    declared = _declared_correlation_pairs(claims_dir)
    seen: set[frozenset] = set()
    for a, b, kind, ln in entries:
        pair = frozenset({a, b})
        label = f"{a} ↔ {b}"
        if kind not in CORRELATION_KINDS:
            problems.append(f"{CORRELATION_KINDS_FILE}:{ln}: unknown kind '{kind}' "
                            f"for {label}")
        if pair in seen:
            problems.append(f"{CORRELATION_KINDS_FILE}:{ln}: duplicate classification "
                            f"for {label} (pair identity is unordered)")
        seen.add(pair)
        if pair not in declared:
            problems.append(f"{CORRELATION_KINDS_FILE}:{ln}: {label} names no declared "
                            "correlated-with edge (orphan classification)")
    return problems


# Calibration-note frontmatter: a note is a calibration note iff it declares
# calibrated_confidence; then it must carry the two discounts and inside_view too.
CALIB_DISCOUNTS = ("out_of_model_discount", "adversarial_discount")


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_warning(msg: str) -> None:
    print(f"[WARNING] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def assessment_mode(config: dict[str, str]) -> str:
    """assessment_layer: off | optional | required (default optional)."""
    raw = config.get("assessment_layer", "").split("#", 1)[0].strip().lower()
    return raw if raw in ("off", "optional", "required") else "optional"


def edge_assessment_mode(config: dict[str, str]) -> str:
    """edge_assessments: off | warn | required (default off — opt-in).
    Under 'required' every supports/rebuts edge must be covered by a matching
    `kind: edge` record (in-band `[rec:]` or a standalone one) — a non-trivial
    inference can't be a bare, unjudged claim."""
    raw = config.get("edge_assessments", "").split("#", 1)[0].strip().lower()
    return raw if raw in ("off", "warn", "required") else "off"


# Edge types whose presence is a non-trivial inference worth a recorded judgement.
ASSESSED_EDGE_TYPES = frozenset({"supports", "rebuts"})


def _norm_ws(s: str) -> str:
    return " ".join(s.split())


_ASSESS_SCHEMA: dict | None = None


def _assess_schema() -> dict:
    global _ASSESS_SCHEMA
    if _ASSESS_SCHEMA is None:
        _ASSESS_SCHEMA = schema_check.load_schema("assessment_record.schema.json")
    return _ASSESS_SCHEMA


def record_problems(record: dict, claims_dir: Path) -> list[str]:
    """Shape + seal + grounding + body-freshness problems for one record."""
    rid = record.get("id", "<no-id>")
    # The record must first conform to the published shape (spec/schemas), so the
    # gate and the emitter cannot drift; deeper semantic checks follow below.
    problems = [f"{rid}: schema — {e}" for e in schema_check.validate(record, _assess_schema())]
    missing = [f for f in REQUIRED_FIELDS if f not in record]
    if missing:
        return problems + [f"{rid}: record missing field(s): {', '.join(missing)}"]
    if record["kind"] not in ASSESS_KINDS:
        problems.append(f"{rid}: unknown kind '{record['kind']}'")
    if not isinstance(record["grounding"], list):
        return problems + [f"{rid}: grounding must be a list"]
    if run_record_digest(record) != record["record_sha256"]:
        problems.append(f"{rid}: record_sha256 inconsistent — edited after sealing "
                        "(re-run assess_record.py --reseal)")
    # Subject resolves.
    subj = cg.parse_address(record["subject"])
    subj_res = cg.resolve(subj, subj.key or "", claims_dir)
    if not subj_res.exists:
        problems.append(f"{rid}: subject unresolved — {subj_res.reason}")
    # Each grounding resolves (bare slug defaults to the subject's ledger).
    for g in record["grounding"]:
        g_res = cg.resolve(cg.parse_address(g), subj.key or "", claims_dir)
        if not g_res.exists:
            problems.append(f"{rid}: grounding '{g}' unresolved — {g_res.reason}")
    # body_sha256 binds to the subject claim's CURRENT body (stale = edited since).
    current = subject_body_sha256(record["subject"], claims_dir)
    if subj_res.exists and record["body_sha256"] != current:
        problems.append(f"{rid}: body_sha256 stale — the subject claim was edited "
                        "after the judgement (re-run assess_record.py --reseal)")
    # A rhetorical OR faithfulness span must be a substring of its grounding
    # claim's verbatim quote — the flag/challenge is pinned to real words.
    if record["kind"] in ("rhetorical", "faithfulness") and record.get("span"):
        ground = record["grounding"][0] if record["grounding"] else record["subject"]
        addr = cg.parse_address(ground)
        ledger = cg.ledger_for_key(claims_dir, addr.key or (subj.key or ""))
        quote = cg.claim_quote(ledger, addr.slug) if ledger else ""
        if _norm_ws(record["span"]) not in _norm_ws(quote):
            problems.append(f"{rid}: {record['kind']} span is not a substring of the "
                            f"grounding quote ({ground}) — it must be quote-pinned")
    # A faithfulness record is an adversarial CONTEST — it must name the recorded
    # inference it disputes (validated same-subject + existing by dispute_problems).
    if record["kind"] == "faithfulness" and not (record.get("disputes") or []):
        problems.append(f"{rid}: faithfulness record must dispute at least one "
                        "record (the edge/judgement whose grounding it challenges)")
    if record["kind"] == "faithfulness-pass" and not (record.get("reviews") or []):
        problems.append(f"{rid}: faithfulness-pass record must review at least one "
                        "edge record")
    return problems


def load_records(records_dir: Path) -> list[tuple[str, dict | None, str]]:
    """(stem, record|None, error) for each *.assess.json (None+error if unreadable)."""
    out: list[tuple[str, dict | None, str]] = []
    if not records_dir.is_dir():
        return out
    for path in sorted(records_dir.glob("*.assess.json")):
        try:
            out.append((path.stem, json.loads(path.read_text(encoding="utf-8")), ""))
        except (OSError, ValueError) as exc:
            out.append((path.stem, None, str(exc)))
    return out


def load_records_validated(records_dir: Path, claims_dir: Path):
    """Load records once and classify. Returns (all_by_id, valid_by_id, record_ids,
    problems). 'valid' passes record_problems AND identity (unique id, filename==id) —
    the coverage the gate blocks on, so read-only surfaces can match enforcement."""
    raw = load_records(records_dir)
    id_counts = Counter(str(r.get("id", stem)).lower()
                        for stem, r, _e in raw if r is not None)
    all_by_id: dict[str, dict] = {}
    valid_by_id: dict[str, dict] = {}
    record_ids: set[str] = set()
    problems: list[str] = []
    for stem, record, error in raw:
        if record is None:
            problems.append(f"{stem}: record unreadable ({error})")
            continue
        rid = str(record.get("id", stem)).lower()
        # Ids must be unique and match the filename (stem is `<id>.assess`).
        file_id = stem.removesuffix(".assess").lower()
        if rid in record_ids:
            problems.append(f"{rid}: duplicate assessment id (case-insensitive) — "
                            "ids must be unique across records")
        if file_id != rid:
            problems.append(f"{stem}.json: filename does not match record id "
                            f"'{rid}' (expected {rid}.assess.json)")
        record_ids.add(rid)
        all_by_id[rid] = record
        rp = record_problems(record, claims_dir)
        problems.extend(rp)
        if not rp and file_id == rid and id_counts[rid] == 1:
            valid_by_id[rid] = record
    return all_by_id, valid_by_id, record_ids, problems


def valid_edge_coverage(records_dir: Path, claims_dir: Path) -> dict[tuple[str, str], set[str]]:
    """Edge coverage from valid records only — what the gate blocks on, for read-only use."""
    _all, valid, _ids, _probs = load_records_validated(records_dir, claims_dir)
    return edge_record_coverage(valid)


# ---- [rec:] references in prose: one resolver for the gate and the renderers ----

# Loose on purpose. REC_REF_RE only matches a well-formed marker, so a typo would not
# match and would pass review unseen — the failure this must report, not skip.
_REC_MARKER_RE = re.compile(r"\[rec:([^\]]*)\]")
# An id may be wrapped ONTO its own line but never wrapped THROUGH: whitespace around it
# is markdown formatting and is stripped, while a break inside it leaves a space no id can
# contain, so it is reported rather than silently repaired into a different id.
_REC_ID_RE = re.compile(r"^[\w-]+$")


@dataclass(frozen=True)
class RecRef:
    """One `[rec: id]` marker in prose, resolved against the sealed records."""
    ref_id: str
    where: str
    line: int
    record: dict | None
    problem: str

    @property
    def resolved(self) -> bool:
        return self.record is not None


def iter_rec_markers(text: str):
    """(line, raw) for every `[rec: …]` marker, well-formed or not.

    Scanned over the WHOLE text, never line by line. Prose wraps at the margin, so a
    marker near it breaks across two lines; a per-line scan cannot match one, and an
    unmatched marker is reported by nobody — the claim silently loses its grounding while
    the gate stays green. That is the exact failure the loose marker pattern exists to
    prevent, so the scan must not reintroduce it. The line is derived from the match
    offset because it is the author's coordinate, not the parser's.
    """
    for match in _REC_MARKER_RE.finditer(text):
        yield text.count("\n", 0, match.start()) + 1, match.group(1).strip()


def gated_prose(content_dir: Path, prefixes: list[str]) -> list[Path]:
    """Every gated .md under content_dir. Follows gated_paths, so ungated material —
    a captured baseline, say — is never held to the reference rule."""
    if not content_dir.is_dir():
        return []
    return [p for p in sorted(content_dir.rglob("*.md"))
            if is_gated(str(p), prefixes)]


def resolve_rec_refs(content_dir: Path, records_dir: Path, claims_dir: Path,
                     prefixes: list[str], root: Path | None = None) -> list[RecRef]:
    """Resolve every `[rec:]` marker in gated prose to a sealed record.

    The gate reads the problems; the pack and dashboard read the records — one
    resolution, so a trace can never render from an address the gate did not accept.
    Resolution demands a record in `valid_by_id`: sealed, schema-clean, grounded, fresh,
    uniquely-identified. A duplicated or unsealed id resolves to nothing rather than to
    the wrong judgement.
    """
    all_by_id, valid_by_id, _ids, _problems = load_records_validated(records_dir, claims_dir)
    refs: list[RecRef] = []
    for path in gated_prose(content_dir, prefixes):
        where = str(path.relative_to(root)) if root else path.name
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line, raw in iter_rec_markers(text):
            if not _REC_ID_RE.match(raw):
                refs.append(RecRef(raw, where, line, None,
                                   f"malformed reference '[rec:{raw}]' — expected "
                                   "[rec: <record-id>]"))
                continue
            rid = raw.lower()
            record = valid_by_id.get(rid)
            if record is not None:
                refs.append(RecRef(rid, where, line, record, ""))
            elif rid in all_by_id:
                refs.append(RecRef(rid, where, line, None,
                                   f"[rec: {raw}] names a record that is not valid or "
                                   "sealed (its own problem is reported above)"))
            else:
                refs.append(RecRef(rid, where, line, None,
                                   f"[rec: {raw}] names no assessment record"))
    return refs


def rec_ref_problems(refs: list[RecRef]) -> list[str]:
    return [f"{r.where}:{r.line}: {r.problem}" for r in refs if r.problem]


def inband_problems(claims_dir: Path, record_ids: set[str]) -> list[str]:
    """In-band marker checks: every `[rec: id]` names a real record; a
    performed-settling claim co-occurs with an open crux."""
    problems: list[str] = []
    if not claims_dir.is_dir():
        return problems
    for ledger in sorted(claims_dir.glob("*.md")):
        if ledger.stem == "TEMPLATE":
            continue
        text = ledger.read_text(encoding="utf-8", errors="ignore")
        has_performed = has_crux = False
        for line in text.splitlines():
            stripped = line.strip()
            for rid in REC_REF_RE.findall(stripped):
                if rid.lower() not in record_ids:
                    problems.append(f"{ledger.stem}: [rec: {rid}] has no record "
                                    f"({RECORDS_DIR_NAME}/{rid}.assess.json)")
            if STATUS_PERFORMED_RE.match(stripped):
                has_performed = True
            if CRUXOF_RE.match(stripped):
                has_crux = True
        if has_performed and not has_crux:
            problems.append(f"{ledger.stem}: **Status: performed-settling** must name "
                            "an open **Crux-of:** — otherwise the claim is unfalsifiable")
    return problems


def _sealed_correlation_pairs(records_dir: Path | None) -> dict[frozenset, str]:
    """{ledger-key pair} -> correlated-with record id. The pair is the set of ledger keys
    the record grounds — how a sealed record names the two sources it relates."""
    pairs: dict[frozenset, str] = {}
    if not records_dir or not records_dir.is_dir():
        return pairs
    for path in sorted(records_dir.glob("*.json")):
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if rec.get("kind") != "correlated-with":
            continue
        keys = {cg.parse_address(str(g)).key for g in (rec.get("grounding") or [])}
        keys = {k for k in keys if k}
        if len(keys) == 2:
            pairs[frozenset(keys)] = str(rec.get("id", ""))
    return pairs


def double_count_findings(claims_dir: Path, records_dir: Path | None = None,
                          kinds: dict | None = None) -> list["DoubleCount"]:
    """Two sources that each support the same claim AND are declared correlated-with each
    other (a shared dependence → not two independent confirmations). The `kind` is read from
    the author-declared correlation-kinds surface (`kinds`, a canonical-pair -> slug map);
    the `basis` stays the ledger annotation's own text. When `records_dir` is given, a pair
    backed by a sealed correlated-with record names it — the 'sealed vs declared-only'
    difference the case summary reports. A pair the surface does not classify defaults to
    other-declared-dependence (via the annotation's own bracket)."""
    kinds = kinds or {}
    supporters: dict[str, set[str]] = {}
    for edge in cg.iter_edges(claims_dir):
        if edge.edge_type == "supports":
            tgt = edge.target.render(edge.originating_key)
            supporters.setdefault(tgt, set()).add(edge.originating_key)
    causes: dict[frozenset, tuple[str, str]] = {}
    if claims_dir.is_dir():
        for ledger in sorted(claims_dir.glob("*.md")):
            if ledger.stem == "TEMPLATE":
                continue
            for line in ledger.read_text(encoding="utf-8", errors="ignore").splitlines():
                m = CORRELATED_RE.match(line.strip())
                if m:
                    tgt = cg.parse_address(m.group(1))
                    pair = frozenset({ledger.stem.lower(),
                                      tgt.key or ledger.stem.lower()})
                    inline_kind, basis = parse_correlation_cause(line)
                    causes[pair] = (kinds.get(pair, inline_kind), basis)
    sealed = _sealed_correlation_pairs(records_dir)
    findings: list[DoubleCount] = []
    for tgt, keys in sorted(supporters.items()):
        for a, b in combinations(sorted(keys), 2):
            pair = frozenset({a, b})
            if pair in causes:
                kind, basis = causes[pair]
                findings.append(DoubleCount(a, b, tgt, kind, basis, sealed.get(pair)))
    return findings


def _record_edge_key(rec: dict) -> tuple[str, str] | None:
    """Canonical (target, grounding) key for a kind: edge record, matching `_edge_key`
    (so a bare same-ledger grounding qualifies to the edge key). None if incomplete."""
    subj = cg.parse_address(str(rec.get("subject", "")))
    grounding = rec.get("grounding") or []
    if not subj.slug or not grounding:
        return None
    g = cg.parse_address(str(grounding[0]))
    return subj.render().lower(), g.render(subj.key).lower()


def edge_record_coverage(records_by_id: dict[str, dict]) -> dict[tuple[str, str], set[str]]:
    """(target, grounding) -> {ids} of the kind: edge records covering that edge. Lets a
    record cover an edge without editing the stamped ledger; competing records both keyed."""
    covered: dict[tuple[str, str], set[str]] = {}
    for rid, rec in records_by_id.items():
        if rec.get("kind") != "edge":
            continue
        key = _record_edge_key(rec)
        if key:
            covered.setdefault(key, set()).add(rid)
    return covered


def covering_record(target: str, grounding: str, rec: str | None,
                    coverage: dict[tuple[str, str], set[str]]) -> str | None:
    """The covering kind: edge record id, or None — the one rule the gate, builder and
    probe share. An in-band `[rec:]` counts only if it names a covering record."""
    ids = coverage.get((target.lower(), grounding.lower())) or set()
    if rec:
        r = str(rec).lower()
        return r if r in ids else None
    return min(ids) if ids else None


def _edge_key(edge: cg.Edge) -> tuple[str, str]:
    target = edge.target.render(edge.originating_key).lower()
    grounding = f"{edge.originating_key}:{edge.grounding or '?'}".lower()
    return target, grounding


def edge_assessment_problems(claims_dir: Path, record_ids: set[str],
                             edge_records: dict[tuple[str, str], set[str]] | None = None) -> list[str]:
    """supports/rebuts edges with no assessment record, by in-band `[rec:]` or by
    a matching sealed `kind: edge` record."""
    problems: list[str] = []
    edge_records = edge_records or {}
    for edge in cg.iter_edges(claims_dir):
        if edge.edge_type not in ASSESSED_EDGE_TYPES:
            continue
        label = (f"{edge.originating_key}:{edge.grounding or '?'} "
                 f"--{edge.edge_type}--> {edge.target.render(edge.originating_key)}")
        target, grounding = _edge_key(edge)
        if covering_record(target, grounding, edge.rec, edge_records) is not None:
            continue
        if edge.rec is None:
            problems.append(f"{label}: no assessment record — a {edge.edge_type} edge "
                            "needs an in-band [rec:] or matching kind=edge record "
                            "(edge_assessments)")
        elif str(edge.rec).lower() not in record_ids:
            problems.append(f"{label}: [rec: {edge.rec}] names no record")
        else:
            problems.append(f"{label}: [rec: {edge.rec}] does not name a valid kind=edge "
                            "judgement of this edge (wrong kind/target/grounding, or the record "
                            "has its own problem reported above) (edge_assessments)")
    return problems


def dispute_problems(records_by_id: dict[str, dict]) -> list[str]:
    """A `disputes` link must name a real record that assesses the SAME subject —
    a competing assessment contests a specific judgement, not a different claim."""
    problems: list[str] = []
    for rid, rec in sorted(records_by_id.items()):
        for d in rec.get("disputes", []) or []:
            d = str(d).lower()
            if d not in records_by_id:
                problems.append(f"{rid}: disputes '{d}' which is not a record")
            elif str(records_by_id[d].get("subject", "")).lower() \
                    != str(rec.get("subject", "")).lower():
                problems.append(f"{rid}: disputes '{d}' but they assess different "
                                "subjects (a dispute must contest the same claim)")
    return problems


def review_problems(records_by_id: dict[str, dict]) -> list[str]:
    """A `reviews` link must name a real edge record on the SAME subject — a
    positive faithfulness pass is about a specific inference, not a loose claim."""
    problems: list[str] = []
    for rid, rec in sorted(records_by_id.items()):
        for reviewed in rec.get("reviews", []) or []:
            reviewed = str(reviewed).lower()
            if reviewed not in records_by_id:
                problems.append(f"{rid}: reviews '{reviewed}' which is not a record")
                continue
            target = records_by_id[reviewed]
            if target.get("kind") != "edge":
                problems.append(f"{rid}: reviews '{reviewed}' which is not an edge record")
            elif str(target.get("subject", "")).lower() \
                    != str(rec.get("subject", "")).lower():
                problems.append(f"{rid}: reviews '{reviewed}' but they assess different "
                                "subjects (a pass must review the same edge target)")
    return problems


def calibration_problems(assess_dir: Path) -> list[str]:
    """Shape-only check of calibration notes (content/assessments/*.md): a note
    declaring calibrated_confidence must carry inside_view + both discounts, all
    numeric, with calibrated ≤ inside_view. Magnitudes are NEVER endorsed."""
    problems: list[str] = []
    if not assess_dir.is_dir():
        return problems
    for note in sorted(assess_dir.glob("*.md")):
        fm = read_frontmatter(note)
        if "calibrated_confidence" not in fm:
            continue   # not a calibration note
        nums: dict[str, float] = {}
        for field in ("inside_view", *CALIB_DISCOUNTS, "calibrated_confidence"):
            raw = fm.get(field, "")
            if raw == "":
                problems.append(f"{note.stem}: calibration note missing '{field}'")
                continue
            try:
                nums[field] = float(raw)
            except ValueError:
                problems.append(f"{note.stem}: '{field}' is not numeric ('{raw}')")
        if "calibrated_confidence" in nums and "inside_view" in nums \
                and nums["calibrated_confidence"] > nums["inside_view"]:
            problems.append(f"{note.stem}: calibrated_confidence "
                            f"({nums['calibrated_confidence']}) exceeds inside_view "
                            f"({nums['inside_view']}) — discounts must not raise it")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Attest judgement records are sealed, grounded, and fresh.")
    ap.add_argument("--claims-dir", default=str(CLAIMS_DIR),
                    help="override verified_claims/ location (tests)")
    ap.add_argument("--assess-dir", default=str(ASSESS_DIR),
                    help="override content/assessments/ location (tests)")
    ap.add_argument("--content-dir", default=str(REPO_ROOT / "content"),
                    help="override content/ location, scanned for [rec:] refs (tests)")
    ap.add_argument("--config", default=str(REPO_ROOT / "ledger.config.md"),
                    help="override ledger.config.md location (tests)")
    ap.add_argument("--assessment", choices=("off", "optional", "required"), default=None,
                    help="override the posture (default: assessment_layer: in config)")
    ap.add_argument("--edge-assessments", choices=("off", "warn", "required"), default=None,
                    help="override edge_assessments (default: in config)")
    args = ap.parse_args()

    config = parse_config(Path(args.config))
    mode = args.assessment or assessment_mode(config)
    # edge_assessments rests on validated records; assessment_layer: off loads none.
    # required can't be honestly satisfied → error; warn is advisory → note but pass.
    edge_mode = args.edge_assessments or edge_assessment_mode(config)
    if mode == "off":
        if edge_mode == "required":
            log_error("edge_assessments: required needs assessment_layer on "
                      "(optional/required) — it rests on validated records, which "
                      "assessment_layer: off does not check.")
            return 1
        if edge_mode == "warn":
            log_warning("edge_assessments is inert under assessment_layer: off "
                        "(records are not validated) — not enforced.")
        log_info("assessment_layer: off — judgement-record validation skipped.")
        return 0

    claims_dir = Path(args.claims_dir)
    assess_dir = Path(args.assess_dir)
    records_by_id, valid_records_by_id, record_ids, problems = load_records_validated(
        assess_dir / RECORDS_DIR_NAME, claims_dir)
    problems.extend(inband_problems(claims_dir, record_ids))
    # The prose-side analogue of inband_problems: a finding citing a judgement is making
    # the same reference a ledger does, and an unresolvable one is the same defect.
    problems.extend(rec_ref_problems(resolve_rec_refs(
        Path(args.content_dir), assess_dir / RECORDS_DIR_NAME, claims_dir,
        gated_prefixes(config), root=Path(args.content_dir).parent)))
    problems.extend(dispute_problems(records_by_id))
    problems.extend(review_problems(records_by_id))
    problems.extend(calibration_problems(assess_dir))

    content_dir = Path(args.content_dir)
    findings = double_count_findings(   # heuristic → always a warning; kind is author-declared
        claims_dir, kinds=load_correlation_kinds(content_dir)[0])
    corr_problems = correlation_kinds_problems(content_dir, claims_dir)

    # Only valid records cover an edge (an invalid one must not satisfy required).
    edge_problems = (edge_assessment_problems(
        claims_dir, record_ids, edge_record_coverage(valid_records_by_id))
                     if edge_mode != "off" else [])

    exit_code = 0
    if findings:
        log_warning("derived double-count finding(s) (heuristic — review):\n  - "
                    + "\n  - ".join(f"[{f.kind_label}] {f.summary}" for f in findings))
    if corr_problems:
        message = ("author-declared correlation-kinds file invalid (orphan / duplicate / "
                   "unknown kind / missing provenance):\n  - " + "\n  - ".join(corr_problems))
        if mode == "required":
            log_error(message)
            exit_code = 1
        else:
            log_warning(message)
    if problems:
        message = ("assessment-record problems (unsealed/ungrounded/stale, bad "
                   "[rec:]/disputes, unfalsifiable status, or calibration shape):\n  - "
                   + "\n  - ".join(problems))
        if mode == "required":
            log_error(message)
            exit_code = 1
        else:
            log_warning(message)
    if edge_problems:
        message = ("supports/rebuts edges with no assessment (edge_assessments):\n  - "
                   + "\n  - ".join(edge_problems))
        if edge_mode == "required":
            log_error(message)
            exit_code = 1
        else:
            log_warning(message)
    if not problems and not edge_problems and not findings and not corr_problems:
        log_info(f"assessment ok — {len(records_by_id)} judgement record(s) sealed, "
                 "grounded, and fresh.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
