# === SCRIPT: Ledger project health — configured, pristine, or broken? ===
# Purpose: mechanically answer "is this project actually set up?" so an
#          unfinished bootstrap is caught, not silently run. The authoring
#          discipline depends on the per-subject config (the reader, the
#          deliverable, the source types) and the subject skin being filled.
#
#          Three states, because this repo is BOTH the starter kit and the
#          meta-project — it ships placeholders by design:
#            - pristine    every required field is a <placeholder> AND the skin
#                          is empty. The untouched starter kit. → OK (exit 0).
#            - configured  no required field is a placeholder, the skin is
#                          non-empty, and every gated_paths entry exists. → OK.
#            - broken      a half-state: some fields filled and some still
#                          <placeholder>, or config filled but skin still empty
#                          (or vice-versa), or a gated_paths entry that does not
#                          exist. → the real failure mode (exit 1).
#
#          So the gate stays green on the untouched kit and on a finished
#          project, and fires only on a bootstrap that did not complete.
# INPUTS : ledger.config.md, content/_ledger/skin_rules.md, the gated dirs.
# OUTPUTS: stdout state + [ERROR] problems. Exit 0 = pristine, or configured with
#          ALL strict postures adopted; 1 = broken, OR a configured project with
#          any soft strict-posture (enforced at EVERY gate — configured is strict
#          by definition), OR (under --require-configured) a pristine kit; 2 = usage.
#          --require-configured is the bootstrap completion assertion: it proves
#          the subject stood up (a pristine kit then fails too).
# Run    : python3 tools/ledger_doctor.py [--require-configured]
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

from check_citations import (claim_header_issues, claim_mode, gated_prefixes,
                             numeric_mode, parse_config)
from check_manifest import provenance_mode, read_frontmatter
from check_structure import structure_mode
from check_assessment import assessment_mode

REPO_ROOT = Path(__file__).resolve().parents[1]

# The two tracked project modes. project_state in ledger.config.md declares one;
# ledger_doctor derives the same answer from the actual config + skin and the two
# must agree (a contradiction is 'broken').
DECLARED_STATES = ("pristine", "configured")

# Whether the subject skin is a first draft or the rules the author stands behind. The
# kit ships a worked example from another project, so a skin holding rule lines is not
# evidence that they are THIS subject's rules — only the author can say that.
SKIN_STATES = ("draft", "confirmed")

# A semantic review older than this (days) earns a non-fatal nudge. Mechanical
# cleanliness ≠ intellectual currency (see content/_ledger/semantic_health.md).
STALENESS_DAYS = 180

# Per-subject fields a real project must fill. unpaywall_email is optional (it
# only gates one fetch rung); project_root is informational; gated_paths /
# claim_ids / skin_rules_file / writing_skill ship with working defaults.
REQUIRED = ["project_name", "deliverable", "source_of_truth", "the_reader", "source_types"]

