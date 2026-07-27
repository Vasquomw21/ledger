# Tests for the assessment gate + record helper (corpus-free; tmp fixtures).
# Covers the plan's cases: a valid sealed record passes; a tampered seal,
# unresolvable grounding, stale body_sha256, and a span-not-substring are caught;
# the derived double-count finding surfaces; an empty layer passes; plus the
# in-band [rec:] / performed-settling and calibration-shape checks.
import json

import assess_record as ar
import check_assessment as ca


def _ledger(claims_dir, key, claims, *, extra=()):
    """Write a ledger: each claim is a `## Claim` block with **ID:** slug + quote.
    `extra` lines (edges / assessment markers) are appended under the first claim."""
    claims_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", 'paper: "X"', "---", ""]
    for i, (slug, quote) in enumerate(claims, start=1):
        lines += [f"## Claim {i}: summary", "", f'> "{quote}"', "",
                  f"**ID:** {slug}", "**Location:** Section 1"]
        if i == 1:
            lines += list(extra)
        lines.append("")
    (claims_dir / f"{key}.md").write_text("\n".join(lines), encoding="utf-8")


def _record(claims_dir, assess_dir, **over):
    """Build + write a sealed record; defaults form a valid rhetorical judgement."""
    fields = dict(kind="rhetorical", rec_id="r1",
                  subject="andersen_2020:fcs", grounding=["andersen_2020:fcs"],
                  span="irrefutably show", assessed_date="20260613")
    fields.update(over)
    record = ar.build_record(fields["kind"], fields["rec_id"], fields["subject"],
                             fields["grounding"], fields["span"],
                             fields["assessed_date"], claims_dir=claims_dir)
    ar.write_record(record, assess_dir=assess_dir)
    return record


def _dirs(tmp_path):
    return tmp_path / "verified_claims", tmp_path / "assessments"


# --- empty layer ----------------------------------------------------------

def test_empty_layer_passes(tmp_path, monkeypatch):
    claims, assess = _dirs(tmp_path)
    assert _run_main(monkeypatch, claims, assess, "required") == 0


# --- a valid record passes ------------------------------------------------

def test_valid_record_passes(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "we irrefutably show the site is engineered")])
    record = _record(claims, assess)
    assert ca.record_problems(record, claims) == []


# --- edge-aptness record (dogfood fix b) ----------------------------------

def test_edge_kind_record_satisfies_edge_assessment(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "src", [("s", "the source claim")],
            extra=["**Supports:** dst:d (grounded by #s) [rec: e1]"])
    _ledger(claims, "dst", [("d", "the target claim")])
    record = _record(claims, assess, kind="edge", rec_id="e1",
                     subject="dst:d", grounding=["src:s"], span="")
    # The edge kind is accepted, and its [rec:] satisfies edge_assessments when the
    # record is the kind=edge one covering this edge (target+grounding match).
    assert ca.record_problems(record, claims) == []
    assert ca.edge_assessment_problems(
        claims, {"e1"}, ca.edge_record_coverage({"e1": record})) == []


def test_external_edge_record_satisfies_edge_assessment_without_inband_rec(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "src", [("s", "the source claim")],
            extra=["**Supports:** dst:d (grounded by #s)"])
    _ledger(claims, "dst", [("d", "the target claim")])
    record = _record(claims, assess, kind="edge", rec_id="e1",
                     subject="dst:d", grounding=["src:s"], span="")
    coverage = ca.edge_record_coverage({"e1": record})
    assert ca.edge_assessment_problems(claims, {"e1"}, coverage) == []


def test_faithfulness_pass_reviews_edge_record(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "src", [("s", "the source claim")],
            extra=["**Supports:** dst:d (grounded by #s)"])
    _ledger(claims, "dst", [("d", "the target claim")])
    edge = _record(claims, assess, kind="edge", rec_id="e1",
                   subject="dst:d", grounding=["src:s"], span="")
    passed = ar.build_record("faithfulness-pass", "e1-pass", "dst:d", ["src:s"], "",
                             "20260615", claims_dir=claims, reviews=["e1"])
    assert ca.record_problems(passed, claims) == []
    assert ca.review_problems({"e1": edge, "e1-pass": passed}) == []


