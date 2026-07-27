# Drift guard for the canonical posture registry (tools/postures.py). The posture set
# was historically re-typed in several places and drifted (the operator dashboard once
# omitted units_layer/synthesis_claims; the judge pack omitted graph_coverage). These
# tests fail if any consumer — the dashboard, the pack checklist, or the config
# template — falls out of sync with the registry, so a newly added posture can't
# silently miss one.
from pathlib import Path

import build_judge_pack
import ledger_status
from check_citations import parse_config
from postures import POSTURE_KEYS

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_registry_keys_are_unique():
    assert len(POSTURE_KEYS) == len(set(POSTURE_KEYS))


def test_judge_pack_gate_keys_match_registry():
    assert {k for k, _label in build_judge_pack.GATE_KEYS} == set(POSTURE_KEYS)


def test_status_dashboard_enumerates_every_posture():
    report = "\n".join(ledger_status.build_report(REPO_ROOT))
    missing = [k for k in POSTURE_KEYS if k not in report]
    assert missing == [], f"ledger_status omits posture(s): {missing}"


def test_config_template_declares_every_posture():
    config = parse_config(REPO_ROOT / "ledger.config.md")
    missing = [k for k in POSTURE_KEYS if k not in config]
    assert missing == [], f"ledger.config.md template omits posture(s): {missing}"
