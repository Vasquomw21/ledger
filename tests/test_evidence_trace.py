# The judge's route: the pack renders the trace a finding's sealed references open.
# The load-bearing rule is that it renders ONLY what the resolver resolved — an address
# the gate would reject must not be able to reach the page.
import assess_record as ar
import build_judge_pack as bjp
import judge_dashboard as jd

FINDING = """# Finding — a case

The lesson this case teaches, stated first.

## Detail
The inference is contested [rec: a-faith]; the certainty is flagged [rec: b-rhetoric].
"""


def _project(tmp_path, finding=FINDING, *, gated=True):
    tmp_path.mkdir(parents=True, exist_ok=True)     # supports tmp_path / "sub" roots
    (tmp_path / "ledger.config.md").write_text(
        "project_name: tracecase\n"
        + ("gated_paths: content/finding.md\n" if gated else "gated_paths: none\n"),
        encoding="utf-8")
    claims = tmp_path / "literature" / "verified_claims"
    claims.mkdir(parents=True)
    (claims / "a_2020.md").write_text("\n".join([
        "---", 'paper: "A et al. (2020)"', "---", "",
        "## Claim 1: premise", "", '> "the grounding quote"', "",
        "**ID:** p", "**Location:** Abstract",
        "**Supports:** b_2021:c (grounded by #p) [rec: a-supports-c]", "",
    ]), encoding="utf-8")
    (claims / "b_2021.md").write_text("\n".join([
        "---", 'paper: "B et al. (2021)"', "---", "",
        "## Claim 1: conclusion", "", '> "we do not believe it is plausible"', "",
        "**ID:** c", "**Location:** Discussion", "",
    ]), encoding="utf-8")
    content = tmp_path / "content"
    assess = content / "assessments"
    (assess / "_records").mkdir(parents=True)
    (content / "inquiry.md").write_text("# Inquiry\n", encoding="utf-8")
    if finding is not None:
        (content / "finding.md").write_text(finding, encoding="utf-8")

    def record(**kw):
        rec = ar.build_record(claims_dir=claims, **kw)
        ar.write_record(rec, assess_dir=assess)
        return rec

    record(kind="edge", rec_id="a-supports-c", subject="b_2021:c",
           grounding=["a_2020:p"], span="", assessed_date="20260101")
    record(kind="faithfulness", rec_id="a-faith", subject="b_2021:c",
           grounding=["a_2020:p"], span="the grounding quote",
           assessed_date="20260101", disputes=["a-supports-c"])
    record(kind="rhetorical", rec_id="b-rhetoric", subject="b_2021:c",
           grounding=["b_2021:c"], span="we do not believe", assessed_date="20260101")
    return tmp_path


# ---- what the trace resolves ------------------------------------------------

def test_the_trace_anchors_on_the_subjects_of_cited_records(tmp_path):
    trace = jd.evidence_trace(_project(tmp_path))
    assert [t["subject"] for t in trace] == ["b_2021:c"]
    assert sorted(trace[0]["cited_by"]) == ["a-faith", "b-rhetoric"]


def test_the_trace_carries_the_subjects_verbatim_quote_and_locus(tmp_path):
    node = jd.evidence_trace(_project(tmp_path))[0]["node"]
    assert node["quote"] == "we do not believe it is plausible"
    assert node["location"] == "Discussion"
    assert node["source"] == "B et al. (2021)"


def test_an_incoming_edge_carries_its_grounding_quote_and_dispute(tmp_path):
    incoming = jd.evidence_trace(_project(tmp_path))[0]["incoming"]
    assert len(incoming) == 1
    edge = incoming[0]
    assert edge["source"] == "a_2020:p" and edge["type"] == "supports"
    assert edge["grounding_quote"] == "the grounding quote"
    assert [r["id"] for r in edge["contested_by"]] == ["a-faith"]
    assert edge["contested_by"][0]["span"] == "the grounding quote"


def test_records_trace_even_when_the_finding_cites_nothing_resolvable(tmp_path):
    # The finding cites an unresolvable ref, but the sealed records still ground the
    # trace — the finding merely contributes no 'authored reference' reason.
    root = _project(tmp_path, "# Finding\n\nLead.\n\n## D\nSee [rec: not-a-record].\n")
    trace = jd.evidence_trace(root)
    assert [t["subject"] for t in trace] == ["b_2021:c"]
    assert trace[0]["cited_by"] == []
    assert jd.TRACE_AUTHORED not in trace[0]["reasons"]
    assert jd.TRACE_JUDGED in trace[0]["reasons"]


def test_an_ungated_finding_adds_no_authored_reason_but_records_still_trace(tmp_path):
    # Gating still governs the AUTHORED layer: an ungated finding is not proved, so it
    # contributes no reason. The sealed records are unaffected and still trace.
    trace = jd.evidence_trace(_project(tmp_path, gated=False))
    assert [t["subject"] for t in trace] == ["b_2021:c"]
    assert all(jd.TRACE_AUTHORED not in t["reasons"] for t in trace)
    assert trace[0]["cited_by"] == []


