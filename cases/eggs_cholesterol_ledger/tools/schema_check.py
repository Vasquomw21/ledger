# === SCRIPT: Dependency-free JSON-Schema-subset validator ===
# Shared by the interchange tests and the assessment gate, so the published schemas in
# spec/ and the records they describe cannot drift. Supports the subset our schemas use:
# type / enum / required / properties / items / pattern / additionalProperties:false.
from __future__ import annotations

import json
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = REPO_ROOT / "spec" / "schemas"


def is_type(value, t: str) -> bool:
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


def validate(instance, schema, path: str = "$") -> list[str]:
    """Conformance errors for the subset our schemas use ([] = valid)."""
    errs: list[str] = []
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(is_type(instance, tt) for tt in types):
            return [f"{path}: expected {types}, got {type(instance).__name__}"]
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: {instance!r} not in enum {schema['enum']}")
    if "pattern" in schema and isinstance(instance, str) \
            and not re.search(schema["pattern"], instance):
        errs.append(f"{path}: {instance!r} fails pattern {schema['pattern']}")
    if is_type(instance, "object") and ("properties" in schema or "required" in schema):
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
                errs += validate(instance[key], sub, f"{path}.{key}")
    if is_type(instance, "array") and "items" in schema:
        for i, item in enumerate(instance):
            errs += validate(item, schema["items"], f"{path}[{i}]")
    return errs


def load_schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
