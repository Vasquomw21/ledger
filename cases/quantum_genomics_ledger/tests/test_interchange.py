# Tests for the tool-independent interchange spec (spec/). No third-party dep: a
# tiny JSON-Schema-subset validator (type/enum/required/properties/items/pattern/
# additionalProperties:false) checks that the published schemas, the bundled
# examples, AND the kit's own emitters (assess_record, build_graph) all agree — so
# the contract in spec/ and the implementation cannot silently drift.
import json
import re
from pathlib import Path

import assess_record as ar
import build_graph as bg

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "spec"
SCHEMAS = SPEC / "schemas"


# --- a minimal JSON Schema (subset) validator -----------------------------

def _validate(instance, schema, path="$"):
    """Return a list of conformance errors. Supports the subset our schemas use."""
    errs = []
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_is_type(instance, tt) for tt in types):
            return [f"{path}: expected {types}, got {type(instance).__name__}"]
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: {instance!r} not in enum {schema['enum']}")
    if "pattern" in schema and isinstance(instance, str) \
            and not re.search(schema["pattern"], instance):
        errs.append(f"{path}: {instance!r} fails pattern {schema['pattern']}")
    if _is_type(instance, "object") and ("properties" in schema or "required" in schema):
        for req in schema.get("required", []):
            if req not in instance:
                errs.append(f"{path}: missing required '{req}'")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in props:
                    errs.append(f"{path}: unexpected property '{key}'")
        for key, sub in props.items():
            if key in instance:
                errs += _validate(instance[key], sub, f"{path}.{key}")
    if _is_type(instance, "array") and "items" in schema:
        for i, item in enumerate(instance):
            errs += _validate(item, schema["items"], f"{path}[{i}]")
    return errs


def _is_type(value, t):
    if t == "null":
        return value is None
    if t == "string":
        return isinstance(value, str)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "array":
        return isinstance(value, list)
    if t == "object":
        return isinstance(value, dict)
    return False


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
