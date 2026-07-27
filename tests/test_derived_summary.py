# Layer 1 — "What Ledger derived from committed records". Deterministic, and each fact
# keeps its provenance: mechanically-computed (the warning, the counts), author-declared
# (the correlation kind + basis), assessment present/absent (a sealed record backs it or
# not). These pin that the summary reads NO finding prose and never asserts truth.
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
    # two typed correlated supporters of the same harmful claim: one sealed, one not
    _ledger(claims, "chen_2021", "whi", "WHI finding", extra=[
        "**Supports:** zhao_2022:harmful (grounded by #whi)",
        "**Correlated-with:** sun_2021:whi (grounded by #whi) "
        "[kind: exact-cohort-reuse; both identify the WHI cohort]"])
    _ledger(claims, "sun_2021", "whi", "WHI finding too",
            extra=["**Supports:** zhao_2022:harmful (grounded by #whi)"])
    _ledger(claims, "dehghan_2020", "pool", "pooled null",
            extra=["**Supports:** drouin_2020:null (grounded by #pool)",
                   "**Correlated-with:** rong_2013:pool (grounded by #pool) "
                   "[kind: overlapping-pools; overlapping cohorts of the same design]"])
    _ledger(claims, "rong_2013", "pool", "pooled null too",
            extra=["**Supports:** drouin_2020:null (grounded by #pool)"])
    _ledger(claims, "zhao_2022", "harmful", "eggs are harmful")
    _ledger(claims, "drouin_2020", "null", "no association")
    # seal only the WHI pair
    rec = ar.build_record("correlated-with", "whi-double-count", "chen_2021:whi",
                          ["chen_2021:whi", "sun_2021:whi"], "", "20260101", claims_dir=claims)
    ar.write_record(rec, assess_dir=assess)
    if finding is not None:
        (content / "finding.md").write_text(finding, encoding="utf-8")
    return tmp_path


def test_the_summary_types_each_warning_and_keeps_the_basis(tmp_path):
    s = jd.derived_summary(_project(tmp_path))
    by_pair = {frozenset((w["a"], w["b"])): w for w in s["warnings"]}
    whi = by_pair[frozenset(("chen_2021", "sun_2021"))]
    assert whi["kind"] == "exact-cohort-reuse"
    assert whi["kind_label"] == "exact cohort reuse"
    assert whi["basis"] == "both identify the WHI cohort"


def test_the_sealed_split_is_derived_not_declared(tmp_path):
    s = jd.derived_summary(_project(tmp_path))
    status = {frozenset((w["a"], w["b"])): w["judgement_status"] for w in s["warnings"]}
    assert status[frozenset(("chen_2021", "sun_2021"))] == "sealed assessment present"
    assert status[frozenset(("dehghan_2020", "rong_2013"))] == \
        "declared only; no sealed assessment"


def test_principal_claims_carry_incoming_counts(tmp_path):
    s = jd.derived_summary(_project(tmp_path))
    counts = {p["claim"]: p["incoming"] for p in s["principal_claims"]}
    assert counts["zhao_2022:harmful"] == 2
    assert counts["drouin_2020:null"] == 2


def test_aptness_counts_reviewed_over_total_edges(tmp_path):
    s = jd.derived_summary(_project(tmp_path))
    # four supports edges, none carry a sealed edge record here
    assert s["aptness"]["total"] == 4
    assert s["aptness"]["reviewed"] == 0


def test_the_summary_is_identical_with_and_without_a_finding(tmp_path):
    # Layer 1 must not read authored prose: adding an interpretation cannot change it.
    bare = jd.derived_summary(_project(tmp_path / "bare"))
    withf = jd.derived_summary(_project(tmp_path / "withf",
                                        finding="# F\n\nA lesson.\n\n## D\nSee stuff.\n"))
    assert bare["warnings"] == withf["warnings"]
    assert bare["principal_claims"] == withf["principal_claims"]
    assert bare["aptness"] == withf["aptness"]


def test_no_warning_when_supporters_are_not_declared_correlated(tmp_path):
    claims = tmp_path / "literature" / "verified_claims"
    content = tmp_path / "content"
    (content / "assessments" / "_records").mkdir(parents=True)
    (content / "inquiry.md").write_text("# Inquiry\n", encoding="utf-8")
    _ledger(claims, "a_2020", "pa", "A", extra=["**Supports:** c_2020:cc (grounded by #pa)"])
    _ledger(claims, "b_2021", "pb", "B", extra=["**Supports:** c_2020:cc (grounded by #pb)"])
    _ledger(claims, "c_2020", "cc", "conclusion")
    s = jd.derived_summary(tmp_path)
    assert s["warnings"] == []
    assert {p["claim"]: p["incoming"] for p in s["principal_claims"]}["c_2020:cc"] == 2