def test_faithfulness_pass_wrong_subject_caught(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "src", [("s", "the source claim")])
    _ledger(claims, "dst", [("d", "the target claim")])
    edge = _record(claims, assess, kind="edge", rec_id="e1",
                   subject="dst:d", grounding=["src:s"], span="")
    passed = ar.build_record("faithfulness-pass", "e1-pass", "src:s", ["src:s"], "",
                             "20260615", claims_dir=claims, reviews=["e1"])
    assert any("different subjects" in p for p in ca.review_problems({
        "e1": edge, "e1-pass": passed
    }))


# --- tampered seal --------------------------------------------------------

def test_tampered_seal_caught(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "we irrefutably show the site")])
    record = _record(claims, assess)
    record["assessed_date"] = "29991231"        # mutate a field without resealing
    problems = ca.record_problems(record, claims)
    assert any("record_sha256 inconsistent" in p for p in problems)


# --- published-schema shape enforcement -----------------------------------

def test_schema_violation_caught(tmp_path):
    # A shape the seal can't catch: reseal a bad assessed_date so only the schema
    # pattern (^[0-9]{8}$) is violated — the gate must reject on the published schema.
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "we irrefutably show the site")])
    record = _record(claims, assess)
    record["assessed_date"] = "2026-06-13"      # dashed → fails the schema pattern
    record["record_sha256"] = ca.run_record_digest(record)   # reseal: seal is consistent
    problems = ca.record_problems(record, claims)
    assert any("schema" in p and "assessed_date" in p for p in problems)


# --- unresolvable grounding -----------------------------------------------

def test_unresolvable_grounding_caught(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "we irrefutably show the site")])
    record = _record(claims, assess, grounding=["ghost_2099:x"])
    problems = ca.record_problems(record, claims)
    assert any("grounding 'ghost_2099:x' unresolved" in p for p in problems)


# --- stale body_sha256 ----------------------------------------------------

def test_stale_body_caught(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "original quote text here for hashing")])
    record = _record(claims, assess, kind="crux-of", span="")
    # Edit the subject claim after the judgement was sealed → body hash drifts.
    _ledger(claims, "andersen_2020", [("fcs", "EDITED quote text here for hashing")])
    problems = ca.record_problems(record, claims)
    assert any("body_sha256 stale" in p for p in problems)


# --- rhetorical span must be a substring of the grounding quote ------------

def test_span_not_substring_caught(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "a measured, hedged scientific statement")])
    record = _record(claims, assess, span="irrefutably show")   # not in the quote
    problems = ca.record_problems(record, claims)
    assert any("not a substring of the grounding quote" in p for p in problems)


def test_span_substring_passes(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "we irrefutably show the site")])
    record = _record(claims, assess, span="irrefutably show")
    assert ca.record_problems(record, claims) == []


# --- derived double-count -------------------------------------------------

def test_double_count_finding(tmp_path):
    claims, _ = _dirs(tmp_path)
    _ledger(claims, "a_2020", [("ca", "premise A")],
            extra=["**Supports:** c_2020:cc (grounded by #ca)",
                   "**Correlated-with:** b_2021:cb (grounded by #ca)"])
    _ledger(claims, "b_2021", [("cb", "premise B")],
            extra=["**Supports:** c_2020:cc (grounded by #cb)"])
    _ledger(claims, "c_2020", [("cc", "the contested conclusion")])
    findings = ca.double_count_findings(claims)
    assert any({f.a, f.b} == {"a_2020", "b_2021"} for f in findings)
    # An untyped correlation is the honest default, never promoted to a stronger kind.
    dc = next(f for f in findings if {f.a, f.b} == {"a_2020", "b_2021"})
    assert dc.kind == "other-declared-dependence" and dc.sealed_record is None


# --- in-band [rec:] and performed-settling --------------------------------

