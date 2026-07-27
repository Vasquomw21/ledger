# === SCRIPT: ledger — one CLI namespace over the kit's gates + a judge demo ===
# A THIN dispatcher: each subcommand shells to the existing tool in the CURRENT project,
# so every tool resolves its own REPO_ROOT and the kit's behaviour is unchanged. It adds
# no gate. Legacy verbs stay routable as silent aliases in DISPATCH.
# INPUTS : the project found by walking up from CWD to the nearest ledger.config.md.
# OUTPUTS: each tool's own output. `ledger --help` lists the commands.
from __future__ import annotations

import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# subcommand -> the tool file (relative to the project root) it dispatches to.
DISPATCH = {
    "status": "tools/ledger_status.py",
    "dashboard": "tools/judge_dashboard.py",
    "pack": "tools/build_judge_pack.py",
    "audit-pack": "tools/build_judge_pack.py",
    "doctor": "tools/ledger_doctor.py",
    "verify": "literature/verify_quotes.py",
    "citations": "tools/check_citations.py",
    "manifest": "tools/check_manifest.py",
    "structure": "tools/check_structure.py",
    "assessment": "tools/check_assessment.py",
    "selection": "tools/check_selection.py",
    "source-flow": "tools/check_source_flow.py",
    "coverage": "tools/check_coverage.py",
    "attestation": "tools/check_attestation.py",
    "units": "tools/check_units.py",
    "synthesis": "tools/check_synthesis.py",
    "graph": "tools/build_graph.py",
    "analyze": "tools/analyze_graph.py",
    "faithfulness": "tools/faithfulness_probe.py",
    "faithfulness-eval": "tools/faithfulness_eval.py",
    "faithfulness-baseline": "tools/faithfulness_baseline.py",
    "repro": "tools/repro.py",
    "assess": "tools/assess_record.py",
    "sign": "tools/sign_records.py",
    "lint": "tools/lint_wiki.py",
}

# The researcher-facing name for each inspectable gate or view -> the command it runs.
# A naming layer over the same tools ('quotes', not 'verify'); the legacy verbs stay in
# DISPATCH as silent aliases.
INSPECT = {
    "analysis": "analyze",
    "assessments": "assessment",
    "attestation": "attestation",
    "citations": "citations",
    "coverage": "coverage",
    "faithfulness": "faithfulness",
    "graph": "graph",
    "provenance": "manifest",
    "quotes": "verify",
    "selection": "selection",
    "source-flow": "source-flow",
    "structure": "structure",
    "synthesis": "synthesis",
    "units": "units",
    "wiki": "lint",
}

# One line per area, so `ledger inspect` with no area is a usable menu rather than a
# list of names you have to already understand.
INSPECT_BLURB = {
    "analysis": "load-bearing claims, dependency closure, double-counts (no verdict)",
    "assessments": "judgement records sealed + grounded + fresh",
    "attestation": "run-records carry a valid signature",
    "citations": "every prose cite has a committed ledger",
    "coverage": "every cited claim has a role in the argument graph",
    "faithfulness": "does each quote warrant the edge it grounds? (worklist)",
    "graph": "the derived argument graph",
    "provenance": "ledgers carry their source identity + stamp",
    "quotes": "verbatim re-proof of every quote against its source",
    "selection": "why each source is in the corpus; declared gaps",
    "source-flow": "each ledger's discovery/screening route in",
    "structure": "claim-graph edges resolve + are grounded",
    "synthesis": "significance claims are anchored or hedged",
    "units": "quotes fall within their declared unit",
    "wiki": "dead wikilinks, orphans, uncatalogued notes",
}

# The ledger.config.md lines each named profile implies. Printed for the user to copy;
# `config set profile` writes the postures only, never project_state.
PROFILES = {
    "pristine": {  # the untouched starter kit — lax by design, nothing to prove yet
        "project_state": "pristine", "claim_ids": "optional",
        "numeric_citations": "warn", "provenance": "warn",
        "structure_layer": "optional", "assessment_layer": "optional",
        "graph_coverage": "off", "edge_assessments": "off",
        "selection_audit": "off", "source_flow": "off",
        "units_layer": "off", "synthesis_claims": "off",
        "attestation": "off", "semantic_health": "warn"},
    "strict-local": {  # configured ⟹ strict: all five strict postures bite locally
        "project_state": "configured", "claim_ids": "required",
        "numeric_citations": "block", "provenance": "required",
        "structure_layer": "required", "assessment_layer": "required",
        "graph_coverage": "off", "edge_assessments": "warn",
        "selection_audit": "warn", "source_flow": "warn",
        "units_layer": "warn", "synthesis_claims": "warn",
        "attestation": "off", "semantic_health": "warn"},
    "submission": {  # everything on — the posture for a reviewed, shareable artefact
        "project_state": "configured", "claim_ids": "required",
        "numeric_citations": "block", "provenance": "required",
        "structure_layer": "required", "assessment_layer": "required",
        "graph_coverage": "required", "edge_assessments": "required",
        "selection_audit": "required", "source_flow": "required",
        "units_layer": "required", "synthesis_claims": "required",
        "attestation": "warn", "semantic_health": "required"},
}

# One-line gloss per profile so the bare `ledger profiles` listing is self-explanatory —
# a project's strictness reads as one named mode, not a wall of individual flags.
PROFILE_BLURB = {
    "pristine": "the untouched starter kit — lax by design, nothing to prove yet",
    "strict-local": "configured ⟹ strict: all five strict postures bite locally",
    "submission": "everything on — the posture for a reviewed, shareable artefact",
}

# Served from the kit's own copy against any target; every other command runs the
# target's copy and is skipped if its (older) kernel lacks it. lint is here so the tour
# reflects CURRENT wiki-health policy — a vendored case's stricter copy would fail a
# healthy case over an orphan note.
_DEMO_KIT_SERVED = {"status", "dashboard", "analyze", "faithfulness", "assessment",
                    "source-flow", "lint"}

class CorpusPolicy(Enum):
    """How a step depends on the git-ignored raw corpus (literature/extracted/)."""
    NONE = "none"                                          # corpus-free; invoke normally
    REQUIRED_FOR_EXISTING_LEDGERS = "required-for-existing-ledgers"   # re-proves bytes
    DEGRADES_WITHOUT_CORPUS = "degrades-without-corpus"    # narrows via --no-corpus


@dataclass(frozen=True)
class Step:
    """One tool invocation, described once. `gate` marks the commit-time enforcement
    set; `demo` marks the read-only evaluator tour; the two overlap but differ (the
    tour also shows non-gate views, e.g. the graph). `posture` is the ledger.config.md
    key that can switch this gate off (None = always active). Parallel command lists
    drifted historically — this registry is the one source both views derive from."""
    label: str
    command: str
    gate: bool
    demo: bool
    posture: str | None
    corpus_policy: CorpusPolicy
    extra_args: tuple = ()


# The canonical step registry, in dependency order. `__content__` is replaced with the
# project's absolute content/ path at run time (check_citations / lint take a positional
# path). All steps are read-only and never mutate the project.
STEPS = (
    Step("project health", "doctor", True, True, None, CorpusPolicy.NONE),
    Step("operator dashboard", "status", False, True, None, CorpusPolicy.NONE),
    Step("verbatim quotes", "verify", True, True, None,
         CorpusPolicy.REQUIRED_FOR_EXISTING_LEDGERS),
    Step("provenance stamps", "manifest", True, True, "provenance", CorpusPolicy.NONE),
    Step("citation coverage", "citations", True, True, None,
         CorpusPolicy.DEGRADES_WITHOUT_CORPUS, ("__content__",)),
    Step("claim-graph structure", "structure", True, True, "structure_layer",
         CorpusPolicy.NONE),
    Step("assessment records", "assessment", True, True, "assessment_layer",
         CorpusPolicy.NONE),
    Step("claim coverage (opt-in)", "coverage", True, True, "graph_coverage",
         CorpusPolicy.NONE),
    Step("run-record attestation (opt-in)", "attestation", True, True, "attestation",
         CorpusPolicy.NONE),
    Step("selection audit (Layer 2)", "selection", True, True, "selection_audit",
         CorpusPolicy.NONE),
    Step("source flow (Layer 2)", "source-flow", True, True, "source_flow",
         CorpusPolicy.NONE),
    Step("unit manifests (opt-in)", "units", True, True, "units_layer", CorpusPolicy.NONE),
    Step("synthesis claims (opt-in)", "synthesis", True, True, "synthesis_claims",
         CorpusPolicy.NONE),
    Step("wiki health", "lint", True, True, None, CorpusPolicy.NONE,
         ("__content__", "--strict")),
    Step("argument graph (Mermaid)", "graph", False, True, None, CorpusPolicy.NONE,
         ("--mermaid",)),
    Step("validity assistance", "analyze", False, True, None, CorpusPolicy.NONE),
    Step("faithfulness worklist", "faithfulness", False, True, None, CorpusPolicy.NONE),
)

