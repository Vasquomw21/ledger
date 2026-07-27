# Tests for the `ledger init` workflow: what it parses, what it asks, what it refuses to
# assume, and that a preview never writes.
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import config_edit as ce
import ledger_cli as lc
import ledger_doctor as ld

# Every field, so nothing is left to prompt for and a reply queue is consumed only by the
# rules and the confirmation.
ANSWER_FLAGS = ["--set", "project_name=water_policy_ke",
                "--set", "deliverable=policy white paper",
                "--set", "source_of_truth=markdown+quartz",
                "--set", "the_reader=a busy minister",
                "--set", "source_types=legislation & gov reports",
                "--set", "unpaywall_email=someone@example.org"]
RULE = "abstraction vs allocation: a licensed volume is not water actually taken"

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


@pytest.fixture
def kit(tmp_path):
    (tmp_path / "ledger.config.md").write_text(_config(), encoding="utf-8")
    skin = tmp_path / "content" / "_ledger" / "skin_rules.md"
    skin.parent.mkdir(parents=True)
    skin.write_text(SKIN, encoding="utf-8")
    for gated in ("concept_notes", "literature_reviews"):
        (tmp_path / "content" / gated).mkdir()
    return tmp_path


def _tty(monkeypatch, is_tty: bool, replies=()):
    """Stand in for a terminal. `replies` are consumed by input() in order."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: is_tty)
    queue = list(replies)
    monkeypatch.setattr("builtins.input", lambda *_: queue.pop(0) if queue else "")


def _tty_until(monkeypatch, replies, giving_up):
    """A terminal that answers `replies`, then raises — somebody walking away mid-answer.
    Returns the prompts it was asked, so a run that carried on regardless is visible."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    queue = list(replies)
    asked: list = []

    def _input(prompt=""):
        asked.append(prompt)
        if queue:
            return queue.pop(0)
        raise giving_up
    monkeypatch.setattr("builtins.input", _input)
    return asked


