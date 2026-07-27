# Tests for init's pure construction layer: what it proposes, what it refuses, what it
# leaves alone, and that computing a plan never reaches the disk.
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import config_edit as ce
import init_plan as ip
import ledger_doctor as ld

KIT_CONFIG = REPO_ROOT / "ledger.config.md"
KIT_SKIN = REPO_ROOT / "content" / "_ledger" / "skin_rules.md"

ANSWERS = {
    "project_name": "water_policy_ke",
    "deliverable": "policy white paper",
    "source_of_truth": "markdown+quartz",
    "the_reader": "a busy minister AND a sceptical hydrologist",
    "source_types": "legislation & gov reports, peer-reviewed papers",
}

RULES = ["abstraction vs allocation: never conflate a licensed volume with the water "
         "actually taken",
         "basin before nation: a national average hides the basin where the shortage bites"]

SKIN = ("# Subject-specific writing rules (the \"skin\")\n"
        "\n"
        "**This file holds only the rules specific to THIS subject.**\n"
        "\n"
        "Worked example — the Quantum KE white paper's pack:\n"
        "- **W1** dual-audience register (a policy so-what AND scientific defensibility)\n"
        "- **W2** no-hype ladder (label every claim demonstrated / plausible)\n"
        "\n"
        "---\n"
        "\n"
        "_(empty — the bootstrap helper drafts this subject's rules here, for you to "
        "edit)_\n")

WRITTEN_SKIN = SKIN.replace(
    "_(empty — the bootstrap helper drafts this subject's rules here, for you to edit)_",
    "Subject rules — water policy:\n- **P1** a rule its author stands behind")


def _config(**overrides) -> str:
    """A config in the kit's shape: aligned values, comment blocks, template tokens."""
    values = {"project_name": "<e.g. water_policy_ke>",
              "deliverable": "<thesis chapter | report | ...>",
              "source_of_truth": "<markdown+quartz | docx+python>",
              "the_reader": "<the bored reader>",
              "source_types": "<peer-reviewed papers | mixed>",
              "unpaywall_email": "<your email for the download service>",
              "project_state": "pristine",
              "gated_paths": "content/concept_notes/, content/literature_reviews/",
              "skin_rules_file": "content/_ledger/skin_rules.md",
              "skin_state": "<draft | confirmed>"}
    values.update(overrides)
    return ("# Ledger project config\n#\n"
            + "".join(f"{(k + ':').ljust(20)} {v}\n" for k, v in values.items()))


FILLED = _config(project_name="lhc_safety", deliverable="report",
                 source_of_truth="markdown+quartz", the_reader="a science journalist",
                 source_types="peer-reviewed papers")


# --- the field registry tracks the kernel ----------------------------------------

def test_required_fields_match_what_doctor_requires():
    # A field doctor requires but init never asks for leaves every init one placeholder
    # short of configured, with nothing to say why.
    assert [f.key for f in ip.FIELDS if f.required] == ld.REQUIRED


def test_source_of_truth_choices_match_the_config_template():
    # The template token in the shipped config is the only statement of what the field
    # accepts; validating against a stale copy of it would reject a legitimate answer.
    line = next(l for l in KIT_CONFIG.read_text(encoding="utf-8").split("\n")
                if l.startswith("source_of_truth:"))
    token = re.search(r"<(.+)>", line).group(1)
    assert tuple(p.strip() for p in token.split("|")) == ip.SOURCE_OF_TRUTH_CHOICES


# --- what init writes, and what it refuses to write -------------------------------

def test_project_state_is_never_written():
    # It is the author's declaration that the project is finished. Stamping it onto a
    # half-built project makes doctor read `broken`, whose gates run lenient while the
    # config claims strictness.
    assert "project_state" not in ip.config_updates(ANSWERS)
    assert "project_state" not in ip.build(_config(), SKIN, ANSWERS, RULES).config_updates