# The shipped skin ends with this sentinel; a configured project replaces it.
SKIN_EMPTY_MARKER = "_(empty —"


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_warning(msg: str) -> None:
    print(f"[WARNING] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def warn_claim_numbering(repo_root: Path) -> None:
    """Non-fatal nudge: ledgers whose authored ## Claim N numbers are
    non-contiguous (positional #cN refs silently re-point on reorder)."""
    claims_dir = repo_root / "literature" / "verified_claims"
    if not claims_dir.is_dir():
        return
    for ledger in sorted(claims_dir.glob("*.md")):
        if ledger.stem == "TEMPLATE":
            continue
        issue = claim_header_issues(ledger)
        if issue:
            log_warning(f"claim numbering: {issue}")


def semantic_mode(config: dict[str, str]) -> str:
    """semantic_health: off | warn | required (default warn). Under 'required' a
    stale/missing semantic review hard-fails a configured commit."""
    raw = config.get("semantic_health", "").split("#", 1)[0].strip().lower()
    return raw if raw in ("off", "warn", "required") else "warn"


def semantic_max_age(config: dict[str, str]) -> int:
    """semantic_max_age_days: from config, else the STALENESS_DAYS default."""
    raw = config.get("semantic_max_age_days", "").split("#", 1)[0].strip()
    return int(raw) if raw.isdigit() else STALENESS_DAYS


def semantic_staleness_problems(repo_root: Path, config: dict[str, str],
                                today: str | None = None) -> list[str]:
    """Problems with the semantic health report ([] = present + fresh): the
    mechanical gates can be green while the knowledge base is intellectually stale
    (contradictions, claims overtaken by newer sources, concept gaps) — that pass
    is skill-ledger-curate's LLM work, tracked in content/_ledger/semantic_health.md.
    main() decides severity from semantic_health: (warn nudges, required blocks)."""
    skin = config.get("skin_rules_file", "content/_ledger/skin_rules.md")
    health = repo_root / Path(skin).parent / "semantic_health.md"
    if not health.is_file():
        return [f"no {health} — record the last semantic review (contradictions / "
                "stale sources / concept gaps) there."]
    last = (read_frontmatter(health).get("last_review") or "").strip()
    if not re.fullmatch(r"\d{8}", last):
        return ["last_review not set — run a semantic review (skill-ledger-curate) "
                "and stamp the date in content/_ledger/semantic_health.md."]
    max_age = semantic_max_age(config)
    today = today or dt.date.today().strftime("%Y%m%d")
    age = (dt.datetime.strptime(today, "%Y%m%d").date()
           - dt.datetime.strptime(last, "%Y%m%d").date()).days
    if age > max_age:
        return [f"last reviewed {last} ({age} days ago, > {max_age}) — re-run the "
                "semantic pass."]
    return []


def is_placeholder(value: str) -> bool:
    """A config value is unfilled if it is empty or a <…> template token."""
    value = value.strip()
    return value == "" or value.startswith("<")


def skin_text_is_empty(text: str) -> bool:
    """The emptiness heuristic itself, so callers holding proposed skin text apply the
    same test as callers holding a file."""
    if SKIN_EMPTY_MARKER in text:
        return True
    # A real skin has at least one rule line: "- **W1** …" / "**C1** …".
    return "**" not in text.replace("**This file holds", "")


def skin_is_empty(skin_path: Path) -> bool:
    """The subject skin is empty if the file is missing, still carries the
    bootstrap sentinel, or has no rule lines (bolded **C1**-style codes)."""
    if not skin_path.is_file():
        return True
    return skin_text_is_empty(skin_path.read_text(encoding="utf-8", errors="ignore"))


def declared_skin_state(config: dict[str, str]) -> str | None:
    """`skin_state` from the config, or None if absent/placeholder.

    None keeps the pre-skin_state behaviour: the shape of the file decides. That is a
    heuristic — "does it contain bold text" cannot tell a subject's real rules from the
    worked example the kit ships — so a project that says which it has is believed over
    the guess."""
    raw = config.get("skin_state", "").split("#", 1)[0].strip().lower()
    return raw if raw in SKIN_STATES else None


def gated_paths_missing(config: dict[str, str], repo_root: Path) -> list[str]:
    """gated_paths entries that do not exist under the repo.

    A directory OR a single file: the citation gate matches a gated prefix against a
    path, so naming one file is a legitimate way to gate prose that lives beside
    ungated prose (a project whose synthesis is content/inquiry.md, not a directory of
    notes). Requiring a directory here made the gate and its own health check disagree
    — a project could be gated correctly and still be reported broken. This is a
    typo-catcher; existence is what it is for."""
    return [prefix for prefix in gated_prefixes(config)
            if not (repo_root / prefix).exists()]


def declared_state(config: dict[str, str]) -> str | None:
    """The project_state declared in ledger.config.md, or None if absent/
    placeholder. None means 'defer to the derivation' (back-compat for projects
    written before this field existed); a present value that contradicts the
    derivation is the broken half-state this tool exists to catch."""
    raw = config.get("project_state", "").split("#", 1)[0].strip().lower()
    return raw if raw in DECLARED_STATES else None


def _derive_state(config: dict[str, str], repo_root: Path) -> tuple[str, list[str]]:
    """Derive (state, problems) from the actual config + skin, ignoring the
    declared project_state. state ∈ {pristine, drafted, configured, broken}."""
    placeholders = [f for f in REQUIRED if is_placeholder(config.get(f, ""))]
    skin_path = repo_root / config.get("skin_rules_file",
                                       "content/_ledger/skin_rules.md")
    skin_state = declared_skin_state(config)
    skin_empty = skin_is_empty(skin_path)

    # Pristine: nothing filled in and no skin — the untouched starter kit.
    if len(placeholders) == len(REQUIRED) and skin_empty and skin_state != "draft":
        return "pristine", []

    problems: list[str] = []
    # Drafted: set up, but the author has not stood behind the skin yet. Not broken —
    # nothing contradicts — and not configured, so the gates stay lenient.
    if not placeholders and skin_state == "draft":
        return "drafted", [
            f"skin_state is 'draft': sharpen {skin_path} into rules you stand behind, "
            "then set skin_state: confirmed (and project_state: configured)."]

    # Configured: everything filled and a skin that is both present and either confirmed
    # or (for a project written before skin_state existed) written-looking. `confirmed`
    # is a claim about rules that exist — it cannot conjure a skin that does not.
    if not placeholders and not skin_empty and skin_state in (None, "confirmed"):
        missing = gated_paths_missing(config, repo_root)
        for d in missing:
            problems.append(f"gated_paths entry does not exist: {d}")
        return ("configured" if not problems else "broken"), problems

    if skin_state == "confirmed" and skin_empty:
        problems.append(f"skin_state says 'confirmed' but {skin_path} is empty")

    # Otherwise a half-state — say exactly what is inconsistent.
    for f in placeholders:
        problems.append(f"required field still a placeholder: {f}")
    if skin_empty and not (len(placeholders) == len(REQUIRED)):
        problems.append(
            f"skin still empty while config is partly filled: {skin_path}")
    if not skin_empty and placeholders:
        problems.append(
            "skin is written but config still has placeholders (above)")
    return "broken", problems


def diagnose(config: dict[str, str], repo_root: Path) -> tuple[str, list[str]]:
    """Return (state, problems): the derived state reconciled with the declared
    project_state. A declared mode that contradicts the derivation is 'broken' —
    that catches a bootstrap that flipped the field but did not finish (or a
    finished project whose field was never set to match)."""
    state, problems = _derive_state(config, repo_root)
    declared = declared_state(config)
    if declared == "configured" and state == "drafted":
        return "broken", [
            "project_state says 'configured' but skin_state is still 'draft' — a "
            "project cannot be configured on rules its author has not stood behind. "
            "Confirm the skin, or drop project_state back to pristine."]
    if declared and state in ("pristine", "configured") and declared != state:
        return "broken", [
            f"project_state says '{declared}' but the project looks '{state}' — "
            "finish or clear ledger.config.md + content/_ledger/skin_rules.md so "
            "the declared mode and the derivation agree (or fix project_state)."]
    return state, problems


def strict_posture_gaps(config: dict[str, str]) -> list[tuple[str, str, str, str]]:
    """(key, current, wanted, why) for each strict posture this config has not adopted.

    A configured subject must adopt them so the gates actually bite: claim_ids closes
    right-paper-wrong-claim; numeric blocks unresolvable markers; provenance requires a
    fresh stamp; structure_layer blocks an ungrounded/dangling edge; assessment_layer
    blocks an unsealed/stale judgement."""
    postures = [
        ("claim_ids", claim_mode(config), "required",
         "every cite names the specific quoted claim it rests on"),
        ("numeric_citations", numeric_mode(config), "block",
         "numeric/superscript markers, which can't resolve to a ledger, are rejected"),
        ("provenance", provenance_mode(config), "required",
         "every committed ledger must carry a fresh, valid provenance stamp"),
        ("structure_layer", structure_mode(config), "required",
         "every claim-graph edge resolves to a grounded verbatim claim"),
        ("assessment_layer", assessment_mode(config), "required",
         "every judgement record is sealed, grounded, and bound to its claim"),
    ]
    return [gap for gap in postures if gap[1] != gap[2]]


def semantic_blocking(config: dict[str, str], repo_root: Path) -> list[str]:
    """Semantic staleness that BLOCKS — only under semantic_health: required. The single
    statement of that rule, so a caller cannot read it differently from main()."""
    if semantic_mode(config) != "required":
        return []
    return semantic_staleness_problems(repo_root, config)


def blocking_problems(config: dict[str, str], repo_root: Path) -> list[str]:
    """Every reason a plain `ledger_doctor` run would fail, or [] — the WHOLE contract,
    not merely the derived state.

    A configured project is strict by definition, so a lax posture bundle fails here
    exactly as it fails at every gate. A caller that read only diagnose() would accept a
    project the real doctor rejects; main() renders this rather than restating it."""
    state, problems = diagnose(config, repo_root)
    if state == "broken":
        return problems
    if state != "configured":
        return []
    return (semantic_blocking(config, repo_root)
            + [f"{key} is '{current}', set '{wanted}' so {why}"
               for key, current, wanted, why in strict_posture_gaps(config)])


def strict_mode(config: dict[str, str], repo_root: Path) -> bool:
    """The single strictness predicate the other gates read: True iff this is a
    fully-configured subject (not the pristine kit, not a half-broken project).
    Absent project_state defers to the derivation; a contradictory one is broken
    (→ not strict). Issues 3/4/5 take their teeth from this."""
    return diagnose(config, repo_root)[0] == "configured"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ledger project health: pristine / configured / broken.")
    parser.add_argument("--require-configured", action="store_true",
                        help="treat a pristine (un-bootstrapped) kit as a failure too")
    parser.add_argument("--print-strict", action="store_true",
                        help="print 'strict' (configured subject) or 'lenient' and exit 0 — "
                        "a machine-readable handle for the pre-commit gate")
    parser.add_argument("--config", default=str(REPO_ROOT / "ledger.config.md"),
                        help="override ledger.config.md location (tests)")
    parser.add_argument("--repo-root", default=str(REPO_ROOT),
                        help="override repo root for path checks (tests)")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_file():
        log_error(f"no ledger.config.md at {config_path}")
        return 2

    config = parse_config(config_path)
    repo_root = Path(args.repo_root)

    if args.print_strict:
        print("strict" if strict_mode(config, repo_root) else "lenient")
        return 0

    state, problems = diagnose(config, repo_root)

    if state == "broken":
        log_error("project is half-configured (bootstrap did not finish):\n  - "
                  + "\n  - ".join(problems)
                  + "\nFinish the setup: fill ledger.config.md and write "
                  "content/_ledger/skin_rules.md (see skill-ledger-bootstrap), "
                  "or revert to the pristine template.")
        return 1
    if state == "pristine":
        if args.require_configured:
            log_error("project is still the pristine template — not bootstrapped. "
                      "Run skill-ledger-bootstrap to stand up the subject.")
            return 1
        log_info("pristine starter kit — not yet bootstrapped (this is fine).")
        return 0
    if state == "drafted":
        # Returns before the strict-posture bundle below: a drafted project is not
        # configured, so it is not yet strict by definition and must not be hard-failed
        # for postures it has not adopted.
        if args.require_configured:
            log_error("project is drafted, not configured — the skin is still a draft:"
                      "\n  - " + "\n  - ".join(problems))
            return 1
        log_info("drafted — config filled and a skin written, but not yet confirmed. "
                 "The gates stay lenient until skin_state: confirmed.")
        for p in problems:
            log_warning(p)
        return 0
    log_info("configured — required fields filled, skin written, gated dirs present.")
    warn_claim_numbering(repo_root)

    # Semantic health is an OPT-IN blocking posture, separate from the
    # strict-posture bundle: forcing a fresh LLM/human review on every commit is
    # too aggressive to be a configured default, so it defaults to 'warn' (nudge)
    # and a project opts into 'required' (block when stale/missing) deliberately.
    blocking_sem = semantic_blocking(config, repo_root)
    if blocking_sem:
        log_error("semantic review is stale/missing and semantic_health: required:"
                  "\n  - " + "\n  - ".join(blocking_sem)
                  + "\nRun the semantic pass (skill-ledger-curate) and stamp "
                  "content/_ledger/semantic_health.md, or soften semantic_health.")
        return 1
    sem_problems = semantic_staleness_problems(repo_root, config)
    if sem_problems and semantic_mode(config) != "off":
        for p in sem_problems:
            log_warning(f"semantic health: {p}")

    # This hard-fails on a PLAIN run — pre-commit and CI run the plain doctor, so a
    # configured project cannot commit while lax; --require-configured additionally fails
    # a pristine kit (the bootstrap-completion assertion).
    lax = strict_posture_gaps(config)
    if lax:
        # A configured project is STRICT BY DEFINITION: a soft posture here is a
        # hard failure at every gate (pre-commit + CI run the plain doctor), not a
        # nudge that an operator must remember to escalate with --require-configured.
        # The flag's remaining job is to additionally fail a pristine kit (above).
        # To run softer, a project must revert to pristine — it cannot be both
        # configured and lax.
        log_error(
            "a configured project must adopt the strict postures — these gates are "
            "OFF until you do:\n  - "
            + "\n  - ".join(f"{k} is '{cur}', set '{want}' so {why}"
                            for k, cur, want, why in lax)
            + "\nSet them in ledger.config.md (or revert the project to pristine).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
