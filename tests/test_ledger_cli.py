# Tests for the ledger CLI dispatcher (ergonomics). No subprocess: we exercise the
# pure routing/profile/demo-wiring logic and assert the dispatch table is consistent
# with the tools actually on disk.
import importlib
import os
import re
import stat
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import ledger_cli as lc
from postures import POSTURE_KEYS

# Where each posture is really read. `ledger check` re-implements this resolution to
# decide what to DISPLAY, so it must agree with the gates themselves.
POSTURE_READERS = {
    "claim_ids": ("check_citations", "claim_mode"),
    "numeric_citations": ("check_citations", "numeric_mode"),
    "provenance": ("check_manifest", "provenance_mode"),
    "structure_layer": ("check_structure", "structure_mode"),
    "assessment_layer": ("check_assessment", "assessment_mode"),
    "graph_coverage": ("check_coverage", "coverage_mode"),
    "edge_assessments": ("check_assessment", "edge_assessment_mode"),
    "selection_audit": ("check_selection", "selection_mode"),
    "source_flow": ("check_source_flow", "source_flow_mode"),
    "units_layer": ("check_units", "units_mode"),
    "synthesis_claims": ("check_synthesis", "synthesis_mode"),
    "semantic_health": ("ledger_doctor", "semantic_mode"),
    "attestation": ("check_attestation", "attestation_mode"),
}


def _reader(key):
    module, func = POSTURE_READERS[key]
    return getattr(importlib.import_module(module), func)


@pytest.fixture
def project(tmp_path):
    """A minimal Ledger project. Strictness and gate results are monkeypatched per
    test — here we only need the shape `check` reads off disk."""
    def _make(ledgers=(), corpus=False, config="project_name: t\n"):
        (tmp_path / "ledger.config.md").write_text(config, encoding="utf-8")
        (tmp_path / "content").mkdir(exist_ok=True)
        claims = tmp_path / "literature" / "verified_claims"
        claims.mkdir(parents=True, exist_ok=True)
        for name in ledgers:
            (claims / f"{name}.md").write_text("x", encoding="utf-8")
        if corpus:
            extracted = tmp_path / "literature" / "extracted"
            extracted.mkdir(parents=True, exist_ok=True)
            (extracted / "a.txt").write_text("x", encoding="utf-8")
        return tmp_path
    return _make


@pytest.fixture
def green(monkeypatch):
    """Make every gate pass without spawning 13 subprocesses. Returns the recorded
    (rel, args) calls so a test can assert HOW a gate was invoked."""
    calls = []

    def _make(rc=0, stream=""):
        def fake_capture(root, rel, args):
            calls.append((rel, args))
            return lc.Captured(rc, stream, "")
        monkeypatch.setattr(lc, "_capture", fake_capture)
        monkeypatch.setattr(lc, "_command", lambda root, rel, args: ["true"])
        return calls
    return _make


def test_usage_on_no_args(capsys):
    assert lc.main([]) == 0
    assert "ledger" in capsys.readouterr().out


def test_unknown_command_errors():
    assert lc.main(["definitely-not-a-command"]) == 2


def test_dispatch_targets_all_exist():
    missing = [rel for rel in lc.DISPATCH.values() if not (REPO_ROOT / rel).is_file()]
    assert missing == []


def test_demo_steps_reference_known_commands():
    assert all(cmd in lc.DISPATCH for _label, cmd, _extra in lc.DEMO_STEPS)


def test_demo_runs_every_precommit_gate():
    # Every pre-commit gate is a demo step, so no failing gate hides behind a green tour.
    invoke_re = re.compile(r"(?:tools|literature)/(\w+)\.py")
    gates = set()
    for line in (REPO_ROOT / ".githooks" / "pre-commit").read_text().splitlines():
        if line.lstrip().startswith("#") or "echo " in line:
            continue
        gates.update(invoke_re.findall(line))
    demo_tools = {Path(lc.DISPATCH[cmd]).stem for _l, cmd, _e in lc.DEMO_STEPS}
    assert gates - demo_tools == set(), \
        f"pre-commit gates missing from the demo tour: {sorted(gates - demo_tools)}"


def test_profiles_list(capsys):
    assert lc.main(["profiles"]) == 0
    out = capsys.readouterr().out
    assert "submission" in out and "pristine" in out


def test_profiles_named_prints_postures(capsys):
    assert lc.main(["profiles", "submission"]) == 0
    out = capsys.readouterr().out
    assert "selection_audit" in out and "required" in out


def test_profiles_unknown_errors():
    assert lc.main(["profiles", "no-such-profile"]) == 2


def test_every_profile_sets_the_same_postures():
    keys = [set(p) for p in lc.PROFILES.values()]
    assert all(k == keys[0] for k in keys)      # no profile silently omits a posture


def test_profiles_cover_every_registry_posture():
    # A profile is a copy-paste config block; it must set every posture in the
    # canonical registry (plus project_state), so none silently defaults.
    for name, prof in lc.PROFILES.items():
        assert set(prof) - {"project_state"} == set(POSTURE_KEYS), f"profile {name}"


def test_configured_profiles_are_doctor_valid():
    # configured ⟹ strict (ledger_doctor hard-fails otherwise): a profile that
    # declares `configured` must set all five strict postures at their block value.
    strict = {"claim_ids": "required", "numeric_citations": "block",
              "provenance": "required", "structure_layer": "required",
              "assessment_layer": "required"}
    for name, prof in lc.PROFILES.items():
        if prof.get("project_state") == "configured":
            lax = {k: prof.get(k) for k, v in strict.items() if prof.get(k) != v}
            assert not lax, f"configured profile {name} is doctor-invalid: {lax}"


def test_dashboard_accepts_positional_dir(tmp_path, monkeypatch):
    # `ledger dashboard <DIR>` (as DEMO.md documents) must resolve the positional to
    # the project root, not forward it as a bare arg judge_dashboard would reject.
    (tmp_path / "ledger.config.md").write_text("project_name: t\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(lc, "_run",
                        lambda root, rel, args: calls.append((root, rel, args)) or 0)
    assert lc.main(["dashboard", str(tmp_path)]) == 0
    root, rel, args = calls[-1]
    assert rel == lc.DISPATCH["dashboard"]
    assert root == tmp_path.resolve()           # positional DIR became the project root
    assert args == []                           # stripped, not forwarded


def test_dashboard_rejects_nonexistent_project():
    # A bare dir would otherwise render an empty page and exit 0 (false success).
    assert lc.main(["dashboard", "/definitely-not-a-ledger-project-xyz"]) == 2


def test_demo_fails_on_nonexistent_project():
    # A tour of a non-project must not print a hybrid report and exit 0.
    assert lc.main(["demo", "/definitely-not-a-ledger-project-xyz"]) == 2


def test_demo_propagates_a_step_failure(monkeypatch):
    # If any tour step hard-fails, the demo's exit code reflects it (not a blanket 0).
    monkeypatch.setattr(lc, "_run", lambda root, rel, args: 1)
    assert lc.main(["demo", str(REPO_ROOT)]) == 1


def test_demo_succeeds_when_every_step_passes(monkeypatch):
    monkeypatch.setattr(lc, "_run", lambda root, rel, args: 0)
    assert lc.main(["demo", str(REPO_ROOT)]) == 0