def test_init_marks_a_skin_it_drafts_as_a_draft():
    assert ip.build(_config(), SKIN, ANSWERS, RULES).config_updates["skin_state"] \
        == "draft"
    assert ip.build(_config(), SKIN, ANSWERS, []).config_updates["skin_state"] == "draft"


def test_init_leaves_the_state_of_a_skin_it_does_not_touch():
    # Whether an author stands behind rules init never wrote is not init's to say.
    plan = ip.build(FILLED, WRITTEN_SKIN, ANSWERS, [], reconfigure=True)
    assert "skin_state" not in plan.config_updates


def test_reconfiguring_a_configured_project_does_not_downgrade_its_skin(tmp_path):
    # Stamping 'draft' over an owned skin makes doctor report `broken` — a project cannot
    # be configured on rules nobody has stood behind — so init could never re-answer a
    # configured project's config.
    configured = _config(project_name="lhc_safety", deliverable="report",
                         source_of_truth="markdown+quartz",
                         the_reader="a science journalist",
                         source_types="peer-reviewed papers",
                         project_state="configured", skin_state="confirmed")
    plan = ip.build(configured, WRITTEN_SKIN, ANSWERS, [], reconfigure=True)

    skin_path = tmp_path / "content" / "_ledger" / "skin_rules.md"
    skin_path.parent.mkdir(parents=True)
    skin_path.write_text(WRITTEN_SKIN, encoding="utf-8")
    for gated in ("concept_notes", "literature_reviews"):
        (tmp_path / "content" / gated).mkdir()
    applied = ce.render(configured, plan.config_updates)
    state, _ = ld.diagnose({l.key: l.value for l in ce.scan(applied)}, tmp_path)
    assert state == "configured"


def test_config_updates_carry_every_answered_field():
    updates = ip.config_updates({**ANSWERS, "unpaywall_email": "a@b.co"})
    assert updates["project_name"] == "water_policy_ke"
    assert updates["unpaywall_email"] == "a@b.co"


def test_unanswered_and_placeholder_fields_are_not_written():
    updates = ip.config_updates({**ANSWERS, "unpaywall_email": "<your email>"})
    assert "unpaywall_email" not in updates


def test_unknown_answers_never_reach_the_config():
    updates = ip.config_updates({**ANSWERS, "project_state": "configured"})
    assert "project_state" not in updates


# --- answer validation ------------------------------------------------------------

def test_complete_answers_have_no_problems():
    assert ip.answer_problems(ANSWERS) == []


def test_missing_required_field_is_reported():
    answers = {k: v for k, v in ANSWERS.items() if k != "the_reader"}
    assert any("the_reader" in p for p in ip.answer_problems(answers))


def test_placeholder_required_field_is_reported():
    problems = ip.answer_problems({**ANSWERS, "deliverable": "<thesis chapter | ...>"})
    assert any("deliverable" in p for p in problems)


def test_unrecognised_source_of_truth_is_reported():
    problems = ip.answer_problems({**ANSWERS, "source_of_truth": "markdown + quartz"})
    assert any("source_of_truth" in p for p in problems)


def test_each_declared_source_of_truth_is_accepted():
    for choice in ip.SOURCE_OF_TRUTH_CHOICES:
        assert ip.answer_problems({**ANSWERS, "source_of_truth": choice}) == []


def test_malformed_unpaywall_email_is_reported():
    problems = ip.answer_problems({**ANSWERS, "unpaywall_email": "not-an-address"})
    assert any("unpaywall_email" in p for p in problems)


def test_omitted_unpaywall_email_is_fine():
    assert ip.answer_problems(ANSWERS) == []


def test_unknown_field_is_reported():
    problems = ip.answer_problems({**ANSWERS, "favourite_colour": "blue"})
    assert any("favourite_colour" in p for p in problems)


# --- filler is not a rule ---------------------------------------------------------

def test_a_real_rule_passes():
    assert ip.rule_problems(RULES, SKIN) == []


