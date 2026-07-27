# Tests for the config mutation primitives: what the write path refuses, what it
# preserves, and that a refusal never reaches the disk.
import os
import stat
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import config_edit as ce

# The kit's own config, in miniature: aligned values, comment blocks above keys, and a
# comment line that itself contains colons — the shape that breaks a naive parser.
SAMPLE = ("# Ledger project config\n"
          "#\n"
          "project_name:        demo\n"
          "# Tracked project mode. bootstrap sets the five strict postures below\n"
          "# (claim_ids: required, numeric_citations: block, provenance: required).\n"
          "project_state:       pristine\n"
          "claim_ids:           optional\n"
          "numeric_citations:   warn\n"
          "semantic_max_age_days: 180\n")


# --- parsing --------------------------------------------------------------------

def test_scan_finds_every_key_and_no_prose():
    keys = [line.key for line in ce.scan(SAMPLE)]
    assert keys == ["project_name", "project_state", "claim_ids",
                    "numeric_citations", "semantic_max_age_days"]


def test_scan_ignores_colons_inside_comment_lines():
    # "# (claim_ids: required, ...)" must not register as a claim_ids declaration —
    # it would look like a duplicate and block every write to the file.
    assert [l.key for l in ce.scan(SAMPLE)].count("claim_ids") == 1
    assert ce.duplicate_keys(SAMPLE) == []


def test_parsed_line_round_trips_exactly():
    for raw in SAMPLE.split("\n"):
        parsed = ce._parse_line(raw)
        if parsed:
            assert parsed.pre + parsed.value + parsed.post == raw


@pytest.mark.parametrize("raw, key, value", [
    ("claim_ids: required", "claim_ids", "required"),
    ("  claim_ids:   required  ", "claim_ids", "required"),
    ("claim_ids:required", "claim_ids", "required"),
    ("claim_ids: required  # why", "claim_ids", "required"),
    ("source_of_truth: https://example.com/x", "source_of_truth",
     "https://example.com/x"),
])
def test_parse_line_shapes(raw, key, value):
    parsed = ce._parse_line(raw)
    assert parsed and (parsed.key, parsed.value) == (key, value)


@pytest.mark.parametrize("raw", ["", "   ", "# a comment", "  # indented comment",
                                 "no colon here", "- a bullet: with a colon"])
def test_parse_line_rejects_non_keys(raw):
    assert ce._parse_line(raw) is None


# --- duplicate detection --------------------------------------------------------

def test_duplicate_keys_are_found():
    text = SAMPLE + "claim_ids:           required\n"
    assert ce.duplicate_keys(text) == ["claim_ids"]


def test_a_duplicate_blocks_the_write_even_for_an_unrelated_key():
    # parse_config keeps the LAST occurrence, so the file already means something other
    # than it looks. Editing a different key would write into that ambiguity.
    text = SAMPLE + "claim_ids:           required\n"
    found = ce.problems(text, {"numeric_citations": "block"})
    assert found and "declared more than once" in found[0]


# --- validation: malformed targets ----------------------------------------------

@pytest.mark.parametrize("updates, fragment", [
    ({"claim_ids": "req\nuired"}, "spans lines"),
    ({"claim_ids": "required # yes"}, "'#'"),
    ({"claim_ids": ""}, "empty"),
    ({"claim_ids": "  required  "}, "whitespace"),
    ({"not a key": "x"}, "not a valid config key"),
])
def test_malformed_targets_are_refused(updates, fragment):
    found = ce.problems(SAMPLE, updates)
    assert any(fragment in problem for problem in found), found


def test_a_valid_update_has_no_problems():
    assert ce.problems(SAMPLE, {"claim_ids": "required"}) == []


# --- planning + idempotence -----------------------------------------------------

def test_plan_omits_keys_already_at_their_value():
    assert ce.plan(SAMPLE, {"claim_ids": "optional"}) == []


def test_plan_reports_a_change_and_an_addition():
    changes = ce.plan(SAMPLE, {"claim_ids": "required", "units_layer": "warn"})
    assert ce.Change("claim_ids", "optional", "required") in changes
    assert ce.Change("units_layer", None, "warn") in changes
    assert [c.adds for c in changes if c.key == "units_layer"] == [True]