def test_removing_the_finding_changes_only_the_authored_layer(tmp_path):
    # Acceptance: Layers 1-2 and the trace stand without a finding. derived_summary and
    # recorded_judgements read no finding, so they are identical; the trace keeps every
    # subject and incoming edge — only the authored-reference reason and cited_by drop.
    withf = _project(tmp_path / "withf")
    nof = _project(tmp_path / "nof", finding=None)
    assert jd.derived_summary(nof) == jd.derived_summary(withf)
    assert jd.recorded_judgements(nof) == jd.recorded_judgements(withf)
    tw, tn = jd.evidence_trace(withf), jd.evidence_trace(nof)
    assert [t["subject"] for t in tn] == [t["subject"] for t in tw]
    assert [t["incoming"] for t in tn] == [t["incoming"] for t in tw]
    assert all(t["cited_by"] == [] and jd.TRACE_AUTHORED not in t["reasons"] for t in tn)


def test_removing_an_assessment_changes_only_its_judgement_and_trace(tmp_path):
    # Acceptance: dropping one sealed record removes its judgement and its trace effect,
    # and nothing else. Here removing the faithfulness dispute leaves the subject traced
    # (other records still name it) but the incoming edge is no longer contested.
    root = _project(tmp_path)
    before = jd.evidence_trace(root)
    assert [r["id"] for r in before[0]["incoming"][0]["contested_by"]] == ["a-faith"]
    faith = root / "content" / "assessments" / "_records" / "a-faith.assess.json"
    faith.rename(faith.with_suffix(".parked"))          # move, never delete
    after = jd.evidence_trace(root)
    assert [t["subject"] for t in after] == [t["subject"] for t in before]
    assert after[0]["incoming"][0]["contested_by"] == []
    assert "a-faith" not in {r["id"] for r in jd.recorded_judgements(root)}


# ---- what the pack renders --------------------------------------------------

def _index(tmp_path, **kw):
    bjp.build_pack(_project(tmp_path, **kw), tmp_path / "pack")
    return (tmp_path / "pack" / "index.html").read_text(encoding="utf-8")


def test_the_first_screen_stacks_the_three_layers_with_focused_actions(tmp_path):
    index = _index(tmp_path)
    # DOM order: trust state -> derived -> judgements -> interpretation.
    assert (index.index('id="overview"') < index.index('id="derived"')
            < index.index('id="judgements"') < index.index('id="interpretation"'))
    # The authored lesson sits in the interpretation layer, not as a first-screen headline.
    assert "The lesson this case teaches, stated first." in index
    # The generic action label is gone; records carry a focused, anchored trace link.
    assert "Inspect the contested inference" not in index
    assert "Inspect judgement evidence" in index
    assert 'href="trace.html#' in index
    # The lead stops at the first heading: the detail is on the finding's own page.
    assert "The inference is contested" not in index


def test_a_finding_that_opens_with_a_heading_has_no_lead(tmp_path):
    # The protocol is one line: open with the lesson. A finding that opens with a section
    # heading has no lead, and the band must not promote its first section into one.
    index = _index(tmp_path, finding="# Finding\n\n## The question\nTwo sub-questions.\n"
                                     "\n## D\nSee [rec: a-faith].\n")
    assert "Two sub-questions." not in index
    assert 'href="finding.html"' in index


def test_every_trace_link_is_anchored_never_the_bare_page_top(tmp_path):
    # Acceptance: every action opens the RELEVANT trace anchor, not the page top. So the
    # bare `trace.html"` link never appears — only `trace.html#<subject>`.
    index = _index(tmp_path, finding="# Finding\n\nLead.\n\n## D\nSee [rec: nope].\n")
    assert "Lead." in index
    assert 'href="trace.html"' not in index
    assert 'href="trace.html#' in index


def test_both_surfaces_quote_the_same_lead(tmp_path):
    # The hero and the pack's first screen once read the finding by different rules, so
    # one authored finding produced two different "leads".
    root = _project(tmp_path)
    lead = jd.finding_lead(root / "content" / "finding.md")
    assert lead == "The lesson this case teaches, stated first."
    assert jd.graphview_payload(root)["case"]["verdict"] == lead
    bjp.build_pack(root, tmp_path / "pack")
    assert lead in (tmp_path / "pack" / "index.html").read_text(encoding="utf-8")


def test_the_lead_is_plain_text(tmp_path):
    # It renders escaped, so markdown left in would show as literal punctuation.
    root = _project(tmp_path, "# F\n\nA `code` and **bold** and [[link]] lead.\n")
    assert jd.finding_lead(root / "content" / "finding.md") == \
        "A code and bold and link lead."