def test_blank_rule_is_rejected():
    assert ip.rule_problems([""], SKIN)
    assert ip.rule_problems(["   "], SKIN)


def test_placeholder_tokens_are_rejected():
    for filler in ["TBD", "todo", "n/a", "none", "...", "<your rule here>"]:
        assert ip.rule_problems([filler], SKIN), filler


def test_the_shipped_worked_example_is_not_this_subjects_rule():
    # The kit ships one worked example from another project. It is the only rules prose
    # to hand, so it is the likeliest thing to be pasted back in to clear the prompt.
    pasted = "dual-audience register (a policy so-what AND scientific defensibility)"
    assert ip.rule_problems([pasted], SKIN)
    assert ip.rule_problems([f"  {pasted.upper()}  "], SKIN)


def test_a_rule_containing_a_filler_word_is_still_a_rule():
    assert ip.rule_problems(["none of the abstraction figures are metered volumes"],
                            SKIN) == []


# --- rule codes -------------------------------------------------------------------

def test_rule_code_follows_the_subject_name():
    assert ip.rule_code("lhc_safety_ledger", SKIN) == "L"
    assert ip.rule_code("eggs_cholesterol", SKIN) == "E"


def test_rule_code_may_use_a_letter_only_the_worked_example_held():
    # The example is removed when the skin is materialised, so it reserves nothing.
    assert ip.rule_code("water_policy_ke", KIT_SKIN.read_text(encoding="utf-8")) == "W"


def test_rule_code_avoids_a_letter_a_retained_rule_holds():
    # A rule that survives into the written skin does reserve its letter: two **W1**s
    # would make a reference to "W1" ambiguous.
    retained = SKIN.replace(ld.SKIN_EMPTY_MARKER,
                            "- **W1** a rule someone here wrote\n\n" + ld.SKIN_EMPTY_MARKER)
    assert ip.rule_code("water_policy_ke", retained) != "W"


def test_rule_code_falls_back_when_the_name_has_no_free_letter():
    assert ip.rule_code("", SKIN).isalpha()
    assert ip.rule_code("123", SKIN).isalpha()


# --- the worked example is not this subject's rules --------------------------------

def test_materialising_the_real_kit_skin_drops_the_worked_example():
    # The kit ships another project's five rules above the sentinel. Once the skin is
    # confirmed nothing marks them as someone else's, so they would become this
    # project's active rules.
    shipped = KIT_SKIN.read_text(encoding="utf-8")
    out = ip.render_skin(shipped, "water_policy_ke", RULES,
                         ip.rule_code("water_policy_ke", shipped))

    assert "Worked example" not in out
    for body in ip.example_rules(shipped):
        assert body not in ip._normalise(out)
    # What remains beneath the preamble is this subject's rules and nothing else.
    rendered = [m.group("body") for m in map(ip.RULE_LINE_RE.match, out.split("\n")) if m]
    assert rendered == [r.strip() for r in RULES]


def test_materialising_keeps_the_shared_explanatory_preamble():
    shipped = KIT_SKIN.read_text(encoding="utf-8")
    out = ip.render_skin(shipped, "water_policy_ke", RULES, "W")
    preamble = shipped.split("Worked example")[0]
    assert out.startswith(preamble.rstrip("\n") + "\n")


def test_stripping_a_skin_with_no_worked_example_changes_nothing():
    plain = "# Skin\n\nsome prose\n\n---\n\n" + ld.SKIN_EMPTY_MARKER + "\n"
    assert ip.strip_worked_example(plain) == plain


def test_stripping_leaves_no_double_gap():
    assert "\n\n\n" not in ip.strip_worked_example(KIT_SKIN.read_text(encoding="utf-8"))


# --- rendering the skin -----------------------------------------------------------

def test_rendering_replaces_the_sentinel():
    out = ip.render_skin(SKIN, "water policy", RULES, "P")
    assert ld.SKIN_EMPTY_MARKER not in out


