# Layers 2 and 3 of the shared trust model. Layer 2 (recorded_judgements) exposes the
# sealed records relevant-first, labels each by its ROLE not its correctness, and reports
# integrity as a fact about the seal. Layer 3 (authored_interpretation) reads provenance
# from the finding's OWN frontmatter, never git, and reports an absent author or an absent
# finding as absent. These pin that no layer converts a seal into a correctness claim.
import json

import assess_record as ar
import judge_dashboard as jd


def _ledger(claims_dir, key, slug, quote, *, extra=()):
    claims_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", 'paper: "X"', "---", "",
             "## Claim 1: summary", "", f'> "{quote}"', "",
             f"**ID:** {slug}", "**Location:** Section 1", *extra, ""]
    (claims_dir / f"{key}.md").write_text("\n".join(lines), encoding="utf-8")


def _project(tmp_path, *, finding=None):
    claims = tmp_path / "literature" / "verified_claims"
    content = tmp_path / "content"
    assess = content / "assessments"
    (assess / "_records").mkdir(parents=True)
    (content / "inquiry.md").write_text("# Inquiry\n", encoding="utf-8")
    # a correlated pair supporting one claim, plus an unrelated claim + rhetorical flag
    _ledger(claims, "chen_2021", "whi", "WHI finding", extra=[
        "**Supports:** zhao_2022:harmful (grounded by #whi)",
        "**Correlated-with:** sun_2021:whi (grounded by #whi) "
        "[kind: exact-cohort-reuse; both identify the WHI cohort]"])
    _ledger(claims, "sun_2021", "whi", "WHI finding too",
            extra=["**Supports:** zhao_2022:harmful (grounded by #whi)"])
    _ledger(claims, "zhao_2022", "harmful", "eggs are harmful")
    _ledger(claims, "off_topic", "aside", "an unrelated claim")

    def record(**kw):
        rec = ar.build_record(claims_dir=claims, **kw)
        ar.write_record(rec, assess_dir=assess)
        return rec

    # relevant: seals the WHI pair the warning names
    record(kind="correlated-with", rec_id="whi-double-count", subject="chen_2021:whi",
           grounding=["chen_2021:whi", "sun_2021:whi"], span="", assessed_date="20260101")
    # not relevant: a flag on the off-topic claim
    record(kind="rhetorical", rec_id="aside-flag", subject="off_topic:aside",
           grounding=["off_topic:aside"], span="unrelated", assessed_date="20260102")
    if finding is not None:
        (content / "finding.md").write_text(finding, encoding="utf-8")
    return tmp_path


# ---- Layer 2: recorded judgements -------------------------------------------

def test_records_relevant_to_a_warning_sort_first(tmp_path):
    recs = jd.recorded_judgements(_project(tmp_path))
    assert recs[0]["id"] == "whi-double-count" and recs[0]["relevant"] is True
    assert recs[1]["id"] == "aside-flag" and recs[1]["relevant"] is False


def test_a_records_label_states_its_role_never_its_correctness(tmp_path):
    claims = tmp_path / "literature" / "verified_claims"
    assess = tmp_path / "content" / "assessments"
    (assess / "_records").mkdir(parents=True)
    _ledger(claims, "a_2020", "p", "the source")
    _ledger(claims, "b_2021", "c", "the target")

    def record(**kw):
        ar.write_record(ar.build_record(claims_dir=claims, **kw), assess_dir=assess)

    record(kind="edge", rec_id="e1", subject="b_2021:c", grounding=["a_2020:p"],
           span="", assessed_date="20260101")
    record(kind="faithfulness", rec_id="f1", subject="b_2021:c", grounding=["a_2020:p"],
           span="the source", assessed_date="20260101", disputes=["e1"])
    record(kind="faithfulness-pass", rec_id="p1", subject="b_2021:c",
           grounding=["a_2020:p"], span="", assessed_date="20260101", reviews=["e1"])
    label = {r["id"]: r["label"] for r in jd.recorded_judgements(tmp_path)}
    assert label == {"e1": "sealed record", "f1": "disputed", "p1": "reviewed — held"}
    # none of the labels asserts the judgement is right
    assert not ({"confirmed", "proved", "valid"} & set(label.values()))


def test_integrity_is_membership_in_the_validated_set(tmp_path):
    root = _project(tmp_path)
    # tamper a sealed record's body without resealing: its digest no longer matches
    park = root / "content" / "assessments" / "_records" / "aside-flag.assess.json"
    rec = json.loads(park.read_text(encoding="utf-8"))
    rec["span"] = "silently altered after sealing"
    park.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    integrity = {r["id"]: r["integrity"] for r in jd.recorded_judgements(root)}
    assert integrity["whi-double-count"] == "verified"
    assert integrity["aside-flag"] == "unverified"


def test_the_trace_anchor_matches_the_subject(tmp_path):
    recs = {r["id"]: r for r in jd.recorded_judgements(_project(tmp_path))}
    assert recs["whi-double-count"]["trace_anchor"] == jd.trace_anchor("chen_2021:whi")


# ---- Layer 3: authored interpretation ---------------------------------------

def test_an_absent_finding_is_reported_absent(tmp_path):
    interp = jd.authored_interpretation(_project(tmp_path, finding=None))
    assert interp == {"present": False, "lead": "", "author": "", "date": "",
                      "has_provenance": False}


def test_provenance_is_read_from_frontmatter_not_git(tmp_path):
    finding = ('---\nauthor: R. Curator\ndate: "20260615"\n---\n\n'
               "# F\n\nThe authored lesson.\n\n## D\nDetail.\n")
    interp = jd.authored_interpretation(_project(tmp_path, finding=finding))
    assert interp["present"] is True
    assert interp["author"] == "R. Curator" and interp["date"] == "20260615"
    assert interp["has_provenance"] is True
    assert interp["lead"] == "The authored lesson."


def test_a_finding_without_provenance_is_marked_unrecorded(tmp_path):
    interp = jd.authored_interpretation(
        _project(tmp_path, finding="# F\n\nA lesson with no author metadata.\n"))
    assert interp["present"] is True
    assert interp["author"] == "" and interp["date"] == ""
    assert interp["has_provenance"] is False
