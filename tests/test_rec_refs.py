# One resolver, two consumers: the gate reads its problems, the renderers read its
# records. A trace must not be renderable from an address the gate would not accept.
import json

import assess_record as ar
import check_assessment as ca

GATED = ["content/concept_notes/", "content/finding.md"]


def _ledger(claims_dir, key, slug, quote):
    claims_dir.mkdir(parents=True, exist_ok=True)
    (claims_dir / f"{key}.md").write_text("\n".join([
        "---", 'paper: "X"', "---", "",
        "## Claim 1: summary", "", f'> "{quote}"', "",
        f"**ID:** {slug}", "**Location:** Section 1", "",
    ]), encoding="utf-8")


def _project(tmp_path, prose, *, rec_id="worobey-faithfulness", filename="finding.md"):
    claims = tmp_path / "verified_claims"
    assess = tmp_path / "assessments"
    _ledger(claims, "andersen_2020", "fcs", "we irrefutably show the site is engineered")
    record = ar.build_record("rhetorical", rec_id, "andersen_2020:fcs",
                             ["andersen_2020:fcs"], "irrefutably show", "20260613",
                             claims_dir=claims)
    ar.write_record(record, assess_dir=assess)
    content = tmp_path / "content"
    content.mkdir(parents=True, exist_ok=True)
    (content / filename).write_text(prose, encoding="utf-8")
    return content, assess, claims


def _refs(tmp_path, prose, **kw):
    content, assess, claims = _project(tmp_path, prose, **kw)
    return ca.resolve_rec_refs(content, assess / ca.RECORDS_DIR_NAME, claims, GATED,
                               root=tmp_path)


# ---- resolution -------------------------------------------------------------

def test_a_reference_to_a_sealed_record_resolves_to_it(tmp_path):
    refs = _refs(tmp_path, "The dispute [rec: worobey-faithfulness] contests it.\n")
    assert len(refs) == 1
    ref = refs[0]
    assert ref.resolved and ref.problem == ""
    assert ref.record["id"] == "worobey-faithfulness"
    assert ref.record["kind"] == "rhetorical"
    assert (ref.where, ref.line) == ("content/finding.md", 1)


def test_the_reported_line_is_the_markers_own(tmp_path):
    refs = _refs(tmp_path, "one\ntwo\nthree [rec: nope] here\n")
    assert refs[0].line == 3


def test_a_reference_to_no_record_is_a_problem(tmp_path):
    refs = _refs(tmp_path, "See [rec: banal-bat-relative].\n")
    assert not refs[0].resolved
    assert "names no assessment record" in refs[0].problem
    assert ca.rec_ref_problems(refs) == [
        "content/finding.md:1: [rec: banal-bat-relative] names no assessment record"]


def test_a_reference_to_an_unsealed_record_does_not_resolve(tmp_path):
    # Existence is not enough: an edited record must not answer a citation of it.
    content, assess, claims = _project(tmp_path, "See [rec: worobey-faithfulness].\n")
    path = assess / ca.RECORDS_DIR_NAME / "worobey-faithfulness.assess.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["span"] = "a span nobody sealed"
    path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    refs = ca.resolve_rec_refs(content, assess / ca.RECORDS_DIR_NAME, claims, GATED,
                               root=tmp_path)
    assert not refs[0].resolved
    assert "not valid or sealed" in refs[0].problem


def test_an_ambiguous_id_resolves_to_nothing_rather_than_a_guess(tmp_path):
    content, assess, claims = _project(tmp_path, "See [rec: worobey-faithfulness].\n")
    records = assess / ca.RECORDS_DIR_NAME
    twin = json.loads(
        (records / "worobey-faithfulness.assess.json").read_text(encoding="utf-8"))
    (records / "worobey-faithfulness-copy.assess.json").write_text(
        json.dumps(twin, indent=2, sort_keys=True), encoding="utf-8")
    refs = ca.resolve_rec_refs(content, records, claims, GATED, root=tmp_path)
    assert not refs[0].resolved


# ---- malformed markers ------------------------------------------------------

def test_a_malformed_marker_is_reported_not_skipped(tmp_path):
    # A strict pattern would not match these at all, so they would ship unseen.
    for prose in ("See [rec: ].\n", "See [rec:].\n", "See [rec: two words].\n",
                  "See [rec: bad/id].\n"):
        refs = _refs(tmp_path, prose)
        assert refs and not refs[0].resolved, prose
        assert "malformed reference" in refs[0].problem, prose


