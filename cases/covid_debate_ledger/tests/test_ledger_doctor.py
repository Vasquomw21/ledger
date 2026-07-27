# Tests for the project-health doctor. Fixtures are built in tmp_path; no
# fixture touches the git-ignored corpus, so the suite runs in CI.
import datetime as dt

import ledger_doctor as ld

PRISTINE_CONFIG = """\
project_name:        <e.g. water_policy_ke>
deliverable:         <thesis chapter | report | ...>
source_of_truth:     <markdown+quartz | docx+python>
the_reader:          <the bored reader ...>
source_types:        <peer-reviewed papers | ...>
gated_paths:         content/concept_notes/, content/literature_reviews/
skin_rules_file:     content/_ledger/skin_rules.md
"""

CONFIGURED_CONFIG = """\
project_name:        water_policy_ke
deliverable:         policy white paper
source_of_truth:     markdown+quartz
the_reader:          a busy minister AND a sceptical scientist
source_types:        legislation & gov reports
gated_paths:         content/concept_notes/, content/literature_reviews/
skin_rules_file:     content/_ledger/skin_rules.md
"""

# A fully-configured project that also adopted the strict postures a bootstrapped
# subject must take (claim refs required, numeric markers blocked, provenance
# required, structure + assessment layers required) — what --require-configured asserts.
STRICT_POSTURES = ("claim_ids:           required\n"
                   "numeric_citations:   block\n"
                   "provenance:          required\n"
                   "structure_layer:     required\n"
                   "assessment_layer:    required\n")
CONFIGURED_REQUIRED = CONFIGURED_CONFIG + STRICT_POSTURES

SKIN_EMPTY = "# skin\n\n_(empty — the bootstrap helper drafts this subject's rules here)_\n"
SKIN_WRITTEN = "# skin\n\n- **W1** dual-audience register\n- **W2** no-hype ladder\n"