# The commit-time enforcement set (pinned to .githooks/pre-commit by test_ledger_cli).
GATE_STEPS = tuple(step for step in STEPS if step.gate)

# Command -> its registry entry, so `inspect` can ask how a tool is really invoked
# rather than keeping a second table of that.
STEP_BY_COMMAND = {step.command: step for step in STEPS}

# The evaluator tour, in the legacy (label, cmd, extra-args) shape its callers consume.
# Derived from STEPS, so a step cannot appear in one view and vanish from the other.
DEMO_STEPS = [
    (step.label, step.command, list(step.extra_args))
    for step in STEPS
    if step.demo
]

# What each gate assumes when ledger.config.md omits the key. NOT uniformly off: six
# default to optional/warn, so treating an absent posture as off under-reports. Pinned to
# the real gate readers by a drift test.
POSTURE_DEFAULTS = {
    "claim_ids": "optional",
    "numeric_citations": "warn",
    "provenance": "warn",
    "structure_layer": "optional",
    "assessment_layer": "optional",
    "graph_coverage": "off",
    "edge_assessments": "off",
    "selection_audit": "off",
    "source_flow": "off",
    "units_layer": "off",
    "synthesis_claims": "off",
    "semantic_health": "warn",
    "attestation": "off",
}

# The values each reader accepts; anything else (an unfilled <placeholder> included)
# falls back to the default above. numeric_citations' off-equivalent is `ignore`.
POSTURE_CHOICES = {
    "claim_ids": ("off", "optional", "required"),
    "numeric_citations": ("ignore", "warn", "block"),
    "provenance": ("off", "warn", "required"),
    "structure_layer": ("off", "optional", "required"),
    "assessment_layer": ("off", "optional", "required"),
    "graph_coverage": ("off", "warn", "required"),
    "edge_assessments": ("off", "warn", "required"),
    "selection_audit": ("off", "warn", "required"),
    "source_flow": ("off", "warn", "required"),
    "units_layer": ("off", "warn", "required"),
    "synthesis_claims": ("off", "warn", "required"),
    "semantic_health": ("off", "warn", "required"),
    "attestation": ("off", "warn", "required"),
}

# One concrete next action per gate, phrased as something the researcher can run or edit
# now. Mirrors the remediation the pre-commit hook prints, so the two cannot diverge.
REMEDIATION = {
    "doctor": "finish or clear ledger.config.md + content/_ledger/skin_rules.md "
              "so the declared state and the derivation agree.",
    "verify": "fix the ledger quote (do not reword it to dodge the check), or rebuild "
              "the corpus: literature/fetch_paper.sh then literature/extract_text.py.",
    "manifest": "re-stamp the ledger: python3 literature/verify_quotes.py --stamp",
    "citations": "quote-first: fetch the paper, write its verified_claims ledger, then cite.",
    "structure": "fix the edge or its (grounded by #slug) clause — run "
                 "`ledger inspect structure` for the failing edge.",
    "assessment": "reseal or fix the record: python3 tools/assess_record.py (see "
                  "`ledger inspect assessments` for the failing id).",
    "coverage": "give the cited claim a role in the argument graph, or set "
                "graph_coverage: off in ledger.config.md.",
    "attestation": "sign the run-records: python3 tools/sign_records.py --key <ssh-key>",
    "selection": "register the source (or name the gap) in content/source_register.md.",
    "source-flow": "add the ledger's discovery/screening route to content/source_flow.md.",
    "units": "re-run python3 tools/enumerate_units.py so the manifest matches the quote.",
    "synthesis": "anchor the claim to a key:slug / [[link]] / `tool` ref, or hedge it.",
    "lint": "fix the dead wikilink / orphan / uncatalogued note (see `ledger inspect wiki`).",
}

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
WARNING_LINE = re.compile(r"^\s*\[WARNING\](?:\s|$)")

# `ledger check` takes one optional project directory; these are its only flags.
CHECK_FLAGS = ("--verbose", "-v")
HELP_FLAGS = ("-h", "--help")

CHECK_USAGE = """ledger check [DIR] [--verbose]

Run every applicable enforcement gate against a Ledger project and report what holds,
what blocks, and the one thing to do next. Read-only — it changes nothing.

  DIR              the project to check (default: the one containing the current
                   directory)
  -v, --verbose    also show the gates hidden as inactive or not applicable, each
                   gate's raw exit code, and the output of gates that passed

Exit codes:
  0  nothing blocking
  1  a blocking finding (a gate failed, or a strict project's proof is unavailable)
  2  the verdict could not be established (a gate could not run, or bad arguments)

Gates switched off by a posture in ledger.config.md are still run, but are hidden
unless they fail. A gate that fails is always shown."""


def _is_project(root: Path) -> bool:
    """A directory is a Ledger project iff it carries a ledger.config.md."""
    return (root / "ledger.config.md").is_file()


def _not_a_project(root: Path) -> int:
    print(f"[ledger] {root} is not a Ledger project (no ledger.config.md).",
          file=sys.stderr)
    return 2


def _project_root() -> Path:
    """Nearest ancestor of CWD holding a ledger.config.md; else this file's dir."""
    here = Path.cwd()
    for d in (here, *here.parents):
        if (d / "ledger.config.md").is_file():
            return d
        if (d / ".git").exists() and (d / "tools").is_dir():
            return d
    return Path(__file__).resolve().parent


def _command(root: Path, rel: str, args: list[str]) -> list[str] | None:
    """The argv for one tool invocation against `root`, or None if this project's kernel
    has no such tool (and the kit cannot serve it). Kit-served tools run the LOCAL copy
    pointed at the target via explicit path flags, so a vendored case with an older
    kernel still gets the current policy. Split out of _run so `ledger check` can capture
    the same invocation _run streams — one definition, two presentations."""
    target = root / rel
    local_root = Path(__file__).resolve().parent
    local_tool = local_root / rel
    foreign = root != local_root

    if foreign and local_tool.is_file():
        if rel in ("tools/ledger_status.py", "tools/judge_dashboard.py"):
            return [sys.executable, str(local_tool), "--repo-root", str(root), *args]
        if rel == "tools/analyze_graph.py":
            return [
                sys.executable, str(local_tool),
                "--claims-dir", str(root / "literature" / "verified_claims"),
                "--content-dir", str(root / "content"),
                *args,
            ]
        if rel == "tools/faithfulness_probe.py":
            return [
                sys.executable, str(local_tool),
                "--claims-dir", str(root / "literature" / "verified_claims"),
                "--assess-dir", str(root / "content" / "assessments"),
                *args,
            ]
        if rel == "tools/check_assessment.py":
            return [
                sys.executable, str(local_tool),
                "--claims-dir", str(root / "literature" / "verified_claims"),
                "--assess-dir", str(root / "content" / "assessments"),
                "--config", str(root / "ledger.config.md"),
                *args,
            ]
        if rel == "tools/lint_wiki.py":
            # args already carry the target content path + --strict (kit lint, current policy).
            return [sys.executable, str(local_tool), *args]
    if not target.is_file():
        if rel == "tools/check_source_flow.py" and local_tool.is_file():
            return [
                sys.executable, str(local_tool),
                "--claims-dir", str(root / "literature" / "verified_claims"),
                "--flow", str(root / "content" / "source_flow.md"),
                "--config", str(root / "ledger.config.md"),
                *args,
            ]
        return None
    return [sys.executable, str(target), *args]