def _snapshot(root):
    return {p.relative_to(root): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


def _values(root):
    text = (root / "ledger.config.md").read_text(encoding="utf-8")
    return {line.key: line.value for line in ce.scan(text)}


# --- routing ----------------------------------------------------------------------

def test_init_is_routed_and_advertised():
    assert "ledger init" in lc.USAGE
    assert lc.main(["init", "--help"]) == 0


def test_init_outside_a_project_is_not_a_project(tmp_path, capsys):
    assert lc.main(["init", str(tmp_path)]) == 2


# --- parsing ----------------------------------------------------------------------

def test_set_takes_its_value_and_is_not_read_as_a_dir(kit):
    request = lc._parse_init(["--set", "project_name=x", str(kit)], kit)
    assert request.root == kit
    assert request.answers == {"project_name": "x"}


def test_rules_accumulate_in_order(kit):
    request = lc._parse_init(["--rule", "first", "--rule", "second"], kit)
    assert request.rules == ["first", "second"]


def test_a_value_flag_at_the_end_is_reported(kit):
    assert lc._parse_init(["--set"], kit) == 2


def test_a_malformed_set_is_reported(kit, capsys):
    assert lc._parse_init(["--set", "noequals"], kit) == 2
    assert "key=value" in capsys.readouterr().err


def test_an_unknown_option_is_reported(kit, capsys):
    assert lc._parse_init(["--force"], kit) == 2
    assert "unknown option" in capsys.readouterr().err


def test_a_second_positional_is_reported(kit):
    assert lc._parse_init([str(kit), "extra"], kit) == 2


# --- what init will not assume ----------------------------------------------------

def test_a_missing_field_without_a_terminal_names_every_one(kit, monkeypatch, capsys):
    _tty(monkeypatch, False)
    assert lc.main(["init", str(kit)]) == 2
    err = capsys.readouterr().err
    for field in ("project_name", "deliverable", "source_of_truth", "the_reader",
                  "source_types"):
        assert field in err


def test_a_mistyped_field_is_named_rather_than_dropped(kit, monkeypatch, capsys):
    # Silently ignoring it would leave the run asking for the field it replaced.
    _tty(monkeypatch, False)
    assert lc.main(["init", str(kit), "--set", "project-name=x"]) == 2
    assert "not a field init sets" in capsys.readouterr().err


def test_a_non_terminal_is_never_consent(kit, monkeypatch, capsys):
    _tty(monkeypatch, False)
    before = _snapshot(kit)
    assert lc.main(["init", str(kit), *ANSWER_FLAGS]) == 2
    assert "nobody to confirm to" in capsys.readouterr().err
    assert _snapshot(kit) == before


def test_declining_at_the_prompt_writes_nothing(kit, monkeypatch):
    _tty(monkeypatch, True, replies=["n"])
    before = _snapshot(kit)
    assert lc.main(["init", str(kit), *ANSWER_FLAGS, "--rule", RULE]) == 0
    assert _snapshot(kit) == before


def test_dry_run_writes_nothing(kit, monkeypatch, capsys):
    _tty(monkeypatch, False)
    before = _snapshot(kit)
    assert lc.main(["init", str(kit), *ANSWER_FLAGS, "--rule", RULE, "--dry-run"]) == 0
    assert "nothing was written" in capsys.readouterr().out
    assert _snapshot(kit) == before


# --- prompting --------------------------------------------------------------------

def test_unanswered_fields_are_asked_for(kit, monkeypatch):
    _tty(monkeypatch, True, replies=["water_policy_ke", "report", "markdown+quartz",
                                     "a minister", "gov reports", "",   # optional email
                                     RULE, "",                          # rules, then stop
                                     "y"])                              # confirm
    assert lc.main(["init", str(kit)]) == 0
    assert _values(kit)["project_name"] == "water_policy_ke"
    assert RULE in (kit / "content/_ledger/skin_rules.md").read_text(encoding="utf-8")


def test_the_optional_field_may_be_skipped(kit, monkeypatch):
    _tty(monkeypatch, True, replies=["p", "report", "markdown+quartz", "r", "s", "",
                                     "", "y"])
    assert lc.main(["init", str(kit)]) == 0
    assert "unpaywall_email" not in [k for k, v in _values(kit).items()
                                     if not v.startswith("<")]


def test_declining_the_rules_prompt_leaves_an_honest_draft(kit, monkeypatch):
    # Filler would be worse than an empty skin; declining must stay possible.
    skin_before = (kit / "content/_ledger/skin_rules.md").read_bytes()
    _tty(monkeypatch, True, replies=["p", "report", "markdown+quartz", "r", "s", "",
                                     "", "y"])
    assert lc.main(["init", str(kit)]) == 0
    assert _values(kit)["skin_state"] == "draft"
    assert (kit / "content/_ledger/skin_rules.md").read_bytes() == skin_before
    assert ld.diagnose(_values(kit), kit)[0] == "drafted"


@pytest.mark.parametrize("giving_up", [KeyboardInterrupt, EOFError])
def test_giving_up_at_the_rules_prompt_writes_nothing(kit, monkeypatch, giving_up):
    # Ctrl-C is not an empty line. With every field answered and --yes there is nothing
    # left to stop the run, so treating "gave up" as "no more rules" would write.
    before = _snapshot(kit)
    _tty_until(monkeypatch, replies=[], giving_up=giving_up)
    assert lc.main(["init", str(kit), *ANSWER_FLAGS, "--yes"]) == 2
    assert _snapshot(kit) == before


@pytest.mark.parametrize("giving_up", [KeyboardInterrupt, EOFError])
def test_giving_up_while_answering_a_field_stops_at_once(kit, monkeypatch, capsys,
                                                         giving_up):
    # Stopping is asserted through the prompts, not the exit code: reading a cancel as an
    # empty answer also exits 2 — build() rejects the fields it then leaves blank — so a
    # run that ignored the cancel and interrogated every remaining field would look
    # identical from the outside.
    before = _snapshot(kit)
    asked = _tty_until(monkeypatch, replies=["water_policy_ke"], giving_up=giving_up)
    assert lc.main(["init", str(kit), "--yes"]) == 2
    assert len(asked) == 2
    assert "cancelled" in capsys.readouterr().err
    assert _snapshot(kit) == before


def test_an_empty_rule_line_finishes_rather_than_cancelling(kit, monkeypatch):
    # The other half of the distinction: Enter still means "no more rules", and the run
    # goes on to apply. Without this, cancelling on any falsy reply would pass the two
    # tests above.
    _tty(monkeypatch, True, replies=[RULE, ""])
    assert lc.main(["init", str(kit), *ANSWER_FLAGS, "--yes"]) == 0
    assert RULE in (kit / "content/_ledger/skin_rules.md").read_text(encoding="utf-8")


def test_rules_given_as_flags_are_not_prompted_for(kit, monkeypatch):
    asked = []

    def reply(prompt=""):
        # Bounded on purpose: answering every prompt "y" would let a re-prompting bug
        # loop forever instead of failing.
        asked.append(prompt)
        return "" if "Rule" in prompt else "y"

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", reply)
    assert lc.main(["init", str(kit), *ANSWER_FLAGS, "--rule", RULE]) == 0
    # Any rule prompt, not just the first: a run that already holds one rule would ask
    # for "Rule 2".
    assert not any(prompt.startswith("Rule ") for prompt in asked)


# --- the whole workflow -----------------------------------------------------------

def test_a_configured_clone_lands_drafted_with_the_rules_in_the_skin(kit, monkeypatch):
    _tty(monkeypatch, False)
    assert lc.main(["init", str(kit), *ANSWER_FLAGS, "--rule", RULE, "--yes"]) == 0

    values = _values(kit)
    assert values["project_name"] == "water_policy_ke"
    assert values["skin_state"] == "draft"
    assert values["project_state"] == "pristine"      # never written by init
    assert ld.diagnose(values, kit)[0] == "drafted"

    skin = (kit / "content/_ledger/skin_rules.md").read_text(encoding="utf-8")
    assert RULE in skin
    assert "Worked example" not in skin


def test_a_second_run_needs_reconfigure(kit, monkeypatch, capsys):
    _tty(monkeypatch, False)
    lc.main(["init", str(kit), *ANSWER_FLAGS, "--rule", RULE, "--yes"])
    assert lc.main(["init", str(kit), *ANSWER_FLAGS, "--yes"]) == 2
    assert "--reconfigure" in capsys.readouterr().err


def test_reconfigure_re_answers_the_config_and_leaves_the_rules(kit, monkeypatch):
    _tty(monkeypatch, False)
    lc.main(["init", str(kit), *ANSWER_FLAGS, "--rule", RULE, "--yes"])
    skin_before = (kit / "content/_ledger/skin_rules.md").read_bytes()

    assert lc.main(["init", str(kit), "--reconfigure", "--yes",
                    "--set", "project_name=renamed", "--set", "deliverable=report",
                    "--set", "source_of_truth=markdown+quartz",
                    "--set", "the_reader=r", "--set", "source_types=s"]) == 0
    assert _values(kit)["project_name"] == "renamed"
    assert (kit / "content/_ledger/skin_rules.md").read_bytes() == skin_before


def test_an_unusable_answer_is_refused_before_any_write(kit, monkeypatch, capsys):
    _tty(monkeypatch, False)
    before = _snapshot(kit)
    assert lc.main(["init", str(kit), "--yes",
                    "--set", "project_name=x", "--set", "deliverable=report",
                    "--set", "source_of_truth=markdown + quartz",
                    "--set", "the_reader=r", "--set", "source_types=s"]) == 2
    assert "source_of_truth" in capsys.readouterr().err
    assert _snapshot(kit) == before


def test_filler_offered_as_a_rule_is_refused(kit, monkeypatch, capsys):
    _tty(monkeypatch, False)
    assert lc.main(["init", str(kit), *ANSWER_FLAGS, "--rule", "TBD", "--yes"]) == 2
    assert "placeholder" in capsys.readouterr().err


def test_a_missing_skin_is_refused_by_the_verb_too(kit, monkeypatch, capsys):
    _tty(monkeypatch, False)
    (kit / "content/_ledger/skin_rules.md").rename(kit / "content/_ledger/moved.md")
    assert lc.main(["init", str(kit), *ANSWER_FLAGS, "--rule", RULE, "--yes"]) == 2
    assert "skin_rules.md is not there" in " ".join(capsys.readouterr().err.split())


# --- what init says it left -------------------------------------------------------

def _declare_finished(kit):
    """Handoff step 3, the one step with no command to run."""
    ce.apply(kit / "ledger.config.md", lc.CONFIRMED,
             ce.digest((kit / "ledger.config.md").read_text(encoding="utf-8")))


def test_the_success_line_names_the_drafted_state_a_first_run_leaves(kit, monkeypatch,
                                                                     capsys):
    _tty(monkeypatch, False)
    assert lc.main(["init", str(kit), *ANSWER_FLAGS, "--rule", RULE, "--yes"]) == 0
    assert "project state: drafted" in capsys.readouterr().out
    assert ld.diagnose(_values(kit), kit)[0] == "drafted"


def test_a_reconfigure_that_lands_configured_says_so_and_drops_the_handoff(kit,
                                                                          monkeypatch,
                                                                          capsys):
    # The path that makes a hardcoded state a lie: --reconfigure leaves a confirmed skin
    # alone, so the project stays configured and the five steps are already behind it.
    _tty(monkeypatch, False)
    lc.main(["init", str(kit), *ANSWER_FLAGS, "--rule", RULE, "--yes"])
    lc.main(["config", "set", "profile", lc.STRICT_PROFILE, str(kit), "--yes"])
    _declare_finished(kit)
    capsys.readouterr()

    assert lc.main(["init", str(kit), "--reconfigure", "--yes",
                    "--set", "project_name=renamed", "--set", "deliverable=report",
                    "--set", "source_of_truth=markdown+quartz",
                    "--set", "the_reader=r", "--set", "source_types=s"]) == 0
    out = capsys.readouterr().out
    assert "project state: configured" in out
    assert lc.HANDOFF[0] not in " ".join(out.split())


# --- the handoff ------------------------------------------------------------------

def test_every_command_the_handoff_names_is_routable():
    # A handoff step nobody can run is worse than no handoff.
    known = set(lc.DISPATCH) | {"profiles", "check", "demo", "inspect", "config", "init"}
    verbs = {v for step in lc.HANDOFF for v in re.findall(r"`ledger ([a-z-]+)", step)}
    assert verbs                                    # the steps really do name commands
    assert verbs <= known, verbs - known


def test_the_configuration_doc_teaches_the_same_lifecycle_init_prints():
    # Narrow on purpose: prose is free to move, but the doc naming a profile the code has
    # renamed would walk a reader into the failure the handoff exists to prevent.
    doc = (REPO_ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
    assert lc.STRICT_PROFILE in doc
    for key, value in lc.CONFIRMED.items():
        assert f"{key}: {value}" in doc or f"`{key}: {value}`" in doc, key


def test_the_handoff_names_the_strict_postures_init_leaves_alone():
    # configured ⟹ strict, and init adopts no postures on the author's behalf, so a
    # handoff that stops at the declaration walks them into a project the doctor rejects.
    assert lc.STRICT_PROFILE in " ".join(lc.HANDOFF)


def test_the_success_message_prints_every_handoff_step_in_order(kit, monkeypatch, capsys):
    # Without this the constants could stay right while nothing rendered them.
    _tty(monkeypatch, False)
    assert lc.main(["init", str(kit), *ANSWER_FLAGS, "--rule", RULE, "--yes"]) == 0
    printed = " ".join(capsys.readouterr().out.split())
    at = [printed.find(" ".join(step.split())) for step in lc.HANDOFF]
    assert all(where >= 0 for where in at), lc.HANDOFF
    assert at == sorted(at)


def test_declaring_it_finished_without_the_postures_is_rejected(kit, monkeypatch):
    # Step 3 without step 2 — the shortcut the handoff exists to head off.
    _tty(monkeypatch, False)
    assert lc.main(["init", str(kit), *ANSWER_FLAGS, "--rule", RULE, "--yes"]) == 0
    _declare_finished(kit)
    assert ld.blocking_problems(_values(kit), kit)


def test_following_the_handoff_in_order_reaches_a_project_the_doctor_accepts(
        kit, monkeypatch, capsys):
    _tty(monkeypatch, False)
    assert lc.main(["init", str(kit), *ANSWER_FLAGS, "--rule", RULE, "--yes"]) == 0
    # 1. the author's own judgement; init already wrote the rule it was handed.
    # 2., driven by the printed constant rather than a copy of it.
    assert lc.main(["config", "set", "profile", lc.STRICT_PROFILE, str(kit), "--yes"]) == 0
    _declare_finished(kit)                                                    # 3.
    assert ld.blocking_problems(_values(kit), kit) == []                      # 4.
    assert ld.diagnose(_values(kit), kit)[0] == "configured"
    capsys.readouterr()
    assert lc.main(["check", str(kit)]) in (0, 1)                             # 5.
    assert "Next:" in capsys.readouterr().out