def test_rendered_rules_are_numbered_from_one():
    out = ip.render_skin(SKIN, "water policy", RULES, "P")
    assert "- **P1** " + RULES[0] in out
    assert "- **P2** " + RULES[1] in out


def test_rendering_a_skin_without_the_sentinel_appends():
    stripped = SKIN.replace(
        "_(empty — the bootstrap helper drafts this subject's rules here, for you to "
        "edit)_\n", "")
    out = ip.render_skin(stripped, "water policy", ["a rule"], "P")
    assert out.rstrip().endswith("- **P1** a rule")
    assert out.startswith(stripped.split("Worked example")[0].rstrip("\n"))


def test_rendering_never_leaves_a_double_gap():
    for text in (SKIN, KIT_SKIN.read_text(encoding="utf-8"),
                 SKIN.replace(ld.SKIN_EMPTY_MARKER, "").rstrip("\n")):
        assert "\n\n\n" not in ip.render_skin(text, "s", ["a rule"], "P")


def test_rendered_skin_is_no_longer_empty_to_the_kernel():
    out = ip.render_skin(SKIN, "water policy", RULES, "P")
    assert not ld.skin_text_is_empty(out)


# --- blockers ---------------------------------------------------------------------

def test_a_pristine_kit_is_not_blocked():
    assert ip.blockers(_config(), SKIN, reconfigure=False) == []


def test_a_filled_config_is_blocked_without_reconfigure():
    problems = ip.blockers(FILLED, SKIN, reconfigure=False)
    assert any("--reconfigure" in p for p in problems)


def test_reconfigure_consents_to_a_filled_config():
    assert ip.blockers(FILLED, SKIN, reconfigure=True) == []


def test_a_written_skin_is_blocked_without_reconfigure():
    assert ip.blockers(_config(), WRITTEN_SKIN, reconfigure=False)


def test_reconfigure_consents_to_a_written_skin():
    assert ip.blockers(_config(), WRITTEN_SKIN, reconfigure=True) == []


# --- the skin belongs to its author -----------------------------------------------

def test_a_written_skin_is_never_rewritten_even_under_reconfigure():
    plan = ip.build(FILLED, WRITTEN_SKIN, ANSWERS, RULES, reconfigure=True)
    assert plan.skin_text is None
    assert plan.skin_diff == ""


def test_rules_offered_for_a_written_skin_are_refused_rather_than_dropped():
    # Silently ignoring them would report success while the rules went nowhere.
    plan = ip.build(FILLED, WRITTEN_SKIN, ANSWERS, RULES, reconfigure=True)
    assert not plan.ok
    assert any("already holds rules" in p for p in plan.problems)


def test_reconfiguring_a_written_skin_without_rules_is_allowed():
    plan = ip.build(FILLED, WRITTEN_SKIN, ANSWERS, [], reconfigure=True)
    assert plan.ok
    assert plan.skin_text is None
    assert any("left untouched" in n for n in plan.notes)


# --- building the plan ------------------------------------------------------------

def test_a_fresh_kit_with_full_answers_builds_cleanly():
    plan = ip.build(_config(), SKIN, ANSWERS, RULES)
    assert plan.ok
    assert plan.config_diff
    assert plan.skin_diff


def test_declining_the_rules_still_builds_and_leaves_a_draft():
    plan = ip.build(_config(), SKIN, ANSWERS, [])
    assert plan.ok
    assert plan.skin_text is None
    assert plan.config_updates["skin_state"] == "draft"


def test_bad_answers_produce_no_config_diff():
    # A diff built from rejected answers would show a change that is never going to
    # happen.
    plan = ip.build(_config(), SKIN, {**ANSWERS, "source_of_truth": "nope"}, RULES)
    assert not plan.ok
    assert plan.config_diff == ""


