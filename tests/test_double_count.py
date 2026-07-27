# The typed double-count: the exact-reuse-vs-overlapping-pool distinction must live in
# machine-readable data, not in a finding's prose. Before this, the reason a correlation
# fired was carried only in a free-text bracket the parser discarded and in hand-tuned
# finding.md wording — so a fresh user running Ledger got a flat "possible double-count"
# with none of the structure. These pin that the kind is read from the annotation and the
# sealed-vs-declared split is derived from the records.
import assess_record as ar
import check_assessment as ca


def _ledger(claims_dir, key, slug, quote, *, extra=()):
    claims_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", 'paper: "X"', "---", "",
             "## Claim 1: summary", "", f'> "{quote}"', "",
             f"**ID:** {slug}", "**Location:** Section 1", *extra, ""]
    (claims_dir / f"{key}.md").write_text("\n".join(lines), encoding="utf-8")


# ---- the annotation parser --------------------------------------------------

def test_each_kind_is_read_from_the_bracket():
    for slug, label in ca.CORRELATION_KINDS.items():
        kind, basis = ca.parse_correlation_cause(
            f"**Correlated-with:** b_2021:cb (grounded by #ca) [kind: {slug}; the basis]")
        assert kind == slug
        assert basis == "the basis"


def test_an_untyped_correlation_defaults_to_declared_dependence():
    # The default states only that a dependence was declared, never a stronger kind — an
    # existing free-text bracket must not be silently promoted to exact-cohort-reuse.
    kind, basis = ca.parse_correlation_cause(
        "**Correlated-with:** b_2021:cb (grounded by #ca) [shared observational cohorts]")
    assert kind == "other-declared-dependence"
    assert basis == "shared observational cohorts"


def test_an_unknown_kind_slug_is_not_accepted_as_a_kind():
    # A typo would otherwise become a silent, unrenderable kind. It falls back and the
    # mistyped text stays visible in the basis rather than masquerading as a real kind.
    kind, basis = ca.parse_correlation_cause(
        "**Correlated-with:** b:cb (grounded by #ca) [kind: exact-cohort-resue; oops]")
    assert kind == "other-declared-dependence"
    assert "exact-cohort-resue" in basis


def test_a_bracketless_annotation_is_declared_dependence():
    kind, basis = ca.parse_correlation_cause("**Correlated-with:** b_2021:cb (grounded by #ca)")
    assert kind == "other-declared-dependence" and basis == ""


# ---- the typed finding ------------------------------------------------------

def _pair(tmp_path, bracket, *, seal=False):
    claims = tmp_path / "verified_claims"
    assess = tmp_path / "assessments"
    _ledger(claims, "a_2020", "pa", "premise A", extra=[
        "**Supports:** c_2020:cc (grounded by #pa)",
        f"**Correlated-with:** b_2021:pb (grounded by #pa) {bracket}"])
    _ledger(claims, "b_2021", "pb", "premise B",
            extra=["**Supports:** c_2020:cc (grounded by #pb)"])
    _ledger(claims, "c_2020", "cc", "the contested conclusion")
    if seal:
        rec = ar.build_record("correlated-with", "ab-corr", "a_2020:pa",
                              ["a_2020:pa", "b_2021:pb"], "", "20260101", claims_dir=claims)
        ar.write_record(rec, assess_dir=assess)
    return claims, assess / ca.RECORDS_DIR_NAME


def test_the_finding_carries_the_declared_kind(tmp_path):
    claims, records = _pair(tmp_path, "[kind: exact-cohort-reuse; the WHI cohort]")
    findings = ca.double_count_findings(claims, records)
    assert len(findings) == 1
    f = findings[0]
    assert {f.a, f.b} == {"a_2020", "b_2021"}
    assert f.target == "c_2020:cc"
    assert f.kind == "exact-cohort-reuse" and f.kind_label == "exact cohort reuse"
    assert f.basis == "the WHI cohort"


def test_a_pair_with_a_correlated_record_is_sealed(tmp_path):
    claims, records = _pair(tmp_path, "[kind: exact-cohort-reuse; WHI]", seal=True)
    f = ca.double_count_findings(claims, records)[0]
    assert f.sealed_record == "ab-corr"


def test_a_pair_without_a_record_is_declared_only(tmp_path):
    claims, records = _pair(tmp_path, "[kind: overlapping-pools; same design]", seal=False)
    f = ca.double_count_findings(claims, records)[0]
    assert f.sealed_record is None
    assert f.kind == "overlapping-pools"


def test_no_records_dir_leaves_every_pair_declared_only(tmp_path):
    # A caller with only the ledgers still gets typed findings; sealed-ness needs records.
    claims, _ = _pair(tmp_path, "[kind: shared-evidence; same method]", seal=True)
    f = ca.double_count_findings(claims)[0]        # no records_dir
    assert f.kind == "shared-evidence" and f.sealed_record is None


def test_the_finding_serialises_to_plain_data(tmp_path):
    # graph.json carries these, so they must be JSON-shaped, not objects.
    claims, records = _pair(tmp_path, "[kind: exact-cohort-reuse; WHI]", seal=True)
    d = ca.double_count_findings(claims, records)[0].as_dict()
    assert d == {"a": "a_2020", "b": "b_2021", "target": "c_2020:cc",
                 "kind": "exact-cohort-reuse", "basis": "WHI", "sealed_record": "ab-corr"}
