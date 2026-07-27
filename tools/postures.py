# === SCRIPT: Canonical posture registry — one source for the config postures ===
# Every gate posture declared in ledger.config.md appears here exactly once: its key,
# a human label (for judge-facing surfaces), and the value at which the gate BLOCKS.
# The operator dashboard (ledger_status) and the judge pack (build_judge_pack) both
# derive their posture enumerations from this list, so a newly added posture cannot
# silently miss a consumer. A drift-guard test (tests/test_postures.py) pins the two
# consumers + the ledger.config.md template to this set.
# INPUTS : none (a pure constant table).
# OUTPUTS: POSTURES + the derived key/label/block-value lookups.
from __future__ import annotations

# (key, label, block_value). block_value is the posture value at which the gate bites
# (all "required" except numeric_citations, which is off/warn/block).
POSTURES: list[tuple[str, str, str]] = [
    ("claim_ids",         "Stable claim IDs",            "required"),
    ("numeric_citations", "Numeric-citation gate",       "block"),
    ("provenance",        "Source provenance + stamps",  "required"),
    ("structure_layer",   "Claim-graph structure",       "required"),
    ("assessment_layer",  "Judgement records",           "required"),
    ("graph_coverage",    "Claim-graph coverage",        "required"),
    ("edge_assessments",  "Edge-aptness coverage",       "required"),
    ("selection_audit",   "Selection audit (Layer 2)",   "required"),
    ("source_flow",       "Source-flow trail (Layer 2)", "required"),
    ("units_layer",       "Unit-manifest binding",       "required"),
    ("synthesis_claims",  "Synthesis-claim anchoring",   "required"),
    ("semantic_health",   "Semantic-health review",      "required"),
    ("attestation",       "Signed run-records",          "required"),
]

POSTURE_KEYS: list[str] = [key for key, _label, _bv in POSTURES]
POSTURE_LABELS: dict[str, str] = {key: label for key, label, _bv in POSTURES}
POSTURE_BLOCK: dict[str, str] = {key: bv for key, _label, bv in POSTURES}