def test_the_lead_carries_no_record_addressing(tmp_path):
    # A lead may cite its judgement — the first screen must not show the machinery. There
    # is nowhere to land a link in one sentence, so the marker goes and the sentence reads.
    root = _project(tmp_path, "# F\n\nThe assurance defers its basis [rec: a-faith] "
                              "and the crux is marked [rec: b-rhetoric].\n")
    lead = jd.finding_lead(root / "content" / "finding.md")
    assert lead == "The assurance defers its basis and the crux is marked."
    bjp.build_pack(root, tmp_path / "pack")
    index = (tmp_path / "pack" / "index.html").read_text(encoding="utf-8")
    assert "[rec:" not in index


def test_a_record_reference_in_the_finding_links_to_its_row(tmp_path):
    # The marker is how a sentence names the judgement it rests on; raw, it names one the
    # reader cannot reach.
    root = _project(tmp_path)
    bjp.build_pack(root, tmp_path / "pack")
    finding = (tmp_path / "pack" / "finding.html").read_text(encoding="utf-8")
    assert "[rec:" not in finding
    assert 'href="assessments.html#rec-a-faith"' in finding
    rows = (tmp_path / "pack" / "assessments.html").read_text(encoding="utf-8")
    assert 'id="rec-a-faith"' in rows


def test_a_ledger_pages_record_reference_links_up_a_directory(tmp_path):
    # Ledger pages are written one level down, so their marker links need the prefix too.
    root = _project(tmp_path)
    bjp.build_pack(root, tmp_path / "pack")
    page = (tmp_path / "pack" / "ledgers" / "a_2020.html").read_text(encoding="utf-8")
    assert "[rec:" not in page
    assert 'href="../assessments.html#rec-a-supports-c"' in page


def test_a_claim_nothing_targets_states_that_rather_than_counting_to_zero(tmp_path):
    # A rhetorical flag names a claim nobody argued over, so an untargeted subject is
    # normal, not a hole. "(0)" over an empty list is a heading that promises a list and
    # withholds it — the reader should be told the fact.
    root = _project(tmp_path, "# F\n\nLead.\n\n## D\nFlagged [rec: b-rhetoric].\n")
    # b-rhetoric's subject is b_2021:c, which the fixture's edge DOES target; retarget the
    # citation at a claim with nothing aimed at it.
    claims = root / "literature" / "verified_claims"
    assess = root / "content" / "assessments"
    rec = ar.build_record(kind="rhetorical", rec_id="lone-flag", subject="a_2020:p",
                          grounding=["a_2020:p"], span="the grounding quote",
                          assessed_date="20260101", claims_dir=claims)
    ar.write_record(rec, assess_dir=assess)
    (root / "content" / "finding.md").write_text(
        "# F\n\nLead.\n\n## D\nFlagged [rec: lone-flag].\n", encoding="utf-8")
    trace = jd.evidence_trace(root)
    lone = next(t for t in trace if t["subject"] == "a_2020:p")
    assert lone["incoming"] == []
    bjp.build_pack(root, tmp_path / "pack")
    page = (tmp_path / "pack" / "trace.html").read_text(encoding="utf-8")
    assert "No incoming argument edges target this claim." in page
    assert "What is aimed at this claim (0)" not in page
    # the claim itself is still fully rendered
    assert "the grounding quote" in page


def test_the_trace_page_shows_the_quote_dispute_span_and_boundary(tmp_path):
    bjp.build_pack(_project(tmp_path), tmp_path / "pack")
    trace = (tmp_path / "pack" / "trace.html").read_text(encoding="utf-8")
    assert "we do not believe it is plausible" in trace
    assert "the grounding quote" in trace
    assert "challenged span" in trace and "disputed" in trace
    assert "Ledger displays these judgements" in trace and "settle them" in trace


def test_a_case_without_a_finding_says_so_but_still_ships_the_records_trace(tmp_path):
    # An absent finding is a fact, not a hole to fill with generated prose — but Layers
    # 1-2 and the trace stand on their own, grounded on the sealed records.
    index = _index(tmp_path, finding=None)
    assert "No case-level interpretation has been authored" in index
    trace_path = tmp_path / "pack" / "trace.html"
    assert trace_path.is_file()
    assert "we do not believe it is plausible" in trace_path.read_text(encoding="utf-8")


def test_an_unresolvable_reference_cannot_reach_the_page(tmp_path):
    # Validation precedes presentation: the gate rejects this address, so the renderer
    # must have no way to draw a trace from it. The records still ship their own trace;
    # the rejected address appears nowhere.
    root = _project(tmp_path, "# Finding\n\nLead.\n\n## D\n[rec: banal-bat-relative]\n")
    bjp.build_pack(root, tmp_path / "pack")
    index = (tmp_path / "pack" / "index.html").read_text(encoding="utf-8")
    assert "banal-bat-relative" not in index
    trace_path = tmp_path / "pack" / "trace.html"
    assert trace_path.is_file()
    assert "banal-bat-relative" not in trace_path.read_text(encoding="utf-8")