def _run(root: Path, rel: str, args: list[str]) -> int:
    """Stream one tool's output to the terminal; return its raw exit code."""
    cmd = _command(root, rel, args)
    if cmd is None:
        print(f"[ledger] no {rel} in {root} — is this a Ledger project?", file=sys.stderr)
        return 2
    return subprocess.run(cmd).returncode


@dataclass(frozen=True)
class Captured:
    """One tool run with its output held back rather than streamed. `stream` is the
    presentation view: stdout then stderr. The two are captured separately, so their
    true interleaving is lost — each gate labels its own lines ([INFO]/[WARNING]/
    [ERROR]), so order across the streams carries no meaning."""
    rc: int
    stdout: str
    stderr: str

    @property
    def stream(self) -> str:
        return "".join(part for part in (self.stdout, self.stderr) if part)


def _capture(root: Path, rel: str, args: list[str]) -> Captured:
    """Run one tool, capturing its output. `ledger check` shows a gate's output only
    when it fails (or under --verbose), so a green run stays quiet."""
    cmd = _command(root, rel, args)
    if cmd is None:
        return Captured(2, "", f"[ledger] no {rel} in {root} — is this a Ledger project?\n")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return Captured(proc.returncode, proc.stdout or "", proc.stderr or "")


def normalise_exit(rc: int) -> int:
    """Raw tool exit -> the CLI's three-value contract. Anything that is neither a clean
    pass nor a clean finding (a usage error, a missing tool, a negative signal death)
    is 'could not execute', never silent success."""
    if rc == 0:
        return 0
    if rc == 1:
        return 1
    return 2


def _count_warnings(stream: str) -> int:
    """[WARNING] lines in a captured stream — display metadata only, never a blocking
    input (the tool's exit code decides that). ANSI colour is stripped first; a warning
    quoted inside a gate's evidence block ('> [WARNING] ...') is not a warning OF this
    run and does not match."""
    plain = ANSI_RE.sub("", stream)
    return sum(1 for line in plain.splitlines() if WARNING_LINE.match(line))


def _corpus_present(root: Path) -> bool:
    """True if extracted source text is on disk, so verbatim re-proof is possible.
    A fresh clone or a vendored case ships the ledgers but not the git-ignored
    corpus, so the bytes cannot be re-hashed here — only the committed stamp can."""
    extracted = root / "literature" / "extracted"
    return extracted.is_dir() and any(extracted.glob("*.txt"))


def _ledgers(root: Path) -> list[Path]:
    """The project's real verified-claims ledgers (the shipped TEMPLATE is not one)."""
    claims = root / "literature" / "verified_claims"
    if not claims.is_dir():
        return []
    return [p for p in claims.glob("*.md") if p.stem != "TEMPLATE"]


