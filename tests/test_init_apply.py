# Tests for init's writer: what it refuses before writing, what it leaves behind when a
# step fails, and that no failure needs a deletion to undo.
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import config_edit as ce
import init_apply as ia
import init_plan as ip
import ledger_doctor as ld

ANSWERS = {
    "project_name": "water_policy_ke",
    "deliverable": "policy white paper",
    "source_of_truth": "markdown+quartz",
    "the_reader": "a busy minister AND a sceptical hydrologist",
    "source_types": "legislation & gov reports",
}
RULES = ["abstraction vs allocation: a licensed volume is not water actually taken"]

SKIN = ("# Subject-specific writing rules (the \"skin\")\n"
        "\n"
        "**This file holds only the rules specific to THIS subject.**\n"
        "\n"
        "Worked example — the Quantum KE white paper's pack:\n"
        "- **W1** dual-audience register (a policy so-what AND scientific defensibility)\n"
        "\n"
        "---\n"
        "\n"
        "_(empty — the bootstrap helper drafts this subject's rules here, for you to "
        "edit)_\n")


def _config(**overrides) -> str:
    values = {"project_name": "<e.g. water_policy_ke>",
              "deliverable": "<thesis chapter | report | ...>",
              "source_of_truth": "<markdown+quartz | docx+python>",
              "the_reader": "<the bored reader>",
              "source_types": "<peer-reviewed papers | mixed>",
              "project_state": "pristine",
              "gated_paths": "content/concept_notes/, content/literature_reviews/",
              "skin_rules_file": "content/_ledger/skin_rules.md",
              "skin_state": "<draft | confirmed>"}
    values.update(overrides)
    return ("# Ledger project config\n#\n"
            + "".join(f"{(k + ':').ljust(20)} {v}\n" for k, v in values.items()))


# A configured project is strict BY DEFINITION: doctor hard-fails one that has not
# adopted these, so a config claiming `configured` without them is not a passing project.
STRICT = {"claim_ids": "required", "numeric_citations": "block",
          "provenance": "required", "structure_layer": "required",
          "assessment_layer": "required"}


@pytest.fixture
def kit(tmp_path):
    """A starter-kit clone: the config, the skin, and the directories it declares."""
    (tmp_path / "ledger.config.md").write_text(_config(), encoding="utf-8")
    skin = tmp_path / "content" / "_ledger" / "skin_rules.md"
    skin.parent.mkdir(parents=True)
    skin.write_text(SKIN, encoding="utf-8")
    for gated in ("concept_notes", "literature_reviews"):
        (tmp_path / "content" / gated).mkdir()
    return tmp_path


def _plan(root, answers=None, rules=None, reconfigure=False):
    config_text = (root / "ledger.config.md").read_text(encoding="utf-8")
    skin_path = root / ip.declared_skin_file(config_text)
    skin_text = skin_path.read_text(encoding="utf-8") if skin_path.is_file() else None
    return ip.build(config_text, skin_text, answers or ANSWERS,
                    RULES if rules is None else rules, reconfigure=reconfigure)