def test_render_is_idempotent():
    once = ce.render(SAMPLE, {"claim_ids": "required"})
    assert ce.render(once, {"claim_ids": "required"}) == once


def test_render_of_a_no_op_returns_the_text_unchanged():
    assert ce.render(SAMPLE, {"claim_ids": "optional"}) is not None
    assert ce.render(SAMPLE, {"claim_ids": "optional"}) == SAMPLE


# --- byte preservation ----------------------------------------------------------

def test_render_changes_only_the_targeted_value():
    after = ce.render(SAMPLE, {"claim_ids": "required"})
    before_lines, after_lines = SAMPLE.split("\n"), after.split("\n")
    differing = [i for i, (b, a) in enumerate(zip(before_lines, after_lines)) if b != a]
    assert len(differing) == 1
    assert after_lines[differing[0]] == "claim_ids:           required"   # padding kept


def test_render_preserves_an_inline_comment():
    text = "claim_ids:  optional  # deliberately lax\n"
    assert ce.render(text, {"claim_ids": "required"}) == \
        "claim_ids:  required  # deliberately lax\n"


def test_render_preserves_a_value_containing_colons():
    text = "source_of_truth: https://example.com/a:b\nclaim_ids: optional\n"
    after = ce.render(text, {"claim_ids": "required"})
    assert "source_of_truth: https://example.com/a:b" in after


def test_render_can_set_a_value_containing_colons():
    after = ce.render("source_of_truth: old\n",
                      {"source_of_truth": "https://example.com/a:b"})
    assert after == "source_of_truth: https://example.com/a:b\n"


def test_render_preserves_a_missing_trailing_newline():
    text = "claim_ids: optional"                       # no trailing newline
    assert ce.render(text, {"claim_ids": "required"}) == "claim_ids: required"


def test_render_preserves_a_present_trailing_newline():
    assert ce.render(SAMPLE, {"claim_ids": "required"}).endswith("\n")


def test_an_appended_key_lands_before_the_trailing_newline():
    after = ce.render(SAMPLE, {"units_layer": "warn"})
    assert after.endswith("units_layer:         warn\n")
    assert after.count("\n") == SAMPLE.count("\n") + 1     # exactly one line added


def test_an_appended_key_matches_the_files_value_column():
    after = ce.render(SAMPLE, {"units_layer": "warn"})
    appended = [l for l in after.split("\n") if l.startswith("units_layer")][0]
    existing = [l for l in after.split("\n") if l.startswith("claim_ids")][0]
    assert appended.index("warn") == existing.index("optional") == ce.VALUE_COLUMN


def test_appending_to_a_file_without_a_trailing_newline():
    after = ce.render("claim_ids: optional", {"units_layer": "warn"})
    assert after == "claim_ids: optional\nunits_layer:         warn"


# --- diff -----------------------------------------------------------------------

def test_diff_is_empty_when_nothing_changes():
    assert ce.diff(SAMPLE, SAMPLE) == ""


def test_diff_shows_the_change():
    after = ce.render(SAMPLE, {"claim_ids": "required"})
    text = ce.diff(SAMPLE, after)
    assert "-claim_ids:           optional" in text
    assert "+claim_ids:           required" in text


# --- apply: the only writer -----------------------------------------------------

@pytest.fixture
def config_file(tmp_path):
    path = tmp_path / "ledger.config.md"
    path.write_text(SAMPLE, encoding="utf-8")
    return path


def _sha(path):
    return ce.digest(path.read_text(encoding="utf-8"))


def test_apply_writes_a_valid_change(config_file):
    changes, problems = ce.apply(config_file, {"claim_ids": "required"},
                                 _sha(config_file))
    assert problems == [] and len(changes) == 1
    assert "claim_ids:           required" in config_file.read_text()


def test_apply_never_writes_when_validation_fails(config_file):
    before = config_file.read_bytes()
    changes, problems = ce.apply(config_file, {"claim_ids": "bad\nvalue"},
                                 _sha(config_file))
    assert problems and changes == []
    assert config_file.read_bytes() == before      # no partial write to roll back