def test_demo_skips_gates_the_target_kernel_lacks(tmp_path, capsys):
    # A gate the target's kernel doesn't ship is skipped, not a hard tour failure.
    (tmp_path / "ledger.config.md").write_text(
        "project_name: t\nproject_state: pristine\n", encoding="utf-8")
    (tmp_path / "content").mkdir()
    (tmp_path / "literature" / "verified_claims").mkdir(parents=True)
    rc = lc.main(["demo", str(tmp_path)])
    out = capsys.readouterr().out
    assert "skipped — this project's kernel has no" in out
    assert rc == 0


def test_demo_signal_death_counts_as_failure(monkeypatch):
    # A signal-killed step returns a negative code; max(0, -9) must not read as success.
    monkeypatch.setattr(lc, "_run", lambda root, rel, args: -9)
    assert lc.main(["demo", str(REPO_ROOT)]) >= 1


def test_dashboard_flag_only_passes_through(monkeypatch):
    # A leading flag (no positional DIR) leaves the arg list untouched.
    calls = []
    monkeypatch.setattr(lc, "_run",
                        lambda root, rel, args: calls.append((root, rel, args)) or 0)
    assert lc.main(["dashboard", "--out", "/tmp/x.html"]) == 0
    _root, _rel, args = calls[-1]
    assert args == ["--out", "/tmp/x.html"]


# --- the step registry -------------------------------------------------------

def test_gate_steps_match_the_precommit_gate_set():
    # `ledger check` must run exactly what the commit blocks on — no more (it would
    # over-report), no less (it would green-light a commit that then fails).
    invoke_re = re.compile(r"(?:tools|literature)/(\w+)\.py")
    gates = set()
    for line in (REPO_ROOT / ".githooks" / "pre-commit").read_text().splitlines():
        if line.lstrip().startswith("#") or "echo " in line:
            continue
        gates.update(invoke_re.findall(line))
    check_tools = {Path(lc.DISPATCH[s.command]).stem for s in lc.GATE_STEPS}
    assert check_tools == gates


def test_demo_only_steps_never_enter_check():
    # The tour also shows non-gate views (dashboard, graph, analysis). None is an
    # enforcement gate, so none may contribute to check's verdict.
    gate_commands = {s.command for s in lc.GATE_STEPS}
    assert gate_commands.isdisjoint({"status", "graph", "analyze", "faithfulness"})


def test_demo_steps_keep_their_legacy_shape():
    # DEMO_STEPS is derived from STEPS now; its consumers still unpack (label, cmd,
    # list-of-args), and the tour's content/order must be unchanged.
    assert lc.DEMO_STEPS == [
        ("project health", "doctor", []),
        ("operator dashboard", "status", []),
        ("verbatim quotes", "verify", []),
        ("provenance stamps", "manifest", []),
        ("citation coverage", "citations", ["__content__"]),
        ("claim-graph structure", "structure", []),
        ("assessment records", "assessment", []),
        ("claim coverage (opt-in)", "coverage", []),
        ("run-record attestation (opt-in)", "attestation", []),
        ("selection audit (Layer 2)", "selection", []),
        ("source flow (Layer 2)", "source-flow", []),
        ("unit manifests (opt-in)", "units", []),
        ("synthesis claims (opt-in)", "synthesis", []),
        ("wiki health", "lint", ["__content__", "--strict"]),
        ("argument graph (Mermaid)", "graph", ["--mermaid"]),
        ("validity assistance", "analyze", []),
        ("faithfulness worklist", "faithfulness", []),
    ]


def test_step_registry_is_immutable():
    # The registry is the one source both views derive from, so it must not be
    # corruptible through a derived list: frozen rows, tuple args.
    assert all(isinstance(step.extra_args, tuple) for step in lc.STEPS)
    with pytest.raises(Exception):
        lc.STEPS[0].label = "mutated"


def test_every_gate_step_posture_is_a_real_posture():
    postures = {s.posture for s in lc.GATE_STEPS if s.posture}
    assert postures <= set(POSTURE_KEYS)


# --- posture resolution ------------------------------------------------------

def test_posture_defaults_match_the_real_gate_readers():
    # An absent posture is NOT uniformly off: six default to optional/warn. If this
    # table drifts from the readers, check would mislabel a live gate as inactive.
    for key in POSTURE_KEYS:
        assert lc.POSTURE_DEFAULTS[key] == _reader(key)({}), key


def test_posture_resolution_matches_the_real_gate_readers():
    # The whole resolution — accepted values, inline comments, case, placeholders,
    # fallback — must agree with each gate's own reader, value for value.
    for key in POSTURE_KEYS:
        reader = _reader(key)
        probes = (*lc.POSTURE_CHOICES[key], "<off|warn|required>", "", "  ",
                  "off # trailing note", "REQUIRED", "nonsense")
        for value in probes:
            config = {key: value}
            assert lc.effective_posture(config, key) == reader(config), (key, value)


def test_posture_choices_cover_every_registry_posture():
    assert set(lc.POSTURE_CHOICES) == set(POSTURE_KEYS)
    assert set(lc.POSTURE_DEFAULTS) == set(POSTURE_KEYS)


def test_resolution_never_infers_a_profile_default():
    # A config identical to `submission` except for one absent posture must resolve that
    # posture to the KERNEL default, never to submission's value: no authoritative
    # profile field exists, so inferring one and resolving through it is circular.
    config = {k: v for k, v in lc.PROFILES["submission"].items() if k != "selection_audit"}
    assert lc.PROFILES["submission"]["selection_audit"] == "required"
    assert lc.effective_posture(config, "selection_audit") == "off"


# --- exit normalisation ------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    (0, 0), (1, 1), (2, 2), (3, 2), (127, 2), (-9, 2), (-15, 2),
])
def test_normalise_exit(raw, expected):
    # A signal death (negative) is 'could not execute', never silent success.
    assert lc.normalise_exit(raw) == expected


# --- warning parsing ---------------------------------------------------------

def test_warning_count_ignores_quoted_evidence_and_ansi():
    stream = (
        "[INFO] fine\n"
        "[WARNING] a real warning\n"
        "\x1b[33m[WARNING]\x1b[0m a coloured warning\n"
        "> [WARNING] a warning quoted inside a gate's evidence block\n"
        "  | [WARNING] likewise piped evidence\n"
        "note about [WARNING] mid-line\n"
    )
    assert lc._count_warnings(stream) == 2


def test_warnings_never_change_the_blocking_outcome(project, green, monkeypatch):
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    green(rc=0, stream="[WARNING] noisy but passing\n")
    assert lc.main(["check", str(project(corpus=True))]) == 0


# --- corpus policy -----------------------------------------------------------

def test_citation_gate_runs_explicitly_without_corpus(project, green, monkeypatch):
    # Without source bytes the citation gate is NARROWED, not dropped: it still
    # enforces that every prose cite has a committed ledger (CI's half).
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    calls = green()
    lc.main(["check", str(project(ledgers=["a_2020"], corpus=False))])
    citations = [args for rel, args in calls if rel == lc.DISPATCH["citations"]]
    assert citations and "--no-corpus" in citations[0]


def test_citation_gate_keeps_full_corpus_check_when_corpus_present(project, green, monkeypatch):
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    calls = green()
    lc.main(["check", str(project(ledgers=["a_2020"], corpus=True))])
    citations = [args for rel, args in calls if rel == lc.DISPATCH["citations"]]
    assert citations and "--no-corpus" not in citations[0]