def test_dangling_rec_ref_caught(tmp_path):
    claims, _ = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "a quote")],
            extra=['**Assess-rhetorical:** "x" — why (grounded by #fcs) [rec: ghost]'])
    problems = ca.inband_problems(claims, record_ids=set())
    assert any("[rec: ghost]" in p for p in problems)


def test_performed_settling_needs_crux(tmp_path):
    claims, _ = _dirs(tmp_path)
    _ledger(claims, "q1_2020", [("c", "a quote")], extra=["**Status:** performed-settling"])
    problems = ca.inband_problems(claims, record_ids=set())
    assert any("performed-settling" in p for p in problems)
    # With an open crux named, it is falsifiable → no problem.
    _ledger(claims, "q1_2020", [("c", "a quote")],
            extra=["**Status:** performed-settling",
                   "**Crux-of:** fcs-engineering (grounded by #c)"])
    assert ca.inband_problems(claims, record_ids=set()) == []


# --- calibration-note shape -----------------------------------------------

def test_calibration_calibrated_exceeds_inside_view(tmp_path):
    claims, assess = _dirs(tmp_path)
    assess.mkdir(parents=True)
    (assess / "fcs.md").write_text(
        "---\ninside_view: 0.6\nout_of_model_discount: 0.1\n"
        "adversarial_discount: 0.1\ncalibrated_confidence: 0.8\n---\n# note\n",
        encoding="utf-8")
    problems = ca.calibration_problems(assess)
    assert any("exceeds inside_view" in p for p in problems)


def test_calibration_valid_shape_passes(tmp_path):
    claims, assess = _dirs(tmp_path)
    assess.mkdir(parents=True)
    (assess / "fcs.md").write_text(
        "---\ninside_view: 0.6\nout_of_model_discount: 0.1\n"
        "adversarial_discount: 0.2\ncalibrated_confidence: 0.4\n---\n# note\n",
        encoding="utf-8")
    assert ca.calibration_problems(assess) == []


# --- posture exit codes via main() ----------------------------------------

def test_required_fails_optional_warns(tmp_path, monkeypatch):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "a hedged statement")])
    _record(claims, assess, span="irrefutably show")    # span not in quote → problem
    assert _run_main(monkeypatch, claims, assess, "required") == 1
    assert _run_main(monkeypatch, claims, assess, "optional") == 0


def test_off_skips(tmp_path, monkeypatch, capsys):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "a hedged statement")])
    _record(claims, assess, span="irrefutably show")
    assert _run_main(monkeypatch, claims, assess, "off") == 0
    assert "off" in capsys.readouterr().out


def _run_main(monkeypatch, claims_dir, assess_dir, mode, edge="off"):
    argv = ["check_assessment.py", "--claims-dir", str(claims_dir),
            "--assess-dir", str(assess_dir), "--assessment", mode,
            "--edge-assessments", edge]
    monkeypatch.setattr("sys.argv", argv)
    return ca.main()


# --- edge_assessments coverage ---------------------------------

def test_edge_without_rec_flagged_under_required(tmp_path, monkeypatch):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "a_2020", [("ca", "premise")],
            extra=["**Supports:** b_2021:cb (grounded by #ca)"])
    _ledger(claims, "b_2021", [("cb", "conclusion")])
    # assessment_layer optional (records clean) but edge_assessments required.
    assert _run_main(monkeypatch, claims, assess, "optional", edge="required") == 1
    assert _run_main(monkeypatch, claims, assess, "optional", edge="off") == 0


def test_edge_with_matching_edge_record_passes(tmp_path, monkeypatch):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "a_2020", [("ca", "premise")],
            extra=["**Supports:** b_2021:cb (grounded by #ca) [rec: j1]"])
    _ledger(claims, "b_2021", [("cb", "conclusion")])
    # a kind=edge record whose subject is the edge target, grounded by the same claim
    rec = ar.build_record("edge", "j1", "b_2021:cb", ["a_2020:ca"], "",
                          "20260613", claims_dir=claims)
    ar.write_record(rec, assess_dir=assess)
    assert _run_main(monkeypatch, claims, assess, "required", edge="required") == 0