def test_an_ambiguous_config_is_refused():
    doubled = _config() + "claim_ids:           required\nclaim_ids:           off\n"
    plan = ip.build(doubled, SKIN, ANSWERS, RULES)
    assert any("claim_ids" in p for p in plan.problems)


def test_the_plan_is_bound_to_the_bytes_it_was_computed_from():
    text = _config()
    plan = ip.build(text, SKIN, ANSWERS, RULES)
    assert plan.config_sha256 == ce.digest(text)
    assert plan.skin_sha256 == ce.digest(SKIN)


def test_a_missing_skin_is_not_an_empty_one():
    # Only None can say the plan expected no file at all, so only None lets the writer
    # refuse a skin that appeared since.
    assert ip.build(_config(), None, ANSWERS, RULES).skin_existed is False
    assert ip.build(_config(), "", ANSWERS, RULES).skin_existed is True
    assert ip.build(_config(), None, ANSWERS, RULES).skin_sha256 is None


# --- the plan goes stale when either target moves ----------------------------------

def test_unmoved_targets_are_not_stale():
    plan = ip.build(_config(), SKIN, ANSWERS, RULES)
    assert ip.staleness(plan, _config(), SKIN) == []


def test_a_changed_config_makes_the_plan_stale():
    plan = ip.build(_config(), SKIN, ANSWERS, RULES)
    assert ip.staleness(plan, _config() + "claim_ids:           off\n", SKIN)


def test_a_changed_skin_makes_the_plan_stale():
    # Rules approved against one skin must never be written over a different one.
    plan = ip.build(_config(), SKIN, ANSWERS, RULES)
    assert ip.staleness(plan, _config(), SKIN + "\n- **X1** written since\n")


def test_a_skin_that_appeared_since_the_preview_makes_the_plan_stale():
    plan = ip.build(_config(), None, ANSWERS, RULES)
    problems = ip.staleness(plan, _config(), WRITTEN_SKIN)
    assert any("did not exist" in p for p in problems)


def test_a_skin_that_vanished_since_the_preview_makes_the_plan_stale():
    plan = ip.build(_config(), SKIN, ANSWERS, RULES)
    assert any("gone now" in p for p in ip.staleness(plan, _config(), None))


def test_a_stale_skin_invalidates_the_plan_even_when_the_config_is_untouched():
    # init writes two files; a plan stale in one is stale entirely, or the config lands
    # against a skin nobody approved.
    plan = ip.build(_config(), SKIN, ANSWERS, RULES)
    assert ip.staleness(plan, _config(), WRITTEN_SKIN)


# --- declared paths must not leave the project ------------------------------------

def test_the_shipped_config_declares_no_escaping_path():
    assert ip.path_problems(KIT_CONFIG.read_text(encoding="utf-8")) == []


# --- the write target comes from the config, and nowhere else ----------------------

def test_no_caller_supplied_target_can_diverge_from_the_configured_skin():
    # A target taken as an argument names a file path_problems never validated: it would
    # check skin_rules_file while the plan wrote somewhere else entirely.
    with pytest.raises(TypeError):
        ip.build(_config(), "", ANSWERS, RULES, skin_file="../../outside.md")


def test_the_write_target_is_the_configured_one():
    plan = ip.build(_config(skin_rules_file="content/_ledger/custom.md"), "", ANSWERS,
                    RULES)
    assert plan.skin_file == "content/_ledger/custom.md"


def test_an_unusable_skin_declaration_falls_back_to_the_kernel_default():
    assert ip.declared_skin_file(_config(skin_rules_file="<path>")) == ip.DEFAULT_SKIN_FILE
    assert ip.declared_skin_file("# nothing declared\n") == ip.DEFAULT_SKIN_FILE


def test_an_escaping_configured_skin_is_refused_rather_than_quietly_redirected():
    # Falling back to the default here would write to a file the config never named.
    text = _config(skin_rules_file="../../outside.md")
    plan = ip.build(text, "", ANSWERS, RULES)
    assert not plan.ok
    assert plan.skin_file == "../../outside.md"