def test_no_ledgers_means_no_unavailable_result(project, green, monkeypatch, capsys):
    # Nothing committed yet ⇒ nothing to re-prove. A pristine kit must not be told its
    # corpus proof is unavailable.
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    green()
    assert lc.main(["check", str(project(ledgers=[], corpus=False))]) == 0
    out = capsys.readouterr().out
    assert "unavail" not in out
    assert "Ceiling" not in out


def test_absent_corpus_is_advisory_for_a_lenient_project(project, green, monkeypatch, capsys):
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    green()
    assert lc.main(["check", str(project(ledgers=["a_2020"], corpus=False))]) == 0
    assert "Ceiling" in capsys.readouterr().out


def test_absent_corpus_blocks_a_strict_project(project, green, monkeypatch, capsys):
    # The false-healthy-exit guard: a configured project whose committed quotes cannot
    # be re-proved must not exit 0.
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: True)
    green()
    assert lc.main(["check", str(project(ledgers=["a_2020"], corpus=False))]) == 1
    out = capsys.readouterr().out
    assert "unproved" in out and "verbatim quotes" in out


def test_verbatim_gate_runs_when_corpus_is_present(project, green, monkeypatch):
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: True)
    calls = green()
    assert lc.main(["check", str(project(ledgers=["a_2020"], corpus=True))]) == 0
    assert any(rel == lc.DISPATCH["verify"] for rel, _args in calls)


def test_ceiling_is_stated_once(project, green, monkeypatch, capsys):
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    green()
    lc.main(["check", str(project(ledgers=["a_2020", "b_2021"], corpus=False))])
    assert capsys.readouterr().out.count("Ceiling:") == 1


# --- check output ------------------------------------------------------------------

def test_inactive_gates_are_hidden_by_default_and_shown_verbose(project, green, monkeypatch, capsys):
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    green()
    root = project(corpus=True)          # every opt-in posture absent ⇒ kernel default off
    lc.main(["check", str(root)])
    default_out = capsys.readouterr().out
    assert "synthesis claims" not in default_out
    assert "inactive or not applicable" in default_out

    lc.main(["check", str(root), "--verbose"])
    verbose_out = capsys.readouterr().out
    assert "synthesis claims" in verbose_out


def test_a_failing_gate_is_shown_even_when_its_posture_is_off(project, green, monkeypatch, capsys):
    # If an 'off' gate fires, this file's posture reading disagreed with the gate's own.
    # Never hide that behind the posture — show it and block.
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    green(rc=1, stream="[ERROR] synthesis claim unanchored\n")
    assert lc.main(["check", str(project(corpus=True))]) == 1
    assert "synthesis claims" in capsys.readouterr().out


def test_passing_gate_output_is_quiet_but_failing_output_is_shown(project, green, monkeypatch, capsys):
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    green(rc=0, stream="[INFO] chatty green detail\n")
    lc.main(["check", str(project(corpus=True))])
    assert "chatty green detail" not in capsys.readouterr().out

    green(rc=1, stream="[ERROR] the actual reason\n")
    lc.main(["check", str(project(corpus=True))])
    assert "the actual reason" in capsys.readouterr().out


def test_a_tool_that_cannot_run_is_an_error_not_a_failure(project, green, monkeypatch, capsys):
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    green(rc=2, stream="[ERROR] usage error\n")
    assert lc.main(["check", str(project(corpus=True))]) == 2
    assert "could not run" in capsys.readouterr().out


def test_a_gate_the_kernel_lacks_is_unavailable_not_an_error(project, monkeypatch, capsys):
    # A vendored case with an older kernel: report the gap, do not fail the project.
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    monkeypatch.setattr(lc, "_command", lambda root, rel, args: None)
    assert lc.main(["check", str(project(corpus=True)), "--verbose"]) == 0
    assert "kernel has no" in capsys.readouterr().out


def _missing_tool(monkeypatch, missing_rel):
    """Every gate present and passing except `missing_rel`, whose tool this kernel lacks."""
    monkeypatch.setattr(lc, "_command",
                        lambda root, rel, args: None if rel == missing_rel else ["true"])
    monkeypatch.setattr(lc, "_capture", lambda root, rel, args: lc.Captured(0, "", ""))


def test_a_missing_applicable_gate_blocks_a_strict_project(project, monkeypatch, capsys):
    # The false-green guard: a strict project whose kernel lacks an enforcement tool has
    # established nothing about that gate — its own pre-commit cannot run it either.
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: True)
    _missing_tool(monkeypatch, lc.DISPATCH["manifest"])      # provenance defaults to warn
    assert lc.main(["check", str(project(ledgers=["a_2020"], corpus=True))]) == 1
    out = capsys.readouterr().out
    assert "unproved" in out and "provenance stamps" in out


def test_a_missing_gate_is_advisory_when_its_posture_is_off(project, monkeypatch, capsys):
    # A tool that would not have run anyway is not a readiness gap, even under strict.
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: True)
    _missing_tool(monkeypatch, lc.DISPATCH["synthesis"])     # synthesis_claims defaults off
    assert lc.main(["check", str(project(ledgers=["a_2020"], corpus=True))]) == 0


def test_a_missing_gate_is_advisory_for_a_lenient_project(project, monkeypatch):
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    _missing_tool(monkeypatch, lc.DISPATCH["manifest"])
    assert lc.main(["check", str(project(ledgers=["a_2020"], corpus=True))]) == 0


def test_missing_kernel_tool_does_not_advise_rebuilding_the_corpus(project, monkeypatch, capsys):
    # Two different causes of 'unavailable' need two different remediations.
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: True)
    _missing_tool(monkeypatch, lc.DISPATCH["manifest"])
    lc.main(["check", str(project(ledgers=["a_2020"], corpus=True))])
    nxt = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("Next:")]
    assert len(nxt) == 1
    assert "corpus" not in nxt[0] and "kernel has no" in nxt[0]


# --- argument discipline -----------------------------------------------------

def test_check_rejects_an_unknown_option(capsys):
    assert lc.main(["check", "--bogus"]) == 2
    assert "unknown option" in capsys.readouterr().err


def test_check_rejects_a_second_positional(project, capsys):
    root = str(project())
    assert lc.main(["check", root, root]) == 2
    assert "at most one project directory" in capsys.readouterr().err


def test_check_accepts_its_own_flags(project, green, monkeypatch):
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    green()
    for flag in lc.CHECK_FLAGS:
        assert lc.main(["check", str(project(corpus=True)), flag]) == 0


# --- check header ------------------------------------------------------------------

def test_header_omits_corpus_state_when_there_are_no_ledgers(project, green, monkeypatch, capsys):
    # The kit ships a smoke-test extract, so 'corpus present' with nothing committed
    # answers a question nobody asked.
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    green()
    lc.main(["check", str(project(ledgers=[], corpus=True))])
    out = capsys.readouterr().out
    assert "no verified sources yet" in out
    assert "corpus present" not in out


def test_header_reports_corpus_state_once_ledgers_exist(project, green, monkeypatch, capsys):
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    green()
    lc.main(["check", str(project(ledgers=["a_2020"], corpus=True))])
    assert "1 ledger(s) · corpus present" in capsys.readouterr().out


def test_check_rejects_a_non_project():
    assert lc.main(["check", "/definitely-not-a-ledger-project-xyz"]) == 2