def _project(tmp_path, config_text, skin_text, make_gated=True):
    """Build a tmp project: ledger.config.md + skin + (optionally) gated dirs.
    tmp_path may be a not-yet-created subdir (so one test can build several)."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "ledger.config.md").write_text(config_text, encoding="utf-8")
    skin = tmp_path / "content" / "_ledger" / "skin_rules.md"
    skin.parent.mkdir(parents=True)
    skin.write_text(skin_text, encoding="utf-8")
    if make_gated:
        (tmp_path / "content" / "concept_notes").mkdir(parents=True)
        (tmp_path / "content" / "literature_reviews").mkdir(parents=True)
    return tmp_path


def _diagnose(tmp_path):
    config = ld.parse_config(tmp_path / "ledger.config.md")
    return ld.diagnose(config, tmp_path)


# --- unit helpers ---

def test_is_placeholder():
    assert ld.is_placeholder("<e.g. foo>")
    assert ld.is_placeholder("   ")
    assert not ld.is_placeholder("water_policy_ke")


def test_skin_is_empty(tmp_path):
    empty = tmp_path / "a.md"
    empty.write_text(SKIN_EMPTY, encoding="utf-8")
    assert ld.skin_is_empty(empty)
    written = tmp_path / "b.md"
    written.write_text(SKIN_WRITTEN, encoding="utf-8")
    assert not ld.skin_is_empty(written)
    assert ld.skin_is_empty(tmp_path / "missing.md")


# --- the three states ---

def test_pristine(tmp_path):
    proj = _project(tmp_path, PRISTINE_CONFIG, SKIN_EMPTY)
    state, problems = _diagnose(proj)
    assert state == "pristine" and problems == []


def test_configured(tmp_path):
    proj = _project(tmp_path, CONFIGURED_CONFIG, SKIN_WRITTEN)
    state, problems = _diagnose(proj)
    assert state == "configured" and problems == []


def test_broken_mixed_placeholders(tmp_path):
    mixed = CONFIGURED_CONFIG.replace(
        "the_reader:          a busy minister AND a sceptical scientist",
        "the_reader:          <the bored reader ...>")
    proj = _project(tmp_path, mixed, SKIN_WRITTEN)
    state, problems = _diagnose(proj)
    assert state == "broken"
    assert any("the_reader" in p for p in problems)


def test_broken_config_filled_skin_empty(tmp_path):
    proj = _project(tmp_path, CONFIGURED_CONFIG, SKIN_EMPTY)
    state, problems = _diagnose(proj)
    assert state == "broken"
    assert any("skin" in p.lower() for p in problems)


def test_broken_missing_gated_dir(tmp_path):
    # Fully configured, but a gated_paths dir does not exist on disk.
    proj = _project(tmp_path, CONFIGURED_CONFIG, SKIN_WRITTEN, make_gated=False)
    state, problems = _diagnose(proj)
    assert state == "broken"
    assert any("gated_paths dir does not exist" in p for p in problems)


# --- CLI exit codes ---

def test_main_pristine_exit_0(tmp_path):
    proj = _project(tmp_path, PRISTINE_CONFIG, SKIN_EMPTY)
    import sys
    argv = sys.argv
    sys.argv = ["ledger_doctor.py", "--config", str(proj / "ledger.config.md"),
                "--repo-root", str(proj)]
    try:
        assert ld.main() == 0
        sys.argv = ["ledger_doctor.py", "--require-configured",
                    "--config", str(proj / "ledger.config.md"),
                    "--repo-root", str(proj)]
        assert ld.main() == 1
    finally:
        sys.argv = argv


def test_main_broken_exit_1(tmp_path):
    proj = _project(tmp_path, CONFIGURED_CONFIG, SKIN_EMPTY)
    import sys
    argv = sys.argv
    sys.argv = ["ledger_doctor.py", "--config", str(proj / "ledger.config.md"),
                "--repo-root", str(proj)]
    try:
        assert ld.main() == 1
    finally:
        sys.argv = argv


# --- claim_ids: required default for bootstrapped projects (the teeth) ---

def _run_main(proj, *flags):
    """Run ledger_doctor.main() on a tmp project; return its exit code."""
    import sys
    argv = sys.argv
    sys.argv = ["ledger_doctor.py", *flags,
                "--config", str(proj / "ledger.config.md"),
                "--repo-root", str(proj)]
    try:
        return ld.main()
    finally:
        sys.argv = argv


def test_require_configured_passes_when_claim_ids_required(tmp_path):
    # A configured project that adopted ALL strict postures passes both the
    # bootstrap completion assertion AND the plain run (configured ⟹ strict).
    proj = _project(tmp_path, CONFIGURED_REQUIRED, SKIN_WRITTEN)
    assert _run_main(proj, "--require-configured") == 0
    assert _run_main(proj) == 0


def test_configured_soft_posture_fails_even_plain(tmp_path, capsys):
    # Configured but claim_ids absent (→ optional): configured is strict BY
    # DEFINITION, so a soft posture is a hard failure on the PLAIN run
    # too — not a nudge — and equally under --require-configured.
    proj = _project(tmp_path, CONFIGURED_CONFIG, SKIN_WRITTEN)
    assert _run_main(proj, "--require-configured") == 1
    assert "claim_ids" in capsys.readouterr().err
    assert _run_main(proj) == 1


def test_configured_explicit_optional_fails_even_plain(tmp_path):
    cfg = CONFIGURED_CONFIG + "claim_ids:           optional\n"
    proj = _project(tmp_path, cfg, SKIN_WRITTEN)
    assert _run_main(proj, "--require-configured") == 1
    assert _run_main(proj) == 1


# --- claim-numbering nudge (non-fatal) ---

def test_claim_numbering_warning_on_configured(tmp_path, capsys):
    # A configured project with a non-contiguous ## Claim N ledger emits a
    # non-fatal warning; the exit code stays 0 (strict postures all adopted).
    proj = _project(tmp_path, CONFIGURED_REQUIRED, SKIN_WRITTEN)
    claims = proj / "literature" / "verified_claims"
    claims.mkdir(parents=True)
    (claims / "smith_2020.md").write_text(
        "## Claim 1: a\n\n## Claim 3: b\n", encoding="utf-8")
    assert _run_main(proj) == 0
    assert "claim numbering" in capsys.readouterr().err


def test_require_configured_needs_all_strict_postures(tmp_path):
    # claim_ids: required alone is no longer enough — numeric_citations: block,
    # provenance: required, AND structure_layer: required must also be set.
    only_claims = CONFIGURED_CONFIG + "claim_ids:           required\n"
    proj = _project(tmp_path, only_claims, SKIN_WRITTEN)
    assert _run_main(proj, "--require-configured") == 1   # numeric/provenance/structure lax
    full = _project(tmp_path / "full", CONFIGURED_REQUIRED, SKIN_WRITTEN)
    assert _run_main(full, "--require-configured") == 0


# --- semantic_health: opt-in blocking posture ---

def _write_semantic(proj, last_review):
    p = proj / "content" / "_ledger" / "semantic_health.md"
    p.write_text(f"---\nlast_review: {last_review}\nreviewer: x\n---\n# sh\n",
                 encoding="utf-8")


def test_semantic_required_blocks_when_stale(tmp_path):
    cfg = CONFIGURED_REQUIRED + "semantic_health:     required\n"
    proj = _project(tmp_path, cfg, SKIN_WRITTEN)
    _write_semantic(proj, "20200101")        # years old → stale
    assert _run_main(proj) == 1


def test_semantic_required_passes_when_fresh(tmp_path):
    cfg = CONFIGURED_REQUIRED + "semantic_health:     required\n"
    proj = _project(tmp_path, cfg, SKIN_WRITTEN)
    _write_semantic(proj, dt.date.today().strftime("%Y%m%d"))
    assert _run_main(proj) == 0


def test_semantic_warn_default_nudges_not_blocks(tmp_path, capsys):
    # No semantic file + default 'warn' → a configured project still passes, with
    # a non-fatal nudge on stderr.
    proj = _project(tmp_path, CONFIGURED_REQUIRED, SKIN_WRITTEN)
    assert _run_main(proj) == 0
    assert "semantic health" in capsys.readouterr().err


def test_semantic_off_is_silent(tmp_path, capsys):
    cfg = CONFIGURED_REQUIRED + "semantic_health:     off\n"
    proj = _project(tmp_path, cfg, SKIN_WRITTEN)
    assert _run_main(proj) == 0
    assert "semantic health" not in capsys.readouterr().err


def test_semantic_max_age_window(tmp_path):
    cfg = CONFIGURED_REQUIRED + "semantic_health:     required\n"
    proj = _project(tmp_path, cfg, SKIN_WRITTEN)
    _write_semantic(proj, "20260101")
    config = ld.parse_config(proj / "ledger.config.md")
    assert ld.semantic_staleness_problems(proj, config, today="20260601") == []   # 151d ≤ 180
    assert ld.semantic_staleness_problems(proj, config, today="20270101") != []   # 365d > 180


# --- project_state: declared mode reconciled with the derivation (keystone) ---

def test_declared_state_absent_defers():
    # No project_state key → declared_state None → derivation is authoritative.
    assert ld.declared_state({}) is None
    assert ld.declared_state({"project_state": "<placeholder>"}) is None
    assert ld.declared_state({"project_state": "configured  # note"}) == "configured"


def test_declared_matches_derivation_ok(tmp_path):
    cfg = CONFIGURED_REQUIRED + "project_state:       configured\n"
    proj = _project(tmp_path, cfg, SKIN_WRITTEN)
    state, problems = _diagnose(proj)
    assert state == "configured" and problems == []


def test_declared_configured_but_derived_pristine_is_broken(tmp_path):
    cfg = PRISTINE_CONFIG + "project_state:       configured\n"
    proj = _project(tmp_path, cfg, SKIN_EMPTY)
    state, problems = _diagnose(proj)
    assert state == "broken"
    assert any("project_state" in p for p in problems)


def test_declared_pristine_but_derived_configured_is_broken(tmp_path):
    cfg = CONFIGURED_REQUIRED + "project_state:       pristine\n"
    proj = _project(tmp_path, cfg, SKIN_WRITTEN)
    state, problems = _diagnose(proj)
    assert state == "broken"
    assert any("project_state" in p for p in problems)


def test_strict_mode_predicate(tmp_path):
    pristine = _project(tmp_path / "p", PRISTINE_CONFIG, SKIN_EMPTY)
    assert ld.strict_mode(ld.parse_config(pristine / "ledger.config.md"), pristine) is False
    configured = _project(tmp_path / "c", CONFIGURED_REQUIRED, SKIN_WRITTEN)
    assert ld.strict_mode(ld.parse_config(configured / "ledger.config.md"), configured) is True


def test_print_strict_flag(tmp_path, capsys):
    pristine = _project(tmp_path / "p", PRISTINE_CONFIG, SKIN_EMPTY)
    assert _run_main(pristine, "--print-strict") == 0
    assert capsys.readouterr().out.strip() == "lenient"
    configured = _project(tmp_path / "c", CONFIGURED_REQUIRED, SKIN_WRITTEN)
    assert _run_main(configured, "--print-strict") == 0
    assert capsys.readouterr().out.strip() == "strict"
