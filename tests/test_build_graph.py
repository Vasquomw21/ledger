# Tests for the derived graph emitter (corpus-free). Checks expected
# nodes/edges, the derived superseded + double-count findings, and a non-empty
# Mermaid view; an empty graph yields empty arrays.
import assess_record as ar
import build_graph as bg
import check_assessment as ca


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


def test_edge_record_id_matches_the_gate_rule():
    # One definition used by the dashboard + analyzer, matching the assessment gate:
    # covered iff a kind:edge record matches target+grounding; an in-band [rec:] must
    # NAME that record (dangling/mismatched → not covered). Coverage is set-valued.
    edge_records = {("t:c", "s:g"): {"cov"}}
    base = {"type": "supports", "target": "t:c", "from_ledger": "s", "grounding": "g"}
    # matching record, no in-band rec → covered
    assert bg.edge_record_id({**base, "rec": None}, edge_records) == "cov"
    # in-band rec names the covering record → covered
    assert bg.edge_record_id({**base, "rec": "cov"}, edge_records) == "cov"
    # in-band rec names something else (dangling/mismatched) → NOT covered
    assert bg.edge_record_id({**base, "rec": "other"}, edge_records) is None
    # no matching record → uncovered; non-supports/rebuts → never covered
    assert bg.edge_record_id({**base, "rec": None}, {}) is None
    assert bg.edge_record_id({**base, "type": "depends-on", "rec": None}, edge_records) is None


def test_edge_record_id_accepts_competing_records():
    # Two records cover one edge; [rec:] naming either is coverage, no-rec pick is stable.
    edge_records = {("t:c", "s:g"): {"cov_a", "cov_b"}}
    base = {"type": "supports", "target": "t:c", "from_ledger": "s", "grounding": "g"}
    assert bg.edge_record_id({**base, "rec": "cov_b"}, edge_records) == "cov_b"
    assert bg.edge_record_id({**base, "rec": "cov_a"}, edge_records) == "cov_a"
    assert bg.edge_record_id({**base, "rec": None}, edge_records) == "cov_a"   # min, stable


def test_empty_graph_is_empty(tmp_path):
    claims = tmp_path / "verified_claims"
    claims.mkdir()
    g = bg.build_graph(claims, tmp_path / "inquiry.md", tmp_path / "assessments")
    assert g["nodes"] == [] and g["edges"] == []
    assert g["findings"]["double_count"] == [] and g["findings"]["superseded"] == []


def test_nodes_and_edges(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "a_2020", [("ca", "premise")],
            extra=["**Rebuts:** b_2021:cb (grounded by #ca)"])
    _ledger(claims, "b_2021", [("cb", "conclusion")])
    g = bg.build_graph(claims, tmp_path / "inquiry.md", tmp_path / "assessments")
    assert "a_2020:ca" in g["nodes"] and "b_2021:cb" in g["nodes"]
    assert g["edges"][0]["type"] == "rebuts"
    assert g["edges"][0]["target_resolved"] is True


def test_superseded_derived(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "new_2023", [("c", "the retraction")],
            extra=["**Supersedes:** old_2021:claim (grounded by #c)"])
    _ledger(claims, "old_2021", [("claim", "the retracted finding")])
    g = bg.build_graph(claims, tmp_path / "inquiry.md", tmp_path / "assessments")
    assert "old_2021:claim" in g["findings"]["superseded"]


def test_double_count_derived(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "a_2020", [("ca", "premise A")],
            extra=["**Supports:** c_2020:cc (grounded by #ca)",
                   "**Correlated-with:** b_2021:cb (grounded by #ca)"])
    _ledger(claims, "b_2021", [("cb", "premise B")],
            extra=["**Supports:** c_2020:cc (grounded by #cb)"])
    _ledger(claims, "c_2020", [("cc", "the conclusion")])
    g = bg.build_graph(claims, tmp_path / "inquiry.md", tmp_path / "assessments")
    # graph.json carries typed dicts now, not strings — the kind travels with the finding.
    dc = g["findings"]["double_count"]
    assert any({d["a"], d["b"]} == {"a_2020", "b_2021"} for d in dc)
    assert all(d["kind"] in ca.CORRELATION_KINDS for d in dc)


def test_assessments_in_graph(tmp_path):
    claims = tmp_path / "verified_claims"
    assess = tmp_path / "assessments"
    _ledger(claims, "andersen_2020", [("fcs", "we irrefutably show the site")])
    rec = ar.build_record("rhetorical", "r1", "andersen_2020:fcs",
                          ["andersen_2020:fcs"], "irrefutably show", "20260613",
                          claims_dir=claims)
    ar.write_record(rec, assess_dir=assess)
    g = bg.build_graph(claims, tmp_path / "inquiry.md", assess)
    assert g["assessments"][0]["id"] == "r1"
    assert "andersen_2020:fcs" in g["nodes"]


def test_reviews_exported(tmp_path):
    # A faithfulness-pass record's reviews link must survive into graph.json.
    claims = tmp_path / "verified_claims"
    assess = tmp_path / "assessments"
    _ledger(claims, "src", [("s", "the source")])
    _ledger(claims, "dst", [("d", "the target")])
    edge = ar.build_record("edge", "e1", "dst:d", ["src:s"], "", "20260615", claims_dir=claims)
    ar.write_record(edge, assess_dir=assess)
    passed = ar.build_record("faithfulness-pass", "e1-pass", "dst:d", ["src:s"], "",
                             "20260615", claims_dir=claims, reviews=["e1"])
    ar.write_record(passed, assess_dir=assess)
    g = bg.build_graph(claims, tmp_path / "inquiry.md", assess)
    pass_rec = next(a for a in g["assessments"] if a["id"] == "e1-pass")
    assert pass_rec["reviews"] == ["e1"]


def test_mermaid_nonempty(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "a_2020", [("ca", "premise")],
            extra=["**Rebuts:** b_2021:cb (grounded by #ca)"])
    _ledger(claims, "b_2021", [("cb", "conclusion")])
    g = bg.build_graph(claims, tmp_path / "inquiry.md", tmp_path / "assessments")
    mer = bg.to_mermaid(g)
    assert mer.startswith("graph TD")
    assert "rebuts" in mer
