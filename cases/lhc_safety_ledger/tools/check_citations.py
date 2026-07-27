# === SCRIPT: Citation coverage gate — every prose cite has paper + ledger ===
# Purpose: the agent-neutral core of the quote-first guarantee. For every
#          citation found in gated prose it checks:
#            Layer 1  a paper on disk (literature/<author>*<year>*) OR a usable
#                     row in literature/REGISTER.tsv  (needs the local corpus)
#            Layer 2  a verified-claims ledger literature/verified_claims/
#                     <author>*<year>*.md             (ledgers are committed)
#          All three enforcement points call this one script, so the check
#          cannot drift between them:
#            - Claude Code hook   .claude/hooks/verify-citations.sh  (--stdin)
#            - pre-commit         .githooks/pre-commit               (full)
#            - CI                 .github/workflows/ci.yml           (--no-corpus:
#              the corpus is git-ignored, so CI enforces ledger coverage only)
#          Numeric/superscript citation styles ([42], method.⁵⁴) cannot be
#          resolved to a ledger without a references map; they are DETECTED and
#          reported per the numeric_citations: config posture (warn by default;
#          set block to fail on them), or a --numeric override — never silently passed.
# INPUTS : prose via --stdin (with --path for gating) or positional paths
#          (.md files / directories, default: content); ledger.config.md
#          (gated_paths), literature/REGISTER.tsv + verified_claims/.
# OUTPUTS: stdout [INFO]; stderr [WARNING]/[ERROR]. Exit 0 = clean / ungated /
#          no citations; 1 = gate fired (missing paper or ledger, or numeric
#          markers under --numeric block); 2 = usage/config error.
# Run    : python3 tools/check_citations.py content
#          printf '%s' "$TEXT" | python3 tools/check_citations.py --stdin --path <file>
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ledger_md import claim_blocks, claim_numbers  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]

# Default gated prefixes when ledger.config.md has no usable gated_paths: value.
DEFAULT_GATED = ["content/concept_notes/", "content/literature_reviews/"]

# Citation patterns, in priority order. Later (broader) patterns are suppressed
# where they overlap an earlier match, so "Smith & Jones (2020)" yields only
# smith 2020, never a spurious jones 2020. Years are constrained to 19xx/20xx
# so "(Model 4096)" can never look like a citation.
#
# Priority is load-bearing, not cosmetic: every pattern captures the FIRST author,
# because a ledger is keyed by first author. A longer author list must therefore be
# matched before a shorter one can match its TAIL. Without the 3+-author pattern below,
# "Harrow, Hassidim & Lloyd 2009" was matched by the "A & B" pattern as
# "Hassidim & Lloyd 2009" — attributing the cite to the middle author, demanding a
# hassidim_2009 ledger that convention says will never exist, and never checking the
# real harrow_2009 ledger at all.
AUTHOR = r"[A-Z][\w'’-]+"
YEAR = r"((?:19|20)\d{2})[a-z]?"
# The conjunction closing an author list. "and" must be whitespace-delimited (so
# "Smithand Jones" cannot match); "&" may be tight ("Smith&Jones"). Ordinary prose
# spells the conjunction as often as it uses the ampersand, and an unsupported form
# does not fail safe — it falls through to a narrower pattern that matches the TAIL
# and credits the wrong author.
CONJ = r"(?:\s*&\s*|\s+and\s+)"
# Optional per-claim ref: "(Smith 2020 #c1)". Placed before the closing paren
# so the paren-anchored patterns still match. See ledger_claim_ids() for ids.
CLAIM = r"(?:\s*#(?P<claim>[\w-]+))?"
CITATION_PATTERNS = [
    # Smith et al. 2020 / Smith et al. (2020) / (Smith et al. 2020 #c1)
    re.compile(rf"({AUTHOR})\s+et\s+al\.?,?\s*\(?{YEAR}{CLAIM}\)?"),
    # Smith, Jones & Brown 2020 / Harrow, Hassidim, and Lloyd (2009) — 3+ authors
    # spelled out, with or without the Oxford comma. Must precede the two-author
    # pattern: it would otherwise match the tail pair and credit a middle author.
    re.compile(rf"({AUTHOR})(?:,\s*{AUTHOR})+,?{CONJ}{AUTHOR},?\s*\(?{YEAR}{CLAIM}\)?"),
    # Smith & Jones 2020 / Smith and Jones (2020) / (Smith & Jones 2020 #c1)
    re.compile(rf"({AUTHOR}){CONJ}{AUTHOR},?\s*\(?{YEAR}{CLAIM}\)?"),
    # Single-author, PAREN-ANCHORED only — "(Smith 2020)" / "Smith (2020)".
    # Requiring the parenthesis is the false-positive control: bare running
    # text ("Since 2020", "by 2020") never matches.
    re.compile(rf"\(({AUTHOR}),?\s+{YEAR}{CLAIM}\)"),
    re.compile(rf"({AUTHOR})\s+\({YEAR}{CLAIM}\)"),
]

