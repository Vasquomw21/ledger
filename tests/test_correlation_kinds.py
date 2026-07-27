# The author-declared correlation-kinds surface. A kind is authored epistemic metadata, so
# it lives in a committed, validated file — NOT in a stamped ledger body, where the edit
# would restale the quote stamp, run record and any bound assessment. These pin that the
# resolver reads the kind from the file (basis still from the ledger), an unclassified pair
# defaults to other-declared-dependence, the validator enforces every rule, and classifying
# a pair never changes whether a sealed correlation assessment exists.
import assess_record as ar
import check_assessment as ca

FRONT = "---\nauthored_by: T. Author\nlast_updated: 20260716\nstatus: active\n---\n\n"


def _ledger(claims_dir, key, slug, quote, *, extra=()):
    claims_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", 'paper: "X"', "---", "", "## Claim 1: summary", "",
             f'> "{quote}"', "", f"**ID:** {slug}", "**Location:** Section 1", *extra, ""]
    (claims_dir / f"{key}.md").write_text("\n".join(lines), encoding="utf-8")


def _pair_project(tmp_path, kinds_md=None, *, seal=False):
    claims = tmp_path / "literature" / "verified_claims"
    content = tmp_path / "content"
    (content / "assessments" / "_records").mkdir(parents=True)
    _ledger(claims, "a_2020", "pa", "premise A", extra=[
        "**Supports:** c_2020:cc (grounded by #pa)",
        "**Correlated-with:** b_2021:pb (grounded by #pa) [both pool the same cohort]"])
    _ledger(claims, "b_2021", "pb", "premise B",
            extra=["**Supports:** c_2020:cc (grounded by #pb)"])
    _ledger(claims, "c_2020", "cc", "the conclusion")
    if kinds_md is not None:
        (content / "correlation_kinds.md").write_text(kinds_md, encoding="utf-8")
    if seal:
        rec = ar.build_record("correlated-with", "ab-corr", "a_2020:pa",
                              ["a_2020:pa", "b_2021:pb"], "", "20260101", claims_dir=claims)
        ar.write_record(rec, assess_dir=content / "assessments")
    return claims, content


def _kinds_md(pair, kind, front=FRONT):
    return f"{front}# Correlation kinds\n\n## {pair}\n- kind: {kind}\n"


# ---- the resolver reads the file, not the ledger body -----------------------

def test_the_kind_comes_from_the_file_and_the_basis_from_the_ledger(tmp_path):
    claims, content = _pair_project(
        tmp_path, _kinds_md("a_2020 ↔ b_2021", "overlapping-pools"))
    kinds = ca.load_correlation_kinds(content)[0]
    f = ca.double_count_findings(claims, kinds=kinds)[0]
    assert f.kind == "overlapping-pools"                 # authored in the file
    assert f.basis == "both pool the same cohort"        # still the ledger annotation


def test_an_unclassified_pair_defaults_to_other_declared_dependence(tmp_path):
    claims, content = _pair_project(tmp_path)            # no correlation_kinds.md
    kinds = ca.load_correlation_kinds(content)[0]
    assert ca.double_count_findings(claims, kinds=kinds)[0].kind == \
        "other-declared-dependence"


def test_pair_identity_is_unordered(tmp_path):
    claims, content = _pair_project(
        tmp_path, _kinds_md("b_2021 ↔ a_2020", "exact-cohort-reuse"))   # reversed
    kinds = ca.load_correlation_kinds(content)[0]
    assert ca.double_count_findings(claims, kinds=kinds)[0].kind == "exact-cohort-reuse"


# ---- the validator enforces every rule --------------------------------------

def test_a_valid_file_has_no_problems(tmp_path):
    claims, content = _pair_project(tmp_path, _kinds_md("a_2020 ↔ b_2021", "shared-evidence"))
    assert ca.correlation_kinds_problems(content, claims) == []


def test_an_orphan_classification_is_caught(tmp_path):
    claims, content = _pair_project(tmp_path, _kinds_md("a_2020 ↔ zz_9999", "shared-evidence"))
    assert any("orphan" in p for p in ca.correlation_kinds_problems(content, claims))


def test_a_duplicate_unordered_pair_is_caught(tmp_path):
    md = (_kinds_md("a_2020 ↔ b_2021", "shared-evidence")
          + "\n## b_2021 ↔ a_2020\n- kind: overlapping-pools\n")
    claims, content = _pair_project(tmp_path, md)
    assert any("duplicate" in p for p in ca.correlation_kinds_problems(content, claims))


def test_an_unknown_kind_is_caught(tmp_path):
    claims, content = _pair_project(tmp_path, _kinds_md("a_2020 ↔ b_2021", "made-up-kind"))
    assert any("unknown kind" in p for p in ca.correlation_kinds_problems(content, claims))


def test_missing_provenance_is_caught(tmp_path):
    md = _kinds_md("a_2020 ↔ b_2021", "shared-evidence", front="---\nstatus: active\n---\n\n")
    claims, content = _pair_project(tmp_path, md)
    probs = ca.correlation_kinds_problems(content, claims)
    assert any("authored_by" in p for p in probs)
    assert any("last_updated" in p for p in probs)


def test_an_absent_file_is_valid(tmp_path):
    claims, content = _pair_project(tmp_path)
    assert ca.correlation_kinds_problems(content, claims) == []


# ---- classifying never changes sealed/declared status -----------------------

def test_classification_is_orthogonal_to_sealed_status(tmp_path):
    claims, content = _pair_project(
        tmp_path, _kinds_md("a_2020 ↔ b_2021", "exact-cohort-reuse"), seal=True)
    records = content / "assessments" / "_records"
    with_kind = ca.double_count_findings(
        claims, records, ca.load_correlation_kinds(content)[0])[0]
    assert with_kind.kind == "exact-cohort-reuse" and with_kind.sealed_record == "ab-corr"
    # drop the classification: the seal is unchanged, only the kind falls back
    without = ca.double_count_findings(claims, records, {})[0]
    assert without.sealed_record == "ab-corr"
    assert without.kind == "other-declared-dependence"