def test_apply_leaves_no_temp_file_behind(config_file):
    ce.apply(config_file, {"claim_ids": "required"}, _sha(config_file))
    assert [p.name for p in config_file.parent.iterdir()] == ["ledger.config.md"]


def test_apply_is_idempotent_and_does_not_touch_the_file(config_file):
    ce.apply(config_file, {"claim_ids": "required"}, _sha(config_file))
    stamp = config_file.stat().st_mtime_ns
    changes, problems = ce.apply(config_file, {"claim_ids": "required"},
                                 _sha(config_file))
    assert (changes, problems) == ([], [])
    assert config_file.stat().st_mtime_ns == stamp   # a no-op does not rewrite


def test_apply_refuses_a_duplicated_file_without_writing(config_file):
    config_file.write_text(SAMPLE + "claim_ids: required\n", encoding="utf-8")
    before = config_file.read_bytes()
    changes, problems = ce.apply(config_file, {"numeric_citations": "block"},
                                 _sha(config_file))
    assert problems and changes == []
    assert config_file.read_bytes() == before


def test_apply_result_reparses_to_the_requested_values(config_file):
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    from check_citations import parse_config

    updates = {"claim_ids": "required", "numeric_citations": "block",
               "units_layer": "warn"}
    ce.apply(config_file, updates, _sha(config_file))
    reparsed = parse_config(config_file)
    for key, value in updates.items():
        assert reparsed[key] == value, key


# --- the write is bound to the previewed bytes ----------------------------------

def test_apply_refuses_bytes_that_changed_since_the_preview(config_file):
    previewed = _sha(config_file)
    config_file.write_text(SAMPLE.replace("optional", "off"), encoding="utf-8")
    changed = config_file.read_bytes()
    updates = {"claim_ids": "required"}
    changes, problems = ce.apply(config_file, updates, previewed)
    assert changes == []
    assert problems and "changed after the preview" in problems[0]
    assert config_file.read_bytes() == changed     # untouched, not "fixed"


def test_a_stale_preview_is_refused_even_though_the_write_would_be_valid(config_file):
    # Re-validation alone would pass here: the edited file is well-formed and the update
    # applies cleanly. It is still the wrong change — the user approved `optional ->
    # required`, and this would silently write `off -> required` instead.
    previewed = _sha(config_file)
    config_file.write_text(SAMPLE.replace("optional", "off"), encoding="utf-8")
    assert ce.problems(config_file.read_text(), {"claim_ids": "required"}) == []
    changes, problems = ce.apply(config_file, {"claim_ids": "required"}, previewed)
    assert (changes, bool(problems)) == ([], True)


def test_digest_matches_the_file_that_produced_it(config_file):
    assert ce.digest(SAMPLE) == _sha(config_file)
    assert ce.digest(SAMPLE) != ce.digest(SAMPLE + "x")


# --- permissions ----------------------------------------------------------------

@pytest.mark.parametrize("mode", [0o600, 0o640, 0o644])
def test_apply_preserves_the_files_permissions(config_file, mode):
    # A fresh temp file takes the umask, so an unguarded replace WIDENS a config the
    # user had restricted.
    os.chmod(config_file, mode)
    ce.apply(config_file, {"claim_ids": "required"}, _sha(config_file))
    assert stat.S_IMODE(config_file.stat().st_mode) == mode


def test_the_temp_file_is_never_wider_than_the_target(config_file, monkeypatch):
    # The temp holds the full contents before the replace; created under the umask it
    # would be briefly world-readable even when the target is 0600.
    os.chmod(config_file, 0o600)
    seen = {}
    real_replace = os.replace

    def spy(src, dst):
        seen["mode"] = stat.S_IMODE(os.stat(src).st_mode)
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy)
    ce.apply(config_file, {"claim_ids": "required"}, _sha(config_file))
    assert seen["mode"] == 0o600


# --- the staging path is never followed or clobbered ----------------------------