# Words that can precede a year without being a surname. Ported from the bash
# hook and extended for the paren-anchored single-author pattern.
STOPWORDS = frozenset("""
    al et de van la von der del den und the of between since during figure
    table section chapter volume issue page review report code progress
    january february march april may june july august september october
    november december
    in by see ref refs vol no pp eq equation appendix fig figs model note
    before after around until over under from circa version release published
    updated accessed copyright
""".split())

# Numeric / superscript citation markers — detectable but not resolvable
# without a references map.
NUMERIC_BRACKET_RE = re.compile(r"\[\d{1,3}(?:\s*[,–-]\s*\d{1,3})*\]")
# A superscript counts as a *citation* marker only when it attaches to the end
# of a word (≥2 ASCII letters, e.g. "previously⁴²") or to sentence punctuation
# ("method.⁵⁴"). A superscript on a single variable, a Greek letter, or a ")"
# is a maths exponent — κ², O(log N)³, N² — not a citation, so it is NOT
# flagged. (Found via the quantum dogfood, where κ² / O(log N)³ over-warned.)
SUPERSCRIPT_RE = re.compile(r"(?:[A-Za-z]{2}|[.,;:])([⁰¹²³⁴-⁹]+)")


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_warning(msg: str) -> None:
    print(f"[WARNING] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def parse_config(config_path: Path) -> dict[str, str]:
    """Loose `key: value` parse of ledger.config.md (placeholders tolerated)."""
    config: dict[str, str] = {}
    if not config_path.is_file():
        return config
    for line in config_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        config[key.strip()] = value.strip()
    return config


def gated_prefixes(config: dict[str, str]) -> list[str]:
    """gated_paths: from config; the kernel default when absent/placeholder.

    `none` gates nothing, and says so deliberately — an empty list here is a declaration,
    which is what distinguishes it from a gated_paths that simply matches no file."""
    raw = config.get("gated_paths", "").split("#", 1)[0].strip()
    if not raw or raw.startswith("<"):
        return DEFAULT_GATED
    if raw.lower() == "none":
        return []
    return [p.strip() for p in re.split(r"[,\s]+", raw) if p.strip()]


def is_gated(path_str: str, prefixes: list[str]) -> bool:
    """Gated prose = under a gated prefix and not a verified_claims/ ledger."""
    normalised = path_str.replace("\\", "/")
    if "verified_claims/" in normalised:
        return False
    return any(prefix in normalised for prefix in prefixes)


def extract_citations(text: str) -> set[tuple[str, str, str | None]]:
    """All (author_lower, year, claim_id) cited in text, with overlap
    suppression. claim_id is the optional `#<id>` ref (lowercased) or None."""
    citations: set[tuple[str, str, str | None]] = set()
    claimed: list[tuple[int, int]] = []
    for pattern in CITATION_PATTERNS:
        for m in pattern.finditer(text):
            if any(m.start() < end and m.end() > start for start, end in claimed):
                continue
            claimed.append((m.start(), m.end()))
            author = m.group(1).replace("’", "'").lower()
            if len(author) < 3 or author in STOPWORDS:
                continue
            claim = m.groupdict().get("claim")
            citations.add((author, m.group(2), claim.lower() if claim else None))
    return citations


def ledger_claim_id_sets(ledger_path: Path) -> tuple[set[str], set[str]]:
    """Return (ordinals, slugs): ordinals are c1, c2, … from `## Claim N` header
    order; slugs are the explicit `**ID:** <slug>` stable aliases. The split lets
    a strict gate reject a BARE ordinal (which silently re-points on reorder)
    while still honouring a stable slug — even one literally named 'c1'."""
    ordinals: set[str] = set()
    slugs: set[str] = set()
    for block in claim_blocks(ledger_path):
        ordinals.add(f"c{block.ordinal}")
        for m in block.fields(_ID_RE):
            slugs.add(m.group(1).lower())
    return ordinals, slugs


def ledger_claim_ids(ledger_path: Path) -> set[str]:
    """All claim ids a cite may resolve to: ordinals ∪ explicit **ID:** slugs.
    Lightweight — read only when a cite carries a `#<id>` ref."""
    ordinals, slugs = ledger_claim_id_sets(ledger_path)
    return ordinals | slugs


_ID_RE = re.compile(r"^\*\*ID:\*\*\s*([\w-]+)", re.IGNORECASE)


def claim_header_issues(ledger_path: Path) -> str | None:
    """Authored `## Claim N` numbers that are non-contiguous or out of order —
    the footgun behind positional #cN refs (insert/reorder a claim and later
    refs silently re-point). Returns a one-line description, or None if the
    numbers run 1, 2, 3, … in order. Unnumbered claims are ignored (they only
    resolve by **ID:**)."""
    numbers = claim_numbers(ledger_path)
    expected = list(range(1, len(numbers) + 1))
    if numbers and numbers != expected:
        return (f"{ledger_path.name}: ## Claim headers numbered {numbers} — "
                f"expected {expected}; positional #cN refs will re-point. "
                "Use stable **ID:** slugs.")
    return None


def claim_mode(config: dict[str, str]) -> str:
    """claim_ids: off | optional | required (default optional)."""
    raw = config.get("claim_ids", "").split("#", 1)[0].strip().lower()
    return raw if raw in ("off", "optional", "required") else "optional"


def numeric_mode(config: dict[str, str]) -> str:
    """numeric_citations: ignore | warn | block (default warn); --numeric overrides."""
    raw = config.get("numeric_citations", "").split("#", 1)[0].strip().lower()
    return raw if raw in ("ignore", "warn", "block") else "warn"


def find_numeric_markers(text: str) -> list[str]:
    """Bracketed-number and superscript-digit citation markers in text."""
    markers = NUMERIC_BRACKET_RE.findall(text)
    markers += SUPERSCRIPT_RE.findall(text)
    return markers


def author_variants(author: str) -> list[str]:
    """The author as written, plus a punctuation-stripped form (o'brien → obrien)."""
    stripped = author.replace("'", "").replace("-", "")
    return [author] if stripped == author else [author, stripped]


def register_usable(register_tsv: Path, author: str, year: str) -> bool:
    """True if REGISTER.tsv has a usable row: key ^author_year[a-z]?$ with
    status verified / downloaded / duplicate_of:<key>."""
    if not register_tsv.is_file():
        return False
    key_re = re.compile(rf"^{re.escape(author)}_{year}[a-z]?$")
    for line in register_tsv.read_text(encoding="utf-8").splitlines()[1:]:
        cols = line.split("\t")
        if len(cols) < 9:
            continue
        if key_re.match(cols[0].lower()):
            status = cols[8]
            if status in ("verified", "downloaded") or status.startswith("duplicate_of:"):
                return True
    return False


def _glob_match(directory: Path, author: str, year: str, suffix: str = "") -> bool:
    """Case-insensitive author*year*[suffix] match among directory's files."""
    if not directory.is_dir():
        return False
    # Anchor the surname with a non-letter boundary so a short name can't match
    # a longer one (author "li" must not be covered by "lin_2020"), and bound
    # the year so "2020" doesn't match "20200". Filenames are <author>_<year>*.
    name_re = re.compile(
        rf"^{re.escape(author)}(?![a-z]).*{year}(?!\d).*{re.escape(suffix)}$")
    return any(
        entry.is_file() and name_re.match(entry.name.lower())
        for entry in directory.iterdir()
    )


def paper_on_disk(literature_dir: Path, author: str, year: str) -> bool:
    return any(
        register_usable(literature_dir / "REGISTER.tsv", v, year)
        or _glob_match(literature_dir, v, year)
        for v in author_variants(author)
    )


def citation_aliases(config: dict[str, str]) -> dict[str, str]:
    """`citation_aliases: <cited key> -> <ledger key>[, …]` from ledger.config.md.

    A cite is resolved to a ledger by filename convention (<author>_<year>), and
    author_variants() already covers punctuation (la-602 → la602). An alias covers what
    it cannot: a ledger key that ABBREVIATES the surname. Cite Drouin-Chartier et al.
    (2020) against a ledger keyed drouin_2020 and the resolver misses — the cheap fix is
    to clip the surname in the prose, which lets an internal identifier dictate the
    reader-facing bibliography. The alias keeps the canonical key (what graph edges and
    sealed assessment records address) untouched and the citation accurate."""
    raw = config.get("citation_aliases", "")
    if not raw or raw.startswith("<"):
        return {}
    aliases: dict[str, str] = {}
    for pair in raw.split(","):
        cited, sep, target = pair.partition("->")
        if sep and cited.strip() and target.strip():
            aliases[cited.strip().lower()] = target.strip().lower()
    return aliases


def alias_problems(config: dict[str, str], claims_dir: Path) -> list[str]:
    """An alias must resolve one way only, and to something real."""
    aliases = citation_aliases(config)
    if not aliases:
        return []
    real = {p.stem.lower() for p in claims_dir.glob("*.md")
            if p.stem != "TEMPLATE"} if claims_dir.is_dir() else set()
    problems = []
    for cited, target in sorted(aliases.items()):
        # Shadowing: the cited key is itself a ledger, so the alias would silently
        # redirect cites that already resolve correctly.
        if cited in real:
            problems.append(f"'{cited}' is a real ledger — an alias must not shadow one")
        if real and target not in real:
            problems.append(f"'{cited} -> {target}': no ledger named '{target}'")
    # A duplicated left-hand side never reaches the dict; catch it in the raw text.
    seen, dupes = set(), set()
    for pair in config.get("citation_aliases", "").split(","):
        cited = pair.partition("->")[0].strip().lower()
        if cited:
            dupes.add(cited) if cited in seen else seen.add(cited)
    problems.extend(f"'{d}' is aliased more than once — ambiguous" for d in sorted(dupes))
    return problems


def ledger_path_for(claims_dir: Path, author: str, year: str,
                    aliases: dict[str, str] | None = None) -> Path | None:
    """The verified_claims/<author>*<year>*.md ledger for a cite, or None."""
    if not claims_dir.is_dir():
        return None
    for v in author_variants(author):
        name_re = re.compile(rf"^{re.escape(v)}(?![a-z]).*{year}(?!\d).*\.md$")
        for entry in sorted(claims_dir.iterdir()):
            if entry.is_file() and name_re.match(entry.name.lower()):
                return entry
    # Only when the filename convention misses, so the common path never pays for it.
    target = (aliases or {}).get(f"{author}_{year}")
    if not target:
        return None
    t_author, _, t_year = target.rpartition("_")
    # aliases=None on the retry: an alias points at a real ledger, never at another
    # alias, so a chain (or a cycle) can never form.
    return ledger_path_for(claims_dir, t_author, t_year)


def ledger_on_disk(claims_dir: Path, author: str, year: str) -> bool:
    return ledger_path_for(claims_dir, author, year) is not None


def corpus_present(literature_dir: Path) -> bool:
    """A local corpus exists if REGISTER.tsv does, or any downloaded source
    (pdf/html/xml) sits in literature/ — both are git-ignored, so a fresh
    clone has neither and Layer 1 must be skipped there."""
    if (literature_dir / "REGISTER.tsv").is_file():
        return True
    return any(
        any(literature_dir.glob(f"*{ext}")) for ext in (".pdf", ".html", ".xml")
    )


ORDINAL_RE = re.compile(r"^c\d+$")


def check_text(text: str, label: str, literature_dir: Path, check_papers: bool,
               claims: str = "optional",
               forbid_ordinal_refs: bool = False,
               aliases: dict[str, str] | None = None
               ) -> tuple[list[str], list[str], list[str]]:
    """Return (missing_paper, missing_ledger, claim_problems) for one gated
    prose blob. `claims` is the claim-ref posture: off | optional | required.
    Layer 2b (claim_problems): a `#<id>` ref that doesn't resolve to a real
    claim always fails; under `required`, a cite with no `#<id>` fails too. When
    `forbid_ordinal_refs` is set (strict default under `required`), a bare
    ordinal ref (#c1, #c2, … with no matching **ID:** slug) is rejected — it
    silently re-points if claims are reordered, so prose must use the stable slug."""
    claims_dir = literature_dir / "verified_claims"
    missing_paper: list[str] = []
    missing_ledger: list[str] = []
    claim_problems: list[str] = []
    for author, year, claim_id in sorted(extract_citations(text),
                                         key=lambda c: (c[0], c[1], c[2] or "")):
        cite = f"{author} {year}" + (f" #{claim_id}" if claim_id else "")
        if check_papers and not paper_on_disk(literature_dir, author, year):
            missing_paper.append(f"{label}: {cite}")
            continue
        ledger = ledger_path_for(claims_dir, author, year, aliases)
        if ledger is None:
            missing_ledger.append(f"{label}: {cite}")
            continue
        if claims == "off":
            continue
        if claim_id is not None:
            ordinals, slugs = ledger_claim_id_sets(ledger)
            if claim_id not in (ordinals | slugs):
                claim_problems.append(
                    f"{label}: {cite} — no claim '{claim_id}' in {ledger.name}")
            elif forbid_ordinal_refs and ORDINAL_RE.match(claim_id) and claim_id not in slugs:
                claim_problems.append(
                    f"{label}: {cite} — bare ordinal #{claim_id} is unstable under "
                    f"reorder; use the claim's **ID:** slug in {ledger.name}")
        elif claims == "required":
            claim_problems.append(
                f"{label}: {cite} — cite needs a #claim ref (claim_ids: required)")
    return missing_paper, missing_ledger, claim_problems


def candidate_files(paths: list[str]) -> list[Path]:
    """Every .md the positional args reach, before gating. Split out of gather_files so
    the caller can tell 'nothing to scan' from 'prose here, but none of it gated'."""
    files: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(sorted(p.rglob("*.md")))
        elif p.is_file():
            files.append(p)
        else:
            log_error(f"path not found: {raw}")
            sys.exit(2)
    return files


def gather_files(paths: list[str], prefixes: list[str]) -> list[Path]:
    """Expand positional args to the gated .md files they contain."""
    return [f for f in candidate_files(paths) if is_gated(str(f.resolve()), prefixes)]


def declares_configured(config: dict[str, str]) -> bool:
    """Whether ledger.config.md DECLARES a stood-up subject.

    Deliberately the declaration, not ledger_doctor.strict_mode: ledger_doctor imports
    this module, so importing it back would be circular. The declaration is the
    conservative half — a project claiming `configured` is held to the configured rule,
    and one that declares it while half-filled is `broken`, which doctor fails anyway."""
    return config.get("project_state", "").split("#", 1)[0].strip().lower() == "configured"


# Bookkeeping the kernel writes or a project keeps as state — not authored prose, so it
# carries no claim to gate. A configured project holding only these has simply not been
# written yet; it must not be told its gating is wrong. Everything else (inquiry, finding,
# assessments, concept notes, literature reviews) counts as prose.
MACHINERY_FILES = frozenset({"log.md", "crosswalk.md", "source_register.md",
                             "source_flow.md"})
MACHINERY_DIRS = ("_ledger",)


def is_machinery(path: Path) -> bool:
    """Project bookkeeping rather than authored prose."""
    return path.name in MACHINERY_FILES or any(d in path.parts for d in MACHINERY_DIRS)


def unscanned_prose_problem(config: dict[str, str], candidates: list[Path],
                            scanned: list[Path]) -> str | None:
    """A configured project whose gated_paths match none of its prose.

    The failure this exists to stop: coverage reports 'ok — 0 gated file(s) checked' and
    every downstream gate reads green, having verified nothing. All five shipped cases
    were in exactly that state — gated_paths named two directories that were empty
    placeholders, while the authored synthesis sat in files nothing pointed at.

    Pristine kits legitimately scan zero (`content/` ships empty by design), so the
    declaration is the discriminator rather than a blanket rule. `gated_paths: none`
    remains an explicit way to say a project gates nothing on purpose. Bookkeeping does
    not count: a freshly configured project holds a log and a crosswalk and no prose yet,
    and must not be told its gating is broken before it has written anything."""
    if scanned or not declares_configured(config):
        return None
    if not gated_prefixes(config):        # `gated_paths: none` — declared, not accidental
        return None
    prose = [p for p in candidates if not is_machinery(p)]
    if not prose:
        return None
    ungated = ", ".join(sorted(p.name for p in prose)[:5])
    return (f"configured project, but gated_paths matches none of its {len(prose)} "
            f"authored prose file(s) — nothing was checked (e.g. {ungated}). Point "
            f"gated_paths at the authored prose, or set `gated_paths: none` to declare "
            f"that this project gates none.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Quote-first citation coverage gate (paper + ledger per cite).")
    parser.add_argument("paths", nargs="*", default=None,
                        help=".md files or directories to scan (default: content)")
    parser.add_argument("--stdin", action="store_true",
                        help="read one prose blob from stdin (write-time hook mode)")
    parser.add_argument("--path", default=None,
                        help="notional path of --stdin content, for gating")
    parser.add_argument("--no-corpus", action="store_true",
                        help="skip Layer 1 (paper on disk); ledger coverage only — for CI")
    parser.add_argument("--numeric", choices=("ignore", "warn", "block"), default=None,
                        help="numeric/superscript markers; default reads numeric_citations: "
                        "from config (warn). Overrides the config posture when given.")
    parser.add_argument("--claims", choices=("off", "optional", "required"), default=None,
                        help="claim-ref posture; default reads claim_ids: from config (optional)")
    parser.add_argument("--forbid-ordinal-refs", action="store_true",
                        help="reject bare ordinal #cN refs (use stable **ID:** slugs); "
                        "default on under claim_ids: required")
    parser.add_argument("--allow-ordinal-refs", action="store_true",
                        help="permit bare ordinal #cN refs even under required (override)")
    parser.add_argument("--literature-dir", default=str(REPO_ROOT / "literature"),
                        help="override literature/ location (tests)")
    parser.add_argument("--config", default=str(REPO_ROOT / "ledger.config.md"),
                        help="override ledger.config.md location (tests)")
    args = parser.parse_args()

    literature_dir = Path(args.literature_dir)
    config = parse_config(Path(args.config))
    prefixes = gated_prefixes(config)
    claims = args.claims or claim_mode(config)
    numeric = args.numeric or numeric_mode(config)
    # Bare ordinal refs are rejected by default once claim_ids is required; the
    # explicit flags override either way (off for a deliberate opt-out, on to
    # tighten an optional project).
    if args.allow_ordinal_refs:
        forbid_ordinal = False
    elif args.forbid_ordinal_refs:
        forbid_ordinal = True
    else:
        forbid_ordinal = claims == "required"

    # Write-time (--stdin) sees one file, not the project, so it cannot tell "nothing
    # gated" from "this file isn't gated" — that judgement belongs to the full scan.
    unscanned = None
    if args.stdin:
        if not args.path:
            log_error("--stdin requires --path (the file the content is bound for)")
            return 2
        if not is_gated(args.path, prefixes):
            return 0
        blobs = [(sys.stdin.read(), args.path)]
    else:
        candidates = candidate_files(args.paths or ["content"])
        files = [f for f in candidates if is_gated(str(f.resolve()), prefixes)]
        unscanned = unscanned_prose_problem(config, candidates, files)
        blobs = [(f.read_text(encoding="utf-8", errors="ignore"), str(f))
                 for f in files]

    check_papers = not args.no_corpus
    if check_papers and not corpus_present(literature_dir):
        log_warning("no local corpus (REGISTER.tsv / sources absent) — "
                    "skipping Layer 1 paper-on-disk; ledger coverage still enforced.")
        check_papers = False

    missing_paper: list[str] = []
    missing_ledger: list[str] = []
    claim_problems: list[str] = []
    numeric_markers: list[str] = []
    for text, label in blobs:
        mp, ml, cp = check_text(text, label, literature_dir, check_papers, claims,
                                forbid_ordinal_refs=forbid_ordinal,
                                aliases=citation_aliases(config))
        missing_paper.extend(mp)
        missing_ledger.extend(ml)
        claim_problems.extend(cp)
        if numeric != "ignore":
            numeric_markers.extend(f"{label}: {m}" for m in find_numeric_markers(text))

    if missing_paper:
        log_error("Layer 1 — paper not downloaded; citations with no file in "
                  "literature/ and no usable REGISTER.tsv row:\n  - "
                  + "\n  - ".join(missing_paper)
                  + "\nLadder-first: 1) literature/check.sh <author> <year>; "
                  "2) literature/fetch_paper.sh; 3) only if the ladder fails, ask "
                  "the user to download manually (never stub); 4) python "
                  "literature/build_register.py, then re-try.")
    if missing_ledger:
        log_error("Layer 2 — no verified claims; paper available but no "
                  "literature/verified_claims/<author>_<year>.md for:\n  - "
                  + "\n  - ".join(missing_ledger)
                  + "\nRead the paper, Grep the specific claim, write the ledger "
                  "with direct quotes + location, then cite. Quote-first — no exceptions.")
    if claim_problems:
        log_error("Layer 2b — claim ref does not resolve; a cite points at a "
                  "specific claim that is not in the ledger (or, under "
                  "claim_ids: required, carries no #ref):\n  - "
                  + "\n  - ".join(claim_problems)
                  + "\nUse the claim's stable **ID:** slug (preferred — survives "
                  "reorder) or, where ordinals are permitted, its #cN position. "
                  "Add the claim to the ledger if it is genuinely missing.")
    if numeric_markers:
        msg = ("numeric/superscript citation markers found — this style cannot "
               "be resolved to a verified_claims ledger (unverified):\n  - "
               + "\n  - ".join(numeric_markers))
        if numeric == "block":
            log_error(msg)
        else:
            log_warning(msg)

    # An ambiguous alias makes every cite through it unreliable, so it blocks whether or
    # not any cite used it — the corpus, not the prose, is what is wrong.
    ambiguous = alias_problems(config, literature_dir / "verified_claims")
    if ambiguous:
        log_error("citation aliases must resolve one way only:\n  - "
                  + "\n  - ".join(ambiguous))

    if unscanned:
        log_error(unscanned)

    fired = bool(missing_paper or missing_ledger or claim_problems or ambiguous
                 or unscanned or (numeric_markers and numeric == "block"))
    if not fired and not args.stdin:
        log_info(f"citation coverage ok — {len(blobs)} gated file(s) checked.")
    return 1 if fired else 0


if __name__ == "__main__":
    sys.exit(main())