def _snapshot(root):
    return {p.relative_to(root): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


# --- the happy path ----------------------------------------------------------------

def test_a_pristine_kit_is_configured_and_lands_drafted(kit):
    applied, problems = ia.apply_plan(kit, _plan(kit))
    assert (applied, problems) == (True, [])
    config = ce.scan((kit / "ledger.config.md").read_text(encoding="utf-8"))
    values = {line.key: line.value for line in config}
    assert values["project_name"] == "water_policy_ke"
    assert values["skin_state"] == "draft"
    assert ld.diagnose(values, kit)[0] == "drafted"


def test_the_rules_reach_the_skin_without_the_worked_example(kit):
    ia.apply_plan(kit, _plan(kit))
    skin = (kit / "content/_ledger/skin_rules.md").read_text(encoding="utf-8")
    assert RULES[0] in skin
    assert "Worked example" not in skin


def test_declining_the_rules_leaves_the_skin_untouched(kit):
    before = (kit / "content/_ledger/skin_rules.md").read_bytes()
    applied, problems = ia.apply_plan(kit, _plan(kit, rules=[]))
    assert (applied, problems) == (True, [])
    assert (kit / "content/_ledger/skin_rules.md").read_bytes() == before


def test_reapplying_the_same_plan_changes_nothing_further(kit):
    ia.apply_plan(kit, _plan(kit))
    after = _snapshot(kit)
    applied, problems = ia.apply_plan(kit, _plan(kit, rules=[], reconfigure=True))
    assert applied
    assert _snapshot(kit) == after


# --- init creates nothing ----------------------------------------------------------

def test_a_missing_skin_is_refused_rather_than_created(kit):
    plan = _plan(kit)
    (kit / "content/_ledger/skin_rules.md").rename(kit / "content/_ledger/moved.md")
    applied, problems = ia.apply_plan(kit, plan)
    assert not applied
    assert any("does not create one" in p for p in problems)
    assert not (kit / "content/_ledger/skin_rules.md").exists()


def test_a_missing_declared_directory_is_refused_rather_than_created(kit):
    (kit / "content" / "concept_notes").rmdir()
    applied, problems = ia.apply_plan(kit, _plan(kit))
    assert not applied
    assert any("creates none" in p for p in problems)
    assert not (kit / "content" / "concept_notes").exists()


def test_a_missing_config_is_refused_rather_than_created(tmp_path):
    plan = ip.build(_config(), SKIN, ANSWERS, RULES)
    applied, problems = ia.apply_plan(tmp_path, plan)
    assert not applied
    assert any("does not create one" in p for p in problems)
    assert not (tmp_path / "ledger.config.md").exists()


def test_a_refusal_writes_nothing_at_all(kit):
    before = _snapshot(kit)
    (kit / "content" / "literature_reviews").rmdir()
    ia.apply_plan(kit, _plan(kit))
    assert {k: v for k, v in _snapshot(kit).items()} == before


# --- the plan must still be valid --------------------------------------------------

def test_a_plan_with_problems_is_refused(kit):
    plan = _plan(kit, answers={**ANSWERS, "source_of_truth": "nope"})
    applied, problems = ia.apply_plan(kit, plan)
    assert not applied
    assert _snapshot(kit)


def test_a_blocked_plan_is_refused(kit):
    # A filled config without --reconfigure.
    ia.apply_plan(kit, _plan(kit))
    applied, problems = ia.apply_plan(kit, _plan(kit, rules=[]))
    assert not applied
    assert any("--reconfigure" in p for p in problems)


# --- staleness is checked immediately before the write -----------------------------

def test_a_config_edited_after_the_plan_is_refused(kit):
    plan = _plan(kit)
    path = kit / "ledger.config.md"
    path.write_text(path.read_text(encoding="utf-8") + "claim_ids:           off\n",
                    encoding="utf-8")
    applied, problems = ia.apply_plan(kit, plan)
    assert not applied
    assert any("changed after the preview" in p for p in problems)


def test_a_skin_edited_after_the_plan_is_refused_and_the_config_untouched(kit):
    # init writes two files: a plan stale in one is stale entirely, or the config lands
    # against a skin nobody approved.
    plan = _plan(kit)
    config_before = (kit / "ledger.config.md").read_bytes()
    skin = kit / "content/_ledger/skin_rules.md"
    skin.write_text(SKIN + "\n- **X1** written since the preview\n", encoding="utf-8")

    applied, problems = ia.apply_plan(kit, plan)
    assert not applied
    assert any("changed after the preview" in p for p in problems)
    assert (kit / "ledger.config.md").read_bytes() == config_before


def test_an_already_stale_skin_stops_the_config_write_before_it_starts(kit, monkeypatch):
    # The pre-write check earns its place here: without it the window re-check would
    # still catch this, but only after writing the config and undoing it again.
    plan = _plan(kit)
    (kit / "content/_ledger/skin_rules.md").write_text(
        SKIN + "\n- **Z1** edited before the write\n", encoding="utf-8")
    attempted = []
    monkeypatch.setattr(ce, "apply",
                        lambda *args: attempted.append(args) or (_ for _ in ()).throw(
                            AssertionError("config was written despite a stale skin")))

    applied, problems = ia.apply_plan(kit, plan)
    assert not applied
    assert attempted == []


def test_a_skin_edited_during_the_write_window_is_not_overwritten(kit, monkeypatch):
    # The skin is checked before the config write; an edit arriving between the two
    # writes would otherwise be overwritten by bytes computed from what it used to hold.
    plan = _plan(kit)
    skin_path = kit / "content/_ledger/skin_rules.md"
    config_before = (kit / "ledger.config.md").read_bytes()
    edited = SKIN + "\n- **Z9** written during the window\n"
    real = ce.apply

    def apply_then_edit(path, updates, expect):
        out = real(path, updates, expect)
        skin_path.write_text(edited, encoding="utf-8")
        return out

    monkeypatch.setattr(ce, "apply", apply_then_edit)
    applied, problems = ia.apply_plan(kit, plan)

    assert not applied
    assert any("changed after the preview" in p for p in problems)
    assert skin_path.read_text(encoding="utf-8") == edited
    assert (kit / "ledger.config.md").read_bytes() == config_before


def _verify_after_editing(path: Path, text: str):
    """A verification failure that races an outside edit to `path`, so rollback meets
    content init did not write."""
    def verify(root):
        (root / path).write_text(text, encoding="utf-8")
        return ["doctor says no"]
    return verify


THEIRS = "# somebody else's edit, made after init wrote\n"


def test_a_config_edited_after_init_wrote_it_survives_rollback(kit, monkeypatch):
    # Restoring `before` unconditionally would revert an edit init never saw.
    monkeypatch.setattr(ia, "_verify",
                        _verify_after_editing(Path("ledger.config.md"), THEIRS))
    applied, problems = ia.apply_plan(kit, _plan(kit))

    assert not applied
    assert (kit / "ledger.config.md").read_text(encoding="utf-8") == THEIRS
    assert any("Rollback INCOMPLETE" in p for p in problems)
    assert any("ledger.config.md no longer holds what init wrote" in p for p in problems)


def test_a_skin_edited_after_init_wrote_it_survives_rollback(kit, monkeypatch):
    skin = Path("content/_ledger/skin_rules.md")
    config_before = (kit / "ledger.config.md").read_bytes()
    monkeypatch.setattr(ia, "_verify", _verify_after_editing(skin, THEIRS))
    applied, problems = ia.apply_plan(kit, _plan(kit))

    assert not applied
    assert (kit / skin).read_text(encoding="utf-8") == THEIRS
    assert any("Rollback INCOMPLETE" in p for p in problems)
    # The config, which nobody else touched, is still put back.
    assert (kit / "ledger.config.md").read_bytes() == config_before


def test_a_file_still_holding_what_init_wrote_is_restored(kit, monkeypatch):
    # The other side of the comparison: init's own bytes are safe to revert.
    before = _snapshot(kit)
    monkeypatch.setattr(ia, "_verify", lambda root: ["doctor says no"])
    _, problems = ia.apply_plan(kit, _plan(kit))

    assert _snapshot(kit) == before
    assert not any("INCOMPLETE" in p for p in problems)


def test_a_failed_rollback_is_reported_as_incomplete_not_as_success(kit, monkeypatch):
    # Saying "put back" before the restore runs states something that may be false.
    monkeypatch.setattr(ia, "_restore",
                        lambda targets: ["ledger.config.md could NOT be put back (ro)"])
    monkeypatch.setattr(ia, "_verify", lambda root: ["doctor says no"])
    _, problems = ia.apply_plan(kit, _plan(kit))

    assert any("Rollback INCOMPLETE" in p for p in problems)
    assert not any("Put back as it was" in p for p in problems)


def test_a_successful_rollback_says_so_only_after_restoring(kit, monkeypatch):
    monkeypatch.setattr(ia, "_verify", lambda root: ["doctor says no"])
    before = _snapshot(kit)
    _, problems = ia.apply_plan(kit, _plan(kit))

    assert any("Put back as it was" in p for p in problems)
    assert not any("INCOMPLETE" in p for p in problems)
    assert _snapshot(kit) == before


# --- containment: a link out of the project ----------------------------------------

def test_a_skin_behind_a_symlinked_parent_is_refused(kit, tmp_path):
    # The lexical check cannot see this: content/_ledger/ is a plain-looking relative
    # path whose parent leads elsewhere, so both the staging temp and the replace would
    # land outside the project.
    outside = tmp_path.parent / "outside_ledger"
    outside.mkdir()
    (outside / "skin_rules.md").write_text(SKIN, encoding="utf-8")
    (kit / "content" / "linked").symlink_to(outside, target_is_directory=True)

    text = _config(skin_rules_file="content/linked/skin_rules.md")
    (kit / "ledger.config.md").write_text(text, encoding="utf-8")
    plan = ip.build(text, SKIN, ANSWERS, RULES)

    assert ia.escapes_root(kit, "content/linked/skin_rules.md")
    applied, problems = ia.apply_plan(kit, plan)
    assert not applied
    assert any("resolves outside the project" in p for p in problems)
    assert (outside / "skin_rules.md").read_text(encoding="utf-8") == SKIN


def test_a_symlinked_skin_is_refused_even_when_it_points_inside(kit):
    # An atomic replace swaps the directory entry: the link would become a regular file
    # and be lost. escapes_root cannot see this — the link resolves inside the project.
    real = kit / "content/_ledger/real_skin.md"
    link = kit / "content/_ledger/skin_rules.md"
    real.write_text(SKIN, encoding="utf-8")
    link.rename(kit / "content/_ledger/kept_original.md")
    link.symlink_to(real)
    plan = _plan(kit)

    applied, problems = ia.apply_plan(kit, plan)
    assert not applied
    assert any("is a symlink" in p for p in problems)
    assert link.is_symlink()
    assert real.read_text(encoding="utf-8") == SKIN


def test_a_symlinked_config_is_refused(kit, tmp_path):
    real = tmp_path.parent / "real_config.md"
    real.write_text(_config(), encoding="utf-8")
    link = kit / "ledger.config.md"
    plan = _plan(kit)
    link.rename(kit / "kept_config.md")
    link.symlink_to(real)

    applied, problems = ia.apply_plan(kit, plan)
    assert not applied
    assert any("is a symlink" in p for p in problems)
    assert link.is_symlink()
    assert real.read_text(encoding="utf-8") == _config()


def test_recovery_instructions_name_the_skins_project_relative_path(kit, monkeypatch):
    monkeypatch.setattr(ia, "_restore", lambda targets: [f"{t.name} failed"
                                                         for t in targets])
    monkeypatch.setattr(ia, "_verify", lambda root: ["nope"])
    _, problems = ia.apply_plan(kit, _plan(kit))
    assert any("content/_ledger/skin_rules.md failed" in p for p in problems)
    assert not any(p.strip().startswith("skin_rules.md") for p in problems)


def test_a_path_inside_the_project_is_contained(kit):
    assert not ia.escapes_root(kit, "content/_ledger/skin_rules.md")
    assert not ia.escapes_root(kit, "content/concept_notes/")
    assert ia.containment_problems(
        kit, (kit / "ledger.config.md").read_text(encoding="utf-8")) == []


def test_a_gated_directory_behind_a_symlink_is_refused(kit, tmp_path):
    outside = tmp_path.parent / "outside_gated"
    outside.mkdir()
    (kit / "content" / "linked_gate").symlink_to(outside, target_is_directory=True)
    text = _config(gated_paths="content/linked_gate/")
    assert any("resolves outside" in p for p in ia.containment_problems(kit, text))


# --- verification and rollback ------------------------------------------------------

def test_a_project_whose_declaration_contradicts_it_is_rolled_back(kit):
    # A real incoherence, not an injected one: filling the config over a skin someone
    # already wrote leaves the project looking configured while project_state still says
    # pristine, which doctor calls broken. init never writes project_state, so it cannot
    # resolve that itself — it must put the file back and say so.
    (kit / "content/_ledger/skin_rules.md").write_text(
        SKIN.replace(ld.SKIN_EMPTY_MARKER, "- **P1** a rule its author wrote"),
        encoding="utf-8")
    before = _snapshot(kit)

    applied, problems = ia.apply_plan(kit, _plan(kit, rules=[], reconfigure=True))
    assert not applied
    assert any("broken" in p for p in problems)
    assert _snapshot(kit) == before


def test_a_project_left_incoherent_is_rolled_back(kit, monkeypatch):
    before = _snapshot(kit)
    monkeypatch.setattr(ia, "_verify", lambda root: ["doctor says no"])
    applied, problems = ia.apply_plan(kit, _plan(kit))
    assert not applied
    assert any("doctor says no" in p for p in problems)
    assert _snapshot(kit) == before


def test_a_failed_skin_write_puts_the_config_back(kit, monkeypatch):
    before = _snapshot(kit)
    real = ce.write_atomically

    def fail_on_skin(path, text):
        if path.name == "skin_rules.md":
            raise OSError("disk full")
        return real(path, text)

    monkeypatch.setattr(ce, "write_atomically", fail_on_skin)
    applied, problems = ia.apply_plan(kit, _plan(kit))
    assert not applied
    assert _snapshot(kit) == before


def test_rollback_restores_bytes_exactly(kit, monkeypatch):
    config_before = (kit / "ledger.config.md").read_bytes()
    monkeypatch.setattr(ia, "_verify", lambda root: ["nope"])
    ia.apply_plan(kit, _plan(kit))
    assert (kit / "ledger.config.md").read_bytes() == config_before


def test_verification_rejects_a_configured_project_with_lax_postures(kit):
    # diagnose() calls this `configured`, but a configured project is strict by
    # definition and the real doctor fails it — so init must not leave it behind.
    (kit / "ledger.config.md").write_text(
        _config(project_name="p", deliverable="report",
                source_of_truth="markdown+quartz", the_reader="r", source_types="s",
                project_state="configured", skin_state="confirmed"), encoding="utf-8")
    (kit / "content/_ledger/skin_rules.md").write_text(
        SKIN.replace(ld.SKIN_EMPTY_MARKER, "- **P1** a rule"), encoding="utf-8")
    before = _snapshot(kit)

    applied, problems = ia.apply_plan(kit, _plan(kit, rules=[], reconfigure=True))
    assert not applied
    assert any("claim_ids" in p for p in problems)
    assert _snapshot(kit) == before


def test_verification_accepts_a_reconfigured_configured_project(kit):
    # The skin init leaves alone keeps its own state, so doctor still reads `configured`.
    ia.apply_plan(kit, _plan(kit))
    path = kit / "ledger.config.md"
    text = path.read_text(encoding="utf-8")
    path.write_text(ce.render(text, {"project_state": "configured",
                                     "skin_state": "confirmed", **STRICT}),
                    encoding="utf-8")
    applied, problems = ia.apply_plan(
        kit, _plan(kit, answers={**ANSWERS, "deliverable": "report"}, rules=[],
                   reconfigure=True))
    assert (applied, problems) == (True, [])
    values = {l.key: l.value for l in
              ce.scan(path.read_text(encoding="utf-8"))}
    assert values["deliverable"] == "report"
    assert values["skin_state"] == "confirmed"
    assert ld.diagnose(values, kit)[0] == "configured"