def test_edge_rec_pointing_at_nonedge_record_is_flagged(tmp_path, monkeypatch):
    # A real record of the wrong kind does not judge the edge's aptness → uncovered.
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "a_2020", [("ca", "premise")],
            extra=["**Supports:** b_2021:cb (grounded by #ca) [rec: j1]"])
    _ledger(claims, "b_2021", [("cb", "conclusion")])
    rec = ar.build_record("crux-of", "j1", "a_2020:ca", ["a_2020:ca"], "",
                          "20260613", claims_dir=claims)
    ar.write_record(rec, assess_dir=assess)
    assert _run_main(monkeypatch, claims, assess, "required", edge="required") == 1


# --- competing assessments via disputes ------------------------

def test_dispute_nonexistent_record_flagged(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "we irrefutably show the site")])
    rec = ar.build_record("rhetorical", "r2", "andersen_2020:fcs",
                          ["andersen_2020:fcs"], "irrefutably show", "20260613",
                          claims_dir=claims, disputes=["ghost"])
    problems = ca.dispute_problems({"r2": rec})
    assert any("disputes 'ghost'" in p for p in problems)


def test_dispute_different_subject_flagged(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "a quote")])
    _ledger(claims, "segreto_2021", [("eng", "another quote")])
    r1 = ar.build_record("crux-of", "r1", "andersen_2020:fcs", ["andersen_2020:fcs"],
                         "", "20260613", claims_dir=claims)
    r2 = ar.build_record("crux-of", "r2", "segreto_2021:eng", ["segreto_2021:eng"],
                         "", "20260613", claims_dir=claims, disputes=["r1"])
    problems = ca.dispute_problems({"r1": r1, "r2": r2})
    assert any("different" in p for p in problems)


def test_valid_competing_dispute_passes(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "a quote")])
    r1 = ar.build_record("rhetorical", "r1", "andersen_2020:fcs",
                         ["andersen_2020:fcs"], "", "20260613", claims_dir=claims)
    r2 = ar.build_record("rhetorical", "r2", "andersen_2020:fcs",
                         ["andersen_2020:fcs"], "", "20260613", claims_dir=claims,
                         disputes=["r1"])
    assert ca.dispute_problems({"r1": r1, "r2": r2}) == []


# --- edge coverage: canonical addressing, competing + valid-only records --------

def test_bare_same_ledger_grounding_covers_edge(tmp_path, monkeypatch):
    # A bare same-ledger grounding must canonicalise to the qualified edge key, or the
    # edge reads as uncovered under required.
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "solo", [("prem", "the premise"), ("concl", "the conclusion")],
            extra=["**Supports:** concl (grounded by #prem)"])
    rec = ar.build_record("edge", "e1", "solo:concl", ["prem"], "",
                          "20260613", claims_dir=claims)
    ar.write_record(rec, assess_dir=assess)
    assert ca.record_problems(rec, claims) == []
    assert _run_main(monkeypatch, claims, assess, "required", edge="required") == 0


def test_competing_edge_records_both_cover(tmp_path, monkeypatch):
    # Two edge records cover one edge; an in-band [rec:] naming either is accepted, even
    # the one a single-id map would overwrite.
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "a_2020", [("ca", "premise")],
            extra=["**Supports:** b_2021:cb (grounded by #ca) [rec: j1]"])
    _ledger(claims, "b_2021", [("cb", "conclusion")])
    for rid in ("j1", "j2"):
        rec = ar.build_record("edge", rid, "b_2021:cb", ["a_2020:ca"], "",
                              "20260613", claims_dir=claims)
        ar.write_record(rec, assess_dir=assess)
    assert _run_main(monkeypatch, claims, assess, "required", edge="required") == 0