def test_check_gives_exactly_one_next_action(project, green, monkeypatch, capsys):
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    green(rc=1, stream="[ERROR] broken\n")
    lc.main(["check", str(project(corpus=True))])
    out = capsys.readouterr().out
    assert len([ln for ln in out.splitlines() if ln.startswith("Next:")]) == 1


def test_next_action_names_a_command_that_exists(project, green, monkeypatch, capsys):
    # A next action pointing at an unimplemented verb is worse than none.
    known = set(lc.DISPATCH) | set(lc.PROFILES) | {"profiles", "check", "demo", "inspect"}
    verb_re = re.compile(r"`ledger ([a-z-]+)")
    for strict in (False, True):
        monkeypatch.setattr(lc, "_is_strict", lambda config, root, s=strict: s)
        green()
        lc.main(["check", str(project(corpus=True))])
        nxt = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("Next:")]
        assert len(nxt) == 1
        for verb in verb_re.findall(nxt[0]):
            assert verb in known, nxt[0]


def test_every_advised_inspect_area_is_real():
    # Advice like `ledger inspect structure` must name an area that resolves — a
    # remediation the researcher cannot run is worse than none.
    area_re = re.compile(r"`ledger inspect ([a-z-]+)`")
    advice = [*lc.REMEDIATION.values(), lc._next_action([], strict=True)]
    areas = {a for text in advice for a in area_re.findall(text)}
    assert areas                                  # the advice really does name areas
    assert areas <= set(lc.INSPECT), areas - set(lc.INSPECT)


def test_lenient_green_project_is_pointed_at_strictness(project, green, monkeypatch, capsys):
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    green()
    assert lc.main(["check", str(project(corpus=True))]) == 0
    assert "strict-local" in capsys.readouterr().out


def test_strict_green_project_is_pointed_at_judgement(project, green, monkeypatch, capsys):
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: True)
    green()
    assert lc.main(["check", str(project(corpus=True))]) == 0
    assert "ledger inspect analysis" in capsys.readouterr().out


def test_first_blocking_gate_supplies_the_next_action(project, green, monkeypatch, capsys):
    # Reports are in dependency order: fix the first thing, not the fifth.
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: False)
    green(rc=1)
    lc.main(["check", str(project(corpus=True))])
    out = capsys.readouterr().out
    first_gate = lc.GATE_STEPS[0]
    assert lc.REMEDIATION[first_gate.command] in out


def test_every_gate_step_has_a_remediation():
    missing = [s.command for s in lc.GATE_STEPS if s.command not in lc.REMEDIATION]
    assert missing == []


def test_check_is_in_the_usage_text():
    assert "ledger check" in lc.USAGE


# --- inspection areas --------------------------------------------------------

def test_every_inspect_area_maps_to_a_real_command():
    unknown = {area: cmd for area, cmd in lc.INSPECT.items() if cmd not in lc.DISPATCH}
    assert unknown == {}


def test_every_inspect_area_has_a_blurb():
    # `ledger inspect` with no area prints the menu; an area with no gloss is a hole in it.
    assert set(lc.INSPECT_BLURB) == set(lc.INSPECT)


def test_inspect_covers_every_documented_area():
    # The researcher-facing vocabulary is a published surface: renaming or dropping one
    # of these silently breaks the docs that name it.
    assert set(lc.INSPECT) == {
        "graph", "analysis", "faithfulness", "quotes", "provenance", "citations",
        "structure", "assessments", "coverage", "selection", "source-flow",
        "attestation", "units", "synthesis", "wiki",
    }


def test_inspect_covers_every_gate_except_project_health():
    # Each gate must be reachable on its own under some area name, so a researcher who
    # hits a failure in `check` can go straight to it. `doctor` keeps its own top-level
    # verb (it is project health, not an inspection of the research).
    gate_commands = {s.command for s in lc.GATE_STEPS} - {"doctor"}
    assert gate_commands <= set(lc.INSPECT.values())


def test_inspect_routes_to_the_legacy_tool(project, monkeypatch):
    calls = []
    monkeypatch.setattr(lc, "_run",
                        lambda root, rel, args: calls.append((root, rel, args)) or 0)
    monkeypatch.setattr(lc, "_project_root", lambda: project())
    assert lc.main(["inspect", "quotes"]) == 0
    _root, rel, _args = calls[-1]
    assert rel == lc.DISPATCH["verify"]


def test_inspect_forwards_its_arguments(project, monkeypatch):
    calls = []
    monkeypatch.setattr(lc, "_run",
                        lambda root, rel, args: calls.append((root, rel, args)) or 0)
    monkeypatch.setattr(lc, "_project_root", lambda: project())
    assert lc.main(["inspect", "analysis", "--target", "a_2020:some-slug"]) == 0
    _root, rel, args = calls[-1]
    assert rel == lc.DISPATCH["analyze"]
    assert args == ["--target", "a_2020:some-slug"]


def test_inspect_unknown_area_exits_2_and_lists_the_choices(capsys):
    assert lc.main(["inspect", "no-such-area"]) == 2
    err = capsys.readouterr().err
    assert "unknown inspection area" in err
    assert "quotes" in err and "structure" in err


def test_inspect_without_an_area_exits_2_and_lists_the_choices(capsys):
    assert lc.main(["inspect"]) == 2
    err = capsys.readouterr().err
    assert "needs an area" in err
    assert "wiki" in err


def test_inspect_rejects_a_non_project(monkeypatch):
    monkeypatch.setattr(lc, "_project_root", lambda: Path("/definitely-not-a-project-xyz"))
    assert lc.main(["inspect", "quotes"]) == 2


def test_inspect_points_content_tools_at_the_project_not_the_cwd(project, monkeypatch):
    # check_citations/lint_wiki default their content path to a CWD-relative "content",
    # so a bare run from a subdirectory exits 2 rather than inspecting the project.
    # `inspect` is meant to work from anywhere in the tree, so it passes the path.
    root = project()
    calls = []
    monkeypatch.setattr(lc, "_run",
                        lambda r, rel, args: calls.append((r, rel, args)) or 0)
    monkeypatch.setattr(lc, "_project_root", lambda: root)
    for area in ("citations", "wiki"):
        assert lc.main(["inspect", area]) == 0
        _r, _rel, args = calls[-1]
        assert args == [str(root / "content")]


def test_inspect_does_not_inject_content_when_the_user_gave_a_path(project, monkeypatch):
    root = project()
    calls = []
    monkeypatch.setattr(lc, "_run",
                        lambda r, rel, args: calls.append((r, rel, args)) or 0)
    monkeypatch.setattr(lc, "_project_root", lambda: root)
    assert lc.main(["inspect", "citations", "content/concept_notes"]) == 0
    _r, _rel, args = calls[-1]
    assert args == ["content/concept_notes"]


# --- inspecting a project other than the current one -------------------------

def _other_project(tmp_path: Path) -> Path:
    other = tmp_path / "other_case"
    (other / "content").mkdir(parents=True)
    (other / "literature" / "verified_claims").mkdir(parents=True)
    (other / "ledger.config.md").write_text("project_name: other\n", encoding="utf-8")
    return other


