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


# --- tampered seal --------------------------------------------------------

def test_tampered_seal_caught(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "we irrefutably show the site")])
    record = _record(claims, assess)
    record["assessed_date"] = "29991231"        # mutate a field without resealing
    problems = ca.record_problems(record, claims)
    assert any("record_sha256 inconsistent" in p for p in problems)


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
    assert any("a_2020" in f and "b_2021" in f and "double-count" in f for f in findings)


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


def test_edge_with_rec_and_record_passes(tmp_path, monkeypatch):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "a_2020", [("ca", "premise")],
            extra=["**Supports:** b_2021:cb (grounded by #ca) [rec: j1]"])
    _ledger(claims, "b_2021", [("cb", "conclusion")])
    rec = ar.build_record("crux-of", "j1", "a_2020:ca", ["a_2020:ca"], "",
                          "20260613", claims_dir=claims)
    ar.write_record(rec, assess_dir=assess)
    assert _run_main(monkeypatch, claims, assess, "required", edge="required") == 0


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
