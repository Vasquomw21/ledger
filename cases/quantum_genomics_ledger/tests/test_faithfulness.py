# Tests for the adversarial-faithfulness mechanism (corpus-free; tmp fixtures).
# A faithfulness record is a sealed, quote-pinned, same-subject CONTEST of an edge
# aptness record: it argues the grounding quote does not warrant the inference.
# Covers: a valid faithfulness record passes; empty-disputes is caught; a span not
# in the grounding quote is caught; a full required-mode run with an edge record +
# its faithfulness dispute passes; and the read-only probe's worklist accounting.
import assess_record as ar
import check_assessment as ca
import faithfulness_probe as fp


def _ledger(claims_dir, key, claims, *, extra=()):
    claims_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", 'paper: "X"', "---", ""]
    for i, (slug, quote) in enumerate(claims, start=1):
        lines += [f"## Claim {i}: summary", "", f'> "{quote}"', "",
                  f"**ID:** {slug}", "**Location:** Section 1"]
        if i == 1:
            lines += list(extra)
        lines.append("")
    (claims_dir / f"{key}.md").write_text("\n".join(lines), encoding="utf-8")


def _dirs(tmp_path):
    return tmp_path / "verified_claims", tmp_path / "assessments"


def _edge_and_faithfulness(claims, assess):
    """An apt edge record (e1) and a faithfulness record disputing it, both on the
    same subject (the target claim). The grounding quote overreaches its inference."""
    # andersen's "can arise by a natural process" grounds a Rebuts of segreto's
    # engineering inference; the faithfulness dispute: possibility != refutation.
    _ledger(claims, "andersen_2020",
            [("natural", "the features can arise by a natural evolutionary process")],
            extra=["**Rebuts:** segreto_2021:engineering "
                   "(grounded by #natural) [rec: e1]"])
    _ledger(claims, "segreto_2021", [("engineering", "the site implies engineering")])
    edge_rec = ar.build_record("edge", "e1", "segreto_2021:engineering",
                               ["andersen_2020:natural"], "", "20260614",
                               claims_dir=claims)
    ar.write_record(edge_rec, assess_dir=assess)
    faith = ar.build_record("faithfulness", "e1-faithfulness",
                            "segreto_2021:engineering", ["andersen_2020:natural"],
                            "can arise by a natural evolutionary process", "20260614",
                            claims_dir=claims, disputes=["e1"])
    ar.write_record(faith, assess_dir=assess)
    return edge_rec, faith


# --- a valid faithfulness record passes -----------------------------------

def test_valid_faithfulness_record_passes(tmp_path):
    claims, assess = _dirs(tmp_path)
    _edge_and_faithfulness(claims, assess)
    faith = ar.build_record("faithfulness", "e1-faithfulness",
                            "segreto_2021:engineering", ["andersen_2020:natural"],
                            "can arise by a natural evolutionary process", "20260614",
                            claims_dir=claims, disputes=["e1"])
    assert ca.record_problems(faith, claims) == []


# --- a faithfulness record must contest something -------------------------

def test_faithfulness_empty_disputes_caught(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020",
            [("natural", "can arise by a natural evolutionary process")])
    faith = ar.build_record("faithfulness", "f0", "andersen_2020:natural",
                            ["andersen_2020:natural"], "natural evolutionary process",
                            "20260614", claims_dir=claims, disputes=[])
    problems = ca.record_problems(faith, claims)
    assert any("must dispute at least one record" in p for p in problems)


# --- the challenged span must be a substring of the grounding quote --------

def test_faithfulness_span_not_substring_caught(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("natural", "a measured, hedged statement")])
    faith = ar.build_record("faithfulness", "f1", "andersen_2020:natural",
                            ["andersen_2020:natural"], "irrefutably proves it",
                            "20260614", claims_dir=claims, disputes=["x"])
    problems = ca.record_problems(faith, claims)
    assert any("faithfulness span is not a substring" in p for p in problems)


# --- full required run: edge record + its faithfulness dispute ------------

def test_edge_and_dispute_pass_under_required(tmp_path, monkeypatch):
    claims, assess = _dirs(tmp_path)
    _edge_and_faithfulness(claims, assess)
    argv = ["check_assessment.py", "--claims-dir", str(claims),
            "--assess-dir", str(assess), "--assessment", "required",
            "--edge-assessments", "required"]
    monkeypatch.setattr("sys.argv", argv)
    assert ca.main() == 0   # edge has [rec: e1]; faithfulness disputes it, same subject


def test_faithfulness_dispute_wrong_subject_caught(tmp_path):
    claims, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("natural", "can arise by a natural process")])
    _ledger(claims, "segreto_2021", [("engineering", "implies engineering")])
    edge = ar.build_record("edge", "e1", "segreto_2021:engineering",
                           ["andersen_2020:natural"], "", "20260614", claims_dir=claims)
    # faithfulness names a DIFFERENT subject than the edge record it disputes.
    faith = ar.build_record("faithfulness", "f1", "andersen_2020:natural",
                            ["andersen_2020:natural"], "natural process", "20260614",
                            claims_dir=claims, disputes=["e1"])
    problems = ca.dispute_problems({"e1": edge, "f1": faith})
    assert any("different" in p for p in problems)


# --- the read-only probe --------------------------------------------------

def test_probe_counts_reviewed_and_unreviewed(tmp_path, capsys):
    claims, assess = _dirs(tmp_path)
    _edge_and_faithfulness(claims, assess)              # e1 is disputed (reviewed)
    rc = fp.probe(claims, assess)
    out = capsys.readouterr().out
    assert rc == 0
    assert "REVIEWED" in out and "e1-faithfulness".rsplit("-", 1)[0] in out
    assert "1 reviewed" in out


def test_probe_disputed_record_ids(tmp_path):
    claims, assess = _dirs(tmp_path)
    _edge_and_faithfulness(claims, assess)
    assert fp.disputed_record_ids(assess / ar.RECORDS_DIR_NAME) == {"e1"}


def test_probe_empty_corpus(tmp_path, capsys):
    claims, assess = _dirs(tmp_path)
    claims.mkdir(parents=True)
    assert fp.probe(claims, assess) == 0
    assert "nothing to adversarially review" in capsys.readouterr().out