def test_inspect_targets_a_project_directory_given_after_the_area(
        project, monkeypatch, tmp_path):
    # check/demo/pack/dashboard all read a DIR as the project to work on; an area that
    # instead handed the path to the tool exited 2 for every gate that takes no positional.
    root = project()
    other = _other_project(tmp_path)
    calls = []
    monkeypatch.setattr(lc, "_run",
                        lambda r, rel, args: calls.append((r, rel, args)) or 0)
    monkeypatch.setattr(lc, "_project_root", lambda: root)
    assert lc.main(["inspect", "quotes", str(other)]) == 0
    called_root, rel, args = calls[-1]
    assert called_root == other.resolve()
    assert rel == lc.DISPATCH["verify"]
    assert args == []           # the path named the project; it is not the tool's argument


def test_inspect_names_the_targets_content_not_the_current_projects(
        project, monkeypatch, tmp_path):
    root = project()
    other = _other_project(tmp_path)
    calls = []
    monkeypatch.setattr(lc, "_run",
                        lambda r, rel, args: calls.append((r, rel, args)) or 0)
    monkeypatch.setattr(lc, "_project_root", lambda: root)
    for area in ("citations", "wiki"):
        assert lc.main(["inspect", area, str(other)]) == 0
        called_root, _rel, args = calls[-1]
        assert called_root == other.resolve()
        # The bug this pins: the target's ROOT reached lint_wiki as its content path, so
        # `wiki` linted the project root, called its AGENTS.md an orphan note, and passed.
        assert args == [str(other.resolve() / "content")]


def test_inspect_leaves_a_path_that_is_not_a_project_for_the_tool(
        project, monkeypatch, tmp_path):
    # Only a directory carrying a ledger.config.md is read as the project, so a content
    # path the tool does take keeps reaching it.
    root = project()
    plain = tmp_path / "just_a_dir"
    plain.mkdir()
    calls = []
    monkeypatch.setattr(lc, "_run",
                        lambda r, rel, args: calls.append((r, rel, args)) or 0)
    monkeypatch.setattr(lc, "_project_root", lambda: root)
    assert lc.main(["inspect", "wiki", str(plain)]) == 0
    called_root, _rel, args = calls[-1]
    assert called_root == root
    assert args == [str(plain)]


def test_inspect_forwards_flags_after_the_target_directory(project, monkeypatch, tmp_path):
    root = project()
    other = _other_project(tmp_path)
    calls = []
    monkeypatch.setattr(lc, "_run",
                        lambda r, rel, args: calls.append((r, rel, args)) or 0)
    monkeypatch.setattr(lc, "_project_root", lambda: root)
    assert lc.main(["inspect", "analysis", str(other), "--target", "a:b"]) == 0
    called_root, _rel, args = calls[-1]
    assert called_root == other.resolve()
    assert args == ["--target", "a:b"]


@pytest.mark.parametrize("area,user_args", [
    ("wiki", ["--strict"]),                       # store_true
    ("citations", ["--no-corpus"]),               # store_true
    ("citations", ["--numeric", "block"]),        # an option and its VALUE, not a path
    ("citations", ["--numeric=block"]),           # the single-token form
    ("citations", ["--no-corpus", "--claims", "required"]),
])
def test_inspect_still_names_the_content_path_when_flags_are_supplied(
        project, monkeypatch, area, user_args):
    # Flags are not a path. Injecting only for a completely empty arg list left this
    # middle case broken: `ledger inspect wiki --strict` from a subdirectory exited 2.
    root = project()
    calls = []
    monkeypatch.setattr(lc, "_run",
                        lambda r, rel, args: calls.append((r, rel, args)) or 0)
    monkeypatch.setattr(lc, "_project_root", lambda: root)
    assert lc.main(["inspect", area, *user_args]) == 0
    _r, _rel, args = calls[-1]
    # The positional leads, and the user's flags follow in the order they were given.
    assert args == [str(root / "content"), *user_args]


@pytest.mark.parametrize("area,user_args", [
    ("citations", ["--no-corpus", "content/concept_notes"]),
    ("citations", ["--numeric", "block", "content/x.md"]),
    ("wiki", ["--strict", "content/concept_notes"]),
])
def test_a_supplied_path_wins_over_the_injected_one(project, monkeypatch, area, user_args):
    root = project()
    calls = []
    monkeypatch.setattr(lc, "_run",
                        lambda r, rel, args: calls.append((r, rel, args)) or 0)
    monkeypatch.setattr(lc, "_project_root", lambda: root)
    assert lc.main(["inspect", area, *user_args]) == 0
    _r, _rel, args = calls[-1]
    assert args == user_args
    assert str(root / "content") not in args


def test_value_flags_match_the_real_parsers():
    # VALUE_FLAGS mirrors each tool's argparse: an option whose nargs is not 0 consumes
    # the next token. If a tool gains such a flag and this table misses it, the flag's
    # value reads as a path and `inspect` silently stops naming the content directory.
    import argparse

    def real_value_flags(module_name):
        module = importlib.import_module(module_name)
        captured = {}

        class _Stop(Exception):
            pass

        def _capture(self, *a, **k):
            captured["parser"] = self
            raise _Stop

        original = argparse.ArgumentParser.parse_args
        argparse.ArgumentParser.parse_args = _capture
        try:
            module.main()
        except _Stop:
            pass
        finally:
            argparse.ArgumentParser.parse_args = original
        return {opt
                for action in captured["parser"]._actions
                if action.option_strings and action.nargs != 0
                for opt in action.option_strings
                if opt.startswith("--")}

    for command, expected in lc.VALUE_FLAGS.items():
        assert real_value_flags(Path(lc.DISPATCH[command]).stem) == expected, command


def test_value_flags_cover_every_content_path_area():
    # Every area that gets a path injected needs an entry, or its flags are misread.
    needs = {cmd for cmd in lc.INSPECT.values() if lc._takes_content_path(cmd)}
    assert needs == set(lc.VALUE_FLAGS)


def test_inspect_matches_its_legacy_alias(project, monkeypatch):
    # Legacy verbs stay as silent aliases. From the project root, `ledger inspect <area>`
    # and the legacy verb must invoke the SAME tool with the SAME arguments — two names
    # for one command, not two commands.
    root = project()
    calls = []
    monkeypatch.setattr(lc, "_run",
                        lambda r, rel, args: calls.append((r, rel, args)) or 0)
    monkeypatch.setattr(lc, "_project_root", lambda: root)
    for area, legacy in lc.INSPECT.items():
        content = [str(root / "content")] if lc._takes_content_path(legacy) else []
        lc.main(["inspect", area])
        via_inspect = calls[-1]
        lc.main([legacy, *content])
        assert calls[-1] == via_inspect, area


def test_inspect_propagates_the_tools_exit_code(project, monkeypatch):
    monkeypatch.setattr(lc, "_project_root", lambda: project())
    monkeypatch.setattr(lc, "_run", lambda root, rel, args: 1)
    assert lc.main(["inspect", "structure"]) == 1


@pytest.mark.parametrize("args", [
    ["inspect", "wiki"],
    ["inspect", "wiki", "--strict"],
    ["inspect", "citations"],
    ["inspect", "citations", "--no-corpus"],
])
def test_inspect_really_runs_from_a_subdirectory(args):
    # The one test that spawns the CLI for real. Run from content/, where a CWD-relative
    # default would exit 2 ("path not found").
    import subprocess
    proc = subprocess.run([sys.executable, str(REPO_ROOT / "ledger_cli.py"), *args],
                          cwd=REPO_ROOT / "content", capture_output=True, text=True)
    assert proc.returncode == 0, f"{args} -> {proc.returncode}\n{proc.stdout}{proc.stderr}"


