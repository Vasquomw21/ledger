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
    # Fully configured, but a gated_paths entry does not exist on disk.
    proj = _project(tmp_path, CONFIGURED_CONFIG, SKIN_WRITTEN, make_gated=False)
    state, problems = _diagnose(proj)
    assert state == "broken"
    assert any("gated_paths entry does not exist" in p for p in problems)


def test_gated_paths_may_name_a_single_file(tmp_path):
    # The citation gate matches a gated prefix against a path, so gating one file is
    # legitimate — a project whose synthesis is content/inquiry.md rather than a
    # directory of notes. Doctor used to require a directory, so such a project was
    # gated correctly and still reported broken.
    config = CONFIGURED_CONFIG.replace(
        "gated_paths:         content/concept_notes/",
        "gated_paths:         content/inquiry.md, content/concept_notes/")
    proj = _project(tmp_path, config, SKIN_WRITTEN)
    (proj / "content" / "inquiry.md").write_text("# Inquiry\n", encoding="utf-8")
    state, problems = _diagnose(proj)
    assert state == "configured", problems
    assert not any("gated_paths" in p for p in problems)


def test_gated_paths_still_catches_a_typo_in_a_file_entry(tmp_path):
    # Accepting files must not weaken the typo-catcher into accepting anything.
    config = CONFIGURED_CONFIG.replace(
        "gated_paths:         content/concept_notes/",
        "gated_paths:         content/inqiury.md, content/concept_notes/")
    proj = _project(tmp_path, config, SKIN_WRITTEN)
    (proj / "content" / "inquiry.md").write_text("# Inquiry\n", encoding="utf-8")
    state, problems = _diagnose(proj)
    assert state == "broken"
    assert any("content/inqiury.md" in p for p in problems)


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


# --- skin_state: is the skin rules the author stands behind? --------------------
# The kit ships a worked example from another project, so "the file contains bold
# text" cannot establish that a skin is THIS subject's. skin_state is the author
# saying so; absent, the old shape-guess still applies.

DRAFT = "skin_state:          draft\n"
CONFIRMED = "skin_state:          confirmed\n"


def test_declared_skin_state():
    assert ld.declared_skin_state({"skin_state": "draft"}) == "draft"
    assert ld.declared_skin_state({"skin_state": "CONFIRMED  # yes"}) == "confirmed"
    for raw in ({}, {"skin_state": "<draft | confirmed>"}, {"skin_state": "maybe"}):
        assert ld.declared_skin_state(raw) is None


def test_a_drafted_skin_is_not_configured(tmp_path):
    project = _project(tmp_path, CONFIGURED_REQUIRED + DRAFT, SKIN_WRITTEN)
    state, problems = _diagnose(project)
    assert state == "drafted"
    assert problems and "sharpen" in problems[0]
    assert not ld.strict_mode(ld.parse_config(project / "ledger.config.md"), project)


def test_a_confirmed_skin_is_configured(tmp_path):
    project = _project(tmp_path, CONFIGURED_REQUIRED + CONFIRMED, SKIN_WRITTEN)
    assert _diagnose(project) == ("configured", [])
    assert ld.strict_mode(ld.parse_config(project / "ledger.config.md"), project)


def test_absent_skin_state_keeps_the_old_shape_guess(tmp_path):
    # Back-compat: projects written before skin_state exists must not change state.
    written = _project(tmp_path / "w", CONFIGURED_REQUIRED, SKIN_WRITTEN)
    assert _diagnose(written)[0] == "configured"
    empty = _project(tmp_path / "e", CONFIGURED_REQUIRED, SKIN_EMPTY)
    assert _diagnose(empty)[0] == "broken"


def test_confirmed_cannot_conjure_a_skin_that_is_not_there(tmp_path):
    # A declaration is believed about rules that exist; it does not create them.
    project = _project(tmp_path, CONFIGURED_REQUIRED + CONFIRMED, SKIN_EMPTY)
    state, problems = _diagnose(project)
    assert state == "broken"
    assert any("confirmed" in p and "empty" in p for p in problems), problems


def test_configured_over_a_draft_skin_is_broken(tmp_path):
    # Claiming configured while the skin is admittedly a draft is the half-state
    # doctor exists to catch: it would run every gate strict on unowned rules.
    project = _project(tmp_path, CONFIGURED_REQUIRED + DRAFT +
                       "project_state:       configured\n", SKIN_WRITTEN)
    state, problems = _diagnose(project)
    assert state == "broken"
    assert any("stood behind" in p for p in problems), problems


def test_a_drafted_project_mid_init_is_not_broken(tmp_path):
    # init fills the config and drafts the skin but never touches project_state, so
    # `pristine` is stale rather than contradictory — not a failure.
    project = _project(tmp_path, CONFIGURED_REQUIRED + DRAFT +
                       "project_state:       pristine\n", SKIN_WRITTEN)
    assert _diagnose(project)[0] == "drafted"


def test_a_drafted_project_exits_0_and_is_not_forced_strict(tmp_path, capsys):
    # Lax postures + drafted must NOT hard-fail: a drafted project is not yet
    # configured, so "configured is strict by definition" does not apply to it.
    project = _project(tmp_path, CONFIGURED_CONFIG + DRAFT, SKIN_WRITTEN)
    assert _run_main(project) == 0
    out = capsys.readouterr().out
    assert "drafted" in out and "lenient" in out


def test_require_configured_rejects_a_drafted_project(tmp_path):
    project = _project(tmp_path, CONFIGURED_REQUIRED + DRAFT, SKIN_WRITTEN)
    assert _run_main(project, "--require-configured") == 1


def test_a_drafted_project_prints_lenient(tmp_path, capsys):
    project = _project(tmp_path, CONFIGURED_REQUIRED + DRAFT, SKIN_WRITTEN)
    assert _run_main(project, "--print-strict") == 0
    assert capsys.readouterr().out.strip() == "lenient"