def test_stale_edge_record_does_not_cover_under_required(tmp_path, monkeypatch):
    # A stale edge record must not satisfy required coverage while the base layer only warns.
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "a_2020", [("ca", "premise")],
            extra=["**Supports:** b_2021:cb (grounded by #ca)"])
    _ledger(claims, "b_2021", [("cb", "the original conclusion")])
    rec = ar.build_record("edge", "e1", "b_2021:cb", ["a_2020:ca"], "",
                          "20260613", claims_dir=claims)
    ar.write_record(rec, assess_dir=assess)
    _ledger(claims, "b_2021", [("cb", "the EDITED conclusion")])   # stale body_sha256
    assert _run_main(monkeypatch, claims, assess, "optional", edge="required") == 1


def test_edge_required_with_assessment_off_is_rejected(tmp_path, monkeypatch):
    # off + required can't be satisfied → error; off + warn is advisory → passes.
    claims, assess = _dirs(tmp_path)
    assert _run_main(monkeypatch, claims, assess, "off", edge="required") == 1
    assert _run_main(monkeypatch, claims, assess, "off", edge="warn") == 0
    assert _run_main(monkeypatch, claims, assess, "off", edge="off") == 0


# --- record id uniqueness + filename binding -----------------------------------

def test_filename_must_match_record_id(tmp_path, monkeypatch):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "we irrefutably show the site")])
    rec = ar.build_record("rhetorical", "r1", "andersen_2020:fcs",
                          ["andersen_2020:fcs"], "irrefutably show", "20260613",
                          claims_dir=claims)
    (assess / "_records").mkdir(parents=True, exist_ok=True)
    (assess / "_records" / "wrongname.assess.json").write_text(
        json.dumps(rec), encoding="utf-8")     # id r1 but filename wrongname
    assert _run_main(monkeypatch, claims, assess, "required") == 1
    assert _run_main(monkeypatch, claims, assess, "optional") == 0


def test_duplicate_record_id_flagged(tmp_path, monkeypatch):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "we irrefutably show the site")])
    rec = ar.build_record("rhetorical", "r1", "andersen_2020:fcs",
                          ["andersen_2020:fcs"], "irrefutably show", "20260613",
                          claims_dir=claims)
    ar.write_record(rec, assess_dir=assess)                       # r1.assess.json
    (assess / "_records" / "r1_dup.assess.json").write_text(      # a second file, same id
        json.dumps(rec), encoding="utf-8")
    assert _run_main(monkeypatch, claims, assess, "required") == 1


# --- read-only coverage matches the gate (valid records only) -------------------

def test_valid_edge_coverage_excludes_invalid_records(tmp_path):
    # The coverage every read-only surface (status/dashboard/probe/analyzer) uses must
    # exclude invalid records, so none can show 'assessed' while the gate blocks.
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "a_2020", [("ca", "premise")],
            extra=["**Supports:** b_2021:cb (grounded by #ca)"])
    _ledger(claims, "b_2021", [("cb", "the original conclusion")])
    rec = ar.build_record("edge", "e1", "b_2021:cb", ["a_2020:ca"], "",
                          "20260613", claims_dir=claims)
    ar.write_record(rec, assess_dir=assess)
    records_dir = assess / "_records"
    assert ca.valid_edge_coverage(records_dir, claims)          # covered while fresh
    _ledger(claims, "b_2021", [("cb", "the EDITED conclusion")])   # stale body_sha256
    assert ca.valid_edge_coverage(records_dir, claims) == {}    # excluded once invalid


def test_identity_defective_edge_record_does_not_cover(tmp_path, monkeypatch):
    # An edge record whose filename ≠ id is identity-defective → excluded from coverage,
    # so it can't satisfy required while the mismatch only warns under optional.
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "a_2020", [("ca", "premise")],
            extra=["**Supports:** b_2021:cb (grounded by #ca)"])
    _ledger(claims, "b_2021", [("cb", "conclusion")])
    rec = ar.build_record("edge", "e1", "b_2021:cb", ["a_2020:ca"], "",
                          "20260613", claims_dir=claims)
    (assess / "_records").mkdir(parents=True, exist_ok=True)
    (assess / "_records" / "misfiled.assess.json").write_text(
        json.dumps(rec), encoding="utf-8")
    assert _run_main(monkeypatch, claims, assess, "optional", edge="required") == 1