# --- tiered help -------------------------------------------------------------

@pytest.mark.parametrize("argv", [
    ["check", "--help"], ["check", "-h"],
    ["inspect", "--help"], ["demo", "--help"], ["profiles", "--help"],
])
def test_every_cli_owned_verb_honours_the_help_footer(argv, capsys):
    # The top-level help ends with "Run a subcommand with --help for its own options."
    # The routed tools get that from argparse; these four are implemented here, so the
    # promise is only true if they answer it themselves.
    assert lc.main(argv) == 0, argv
    assert argv[0] in capsys.readouterr().out


def test_demo_help_does_not_run_the_tour(monkeypatch, capsys):
    # --help used to fall through and run every gate: slow, and it changes what the
    # exit code means.
    monkeypatch.setattr(lc, "_run",
                        lambda root, rel, args: pytest.fail("demo --help ran a gate"))
    assert lc.main(["demo", "--help"]) == 0
    assert "end of tour" not in capsys.readouterr().out


def test_check_help_is_not_mistaken_for_a_project_dir(capsys):
    assert lc.main(["check", "--help"]) == 0
    out = capsys.readouterr().out
    assert "--verbose" in out and "Exit codes:" in out


def test_usage_is_tiered():
    for tier in ("Everyday work", "Audit a project", "Advanced inspection",
                 "Protocol development"):
        assert tier in lc.USAGE, tier


def test_usage_advertises_inspect_rather_than_the_flat_gate_verbs():
    # Individual gates are reachable through `inspect`; the help must not list them.
    for line in lc.USAGE.splitlines():
        for legacy in ("ledger verify", "ledger lint", "ledger citations",
                       "ledger manifest", "ledger analyze", "ledger structure"):
            assert legacy not in line, line
    assert "ledger inspect <area>" in lc.USAGE


def test_usage_does_not_advertise_unimplemented_workflow_verbs():
    # A verb is advertised only once Ledger can complete what it promises. `init` now
    # can, so it is advertised; the rest stay out until they work.
    for verb in ("ledger add", "ledger review", "ledger publish"):
        assert verb not in lc.USAGE, verb
    assert "ledger init" in lc.USAGE


def test_unimplemented_workflow_verbs_are_not_routed():
    for verb in ("add", "review", "publish"):
        assert verb not in lc.DISPATCH, verb
        assert lc.main([verb]) == 2, verb


def test_legacy_verbs_stay_routable_though_unadvertised(project, monkeypatch):
    # Silent aliases: absent from the help, still working for anyone with them in a
    # script or an older doc.
    calls = []
    monkeypatch.setattr(lc, "_run",
                        lambda root, rel, args: calls.append(rel) or 0)
    monkeypatch.setattr(lc, "_project_root", lambda: project())
    for legacy in ("verify", "lint", "analyze", "manifest", "audit-pack"):
        assert lc.main([legacy]) == 0, legacy
        assert calls[-1] == lc.DISPATCH[legacy]


# --- `ledger config effective` ------------------------------------------------
# A read-only report: it runs no gate and returns no verdict, so nothing here may block
# a project.

STRICT_CONFIG = ("project_state: configured\nclaim_ids: required\n"
                 "numeric_citations: block\nprovenance: required\n"
                 "structure_layer: required\nassessment_layer: required\n")


def test_posture_keys_match_the_canonical_registry():
    # ledger_cli mirrors the registry rather than importing it (it must not depend on
    # the target project's kernel). Same keys, same order, or the report misreports.
    assert list(lc.POSTURE_KEYS) == list(POSTURE_KEYS)


def test_project_state_is_not_a_posture():
    # The strictness declaration is not a gate posture; including it would make every
    # configured project differ from `pristine` for a reason unrelated to strictness.
    assert "project_state" not in lc.POSTURE_KEYS
    assert "project_state" not in lc.POSTURE_DEFAULTS


def test_resolve_posture_agrees_with_effective_posture():
    # effective_posture is the gate-facing API; resolve_posture only adds the origin.
    # If they disagree, the report describes a project the gates do not run.
    for config in ({}, {"claim_ids": "off"}, {"claim_ids": "<placeholder>"}):
        for key in lc.POSTURE_KEYS:
            assert lc.resolve_posture(config, key).value == lc.effective_posture(config, key)


def test_resolve_posture_marks_origin():
    assert lc.resolve_posture({"claim_ids": "required"}, "claim_ids") == \
        lc.Posture("claim_ids", "required", True)
    # Absent, placeholder and unreadable values all fall back — and none reads as
    # "explicit", so a typo cannot masquerade as a deliberate choice.
    for raw in ({}, {"claim_ids": "<fill me in>"}, {"claim_ids": "yes-please"}):
        assert lc.resolve_posture(raw, "claim_ids") == lc.Posture("claim_ids", "optional", False)


def test_resolve_posture_strips_comments_and_case():
    assert lc.resolve_posture({"claim_ids": "REQUIRED  # why"}, "claim_ids").value == "required"


def test_profile_differences_is_empty_for_its_own_profile():
    for name, prof in lc.PROFILES.items():
        assert lc.profile_differences(prof, name) == [], name


def test_profile_differences_ignores_project_state():
    # Same postures as pristine, opposite project_state ⇒ still zero differences.
    config = dict(lc.PROFILES["pristine"], project_state="configured")
    assert lc.profile_differences(config, "pristine") == []


def test_nearest_profile_is_fewest_differing_postures():
    config = dict(lc.PROFILES["submission"], attestation="off")   # 1 away from submission
    assert lc.nearest_profiles(config) == (["submission"], 1)


def test_nearest_profile_reports_every_co_nearest_on_a_tie(monkeypatch):
    # A tie must not silently pick a winner: equidistant means it resembles neither.
    # Synthetic profiles, so the assertion does not depend on the real tables.
    baseline = {k: lc.POSTURE_DEFAULTS[k] for k in lc.POSTURE_KEYS}
    a = dict(baseline, claim_ids="off")        # 1 away from baseline
    b = dict(baseline, provenance="off")       # also 1 away
    monkeypatch.setattr(lc, "PROFILES", {"a": a, "b": b})
    assert lc.nearest_profiles(baseline) == (["a", "b"], 1)


def test_nearest_profiles_is_deterministic_and_ordered():
    config = {"claim_ids": "off"}
    assert lc.nearest_profiles(config) == lc.nearest_profiles(config)
    names, _ = lc.nearest_profiles(config)
    assert names == [n for n in lc.PROFILES if n in names]   # declaration order


def test_config_effective_reports_state_and_every_posture(project, capsys):
    root = project(config=STRICT_CONFIG)
    assert lc.main(["config", "effective", str(root)]) == 0
    out = capsys.readouterr().out
    assert "configured" in out
    for key in lc.POSTURE_KEYS:
        assert key in out, key


def test_config_effective_distinguishes_explicit_from_default(project, capsys):
    root = project(config=STRICT_CONFIG)
    assert lc.main(["config", "effective", str(root)]) == 0
    out = capsys.readouterr().out
    assert re.search(r"claim_ids\s+required\s+explicit", out)
    # attestation is unset in STRICT_CONFIG, so it must read as the kernel default.
    assert re.search(r"attestation\s+off\s+kernel default", out)


