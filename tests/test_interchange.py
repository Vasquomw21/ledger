# Tests for the tool-independent interchange spec (spec/). No third-party dep: a
# tiny JSON-Schema-subset validator (type/enum/required/properties/items/pattern/
# additionalProperties:false) checks that the published schemas, the bundled
# examples, AND the kit's own emitters (assess_record, build_graph) all agree — so
# the contract in spec/ and the implementation cannot silently drift.
import json
from pathlib import Path

import assess_record as ar
import build_graph as bg
import claim_graph as cg
from schema_check import validate as _validate   # the one shared subset validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "spec"
SCHEMAS = SPEC / "schemas"


def _schema(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


# --- the schemas themselves are valid JSON --------------------------------

def test_schemas_are_valid_json():
    for s in SCHEMAS.glob("*.schema.json"):
        json.loads(s.read_text(encoding="utf-8"))   # raises on malformed


# --- the validator catches a real violation (self-test) -------------------

def test_validator_rejects_bad_instance():
    schema = _schema("assessment_record.schema.json")
    bad = {"kind": "not-a-kind", "id": "x"}          # bad enum + missing required
    errs = _validate(bad, schema)
    assert any("enum" in e for e in errs)
    assert any("missing required" in e for e in errs)


# --- bundled examples conform ---------------------------------------------

def test_example_assessment_record_conforms():
    inst = json.loads((SPEC / "examples" / "assessment_record.example.json")
                      .read_text(encoding="utf-8"))
    assert _validate(inst, _schema("assessment_record.schema.json")) == []


def test_example_graph_conforms():
    inst = json.loads((SPEC / "examples" / "graph.example.json")
                      .read_text(encoding="utf-8"))
    assert _validate(inst, _schema("graph.schema.json")) == []


# --- the kit's own emitters produce conformant output ---------------------

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


def test_assess_record_emitter_conforms(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "a_2020", [("c", "a verbatim quote here")])
    rec = ar.build_record("rhetorical", "r1", "a_2020:c", ["a_2020:c"],
                          "verbatim quote", "20260614", claims_dir=claims)
    assert _validate(rec, _schema("assessment_record.schema.json")) == []


def test_build_graph_emitter_conforms(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "a_2020", [("ca", "premise A")],
            extra=["**Supports:** b_2021:cb (grounded by #ca) [rec: j1]"])
    _ledger(claims, "b_2021", [("cb", "the conclusion")])
    content = tmp_path / "content"
    content.mkdir()
    graph = bg.build_graph(claims, content / "inquiry.md", content / "assessments")
    assert _validate(graph, _schema("graph.schema.json")) == []


# --- taxonomy parity: code registries == published schema enums -----------

def _enum_for(node, prop):
    """The enum list declared for a property named `prop`, anywhere in the schema."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == prop and isinstance(v, dict) and "enum" in v:
                return v["enum"]
            found = _enum_for(v, prop)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _enum_for(item, prop)
            if found is not None:
                return found
    return None


def test_edge_type_registry_matches_schema_enum():
    schema_enum = _enum_for(_schema("graph.schema.json"), "type")
    assert set(cg.EDGE_LABELS) == set(schema_enum)


def test_assess_kind_registry_matches_schema_enums():
    assert set(ar.ASSESS_KINDS) == set(_enum_for(_schema("assessment_record.schema.json"), "kind"))
    assert set(ar.ASSESS_KINDS) == set(_enum_for(_schema("graph.schema.json"), "kind"))