def _kit_import(module: str):
    """Import a module from the KIT's tools/, whatever project we are pointed at. The
    config file is plain-file protocol, so the kit's own reader parses a foreign
    project's config correctly; this keeps one parser rather than a second copy here
    that could drift."""
    tools = str(Path(__file__).resolve().parent / "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    return __import__(module)


def _parse_config(root: Path) -> dict:
    return _kit_import("check_citations").parse_config(root / "ledger.config.md")


def _is_strict(config: dict, root: Path) -> bool:
    """ledger_doctor.strict_mode is the single strictness predicate every gate reads;
    ask it rather than re-deriving 'configured' here."""
    return _kit_import("ledger_doctor").strict_mode(config, root)


def _diagnose(config: dict, root: Path) -> tuple[str, list[str]]:
    """(state, problems) from ledger_doctor: pristine | configured | broken. strict_mode
    alone cannot tell a pristine kit from a broken one — both are lenient."""
    return _kit_import("ledger_doctor").diagnose(config, root)


def _declared_state(config: dict) -> str | None:
    """The declared project_state, or None if absent/placeholder."""
    return _kit_import("ledger_doctor").declared_state(config)


def _wrap(text: str, indent: str) -> str:
    """One diagnostic, wrapped and hanging-indented."""
    return textwrap.fill(text, width=88, initial_indent=indent,
                         subsequent_indent=indent)


@dataclass(frozen=True)
class Posture:
    """One resolved posture. `explicit` False = the config said nothing usable, so the
    kernel default applies."""
    key: str
    value: str
    explicit: bool


def resolve_posture(config: dict, key: str) -> Posture:
    """The value a gate will act on, plus its origin: the config's value, or the kernel
    default when the key is absent, a placeholder, or not an accepted value.

    Resolution is `explicit -> kernel default`, with no profile term: no authoritative
    `profile:` field exists, so inferring one and resolving through it would be circular."""
    raw = config.get(key, "").split("#", 1)[0].strip().lower()
    if raw in POSTURE_CHOICES[key]:
        return Posture(key, raw, True)
    return Posture(key, POSTURE_DEFAULTS[key], False)


def effective_posture(config: dict, key: str) -> str:
    """The resolved value alone — what every gate-facing caller wants."""
    return resolve_posture(config, key).value


# Mirrors tools/postures.py rather than importing it: the CLI must not depend on the
# TARGET project's kernel, which may be an older vendored copy. Drift-tested on keys and
# order. project_state is excluded — it declares strictness, it is not a gate posture.
POSTURE_KEYS = tuple(POSTURE_DEFAULTS)


def profile_differences(config: dict, name: str) -> list[tuple[str, str, str]]:
    """(key, this project's effective value, the profile's value) per differing posture."""
    return [(key, effective_posture(config, key), PROFILES[name][key])
            for key in POSTURE_KEYS
            if effective_posture(config, key) != PROFILES[name][key]]


def nearest_profiles(config: dict) -> tuple[list[str], int]:
    """The profile(s) closest to this project's postures, and that distance — an
    unweighted count of differing values. Ties return EVERY co-nearest profile:
    equidistant means it resembles neither. Declaration order, so ties are deterministic."""
    scored = [(len(profile_differences(config, name)), name) for name in PROFILES]
    best = min(distance for distance, _ in scored)
    return [name for distance, name in scored if distance == best], best


DEMO_USAGE = """ledger demo [DIR]

Read-only walkthrough of a Ledger project for an evaluator: every commit-time gate in
turn, then the graph views (argument graph, validity assistance, faithfulness worklist).

  DIR    the project to tour (default: the one containing the current directory)

Exit code: the worst of every applicable gate, so no failing gate hides behind a green
tour.

Where a project ships its ledgers but not the git-ignored raw corpus, the tour attests
each committed stamp (CI's check) rather than re-proving the source bytes, and says so.
`ledger check` is the local counterpart: it refuses to call those quotes proved."""


def _demo(root: Path, args: list[str]) -> int:
    """A read-only walkthrough that mirrors the full commit-time gate set (so its exit
    code is the worst of every applicable gate — no gate can hide behind a green tour),
    then the read-only graph views. Point it at any configured project (default: the
    current one)."""
    if any(arg in HELP_FLAGS for arg in args):
        print(DEMO_USAGE)
        return 0
    if args and not args[0].startswith("-"):
        root = Path(args[0]).resolve()
    # Fail fast on a non-project so the tour never prints a hybrid report and then
    # exits 0 (a wrapper would read that as success).
    if not _is_project(root):
        return _not_a_project(root)
    ledgers = _ledgers(root)
    have_corpus = _corpus_present(root)
    content_dir = str(root / "content")
    print(f"=== ledger demo — {root} ===", flush=True)
    print("(read-only: the full commit-time gate set, then what the graph says)\n", flush=True)
    worst = 0
    for label, cmd, extra in DEMO_STEPS:
        # Verbatim re-proof needs the git-ignored corpus. When ledgers exist but the
        # corpus does not (a fresh clone or a vendored case), skip the byte re-proof and
        # note the honest local-vs-CI boundary — the stamp is attested by the dedicated
        # `provenance stamps` (manifest) step below, not shown here as a red FAIL.
        if cmd == "verify" and ledgers and not have_corpus:
            print(f"\n----- {label}  (corpus absent → attested by provenance stamps) -----",
                  flush=True)
            print("  [note] raw corpus is git-ignored and not shipped; the committed stamp +",
                  flush=True)
            print("         body-hash are attested by the manifest step (CI's check). Rebuild",
                  flush=True)
            print("         the corpus via literature/fetch_paper.sh to re-prove the bytes.",
                  flush=True)
            continue
        rel = DISPATCH[cmd]
        # Skip a gate the target's kernel lacks rather than hard-failing at exit 2.
        if cmd not in _DEMO_KIT_SERVED and not (root / rel).is_file():
            print(f"\n----- {label}  (skipped — this project's kernel has no {rel}) -----",
                  flush=True)
            continue
        step_args = [content_dir if a == "__content__" else a for a in extra]
        print(f"\n----- {label}  (ledger {cmd}) -----", flush=True)
        rc = _run(root, DISPATCH[cmd], step_args)
        if rc != 0:                      # nonzero incl. negative signal death → failure
            worst = max(worst, rc, 1)
    print("\n=== end of tour ===", flush=True)
    return worst


# Why a proof could not be established. An unavailable gate needs its cause to pick a
# remediation — "rebuild the corpus" is the wrong advice for a kernel that never shipped
# the tool.
CAUSE_NO_CORPUS = "no-corpus"
CAUSE_KERNEL_MISSING_TOOL = "kernel-missing-tool"


@dataclass(frozen=True)
class GateReport:
    """One gate's outcome. `blocking` is this gate's contribution to the exit code —
    kept separate from `status` because an unavailable proof blocks a strict project
    but is merely advisory in a pristine one."""
    step: Step
    status: str       # pass | fail | error | unavailable | not-applicable
    rc: int           # the tool's raw exit code (shown under --verbose)
    stream: str       # captured output (shown on failure/error, or --verbose)
    warnings: int     # display metadata only — never an input to `blocking`
    blocking: bool
    note: str = ""
    cause: str = ""   # unavailable only: CAUSE_*

    @property
    def hidden(self) -> bool:
        """Inactive machinery is noise: a gate switched off by its posture, or one with
        nothing to act on, is hidden while it passes. A gate that FAILS is always shown,
        whatever its posture — an 'off' gate that fires is a contradiction worth seeing,
        and it means the posture read here disagreed with the gate's own."""
        return self.status in ("not-applicable", "inactive")


def _gate_report(root: Path, step: Step, config: dict, ledgers: list,
                 have_corpus: bool, strict: bool, content_dir: str) -> GateReport:
    """Run one gate against `root` and classify the result.

    Every applicable gate is really executed — the posture is read only to decide what
    to SHOW. Skipping a gate on the strength of this file's own posture reading would
    make the verdict depend on that reading; running it means a drifted default can
    only cost a hidden line, never a missed failure."""
    if step.corpus_policy is CorpusPolicy.REQUIRED_FOR_EXISTING_LEDGERS:
        if not ledgers:
            return GateReport(step, "not-applicable", 0, "", 0, False,
                              "no ledgers yet — nothing to re-prove")
        if not have_corpus:
            # Without the git-ignored corpus the bytes cannot be re-hashed. Advisory for
            # a pristine kit; blocking for a configured project, whose committed quotes
            # would otherwise go unverified behind a green tick.
            return GateReport(step, "unavailable", 0, "", 0, strict,
                              "raw corpus absent — committed stamps are attested by "
                              "`provenance stamps`, source bytes not re-proved",
                              CAUSE_NO_CORPUS)

    rel = DISPATCH[step.command]
    if _command(root, rel, []) is None:
        # A gate this project's kernel never shipped. Advisory where it would not have
        # bitten anyway; blocking for a strict project where it applies — an absent tool
        # must not read as a satisfied one.
        applies = not (step.posture and effective_posture(config, step.posture) == "off")
        return GateReport(step, "unavailable", 0, "", 0, strict and applies,
                          f"this project's kernel has no {rel}",
                          CAUSE_KERNEL_MISSING_TOOL)

    extra = list(step.extra_args)
    if step.corpus_policy is CorpusPolicy.DEGRADES_WITHOUT_CORPUS and not have_corpus:
        # Narrow the gate rather than drop it: without source bytes it still enforces
        # that every prose cite has a committed ledger (CI's half of the guarantee).
        extra.append("--no-corpus")
    step_args = [content_dir if a == "__content__" else a for a in extra]

    cap = _capture(root, rel, step_args)
    exit_code = normalise_exit(cap.rc)
    status = {0: "pass", 1: "fail"}.get(exit_code, "error")
    if status == "pass" and step.posture and effective_posture(config, step.posture) == "off":
        status = "inactive"
    return GateReport(step, status, cap.rc, cap.stream, _count_warnings(cap.stream),
                      blocking=exit_code != 0)


_MARK = {"pass": "ok", "inactive": "off", "fail": "FAIL", "error": "ERROR",
         "unavailable": "unavail", "not-applicable": "n/a"}


def _check(root: Path, args: list[str]) -> int:
    """The researcher's one command: run every applicable gate, say what holds, and give
    exactly one next action. Read-only. Exit 0 = nothing blocking, 1 = a blocking
    finding, 2 = could not establish the verdict."""
    # Reject what we cannot honour rather than silently ignoring it: a mistyped flag or a
    # second directory means the caller expected something this command did not do.
    verbose = False
    positional = []
    for arg in args:
        if arg in HELP_FLAGS:
            print(CHECK_USAGE)
            return 0
        if arg in CHECK_FLAGS:
            verbose = True
        elif arg.startswith("-"):
            print(f"[ledger] unknown option '{arg}' for `ledger check` "
                  f"(known: {', '.join(sorted(CHECK_FLAGS))}).", file=sys.stderr)
            return 2
        else:
            positional.append(arg)
    if len(positional) > 1:
        print(f"[ledger] `ledger check` takes at most one project directory, got "
              f"{len(positional)}: {' '.join(positional)}", file=sys.stderr)
        return 2
    if positional:
        root = Path(positional[0]).resolve()
    if not _is_project(root):
        return _not_a_project(root)

    config = _parse_config(root)
    strict = _is_strict(config, root)
    ledgers = _ledgers(root)
    have_corpus = _corpus_present(root)
    content_dir = str(root / "content")

    print(f"=== ledger check — {root} ===")
    # With nothing committed, corpus readiness answers a question nobody asked — the kit
    # ships a smoke-test extract, so a bare "corpus present" here means nothing.
    if ledgers:
        print(f"{'strict' if strict else 'lenient'} · {len(ledgers)} ledger(s) · "
              f"corpus {'present' if have_corpus else 'absent'}\n")
    else:
        print(f"{'strict' if strict else 'lenient'} · no verified sources yet\n")

    reports = [_gate_report(root, step, config, ledgers, have_corpus, strict, content_dir)
               for step in GATE_STEPS]

    width = max(len(r.step.label) for r in reports)
    for report in reports:
        if report.hidden and not verbose:
            continue
        line = f"  {_MARK[report.status]:<7} {report.step.label.ljust(width)}"
        if verbose:
            # No rc for a gate that never ran — printing rc=0 there would read as a pass.
            ran = report.status not in ("unavailable", "not-applicable")
            line += (f"  (ledger {report.step.command}, rc={report.rc})" if ran
                     else f"  (ledger {report.step.command}, not run)")
        if report.warnings:
            line += f"  [{report.warnings} warning(s)]"
        print(line.rstrip())
        if report.note:
            print(f"          {report.note}")
        if report.stream and (verbose or report.status in ("fail", "error")):
            for out_line in report.stream.rstrip("\n").splitlines():
                print(f"          | {out_line}")

    hidden = [r for r in reports if r.hidden]
    if hidden and not verbose:
        print(f"\n{len(hidden)} of {len(reports)} gates inactive or not applicable "
              f"(--verbose to show).")

    # The corpus ceiling, stated once for the whole run rather than per gate.
    if ledgers and not have_corpus:
        print("\nCeiling: the raw corpus is git-ignored and absent here, so committed "
              "stamps are\n         attested, not re-proved from source bytes. Rebuild it "
              "with literature/fetch_paper.sh\n         to verify the bytes locally.")

    failed = [r for r in reports if r.status == "fail"]
    errored = [r for r in reports if r.status == "error"]
    blocked = [r for r in reports if r.blocking and r.status == "unavailable"]
    print()
    if failed:
        print(f"failed: {', '.join(r.step.label for r in failed)}")
    if errored:
        print(f"could not run: {', '.join(r.step.label for r in errored)}")
    if blocked:
        print(f"unproved: {', '.join(r.step.label for r in blocked)}")
    if not (failed or errored or blocked):
        print(f"{sum(1 for r in reports if r.status == 'pass')} gate(s) pass, "
              "nothing blocking.")

    print(f"\nNext: {_next_action(reports, strict)}")
    if errored:
        return 2
    return 1 if any(r.blocking for r in reports) else 0


def _next_action(reports: list, strict: bool) -> str:
    """Exactly one next action, naming a command that exists at this commit. Reports are
    in dependency order, so the first blocking gate is the one to fix first — a list of
    five things to do is a list of none."""
    for report in reports:
        if not report.blocking:
            continue
        if report.cause == CAUSE_NO_CORPUS:
            return ("rebuild the corpus so the committed quotes can be re-proved: "
                    "literature/fetch_paper.sh then literature/extract_text.py")
        if report.cause == CAUSE_KERNEL_MISSING_TOOL:
            return (f"this project's kernel has no {DISPATCH[report.step.command]}, so "
                    f"'{report.step.label}' cannot be established — re-bootstrap the "
                    "project onto the current kit (its own pre-commit cannot run this "
                    "gate either).")
        return REMEDIATION[report.step.command]
    if not strict:
        return ("nothing blocking. This project is lenient; to make the strict postures "
                "bite, see `ledger profiles strict-local`.")
    return "nothing blocking. Where the argument is load-bearing: `ledger inspect analysis`."


def _takes_content_path(command: str) -> bool:
    """True if this tool takes the content directory as a positional. The registry
    already records that (`__content__`), so `inspect` reads it rather than repeating it."""
    step = STEP_BY_COMMAND.get(command)
    return bool(step and "__content__" in step.extra_args)


# Flags that swallow the NEXT token as their value, for the tools that take a positional
# content path. Needed to tell `--numeric block` (an option and its value) from a real
# positional path: without this, 'block' would read as a path and suppress the injection.
# `--flag=value` needs no entry — it is a single token starting with '-'.
# Pinned to each tool's own parser by test_value_flags_match_the_real_parsers; if a new
# value-taking flag is ever added and missed here, `inspect` stops injecting for
# invocations using it — a visible exit 2 from a subdirectory, never a silent pass.
VALUE_FLAGS = {
    "citations": {"--path", "--numeric", "--claims", "--literature-dir", "--config"},
    "lint": set(),
}


def _has_positional(command: str, args: list[str]) -> bool:
    """Did the caller name a path themselves? Options and their values do not count."""
    value_flags = VALUE_FLAGS.get(command, set())
    expect_value = False
    for arg in args:
        if expect_value:
            expect_value = False
            continue
        if arg.startswith("-"):
            expect_value = arg in value_flags
            continue
        return True
    return False


def _inspect_args(command: str, root: Path, args: list[str]) -> list[str]:
    """The arguments to hand the tool. These tools default their content path to a
    CWD-relative "content", so a bare run from a subdirectory exits 2 ("path not found")
    instead of inspecting the project — `inspect` names the project's content itself so
    it works from anywhere in the tree. Run from the root the result is the identical
    invocation, which keeps every area an exact alias of its legacy verb. A path the
    caller supplied always wins, and the positional leads so flag order is preserved."""
    if _takes_content_path(command) and not _has_positional(command, args):
        return [str(root / "content"), *args]
    return list(args)


def _inspect_target(root: Path, rest: list[str]) -> tuple[Path, list[str]]:
    """Split a leading project directory off the tool's arguments.

    `check`/`demo`/`pack`/`dashboard` all read a DIR as the project to work on, and an area
    must mean the same thing there — reaching the tool instead, the path is either an
    argument it has no parameter for (exit 2) or, for the one area whose tool does take a
    positional, a content path: `wiki` then lints the project ROOT and calls its AGENTS.md
    an orphan note, passing while inspecting the wrong tree.

    Only a directory carrying a ledger.config.md is taken. A path that is not a project is
    still the tool's own argument, so `inspect wiki some/content` keeps working.
    """
    if rest and not rest[0].startswith("-") and _is_project(Path(rest[0]).resolve()):
        return Path(rest[0]).resolve(), rest[1:]
    return root, rest


def _print_areas(stream) -> None:
    width = max(len(area) for area in INSPECT)
    print("Inspection areas:", file=stream)
    for area in sorted(INSPECT):
        print(f"  {area.ljust(width)}  — {INSPECT_BLURB[area]}", file=stream)


def _inspect(root: Path, args: list[str]) -> int:
    """Run one gate or view on its own, under the name a researcher would use for it.
    A routing layer only: the tool, its flags and its output are unchanged, so this is
    the same thing the legacy verb does — `ledger check` remains the way to run the set."""
    if args and args[0] in HELP_FLAGS:
        print("ledger inspect <area> [DIR] [ARGS]\n\nRun one gate or view on its own, on DIR\n"
              "(default: the current project). Any further arguments go to the underlying\n"
              "tool unchanged (`--help` included).\n")
        _print_areas(sys.stdout)
        return 0
    if not args:
        print("[ledger] `ledger inspect` needs an area.", file=sys.stderr)
        _print_areas(sys.stderr)
        return 2
    area, rest = args[0], args[1:]
    if area not in INSPECT:
        print(f"[ledger] unknown inspection area '{area}'.", file=sys.stderr)
        _print_areas(sys.stderr)
        return 2
    root, rest = _inspect_target(root, rest)
    if not _is_project(root):
        return _not_a_project(root)
    command = INSPECT[area]
    return _run(root, DISPATCH[command], _inspect_args(command, root, rest))


def _profiles(args: list[str]) -> int:
    if args and args[0] in HELP_FLAGS:
        print("ledger profiles [NAME]\n\nPrint the named posture profiles for "
              "ledger.config.md, or one profile's postures.\nCopy the block in yourself — "
              "profiles are never auto-applied; a config edit is\nyours to make.\n")
        args = []
    if not args:
        print("Named posture profiles (copy the block into ledger.config.md):\n")
        width = max(len(n) for n in PROFILES)
        for name in PROFILES:
            print(f"  {name.ljust(width)}  — {PROFILE_BLURB[name]}")
        print("\nRun `ledger profiles <name>` to print that profile's postures.")
        return 0
    name = args[0]
    if name not in PROFILES:
        print(f"[ledger] unknown profile '{name}'. Known: {', '.join(PROFILES)}",
              file=sys.stderr)
        return 2
    print(f"# profile: {name} — paste into ledger.config.md")
    width = max(len(k) for k in PROFILES[name])
    for key, value in PROFILES[name].items():
        print(f"{(key + ':').ljust(width + 1)} {value}")
    return 0


CONFIG_USAGE = """ledger config effective [DIR]

Report how this project's ledger.config.md is actually being read: its declared
project_state, the value each of the 13 gate postures resolves to and whether that
came from the config or the kernel default, and which named profile the postures sit
closest to.

  DIR    the project to report on (default: the one containing the current directory)

Read-only. It never edits ledger.config.md — `ledger profiles <name>` prints a block
to paste in yourself.

Exit code: 0 once reported; 2 if DIR is not a Ledger project."""

CONFIG_DIFF_USAGE = """ledger config diff profile <name> [DIR]

Show what adopting a named profile's postures would change in ledger.config.md, as a
unified diff. Read-only: it writes nothing, and is the same preview `config set` shows.

Exit code: 0 once reported (whether or not anything would change); 2 if DIR is not a
Ledger project, the profile is unknown, or the config cannot be written to safely."""

CONFIG_SET_USAGE = """ledger config set profile <name> [DIR] [--dry-run] [--yes]

Adopt a named profile's 13 gate postures in ledger.config.md: preview the diff, confirm,
then one atomic write. Everything outside the changed values is preserved byte-for-byte,
including comments, padding and a missing trailing newline. Re-running is a no-op.

  --dry-run   print the preview and exit without writing
  --yes       skip the confirmation prompt (required when not run from a terminal)

`project_state` is NOT written. A profile block carries it for a human to paste once
their config is genuinely finished; stamping `configured` onto a half-filled project
makes ledger_doctor report `broken`, and a broken project's gates run LENIENT while its
config claims strictness. Adopt the postures here, then declare project_state yourself
and check the result with `ledger config effective`.

The config is git-tracked: review an applied change with `git diff ledger.config.md`, and
undo it by reverting the value changes or with `git restore -p ledger.config.md`. (A plain
`git restore` would discard unrelated edits of your own in the same file.)

The write is bound to the diff you were shown: if the file changes while you are deciding,
the write is refused and you get a fresh preview instead.

Exit code: 0 applied / nothing to do / declined; 2 if DIR is not a Ledger project, the
profile is unknown, the config is unsafe to write, the file changed after the preview, or
confirmation is impossible."""

CONFIG_SUBCOMMANDS = ("effective", "diff", "set")
CONFIG_TARGETS = ("profile",)


def profile_updates(name: str) -> dict[str, str]:
    """The 13 postures a profile materialises. project_state is excluded: stamping
    `configured` onto a half-filled project makes doctor report `broken`, whose gates run
    LENIENT while the config claims strictness."""
    return {key: value for key, value in PROFILES[name].items() if key in POSTURE_KEYS}


# Broken projects remain lenient even when project_state says configured.
STATE_NOTE = {
    "pristine": "the untouched starter kit; nothing to prove yet",
    "drafted": "set up, but the skin is still a draft; gates stay lenient",
    "configured": "a real subject; all five strict postures are required",
    "broken": "the declared and derived states disagree",
}


def _print_config_subcommands(stream) -> None:
    print("Config subcommands:", file=stream)
    print("  effective            — how ledger.config.md is actually being read",
          file=stream)
    print("  diff profile <name>  — what adopting a profile would change (read-only)",
          file=stream)
    print("  set profile <name>   — adopt a profile's postures (preview, then confirm)",
          file=stream)


@dataclass(frozen=True)
class ProfileRequest:
    """A parsed `config diff|set profile <name> [DIR] [--flags]`."""
    name: str
    root: Path
    flags: set


def _parse_profile_request(sub: str, args: list[str], root: Path,
                           allowed: set) -> ProfileRequest | int:
    """Shared parse for both profile verbs, or an exit code — so `diff` and `set` cannot
    disagree about which project or profile they mean."""
    positional = [a for a in args if not a.startswith("-")]
    flags = {a for a in args if a.startswith("-")}
    unknown = flags - allowed
    if unknown:
        print(f"[ledger] unknown option '{sorted(unknown)[0]}' for `config {sub}`.",
              file=sys.stderr)
        return 2
    if not positional or positional[0] not in CONFIG_TARGETS:
        print(f"[ledger] `config {sub}` needs a target: "
              f"{' | '.join(CONFIG_TARGETS)} <name>.", file=sys.stderr)
        return 2
    if len(positional) < 2:
        print(f"[ledger] `config {sub} profile` needs a profile name. "
              f"Known: {', '.join(PROFILES)}", file=sys.stderr)
        return 2
    name = positional[1]
    if name not in PROFILES:
        print(f"[ledger] unknown profile '{name}'. Known: {', '.join(PROFILES)}",
              file=sys.stderr)
        return 2
    if len(positional) > 3:
        print(f"[ledger] unexpected argument '{positional[3]}'.", file=sys.stderr)
        return 2
    if len(positional) == 3:
        root = Path(positional[2]).resolve()
    if not _is_project(root):
        return _not_a_project(root)
    return ProfileRequest(name, root, flags)


@dataclass(frozen=True)
class Preview:
    """A computed change, bound to the bytes it was computed from. `sha256` is what makes
    the write land on the file the user actually saw."""
    diff: str
    changes: list
    problems: list
    sha256: str


def _profile_preview(request: ProfileRequest) -> Preview:
    """What adopting a profile would do — computed, never written."""
    edit = _kit_import("config_edit")
    text = (request.root / "ledger.config.md").read_text(encoding="utf-8")
    sha = edit.digest(text)
    updates = profile_updates(request.name)
    found = edit.problems(text, updates)
    if found:
        return Preview("", [], found, sha)
    return Preview(edit.diff(text, edit.render(text, updates)),
                   edit.plan(text, updates), [], sha)


def _print_profile_problems(problems: list[str]) -> None:
    print("[ledger] this config cannot be written to safely:", file=sys.stderr)
    for problem in problems:
        print(_wrap(problem, indent="  "), file=sys.stderr)


def _config_diff(root: Path, args: list[str]) -> int:
    """What adopting a profile would change. Read-only — the preview `set` shows, without
    the write."""
    if args and args[0] in HELP_FLAGS:
        print(CONFIG_DIFF_USAGE)
        return 0
    request = _parse_profile_request("diff", args, root, allowed=set())
    if isinstance(request, int):
        return request
    preview = _profile_preview(request)
    if preview.problems:
        _print_profile_problems(preview.problems)
        return 2
    if not preview.changes:
        print(f"Already at profile '{request.name}' — nothing to change.")
        return 0
    print(f"# adopting profile '{request.name}' would change "
          f"{len(preview.changes)} posture(s):\n")
    print(preview.diff, end="")
    print("\nproject_state is not written by this command — see "
          "`ledger config set profile --help`.")
    print(f"Nothing was written. `ledger config set profile {request.name}` "
          f"applies this.")
    return 0


def _confirm(prompt: str) -> bool:
    """Interactive confirmation. A non-tty NEVER counts as consent: a piped or CI
    invocation must pass --yes."""
    if not sys.stdin.isatty():
        return False
    try:
        return input(f"{prompt} [y/N] ").strip().lower() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def _config_set(root: Path, args: list[str]) -> int:
    """Adopt a profile's postures: preview, confirm, then one atomic write."""
    if args and args[0] in HELP_FLAGS:
        print(CONFIG_SET_USAGE)
        return 0
    request = _parse_profile_request("set", args, root,
                                     allowed={"--dry-run", "--yes"})
    if isinstance(request, int):
        return request
    preview = _profile_preview(request)
    if preview.problems:
        _print_profile_problems(preview.problems)
        return 2
    if not preview.changes:
        print(f"Already at profile '{request.name}' — nothing to change.")
        return 0

    print(f"# adopting profile '{request.name}' — {len(preview.changes)} posture(s):\n")
    print(preview.diff, end="")
    added = [c.key for c in preview.changes if c.adds]
    if added:
        print(f"\n  {len(added)} key(s) absent from the file would be appended at the "
              f"end: {', '.join(added)}")
    print(f"\n  project_state is NOT written — it stays your declaration that the "
          f"project is\n  genuinely finished. Adopting strict postures does not by "
          f"itself make the gates\n  strict; run `ledger config effective` after.")

    if "--dry-run" in request.flags:
        print("\n--dry-run: nothing was written.")
        return 0
    if "--yes" not in request.flags and not _confirm("\nApply to ledger.config.md?"):
        if not sys.stdin.isatty():
            print("[ledger] not a terminal, so there is nobody to confirm to: "
                  "re-run with --yes to apply.", file=sys.stderr)
            return 2
        print("Not applied.")
        return 0

    edit = _kit_import("config_edit")
    # Bound to preview.sha256: a file edited during confirmation is refused, so the write
    # cannot land on bytes the user never saw.
    applied, problems = edit.apply(request.root / "ledger.config.md",
                                   profile_updates(request.name), preview.sha256)
    if problems:
        _print_profile_problems(problems)
        return 2
    print(f"\nApplied {len(applied)} change(s) to {request.root / 'ledger.config.md'}.")
    print("Review with `git diff ledger.config.md`. To undo, revert the value changes\n"
          "shown above, or `git restore -p ledger.config.md` to pick them out — a plain\n"
          "`git restore ledger.config.md` would also discard any unrelated edits of your "
          "own.")
    return 0


def _config_effective(root: Path, args: list[str]) -> int:
    """Report the resolved config. Descriptive only: it runs no gate and returns no
    verdict, so a project is never blocked by what this prints."""
    if args and args[0] in HELP_FLAGS:
        print(CONFIG_USAGE)
        return 0
    if args and not args[0].startswith("-"):
        root = Path(args[0]).resolve()
        args = args[1:]
    if args:
        print(f"[ledger] unexpected argument '{args[0]}'. Run `ledger config "
              f"effective --help`.", file=sys.stderr)
        return 2
    if not _is_project(root):
        return _not_a_project(root)

    config = _parse_config(root)
    postures = [resolve_posture(config, key) for key in POSTURE_KEYS]
    declared = _declared_state(config)
    state, problems = _diagnose(config, root)
    strict = _is_strict(config, root)

    print(f"Project:        {root}")
    print(f"project_state:  {declared or '(unset — deferring to the derivation)'}")
    print(f"Health:         {state} — {STATE_NOTE[state]}")
    # strict_mode is the predicate the gates read, so report it rather than the declared
    # word: `configured` + unfinished derives as broken, and broken runs lenient.
    print(f"Gates run:      {'strict' if strict else 'lenient'}")
    if state == "broken":
        print("                A `configured` declaration does not make gates strict —\n"
              "                run `ledger doctor` and reconcile:")
    for problem in problems:
        print(_wrap(problem, indent=" " * 18))

    print("\nEffective postures (explicit value, else kernel default):\n")
    width = max(len(p.key) for p in postures)
    for posture in postures:
        origin = "explicit" if posture.explicit else "kernel default"
        print(f"  {posture.key.ljust(width)}  {posture.value.ljust(8)}  {origin}")
    explicit = sum(1 for p in postures if p.explicit)
    defaulted = len(postures) - explicit
    verb = "resolves" if defaulted == 1 else "resolve"
    tail = (" — the config states every one." if not defaulted else
            f"; the other {defaulted} {verb} to the kernel default.")
    print(f"\n  {explicit} of {len(postures)} set explicitly{tail}")

    names, distance = nearest_profiles(config)
    if distance == 0:
        print(f"\nMatches:        {names[0]} exactly.")
    else:
        label = " / ".join(names)
        noun = "posture differs" if distance == 1 else "postures differ"
        print(f"\nClosest:        {label} ({distance} {noun})")
        for name in names:
            print(f"\n  vs {name}:")
            keys = [k for k, _, _ in profile_differences(config, name)]
            kw = max(len(k) for k in keys)
            for key, mine, theirs in profile_differences(config, name):
                print(f"    {key.ljust(kw)}  this project: {mine.ljust(8)}"
                      f"  {name}: {theirs}")

    print("\nResemblance is descriptive. No `profile:` field exists, so nothing above is\n"
          "resolved through a profile — each posture resolves `explicit -> kernel default`\n"
          "on its own. project_state is excluded from the comparison: it declares\n"
          "strictness rather than configuring a gate.")
    return 0


def _config(root: Path, args: list[str]) -> int:
    if args and args[0] in HELP_FLAGS:
        print(CONFIG_USAGE)
        print()
        _print_config_subcommands(sys.stdout)
        return 0
    if not args:
        print("[ledger] `ledger config` needs a subcommand.", file=sys.stderr)
        _print_config_subcommands(sys.stderr)
        return 2
    sub, rest = args[0], args[1:]
    if sub not in CONFIG_SUBCOMMANDS:
        print(f"[ledger] unknown config subcommand '{sub}'.", file=sys.stderr)
        _print_config_subcommands(sys.stderr)
        return 2
    return {"effective": _config_effective, "diff": _config_diff,
            "set": _config_set}[sub](root, rest)


INIT_USAGE = """ledger init [DIR] [--set key=value] [--rule TEXT] [--reconfigure]
                 [--dry-run] [--yes]

Configure this starter-kit clone for a subject: fill the per-subject fields in
ledger.config.md and, if you give any rules, write them into the subject skin. It
previews everything first, then asks; each file is replaced in one atomic write.

  --set key=value   answer a field without being asked (repeatable)
  --rule TEXT       one writing rule specific to this subject (repeatable)
  --reconfigure     re-answer a config that is already filled
  --dry-run         print the preview and exit without writing
  --yes             skip the confirmation prompt (required when not run from a terminal)

Anything left unanswered is asked for, when there is a terminal to ask at; otherwise
give it with --set. The fields are listed below.

init REPLACES the kit's own scaffold and creates nothing. A missing ledger.config.md,
skin, or declared directory is a refusal, not something init makes for you: a file it
created could not be removed again if a later step failed, and this kit never deletes.

`project_state` is never written — that stays your declaration that the project is
finished. When init drafts the skin it records `skin_state: draft`, so a project whose
rules you have not yet stood behind reads as 'drafted' and its gates stay lenient. The
skin is never rewritten once it holds rules: --reconfigure re-answers the config only.

Exit code: 0 applied / nothing to do / declined; 2 if DIR is not a Ledger project, an
answer is unusable, the project cannot be written to safely, or there is nobody to
confirm to."""

INIT_FLAGS = ("--reconfigure", "--dry-run", "--yes")
INIT_VALUE_FLAGS = ("--set", "--rule")

# The two fields init deliberately leaves to their author, and the profile that arms the
# gates. Named here so the handoff below and the tests that follow it read the same values.
STRICT_PROFILE = "strict-local"
CONFIRMED = {"skin_state": "confirmed", "project_state": "configured"}

# Every step from a written config to a project whose gates bite. The posture step is not
# optional bookkeeping: configured ⟹ strict, so declaring the project finished without
# adopting the postures leaves one ledger_doctor rejects.
HANDOFF = (
    "Sharpen the skin into rules you stand behind.",
    f"Arm the gates: `ledger config set profile {STRICT_PROFILE}`.",
    "Declare it finished: set "
    + ", ".join(f"{key}: {value}" for key, value in CONFIRMED.items())
    + " in ledger.config.md.",
    "Confirm it all agrees: `ledger doctor`.",
    "See which gates hold: `ledger check`.",
)


@dataclass(frozen=True)
class InitRequest:
    """A parsed `init [DIR] [--set ...] [--rule ...] [--flags]`."""
    root: Path
    answers: dict
    rules: list
    flags: set


def _parse_init(args: list[str], root: Path):
    """The request, or an exit code. --set/--rule take a value, so their arguments are
    consumed here rather than read as a DIR."""
    answers: dict = {}
    rules: list = []
    flags: set = set()
    positional: list = []

    index = 0
    while index < len(args):
        arg = args[index]
        if arg in INIT_VALUE_FLAGS:
            if index + 1 >= len(args):
                print(f"[ledger] {arg} needs a value.", file=sys.stderr)
                return 2
            value = args[index + 1]
            index += 2
            if arg == "--rule":
                rules.append(value)
                continue
            key, sep, answer = value.partition("=")
            if not sep or not key.strip():
                print(f"[ledger] --set wants key=value, got '{value}'.", file=sys.stderr)
                return 2
            answers[key.strip()] = answer.strip()
            continue
        if arg.startswith("-"):
            if arg not in INIT_FLAGS:
                print(f"[ledger] unknown option '{arg}' for `init`.", file=sys.stderr)
                return 2
            flags.add(arg)
            index += 1
            continue
        positional.append(arg)
        index += 1

    if len(positional) > 1:
        print(f"[ledger] unexpected argument '{positional[1]}'.", file=sys.stderr)
        return 2
    if positional:
        root = Path(positional[0]).resolve()
    if not _is_project(root):
        return _not_a_project(root)
    return InitRequest(root, answers, rules, flags)


def _ask(prompt: str) -> str | None:
    """One typed answer, or None if there is nobody to ask or they gave up. An empty
    string is an answer — the caller decides what it means; None never is."""
    if not sys.stdin.isatty():
        return None
    try:
        return input(f"{prompt}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def _cancelled() -> int:
    print("[ledger] cancelled — nothing was written.", file=sys.stderr)
    return 2


def _project_state(root: Path) -> str:
    """The state the project now reads as, per the kernel that decides it."""
    return _kit_import("ledger_doctor").diagnose(_parse_config(root), root)[0]


def _gather_answers(request: InitRequest, init_plan):
    """Every field's answer, asked for if not given. Missing required fields are reported
    together rather than one refusal at a time."""
    answers = dict(request.answers)
    known = {field.key for field in init_plan.FIELDS}
    unknown = sorted(set(answers) - known)
    if unknown:
        # Reported here rather than left to build(): a mistyped key would otherwise be
        # dropped, and the run would only ask for the field it thought was missing.
        print(f"[ledger] '{unknown[0]}' is not a field init sets. Fields: "
              f"{', '.join(field.key for field in init_plan.FIELDS)}.", file=sys.stderr)
        return 2
    unanswered = [field for field in init_plan.FIELDS if field.key not in answers]

    if not sys.stdin.isatty():
        needed = [field.key for field in unanswered if field.required]
        if needed:
            print(f"[ledger] not a terminal, so there is nobody to ask. Give these with "
                  f"--set key=value: {', '.join(needed)}.", file=sys.stderr)
            return 2
        return answers

    for field in unanswered:
        suffix = "" if field.required else "  (optional — Enter to skip)"
        answer = _ask(f"{field.prompt}{suffix}")
        if answer is None:
            return _cancelled()
        if answer:
            answers[field.key] = answer
    return answers


def _gather_rules(request: InitRequest, init_plan, skin_text: str | None):
    """The subject's rules. Asked for once, because a skin of filler is worse than a skin
    that admits it is empty — declining leaves `skin_state: draft` and an honest project
    rather than a configured-looking one."""
    if request.rules:
        return list(request.rules)
    if not sys.stdin.isatty():
        return []
    if not init_plan.skin_text_is_empty(skin_text or ""):
        return []

    print(_wrap("The skin holds the writing rules specific to THIS subject — the ones "
                "the shared writing skill cannot know. Give any you would stand behind, "
                "one per line. Enter on its own stops.", indent=""))
    rules: list = []
    while True:
        rule = _ask(f"Rule {len(rules) + 1}")
        if rule is None:
            # Enter finishes the list; Ctrl-C abandons the command. Reading both as
            # "no more rules" would apply the plan on the way out of a run someone
            # stopped — and with --yes there is no confirmation left to catch it.
            return _cancelled()
        if not rule:
            return rules
        rules.append(rule)


def _print_init_problems(problems: list[str]) -> None:
    print("[ledger] init did not run:", file=sys.stderr)
    for problem in problems:
        print(_wrap(problem, indent="  ") if problem else "", file=sys.stderr)


def _print_init_preview(plan) -> None:
    if plan.config_diff:
        print(f"# ledger.config.md — {len(plan.changes)} field(s):\n")
        print(plan.config_diff, end="")
    if plan.skin_diff:
        print(f"\n# {plan.skin_file}:\n")
        print(plan.skin_diff, end="")
    if plan.notes:
        print()
        for note in plan.notes:
            print(_wrap(note, indent="  "))
    print(_wrap("project_state is NOT written — it stays your declaration that the "
                "project is finished. Check the result with `ledger config effective`.",
                indent="  "))


def _init(root: Path, args: list[str]) -> int:
    """Configure this clone for a subject: preview, confirm, then one atomic write per
    file."""
    if args and args[0] in HELP_FLAGS:
        print(INIT_USAGE)
        # Listed from FIELDS rather than spelled out above, so the help cannot name a
        # field init does not set.
        print("\nFields:")
        for field in _kit_import("init_plan").FIELDS:
            optional = "" if field.required else "  (optional)"
            print(f"  {field.key:18} {field.prompt}{optional}")
        return 0
    request = _parse_init(args, root)
    if isinstance(request, int):
        return request

    init_plan = _kit_import("init_plan")
    init_apply = _kit_import("init_apply")

    config_text = (request.root / "ledger.config.md").read_text(encoding="utf-8")
    skin_path = request.root / init_plan.declared_skin_file(config_text)
    skin_text = skin_path.read_text(encoding="utf-8") if skin_path.is_file() else None

    answers = _gather_answers(request, init_plan)
    if isinstance(answers, int):
        return answers
    rules = _gather_rules(request, init_plan, skin_text)
    if isinstance(rules, int):
        return rules

    # Built from the bytes read BEFORE the prompts: whatever the answering took, the plan
    # is bound to what it was computed from, and apply_plan refuses a file that moved.
    plan = init_plan.build(config_text, skin_text, answers, rules,
                           reconfigure="--reconfigure" in request.flags)
    if not plan.ok:
        _print_init_problems(plan.problems + plan.blockers)
        return 2
    if not plan.changes and plan.skin_text is None:
        print("Already configured as answered — nothing to change.")
        return 0

    _print_init_preview(plan)
    if "--dry-run" in request.flags:
        print("\n--dry-run: nothing was written.")
        return 0
    if "--yes" not in request.flags and not _confirm("\nApply?"):
        if not sys.stdin.isatty():
            print("[ledger] not a terminal, so there is nobody to confirm to: re-run "
                  "with --yes to apply.", file=sys.stderr)
            return 2
        print("Not applied.")
        return 0

    applied, problems = init_apply.apply_plan(request.root, plan)
    if not applied:
        _print_init_problems(problems)
        return 2

    # Derived, never assumed: --reconfigure leaves a confirmed skin alone, so init lands
    # 'configured' there and 'drafted' on a first run. Naming the wrong one would erase
    # the distinction the state field exists to carry.
    state = _project_state(request.root)
    print(f"\nInitialised {request.root} — project state: {state}.")
    print(_wrap("Review with `git diff`.", indent="  "))
    if state == "configured":
        return 0
    print(_wrap("The gates stay lenient until you finish:", indent="  "))
    for number, step in enumerate(HANDOFF, start=1):
        # Hanging indent: at a flush one, a wrapped step's tail reads as its own step.
        print(textwrap.fill(f"{number}. {step}", width=88,
                            initial_indent="  ", subsequent_indent="     "))
    return 0


USAGE = """ledger — keep every cited claim tied to a verified quote

Everyday work
  ledger init [DIR]         configure this clone for a subject (preview, then confirm)
  ledger check [DIR]        run every applicable gate; what holds, what to fix next
  ledger status             operator dashboard (state, postures, counts)

Audit a project
  ledger demo [DIR]         read-only tour of a project (default: current)
  ledger dashboard [DIR]    static HTML judge dashboard (stdout or --out)
  ledger pack DIR --out OUT one-folder judge/audit bundle

Advanced inspection
  ledger inspect <area> [DIR]
                            run one gate or view on its own (default: current)
                            (`ledger inspect` lists the areas)

Configure a project
  ledger config effective   how ledger.config.md is actually being read
  ledger config diff profile <name>
                            what adopting a profile would change (read-only)
  ledger config set profile <name>
                            adopt a profile's postures (preview, then confirm)
  ledger profiles [NAME]    named posture profiles for ledger.config.md
  ledger doctor             project health / strict-mode check

Protocol development
  ledger assess             write/reseal an attested judgement record
  ledger sign               sign the run-records (attestation posture)
  ledger repro A/ B/        measure extraction convergence between two runs
  ledger faithfulness-eval --emit-blind | --score V.jsonl
                            measure a detector's out-of-context rate
  ledger faithfulness-baseline [blind.jsonl]
                            transparent rule baseline for the benchmark

Run a subcommand with --help for its own options."""


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "profiles":
        return _profiles(rest)
    root = _project_root()
    if cmd == "init":
        return _init(root, rest)
    if cmd == "check":
        return _check(root, rest)
    if cmd == "config":
        return _config(root, rest)
    if cmd == "inspect":
        return _inspect(root, rest)
    if cmd == "demo":
        return _demo(root, rest)
    # judge_dashboard has no positional (it reads --repo-root), so translate `dashboard
    # <DIR>` to the project root and let _run inject the flag. pack keeps its positional:
    # build_judge_pack.py consumes the DIR itself.
    if cmd == "dashboard" and rest and not rest[0].startswith("-"):
        root = Path(rest[0]).resolve()
        rest = rest[1:]
        if not _is_project(root):     # a bare dir would render an empty page, exit 0
            return _not_a_project(root)
    if cmd not in DISPATCH:
        print(f"[ledger] unknown command '{cmd}'. Run `ledger --help`.", file=sys.stderr)
        return 2
    return _run(root, DISPATCH[cmd], rest)


if __name__ == "__main__":
    sys.exit(main())