def test_a_well_formed_marker_is_not_called_malformed(tmp_path):
    refs = _refs(tmp_path, "See [rec:worobey-faithfulness] and [rec:  worobey-faithfulness ].\n")
    assert len(refs) == 2 and all(r.resolved for r in refs)


# ---- markers that prose has wrapped -----------------------------------------

def test_a_marker_wrapped_onto_the_next_line_still_resolves(tmp_path):
    # Prose wraps at the margin. A per-line scan cannot match this marker at all, and an
    # unmatched marker is reported by nobody: the claim silently loses its grounding while
    # the gate stays green. Wrapping is formatting, so the id survives it.
    refs = _refs(tmp_path,
                 "The step carries a sealed faithfulness dispute [rec:\n"
                 "worobey-faithfulness]: the quote is narrower than the claim.\n")
    assert len(refs) == 1, "a wrapped marker must not be invisible"
    assert refs[0].resolved and refs[0].problem == ""
    assert refs[0].ref_id == "worobey-faithfulness"


def test_a_wrapped_marker_reports_the_line_it_opens_on(tmp_path):
    refs = _refs(tmp_path, "one\ntwo\nthree [rec:\nworobey-faithfulness] four\n")
    assert refs[0].line == 3


def test_a_line_break_inside_the_id_is_malformed_not_repaired(tmp_path):
    # Wrapped ONTO its own line is formatting; wrapped THROUGH the id is a broken address.
    # Rejoining it would invent an id the author never wrote.
    refs = _refs(tmp_path, "See [rec: worobey-\nfaithfulness] here.\n")
    assert len(refs) == 1
    assert not refs[0].resolved
    assert "malformed reference" in refs[0].problem


def test_every_marker_in_wrapped_prose_is_seen(tmp_path):
    # The count is the point: the defect lost one of several markers, leaving the rest to
    # make the page look complete.
    refs = _refs(tmp_path,
                 "First [rec: worobey-faithfulness] then a long clause that runs to the\n"
                 "margin and wraps its second marker [rec:\n"
                 "worobey-faithfulness] and a third [rec: worobey-faithfulness].\n")
    assert len(refs) == 3, f"markers seen: {[r.ref_id for r in refs]}"
    assert all(r.resolved for r in refs)


# ---- gating -----------------------------------------------------------------

def test_ungated_prose_is_left_alone(tmp_path):
    # Raw baseline material is captured model output, not authored claims: it cites
    # things this project holds no record for, and that is the demonstration.
    refs = _refs(tmp_path, "Raw output citing [rec: nothing-real].\n",
                 filename="baseline_research_raw.md")
    assert refs == []


def test_a_gated_file_is_scanned(tmp_path):
    refs = _refs(tmp_path, "See [rec: nothing-real].\n", filename="finding.md")
    assert len(refs) == 1


# ---- the gate ---------------------------------------------------------------

def _run(monkeypatch, tmp_path, content, assess, claims, mode="required"):
    monkeypatch.setattr("sys.argv", [
        "check_assessment.py", "--claims-dir", str(claims), "--assess-dir", str(assess),
        "--content-dir", str(content), "--assessment", mode, "--edge-assessments", "off",
        "--config", str(tmp_path / "ledger.config.md")])
    return ca.main()


def _config(tmp_path):
    (tmp_path / "ledger.config.md").write_text(
        "gated_paths: content/concept_notes/, content/finding.md\n"
        "assessment_layer: required\n", encoding="utf-8")


def test_the_gate_blocks_an_unresolvable_reference_in_gated_prose(tmp_path, monkeypatch):
    content, assess, claims = _project(tmp_path, "See [rec: banal-bat-relative].\n")
    _config(tmp_path)
    assert _run(monkeypatch, tmp_path, content, assess, claims) == 1


def test_the_gate_passes_a_resolvable_reference(tmp_path, monkeypatch):
    content, assess, claims = _project(tmp_path, "See [rec: worobey-faithfulness].\n")
    _config(tmp_path)
    assert _run(monkeypatch, tmp_path, content, assess, claims) == 0