def _states(monkeypatch, state, problems=()):
    """Pin ledger_doctor's verdict: these test what the report SAYS about a state, not
    how doctor derives it."""
    monkeypatch.setattr(lc, "_diagnose", lambda config, root: (state, list(problems)))
    monkeypatch.setattr(lc, "_is_strict", lambda config, root: state == "configured")


def test_config_effective_never_calls_a_broken_project_pristine(project, monkeypatch, capsys):
    # strict_mode() is False for a pristine kit AND for a broken one; only the first
    # has nothing to prove yet.
    _states(monkeypatch, "broken", ["project_state says 'configured' but the project "
                                    "looks 'pristine'"])
    root = project(config="project_state: configured\n")
    assert lc.main(["config", "effective", str(root)]) == 0
    out = capsys.readouterr().out
    assert "nothing to prove yet" not in out
    assert "broken" in out and "lenient" in out
    assert "ledger doctor" in out                    # names the remediation
    assert "looks 'pristine'" in out                 # surfaces doctor's own diagnosis


def test_config_effective_states_are_distinct(project, monkeypatch, capsys):
    seen = {}
    for state in ("pristine", "configured", "broken"):
        _states(monkeypatch, state)
        root = project(config=STRICT_CONFIG)
        assert lc.main(["config", "effective", str(root)]) == 0
        seen[state] = capsys.readouterr().out.splitlines()[2]   # the Health line
        assert state in seen[state]
    # Compare the NOTE, not the whole line: every line carries its own state name, so a
    # whole-line comparison passes even when all three glosses are identical.
    notes = {s: line.split("—", 1)[1].strip() for s, line in seen.items()}
    assert len(set(notes.values())) == 3, notes
    assert "nothing to prove yet" in notes["pristine"]        # only the kit gets this
    assert "nothing to prove yet" not in notes["broken"]


def test_config_effective_reports_strictness_from_the_predicate(project, monkeypatch, capsys):
    # A broken project declares `configured`; following the declaration would promise
    # strictness the gates do not deliver.
    _states(monkeypatch, "broken")
    root = project(config="project_state: configured\n")
    lc.main(["config", "effective", str(root)])
    out = capsys.readouterr().out
    assert re.search(r"Gates run:\s+lenient", out)
    assert not re.search(r"Gates run:\s+strict", out)


def test_config_effective_says_resemblance_is_descriptive(project, capsys):
    root = project(config=STRICT_CONFIG)
    lc.main(["config", "effective", str(root)])
    out = capsys.readouterr().out
    assert "descriptive" in out and "No `profile:` field exists" in out


def test_config_effective_never_writes(project):
    root = project(config=STRICT_CONFIG)
    before = (root / "ledger.config.md").read_bytes()
    assert lc.main(["config", "effective", str(root)]) == 0
    assert (root / "ledger.config.md").read_bytes() == before


def test_config_effective_on_a_non_project_is_2(tmp_path):
    assert lc.main(["config", "effective", str(tmp_path)]) == 2


def test_config_needs_a_known_subcommand(project, monkeypatch, capsys):
    monkeypatch.setattr(lc, "_project_root", lambda: project())
    assert lc.main(["config"]) == 2
    assert "effective" in capsys.readouterr().err


def test_config_effective_rejects_stray_arguments(project, monkeypatch):
    monkeypatch.setattr(lc, "_project_root", lambda: project(config=STRICT_CONFIG))
    assert lc.main(["config", "effective", ".", "extra"]) == 2


def test_config_effective_is_in_the_help():
    assert "config effective" in lc.USAGE


# --- `ledger config diff|set profile <name>` -----------------------------------
# The mutation surface (primitives: test_config_edit.py). Preview matches the write,
# consent is required, and every refusal leaves the file untouched.

@pytest.fixture
def real_config(tmp_path):
    """A project carrying the kit's ACTUAL ledger.config.md, so byte-preservation is
    asserted against the real file rather than a convenient stub."""
    (tmp_path / "content").mkdir()
    (tmp_path / "literature" / "verified_claims").mkdir(parents=True)
    target = tmp_path / "ledger.config.md"
    target.write_text((REPO_ROOT / "ledger.config.md").read_text(encoding="utf-8"),
                      encoding="utf-8")
    return tmp_path


def _tty(monkeypatch, is_tty, reply=""):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: is_tty)
    monkeypatch.setattr("builtins.input", lambda _prompt="": reply)


def test_profile_updates_never_writes_project_state():
    # Materialising it onto a half-filled project makes doctor report `broken`:
    # declared strict, gates lenient.
    for name in lc.PROFILES:
        assert "project_state" not in lc.profile_updates(name), name
        assert set(lc.profile_updates(name)) == set(lc.POSTURE_KEYS), name


def test_config_diff_is_read_only(real_config, capsys):
    before = (real_config / "ledger.config.md").read_bytes()
    assert lc.main(["config", "diff", "profile", "submission", str(real_config)]) == 0
    assert (real_config / "ledger.config.md").read_bytes() == before
    out = capsys.readouterr().out
    assert "claim_ids" in out and "Nothing was written" in out


def test_config_diff_on_an_already_matching_project(real_config, capsys):
    lc.main(["config", "set", "profile", "submission", str(real_config), "--yes"])
    capsys.readouterr()
    assert lc.main(["config", "diff", "profile", "submission", str(real_config)]) == 0
    assert "nothing to change" in capsys.readouterr().out


def test_config_set_dry_run_writes_nothing(real_config, capsys):
    before = (real_config / "ledger.config.md").read_bytes()
    assert lc.main(["config", "set", "profile", "submission", str(real_config),
                    "--dry-run"]) == 0
    assert (real_config / "ledger.config.md").read_bytes() == before
    assert "--dry-run: nothing was written." in capsys.readouterr().out


def test_config_set_refuses_without_consent_when_not_a_terminal(real_config, monkeypatch,
                                                                capsys):
    # A pipe or a CI job is never consent: nobody is looking at the preview.
    _tty(monkeypatch, False)
    before = (real_config / "ledger.config.md").read_bytes()
    assert lc.main(["config", "set", "profile", "submission", str(real_config)]) == 2
    assert (real_config / "ledger.config.md").read_bytes() == before
    assert "--yes" in capsys.readouterr().err


def test_config_set_declined_at_the_prompt_writes_nothing(real_config, monkeypatch,
                                                          capsys):
    _tty(monkeypatch, True, reply="n")
    before = (real_config / "ledger.config.md").read_bytes()
    assert lc.main(["config", "set", "profile", "submission", str(real_config)]) == 0
    assert (real_config / "ledger.config.md").read_bytes() == before
    assert "Not applied." in capsys.readouterr().out


@pytest.mark.parametrize("reply", ["y", "yes", "Y", "YES"])
def test_config_set_accepted_at_the_prompt_applies(real_config, monkeypatch, reply):
    _tty(monkeypatch, True, reply=reply)
    assert lc.main(["config", "set", "profile", "submission", str(real_config)]) == 0
    config = lc._parse_config(real_config)
    assert config["claim_ids"] == "required"


@pytest.mark.parametrize("reply", ["", "n", "no", "later", "Ynot"])
def test_only_an_explicit_yes_counts_as_consent(real_config, monkeypatch, reply):
    # Bare Enter must not apply: the prompt is [y/N], so the default is refusal.
    _tty(monkeypatch, True, reply=reply)
    before = (real_config / "ledger.config.md").read_bytes()
    assert lc.main(["config", "set", "profile", "submission", str(real_config)]) == 0
    assert (real_config / "ledger.config.md").read_bytes() == before