def test_a_pre_existing_temp_file_blocks_the_write_and_survives(config_file):
    # The staging path is predictable. Without O_EXCL it is opened, truncated, and then
    # consumed by the replace — destroying whatever was there.
    stale = ce.temp_path(config_file)
    stale.write_text("someone else's data", encoding="utf-8")
    before = config_file.read_bytes()

    changes, problems = ce.apply(config_file, {"claim_ids": "required"},
                                 _sha(config_file))

    assert changes == [] and problems and "already occupied" in problems[0]
    assert stale.read_text() == "someone else's data"    # untouched, not cleared
    assert config_file.read_bytes() == before


def test_a_symlink_at_the_temp_path_is_refused_and_its_target_untouched(config_file):
    # The dangerous shape: a followed symlink would leave an unrelated file containing
    # this config, with the command reporting success.
    victim = config_file.parent / "victim.txt"
    victim.write_text("important unrelated data", encoding="utf-8")
    link = ce.temp_path(config_file)
    os.symlink(victim, link)
    before = config_file.read_bytes()

    changes, problems = ce.apply(config_file, {"claim_ids": "required"},
                                 _sha(config_file))

    assert changes == [] and problems and "already occupied" in problems[0]
    assert victim.read_text() == "important unrelated data"
    assert link.is_symlink()                             # left as found, not removed
    assert config_file.read_bytes() == before


def test_a_dangling_symlink_at_the_temp_path_is_also_refused(config_file):
    # O_CREAT|O_EXCL refuses a symlink whether or not its target exists, so a link
    # pointing at a path that does not exist yet cannot be used to create one.
    link = ce.temp_path(config_file)
    os.symlink(config_file.parent / "does-not-exist", link)
    before = config_file.read_bytes()

    changes, problems = ce.apply(config_file, {"claim_ids": "required"},
                                 _sha(config_file))

    assert changes == [] and problems
    assert not (config_file.parent / "does-not-exist").exists()
    assert config_file.read_bytes() == before


def test_the_refusal_names_the_path_and_does_not_offer_to_clear_it(config_file):
    stale = ce.temp_path(config_file)
    stale.write_text("x", encoding="utf-8")
    _changes, problems = ce.apply(config_file, {"claim_ids": "required"},
                                  _sha(config_file))
    assert stale.name in problems[0]
    assert "yourself" in problems[0]


# --- malformed existing config --------------------------------------------------

def test_a_dropped_colon_is_reported_not_silently_duplicated():
    # `claim_ids required` is skipped by every reader, so the posture falls to its
    # kernel default while the line still reads as a declaration to a human.
    text = "claim_ids required\nnumeric_citations:   warn\n"
    assert ce.malformed_lines(text) == [(1, "claim_ids required")]
    found = ce.problems(text, {"claim_ids": "required"})
    assert found and "line 1" in found[0]


def test_apply_refuses_a_malformed_config_without_writing(config_file):
    config_file.write_text("claim_ids required\n", encoding="utf-8")
    before = config_file.read_bytes()
    changes, problems = ce.apply(config_file, {"claim_ids": "required"},
                                 _sha(config_file))
    assert problems and changes == []
    assert config_file.read_bytes() == before


@pytest.mark.parametrize("raw", ["claim_ids required", "- a bullet", "some prose here",
                                 "claim_ids;  required"])
def test_non_declaration_lines_are_malformed(raw):
    assert ce.malformed_lines(f"{raw}\n") == [(1, raw)]


@pytest.mark.parametrize("raw", ["claim_ids: required", "  claim_ids: required",
                                 "# a comment", "  # indented comment", "",
                                 "# claim_ids: required"])
def test_comments_blanks_and_indented_declarations_are_not_malformed(raw):
    # Indented declarations are VALID: parse_config strips before partitioning, so every
    # gate reads them. Rejecting them would refuse a file the readers accept.
    assert ce.malformed_lines(f"{raw}\n") == []


def test_the_kits_own_config_is_well_formed():
    assert ce.malformed_lines((REPO_ROOT / "ledger.config.md").read_text()) == []
    assert ce.duplicate_keys((REPO_ROOT / "ledger.config.md").read_text()) == []