def test_a_gated_path_climbing_out_of_the_project_is_refused():
    text = _config(gated_paths="../outside/")
    assert any("gated_paths" in p for p in ip.path_problems(text))
    assert not ip.build(text, SKIN, ANSWERS, RULES).ok


def test_an_absolute_gated_path_is_refused():
    text = _config(gated_paths="/etc/")
    assert any("absolute" in p for p in ip.path_problems(text))
    assert not ip.build(text, SKIN, ANSWERS, RULES).ok


def test_a_skin_path_climbing_out_of_the_project_is_refused():
    text = _config(skin_rules_file="../../skin.md")
    assert any("skin_rules_file" in p for p in ip.path_problems(text))
    assert not ip.build(text, SKIN, ANSWERS, RULES).ok


def test_a_home_relative_path_is_refused():
    assert ip.path_problems(_config(skin_rules_file="~/skin.md"))


def test_an_escaping_path_is_never_offered_as_a_directory_to_create():
    # Reported AND dropped: a caller that ignores path_problems still cannot be handed
    # one.
    assert ip.dirs_to_ensure(_config(gated_paths="../outside/")) == ["content/_ledger/"]
    assert not any(".." in d for d in
                   ip.dirs_to_ensure(_config(skin_rules_file="../../skin.md")))


def test_applying_the_plan_and_rebuilding_proposes_nothing_further():
    plan = ip.build(_config(), SKIN, ANSWERS, RULES)
    applied = ce.render(_config(), plan.config_updates)
    again = ip.build(applied, plan.skin_text, ANSWERS, [], reconfigure=True)
    assert again.changes == []


def test_the_proposed_project_derives_as_drafted(tmp_path):
    # The whole point of the plan: a project that is set up, honest about its skin, and
    # not yet claiming to be configured.
    plan = ip.build(_config(), SKIN, ANSWERS, RULES)
    applied = ce.render(_config(), plan.config_updates)
    skin_path = tmp_path / "content" / "_ledger" / "skin_rules.md"
    skin_path.parent.mkdir(parents=True)
    skin_path.write_text(plan.skin_text, encoding="utf-8")
    for gated in ("concept_notes", "literature_reviews"):
        (tmp_path / "content" / gated).mkdir()
    state, _ = ld.diagnose({l.key: l.value for l in ce.scan(applied)}, tmp_path)
    assert state == "drafted"


def test_building_a_plan_writes_nothing(tmp_path):
    before = {p: p.read_bytes() for p in (KIT_CONFIG, KIT_SKIN)}
    ip.build(KIT_CONFIG.read_text(encoding="utf-8"),
             KIT_SKIN.read_text(encoding="utf-8"), ANSWERS, RULES, reconfigure=True)
    assert {p: p.read_bytes() for p in (KIT_CONFIG, KIT_SKIN)} == before
    assert list(tmp_path.iterdir()) == []


# --- directories the config declares ----------------------------------------------

def test_declared_gated_directories_are_listed():
    # Git does not track an empty directory, so a correctly declared gated path can be
    # missing from a clone — which doctor reports as broken.
    dirs = ip.dirs_to_ensure(_config())
    assert "content/concept_notes/" in dirs
    assert "content/literature_reviews/" in dirs


def test_the_skins_directory_is_listed():
    assert "content/_ledger/" in ip.dirs_to_ensure(_config())


def test_a_gated_path_naming_a_single_file_is_not_made_a_directory():
    dirs = ip.dirs_to_ensure(_config(gated_paths="content/inquiry.md"))
    assert "content/inquiry.md" not in dirs
    assert not any(d.startswith("content/inquiry") for d in dirs)


def test_gating_nothing_still_lists_the_skins_directory():
    assert ip.dirs_to_ensure(_config(gated_paths="none")) == ["content/_ledger/"]
