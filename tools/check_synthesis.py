# === SCRIPT: Synthesis-claim gate — is every significance/superiority claim anchored? ===
# The kit guards CLAIMS (verbatim quotes) but not the AUTHOR'S PROSE ABOUT the claims. The
# failure mode: synthesis prose overclaims — "the one genuinely non-obvious result", "beats
# a baseline", "saturated", "a fluent survey flattens" — significance/novelty/superiority
# assertions pinned to nothing. Those are Layer 4-5 (validity/clarity) claims written with
# Layer-1 (fidelity) confidence,
# in exactly the zone the integrity framework marks "judged, not guaranteed".
#
# This gate scans the synthesis surface (baseline_comparison, inquiry, calibration notes) for
# a tight watchlist of significance/superiority/novelty/certainty/completeness tokens, and
# flags any such sentence that carries NO evidence anchor (a `key:slug` claim address, a
# [[wikilink]], a `code/tool` ref, a markdown link, or an explicit hedge). It forces every
# superiority claim to either POINT AT SOMETHING or admit it is judgement.
#
# HONEST BOUNDARY (the same seam as the rest of the kit): this enforces ANCHORING (form),
# NOT TRUTH. An anchored-but-overstated claim
# passes here — whether an anchored claim is actually warranted is the adversarial-faithfulness
# ASSIST's job (a human/agent read), exactly as check_structure proves an edge resolves but
# never that it is apt. The value is that it forces the verification the author skipped.
#
# Scope/pristine invariant: posture `synthesis_claims: off|warn|required` (default off — opt-in,
# NOT in the strict set). No synthesis files / no flagged claims → passes every mode.
# INPUTS : content/baseline_comparison.md, content/inquiry.md, content/assessments/*.md;
#          synthesis_claims: in ledger.config.md.
# OUTPUTS: [INFO]/[WARNING]/[ERROR]; exit 0 = ok or off/warn; 1 = unanchored claim under required.
# Run    : python3 tools/check_synthesis.py
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from check_citations import parse_config

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTENT = REPO_ROOT / "content"

# The synthesis surface: where the author writes ABOUT the claims (not the ledgers themselves).
def synthesis_files(content: Path) -> list[Path]:
    files: list[Path] = []
    for name in ("baseline_comparison.md", "inquiry.md"):
        p = content / name
        if p.is_file():
            files.append(p)
    assess = content / "assessments"
    if assess.is_dir():
        files.extend(sorted(assess.glob("*.md")))
    return files

# Significance / superiority / novelty / certainty / completeness watchlist. Tight by design:
# high-signal author-significance words, not ordinary prose. Word-boundary, case-insensitive.
WATCH = {
    "novelty": r"non-obvious|novel|unprecedented|first to|the only|uniquely|unique\b",
    "superiority": r"beats|outperform\w*|better than|superior|flatten\w*|misses what|surfaces what",
    "certainty": r"proves|proven|dispositive|definitively|irrefutabl\w*|indisputabl\w*",
    "completeness": r"saturat\w*|exhaustive|fully independent|complete coverage",
    "structural": r"isolated node|dependency inversion",
}
WATCH_RE = {cat: re.compile(rf"(?i)(?<![\w-])(?:{pat})(?![\w-])") for cat, pat in WATCH.items()}

# An anchor: the claim points at something checkable, or is explicitly marked judgement.
CLAIM_ADDR_RE = re.compile(r"(?<![\w/])[a-z][a-z0-9_]+:[a-z0-9][a-z0-9-]+")  # key:slug (not a URL)
HEDGE_RE = re.compile(
    r"(?i)\b(?:we do not claim|do not claim|not claimed|not novel|no novelty|known but|"
    r"not a discovery|judgement,? not|assist,? not|not proven|does not prove|not guaranteed|"
    r"form,? not|not independent proof|concede|honest(?:ly)?)\b")


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_warning(msg: str) -> None:
    print(f"[WARNING] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def synthesis_mode(config: dict[str, str]) -> str:
    """synthesis_claims: off | warn | required (default off — opt-in, not in strict set)."""
    raw = config.get("synthesis_claims", "").split("#", 1)[0].strip().lower()
    return raw if raw in ("off", "warn", "required") else "off"


def has_anchor(line: str) -> bool:
    """A line is anchored if it points at a checkable object or marks itself as judgement."""
    if "`" in line or "[[" in line or "](" in line:
        return True
    if CLAIM_ADDR_RE.search(line):
        return True
    if HEDGE_RE.search(line):
        return True
    return False


def flagged_lines(path: Path) -> list[tuple[int, str, str]]:
    """Return (line_no, category, line) for each unanchored significance/superiority line.

    Skips frontmatter, fenced code, headings, HTML comments, and blockquotes — a superlative
    inside a verbatim source quote (`> "...no risk whatsoever"`) is the SOURCE's rhetoric, the
    rhetorical-assessment layer's concern, not the author's synthesis claim.
    """
    out: list[tuple[int, str, str]] = []
    in_frontmatter = False
    in_code = False
    in_comment = False
    for i, raw in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        line = raw.strip()
        if i == 1 and line == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if line == "---":
                in_frontmatter = False
            continue
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.startswith("<!--"):
            in_comment = True
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if not line or line.startswith("#") or line.startswith(">"):
            continue
        if has_anchor(line):
            continue
        for cat, rx in WATCH_RE.items():
            if rx.search(line):
                out.append((i, cat, raw.strip()))
                break
    return out


def synthesis_problems(content: Path) -> list[str]:
    problems: list[str] = []
    for path in synthesis_files(content):
        for line_no, cat, line in flagged_lines(path):
            rel = path.relative_to(content.parent) if content.parent in path.parents else path.name
            snippet = line if len(line) <= 100 else line[:97] + "..."
            problems.append(f"{rel}:{line_no} [{cat}] unanchored significance claim — pin it to "
                            f"a key:slug / [[link]] / `tool` or hedge it:\n      {snippet}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Synthesis-claim gate: every significance/superiority claim is anchored.")
    ap.add_argument("--content", default=str(CONTENT))
    ap.add_argument("--config", default=str(REPO_ROOT / "ledger.config.md"))
    ap.add_argument("--synthesis", choices=("off", "warn", "required"), default=None,
                    help="override the posture (default: synthesis_claims: in config)")
    args = ap.parse_args()

    config = parse_config(Path(args.config))
    mode = args.synthesis or synthesis_mode(config)
    if mode == "off":
        log_info("synthesis_claims: off — synthesis-claim check skipped.")
        return 0

    problems = synthesis_problems(Path(args.content))
    if not problems:
        log_info("synthesis ok — every flagged significance claim is anchored (form, not truth).")
        return 0
    header = (f"unanchored synthesis claims ({len(problems)}) — anchor to evidence or hedge:")
    message = header + "\n  - " + "\n  - ".join(problems)
    if mode == "required":
        log_error(message)
        return 1
    log_warning(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
