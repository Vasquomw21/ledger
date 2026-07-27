# Tests for the semantic-health check. semantic_staleness_problems() returns the
# problem strings (missing / unset / stale report); main() decides severity from
# the semantic_health posture (warn nudges, required blocks — see
# test_ledger_doctor.py). Fixtures in tmp_path; corpus-free.
import ledger_doctor as ld

CONFIG = {"skin_rules_file": "content/_ledger/skin_rules.md"}


def _health(tmp_path, body):
    d = tmp_path / "content" / "_ledger"
    d.mkdir(parents=True, exist_ok=True)
    (d / "semantic_health.md").write_text(body, encoding="utf-8")
    return tmp_path


def test_missing_report_is_a_problem(tmp_path):
    problems = ld.semantic_staleness_problems(tmp_path, CONFIG)
    assert any("semantic_health.md" in p for p in problems)


def test_unset_last_review_is_a_problem(tmp_path):
    _health(tmp_path, "---\nlast_review: never\n---\n")
    problems = ld.semantic_staleness_problems(tmp_path, CONFIG)
    assert any("last_review not set" in p for p in problems)


def test_stale_review_is_a_problem(tmp_path):
    _health(tmp_path, "---\nlast_review: 20250101\n---\n")
    problems = ld.semantic_staleness_problems(tmp_path, CONFIG, today="20260101")
    assert any("last reviewed 20250101" in p for p in problems)


def test_fresh_review_is_clean(tmp_path):
    _health(tmp_path, "---\nlast_review: 20251220\n---\n")
    assert ld.semantic_staleness_problems(tmp_path, CONFIG, today="20260101") == []


def test_max_age_override(tmp_path):
    # A tighter window via config makes a 30-day-old review stale.
    cfg = {**CONFIG, "semantic_max_age_days": "14"}
    _health(tmp_path, "---\nlast_review: 20251202\n---\n")
    assert ld.semantic_staleness_problems(tmp_path, cfg, today="20260101") != []