def test_config_set_yes_applies_and_matches_the_profile(real_config, capsys):
    assert lc.main(["config", "set", "profile", "submission", str(real_config),
                    "--yes"]) == 0
    assert "Applied 13 change(s)" in capsys.readouterr().out
    config = lc._parse_config(real_config)
    for key, value in lc.profile_updates("submission").items():
        assert lc.effective_posture(config, key) == value, key


def test_config_set_leaves_project_state_alone(real_config):
    before = lc._parse_config(real_config)["project_state"]
    lc.main(["config", "set", "profile", "submission", str(real_config), "--yes"])
    assert lc._parse_config(real_config)["project_state"] == before == "pristine"


def test_config_set_preserves_every_comment_and_the_line_count(real_config):
    raw = (real_config / "ledger.config.md").read_text()
    lc.main(["config", "set", "profile", "submission", str(real_config), "--yes"])
    after = (real_config / "ledger.config.md").read_text()
    comments = lambda t: [l for l in t.split("\n") if l.lstrip().startswith("#")]
    assert comments(raw) == comments(after)
    assert len(raw.split("\n")) == len(after.split("\n"))    # nothing appended


def test_config_set_is_idempotent(real_config, capsys):
    lc.main(["config", "set", "profile", "submission", str(real_config), "--yes"])
    capsys.readouterr()
    stamp = (real_config / "ledger.config.md").stat().st_mtime_ns
    assert lc.main(["config", "set", "profile", "submission", str(real_config),
                    "--yes"]) == 0
    assert "nothing to change" in capsys.readouterr().out
    assert (real_config / "ledger.config.md").stat().st_mtime_ns == stamp


def test_config_set_refuses_a_file_edited_during_confirmation(real_config, monkeypatch,
                                                              capsys):
    # The user reads the preview, then something else writes the file before they answer.
    # Applying anyway would write a change nobody approved.
    path = real_config / "ledger.config.md"

    def edit_then_confirm(_prompt):
        path.write_text(path.read_text().replace("claim_ids:           optional",
                                                 "claim_ids:           off"),
                        encoding="utf-8")
        return True

    monkeypatch.setattr(lc, "_confirm", edit_then_confirm)
    assert lc.main(["config", "set", "profile", "submission", str(real_config)]) == 2
    assert "changed after the preview" in capsys.readouterr().err
    assert lc._parse_config(real_config)["claim_ids"] == "off"     # left as found


def test_config_set_preserves_permissions(real_config):
    path = real_config / "ledger.config.md"
    os.chmod(path, 0o600)
    assert lc.main(["config", "set", "profile", "submission", str(real_config),
                    "--yes"]) == 0
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_config_set_refuses_an_occupied_staging_path(real_config, capsys):
    edit = lc._kit_import("config_edit")
    path = real_config / "ledger.config.md"
    stale = edit.temp_path(path)
    stale.write_text("not ours", encoding="utf-8")
    before = path.read_bytes()

    assert lc.main(["config", "set", "profile", "submission", str(real_config),
                    "--yes"]) == 2

    assert "already occupied" in capsys.readouterr().err
    assert stale.read_text() == "not ours"
    assert path.read_bytes() == before


def test_config_set_never_writes_through_a_symlinked_staging_path(real_config, capsys):
    edit = lc._kit_import("config_edit")
    path = real_config / "ledger.config.md"
    victim = real_config / "victim.txt"
    victim.write_text("unrelated", encoding="utf-8")
    os.symlink(victim, edit.temp_path(path))
    before = path.read_bytes()

    assert lc.main(["config", "set", "profile", "submission", str(real_config),
                    "--yes"]) == 2

    assert victim.read_text() == "unrelated"
    assert path.read_bytes() == before


def test_config_set_refuses_a_malformed_config(real_config, capsys):
    path = real_config / "ledger.config.md"
    path.write_text(path.read_text() + "units_layer warn\n", encoding="utf-8")
    before = path.read_bytes()
    assert lc.main(["config", "set", "profile", "submission", str(real_config),
                    "--yes"]) == 2
    assert path.read_bytes() == before
    assert "neither a comment nor" in capsys.readouterr().err


def test_config_diff_reports_a_malformed_config(real_config, capsys):
    path = real_config / "ledger.config.md"
    path.write_text(path.read_text() + "units_layer warn\n", encoding="utf-8")
    assert lc.main(["config", "diff", "profile", "submission", str(real_config)]) == 2
    assert "neither a comment nor" in capsys.readouterr().err


def test_config_set_refuses_a_config_with_duplicate_keys(real_config, capsys):
    path = real_config / "ledger.config.md"
    path.write_text(path.read_text() + "claim_ids: off\n", encoding="utf-8")
    before = path.read_bytes()
    assert lc.main(["config", "set", "profile", "submission", str(real_config),
                    "--yes"]) == 2
    assert path.read_bytes() == before
    assert "declared more than once" in capsys.readouterr().err


def test_the_preview_matches_what_is_written(real_config, capsys):
    # A preview describing a different change from the write is worse than none.
    lc.main(["config", "diff", "profile", "strict-local", str(real_config)])
    previewed = capsys.readouterr().out
    added = {l[1:].split(":")[0] for l in previewed.split("\n")
             if l.startswith("+") and not l.startswith("+++")}
    lc.main(["config", "set", "profile", "strict-local", str(real_config), "--yes"])
    capsys.readouterr()
    raw = (real_config / "ledger.config.md").read_text()
    for key in added:
        assert f"{key}:" in raw
    config = lc._parse_config(real_config)
    for key, value in lc.profile_updates("strict-local").items():
        assert lc.effective_posture(config, key) == value, key


@pytest.mark.parametrize("argv", [
    ["config", "set"],                              # no target
    ["config", "set", "profile"],                   # no name
    ["config", "set", "profile", "no-such"],        # unknown profile
    ["config", "set", "key", "claim_ids"],          # unknown target kind
    ["config", "diff", "profile", "no-such"],
    ["config", "diff"],
])
def test_malformed_profile_commands_exit_2(real_config, monkeypatch, argv):
    monkeypatch.setattr(lc, "_project_root", lambda: real_config)
    before = (real_config / "ledger.config.md").read_bytes()
    assert lc.main(argv) == 2
    assert (real_config / "ledger.config.md").read_bytes() == before


def test_unknown_option_is_rejected_rather_than_ignored(real_config, monkeypatch):
    monkeypatch.setattr(lc, "_project_root", lambda: real_config)
    before = (real_config / "ledger.config.md").read_bytes()
    assert lc.main(["config", "set", "profile", "submission", "--force"]) == 2
    assert (real_config / "ledger.config.md").read_bytes() == before


def test_config_set_on_a_non_project_is_2(tmp_path):
    assert lc.main(["config", "set", "profile", "submission", str(tmp_path)]) == 2


def test_config_profile_verbs_are_in_the_help():
    assert "config diff profile" in lc.USAGE and "config set profile" in lc.USAGE


@pytest.mark.parametrize("argv", [["config", "diff", "--help"],
                                  ["config", "set", "--help"]])
def test_profile_verbs_have_help(argv, capsys):
    assert lc.main(argv) == 0
    assert "profile" in capsys.readouterr().out
