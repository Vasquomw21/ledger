# === SCRIPT: Data-driven quote verifier — ledgers are the source of truth ===
# Purpose: mechanically confirm that every direct quote recorded in a
#          literature/verified_claims/<key>.md ledger is verbatim present in that
#          paper's extracted full text (literature/extracted/<key>.txt). This is
#          the LOCAL guard that the quote-first citation discipline is honoured;
#          it needs the gitignored paper corpus, so it does NOT run in CI.
#
#          Replaces the hand-curated, per-layer scripts (verify_quotes_l2.py,
#          _l3.py, _l4.py) whose FRAGMENTS dicts drifted from the ledgers and
#          whose ligature-stripping norm() produced false FAILs on fi/ff/ffi
#          words. Here the checks are derived from the ledgers themselves, so a
#          new ledger is covered automatically and the check can never disagree
#          with what was actually recorded.
#
# How a quote is checked (first matching stage wins):
#   - Only quote-delimited blockquote lines (`> "..."`) are checked; unquoted
#     blockquotes are editorial notes (e.g. contestation pointers), reported as
#     [NOTE] and skipped, not failed.
#   - Each quote is split on ellipses (... / … / [...]) into the contiguous spans
#     the author actually lifted from the source; each span must appear verbatim.
#   - Stage 1 [PASS]  — full normalised match. norm() NFKD-decomposes before
#     stripping to [a-z0-9], so a true-letter ledger quote ("first", "efficient")
#     matches source typeset with ligature glyphs ("ﬁrst", "eﬃcient").
#   - DIGIT GUARD — a span whose ledger text contains a digit must pass Stage 1
#     or it FAILs. Stages 2/3 drop digits before matching, so without this guard
#     a quote saying "fell by 70%" would verify against a source saying "fell by
#     90%" — and the fallbacks fire exactly when the exact match fails, i.e.
#     precisely when a number is wrong. Fallbacks are for digit-free spans only.
#   - Stage 2 [PASS*] — letters-only. Tolerates source-side punctuation/symbol
#     garbling for spans that carry no digits of their own.
#   - Stage 3 [PASS~] — maths-tolerant: strips big-O expressions and maths glyphs
#     (which the extractor drops/garbles, e.g. "O(√N)"→"", ε→ǫ) then matches
#     letters-only; the maths itself is NOT grep-verified for that span.
#   - A genuine paraphrase still FAILs every stage (e.g. ledger "double
#     exponential growth rate" vs source "double exponential rate").
#   - Spans shorter than MIN_SEGMENT_CHARS (normalised) are skipped (reported) to
#     avoid trivial substring matches from maths-only fragments.
#
# Provenance stamp: --stamp records each ledger's source/extract sha256 + verdict
# in its frontmatter, so the local-only verbatim result becomes a committed
# record. The default run (pre-commit) re-computes and compares those hashes, so a
# changed/missing/non-pass stamp is caught, per `provenance:` in ledger.config.md
# (off | warn | required). CI can't re-prove it (corpus git-ignored);
# tools/check_manifest.py attests the stamp's shape+verdict there.
# INPUTS : literature/verified_claims/<key>.md  (tracked ledgers; frontmatter holds the stamp)
#          literature/extracted/<key>.txt       (gitignored full text)
#          literature/<key>.<ext>               (gitignored source, via the ledger `file:`)
# OUTPUTS: PASS/PASS*/PASS~/FAIL/SKIP/NOTE per span; non-zero exit on FAIL or, under
#          provenance: required, a broken bind.
# Run    : python3 literature/verify_quotes.py          # verify + bind
#          python3 literature/verify_quotes.py --stamp  # write the provenance stamp
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

LITERATURE_DIR = Path(__file__).resolve().parent
LEDGER_DIR = LITERATURE_DIR / "verified_claims"
EXTRACTED_DIR = LITERATURE_DIR / "extracted"
# Per-ledger verification run-records live here (committed, auditable in PRs/CI);
# the raw corpus they reference stays git-ignored. See write_run_record().
RUN_DIR_NAME = "_runs"

VERIFIER_VERSION = "2"   # bump to mark older stamps as a prior verifier's;
                         # v2 added body_sha256 (binds the ledger's own text)

# Stamp keys, read/written as flat frontmatter scalars (no PyYAML in the kit).
# body_sha256 hashes the ledger text below the frontmatter — the quotes
# themselves — so a quote edited after stamping is caught corpus-free (CI
# recomputes it from the committed ledger), not only by the local verbatim run.
STAMP_KEYS = ("source_sha256", "extract_sha256", "body_sha256", "verifier_version",
              "verified_verdict", "verified_date")
FRONTMATTER_LINE_RE = re.compile(r"^([A-Za-z0-9_]+):\s*(.*?)\s*$")

# Source-identity fields (author-filled, per TEMPLATE.md): hashes prove the bytes
# are unchanged, but not that they are the INTENDED paper — identity does. Under
# provenance: required, every ledger must name its source file, its version, the
# retrieval date, AND at least one durable locator. Checked by check_manifest
# (corpus-free, at commit/CI) and the local bind below; the schema lives here so
# both read one definition.
IDENTITY_FIELDS = ("file", "source_version", "retrieved")
IDENTITY_LOCATORS = ("doi", "pmcid", "url")


def _identity_unset(fm: dict[str, str], field: str) -> bool:
    """A frontmatter identity field is unset if empty or a <…> template token."""
    value = (fm.get(field) or "").strip()
    return not value or value.startswith("<")


def identity_problems(fm: dict[str, str], key: str) -> list[str]:
    """Source-identity gaps in a ledger's frontmatter ([] = complete). Each
    IDENTITY_FIELD must be present, and at least one IDENTITY_LOCATOR."""
    problems = [f"{key}: missing source identity '{field}'"
                for field in IDENTITY_FIELDS if _identity_unset(fm, field)]
    if all(_identity_unset(fm, loc) for loc in IDENTITY_LOCATORS):
        problems.append(f"{key}: needs at least one source locator "
                        f"({'/'.join(IDENTITY_LOCATORS)})")
    return problems

# Minimum length (after normalisation) for a quote span to be checked. Spans
# below this are dominated by maths/symbols once stripped and would match
# spuriously, so they are skipped and reported rather than asserted.
MIN_SEGMENT_CHARS = 25

# Split a quote on the ellipsis forms used in the ledgers to mark omitted source
# text: "...", unicode "…", spaced ". . .", and bracketed "[...]".
ELLIPSIS_RE = re.compile(r"\[\s*\.\.\.\s*\]|\.\s\.\s\.|\.{3}|…")

# A blockquote line, with the leading ">" already removed by the caller.
BLOCKQUOTE_RE = re.compile(r"^>\s*(.*?)\s*$")

DOUBLE_QUOTES = '"“”'

# Stage-3 (maths-tolerant) helpers. Big-O notation is frequently dropped or
# garbled by the PDF text extractor (e.g. "O(√N)" emerges as empty), and Greek
# / operator glyphs are mis-rendered (ε → ǫ). When the prose around the maths
# matches but the maths itself does not, the quote is still faithful — the
# notation is simply not grep-verifiable — so we strip it from both sides and
# re-check, reporting PASS~ (maths NOT grep-verified for that span).
BIG_O_RE = re.compile(r"[Oo]\s*\(\s*[^)]*\)")
MATH_GLYPHS = set("κεǫλσςνμµδ∆θφϕψωρταβγ√∑∏∂ℏ⟨⟩∣∥×·∘≈∼≃≅≤≥≠≪≫∞⊗→∈±∓")


def norm(s: str) -> str:
    """Lowercase, NFKD-decompose (expands ligatures: ﬁ→fi), strip to [a-z0-9].

    NFKD decomposition is the key difference from the old per-layer scripts:
    PDF extraction preserves ligature glyphs (ﬁ, ﬀ, ﬃ, ﬄ, ﬂ); decomposing them
    yields the true letters so a quote recorded with real characters matches."""
    decomposed = unicodedata.normalize("NFKD", s).casefold()
    return re.sub(r"[^a-z0-9]", "", decomposed)


def letters(s: str) -> str:
    """Like norm() but also drops digits — leaves lowercase letters only."""
    return re.sub(r"[0-9]", "", norm(s))


def mathless(s: str) -> str:
    """Drop big-O expressions and maths glyphs, then reduce to letters only.

    Used as the last-resort match for quotes whose only un-greppable content is
    inline mathematics the extractor dropped or garbled (BIG_O_RE/MATH_GLYPHS)."""
    no_big_o = BIG_O_RE.sub(" ", s)
    no_glyphs = "".join(ch for ch in no_big_o if ch not in MATH_GLYPHS)
    return letters(no_glyphs)


def classify_span(span: str, hay: str, hay_letters: str, hay_mathless: str) -> str:
    """Verdict for one contiguous quote span: PASS / PASS* / PASS~ / FAIL /
    SKIP (too short to assert) / EMPTY (nothing left after normalisation).

    A span containing a digit must match Stage 1 exactly or FAIL — the
    letters-only / maths fallbacks drop digits from both sides, so they are
    reserved for digit-free spans (this is the gate against a quote whose
    numbers differ from the source)."""
    needle = norm(span)
    if len(needle) < MIN_SEGMENT_CHARS:
        return "SKIP" if needle else "EMPTY"
    if needle in hay:
        return "PASS"
    if re.search(r"\d", span):
        return "FAIL"
    if letters(span) in hay_letters:
        return "PASS*"
    m = mathless(span)
    if m and m in hay_mathless:
        return "PASS~"
    return "FAIL"


def extract_quotes(ledger_path: Path) -> tuple[list[str], int]:
    """Return (quotes, n_notes). A quote = the text between the first and last
    double-quote on a blockquote line. Blockquote lines with no double-quote are
    editorial notes (counted, not returned)."""
    quotes: list[str] = []
    n_notes = 0
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip()
        if not stripped.startswith(">"):
            continue
        body = BLOCKQUOTE_RE.match(stripped).group(1).strip()
        if not body:
            continue
        idx = [i for i, ch in enumerate(body) if ch in DOUBLE_QUOTES]
        if len(idx) >= 2 and idx[-1] > idx[0]:
            quotes.append(body[idx[0] + 1:idx[-1]])
        else:
            n_notes += 1
    return quotes, n_notes


def check_ledger(key: str, ledger_path: Path,
                 extracted_dir: Path = EXTRACTED_DIR,
                 log: list[str] | None = None) -> dict[str, int]:
    """Verify one ledger. Returns a tally dict keyed by verdict
    (pass / pass_star / pass_tilde / fail / skip / notes). If `log` is given,
    every emitted line is also appended to it — the run-record (write_run_record)
    hashes that transcript so a verdict is reproducible-on-audit."""
    def emit(msg: str) -> None:
        print(msg)
        if log is not None:
            log.append(msg)

    tally = {"pass": 0, "pass_star": 0, "pass_tilde": 0,
             "fail": 0, "skip": 0, "notes": 0}
    extract_path = extracted_dir / f"{key}.txt"
    emit(f"=== {key} ===")
    if not extract_path.exists():
        emit(f"  [FAIL] missing extract: {extract_path}")
        tally["fail"] += 1
        return tally

    raw = extract_path.read_text(encoding="utf-8")
    hay, hay_letters, hay_mathless = norm(raw), letters(raw), mathless(raw)
    quotes, n_notes = extract_quotes(ledger_path)
    tally["notes"] = n_notes
    if n_notes:
        emit(f"  [NOTE] {n_notes} unquoted blockquote line(s) skipped (editorial)")
    if not quotes:
        emit("  [WARNING] no quoted blockquotes found in ledger")

    labels = {"PASS": ("pass", "[PASS]  "),
              "PASS*": ("pass_star", "[PASS*] (letters-only fallback) "),
              "PASS~": ("pass_tilde", "[PASS~] (maths not grep-verified) "),
              "FAIL": ("fail", "[FAIL]  "),
              "SKIP": ("skip", "[SKIP]  (too short) ")}
    for quote in quotes:
        for span in ELLIPSIS_RE.split(quote):
            verdict = classify_span(span, hay, hay_letters, hay_mathless)
            if verdict == "EMPTY":
                continue
            counter, label = labels[verdict]
            tally[counter] += 1
            emit(f"  {label}{span.strip()[:66]}")
    print()
    return tally


# --- provenance stamp: bind hashes + verdict into ledger frontmatter ---------

def sha256_file(path: Path) -> str:
    """Hex sha256 of a file's bytes (symlinks resolve to the real target)."""
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    """Hex sha256 of a string's UTF-8 bytes (for hashing the ledger body)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ledger_body(ledger_path: Path) -> str:
    """The ledger text below the frontmatter, in the exact canonical form
    upsert_frontmatter writes (lines joined by newlines, one trailing newline).
    This is the verified content — the quotes — so hashing it binds what was
    verified to what is committed. No frontmatter / empty body yields ""."""
    lines = Path(ledger_path).read_text(encoding="utf-8", errors="ignore").splitlines()
    body = lines
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        body = lines[end + 1:] if end is not None else lines
    return ("\n".join(body) + "\n") if body else ""


def read_frontmatter(ledger_path: Path) -> dict[str, str]:
    """Flat key->value map of a ledger's `---…---` block, or {} if none."""
    lines = Path(ledger_path).read_text(encoding="utf-8", errors="ignore").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = FRONTMATTER_LINE_RE.match(line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"')
    return fm


def upsert_frontmatter(ledger_path: Path, updates: dict[str, str]) -> None:
    """Insert/replace the given keys in the ledger frontmatter (created if absent);
    other lines preserved verbatim."""
    path = Path(ledger_path)
    lines = path.read_text(encoding="utf-8").splitlines()
    has_fm = bool(lines) and lines[0].strip() == "---"
    end = None
    if has_fm:
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is None:                      # malformed: treat as no frontmatter
            has_fm = False
    block = lines[1:end] if has_fm else []
    rest = lines[end + 1:] if has_fm else lines
    remaining = dict(updates)
    new_block: list[str] = []
    for line in block:
        m = FRONTMATTER_LINE_RE.match(line)
        if m and m.group(1) in remaining:
            new_block.append(f'{m.group(1)}: "{remaining.pop(m.group(1))}"')
        else:
            new_block.append(line)
    for key, value in remaining.items():
        new_block.append(f'{key}: "{value}"')
    rebuilt = ["---", *new_block, "---", *rest]
    path.write_text("\n".join(rebuilt) + "\n", encoding="utf-8")


def verdict_for(tally: dict[str, int]) -> str:
    """A ledger's verdict from its span tally: pass iff nothing FAILed."""
    return "fail" if tally.get("fail", 0) else "pass"


def ledger_source_path(ledger_path: Path, repo_root: Path) -> Path | None:
    """The source a ledger attests, from its `file:` frontmatter (repo-relative),
    or None if unset."""
    rel = read_frontmatter(ledger_path).get("file", "")
    return (repo_root / rel) if rel else None


def stamp_ledger(ledger_path: Path, extract_path: Path, source_path: Path,
                 verdict: str, today: str | None = None) -> dict[str, str]:
    """Compute the binding fields and write them into the ledger frontmatter.
    body_sha256 is read before the write — upsert touches only the frontmatter,
    so the body is identical either way."""
    kv = {
        "source_sha256": sha256_file(source_path),
        "extract_sha256": sha256_file(extract_path),
        "body_sha256": sha256_text(ledger_body(ledger_path)),
        "verifier_version": VERIFIER_VERSION,
        "verified_verdict": verdict,
        "verified_date": today or dt.date.today().strftime("%Y%m%d"),
    }
    upsert_frontmatter(ledger_path, kv)
    return kv


# --- verification run-record: an auditable, attributable attestation ----------
# The stamp records WHAT was verified (the hashes + verdict). The run-record adds
# the CIRCUMSTANCES — toolchain, committer, the verbatim transcript — so a local
# verification is auditable and attributable, and CI can cross-check three copies
# of body_sha256 (ledger, stamp, run-record) corpus-free. HONEST LIMIT: a locally
# self-generated JSON is still self-attested; this raises the cost and traceability
# of forgery, it is NOT independent proof (CI has no corpus to re-hash the source).

def run_record_digest(record: dict) -> str:
    """Canonical sha256 over a run-record's fields EXCEPT record_sha256 — the
    internal-consistency seal CI recomputes corpus-free. Both writer and checker
    must canonicalise identically (sorted keys, UTF-8), so it lives here."""
    payload = {k: v for k, v in record.items() if k != "record_sha256"}
    return sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False))


def extract_toolchain() -> str:
    """Best-effort identity of the text-extraction toolchain PRESENT at verify
    time (pypdf for PDFs, bs4+lxml for HTML). This records what could have made
    the extract, not proof of what did — a future extractor change that alters
    bytes is then at least diagnosable. 'absent' if a package is not installed."""
    import importlib.metadata as im
    parts = []
    for pkg in ("pypdf", "beautifulsoup4", "lxml"):
        try:
            parts.append(f"{pkg}={im.version(pkg)}")
        except Exception:
            parts.append(f"{pkg}=absent")
    return ";".join(parts)


def git_committer(repo_root: Path) -> str:
    """The committer's git email — binds the run-record to an identity, so a
    forged record is at least attributable. Empty if git/identity is unavailable."""
    try:
        out = subprocess.run(["git", "config", "user.email"], cwd=str(repo_root),
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip()
    except Exception:
        return ""


def write_run_record(ledger_path: Path, stamp_kv: dict[str, str],
                     transcript_lines: list[str], repo_root: Path,
                     command: str) -> Path:
    """Write literature/verified_claims/_runs/<key>.run.json capturing the
    circumstances of THIS local verification (committed, auditable). Identity is
    copied from the ledger frontmatter; the hashes mirror the stamp so CI can
    cross-check them; record_sha256 seals the record against later hand-editing."""
    fm = read_frontmatter(ledger_path)
    key = Path(ledger_path).stem
    runs_dir = Path(ledger_path).parent / RUN_DIR_NAME
    runs_dir.mkdir(exist_ok=True)
    record = {
        "key": key,
        "verified_date": stamp_kv["verified_date"],
        "verified_verdict": stamp_kv["verified_verdict"],
        "verifier_version": stamp_kv["verifier_version"],
        "source_sha256": stamp_kv["source_sha256"],
        "extract_sha256": stamp_kv["extract_sha256"],
        "body_sha256": stamp_kv["body_sha256"],
        "extract_tool": "extract_text.py",
        "extract_tool_version": extract_toolchain(),
        "file": fm.get("file", ""),
        "doi": fm.get("doi", ""),
        "pmcid": fm.get("pmcid", ""),
        "url": fm.get("url", ""),
        "retrieved": fm.get("retrieved", ""),
        "command": command,
        "transcript_sha256": sha256_text("\n".join(transcript_lines)),
        "host_user": git_committer(repo_root),
    }
    record["record_sha256"] = run_record_digest(record)
    rec_path = runs_dir / f"{key}.run.json"
    rec_path.write_text(json.dumps(record, indent=2, sort_keys=True,
                                   ensure_ascii=False) + "\n", encoding="utf-8")
    return rec_path


def check_binding(ledger_path: Path, extract_path: Path,
                  source_path: Path | None,
                  require_identity: bool = False) -> list[str]:
    """Recompute hashes, compare to the recorded stamp; return problems ([] =
    bound & fresh). The compare is what makes the stamp un-forgeable/un-stale.
    Under require_identity (provenance: required) the source-identity fields must
    also be present — hashes prove byte-continuity, identity proves it's the
    intended paper."""
    fm = read_frontmatter(ledger_path)
    key = Path(ledger_path).stem
    if not fm.get("source_sha256") or not fm.get("extract_sha256"):
        return [f"{key}: no provenance stamp (run verify_quotes.py --stamp)"]
    problems: list[str] = identity_problems(fm, key) if require_identity else []
    if fm.get("verified_verdict") != "pass":
        problems.append(f"{key}: verified_verdict is "
                        f"'{fm.get('verified_verdict') or '<unset>'}', not pass")
    if extract_path.exists() and sha256_file(extract_path) != fm["extract_sha256"]:
        problems.append(f"{key}: extract_sha256 stale — extracted/{key}.txt "
                        "changed since the stamp; re-run --stamp")
    if source_path and source_path.exists() and sha256_file(source_path) != fm["source_sha256"]:
        problems.append(f"{key}: source_sha256 stale — the source file changed "
                        "since the stamp; re-run --stamp")
    # body_sha256 is corpus-free (the ledger hashes itself): a missing one is a
    # pre-v2 stamp; a mismatch means the quoted text was edited after stamping.
    if not fm.get("body_sha256"):
        problems.append(f"{key}: stamp predates body binding (v2) — re-run --stamp")
    elif sha256_text(ledger_body(ledger_path)) != fm["body_sha256"]:
        problems.append(f"{key}: body_sha256 stale — the ledger's quoted text "
                        "changed since the stamp; re-run --stamp")
    return problems


def provenance_mode(config_path: Path) -> str:
    """provenance: off | warn | required (default warn). Read with the kit's flat
    line parse — no PyYAML."""
    if not Path(config_path).is_file():
        return "warn"
    for line in Path(config_path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*provenance:\s*([A-Za-z]+)", line)
        if m and m.group(1).lower() in ("off", "warn", "required"):
            return m.group(1).lower()
    return "warn"


def main(ledger_dir: Path = LEDGER_DIR,
         extracted_dir: Path = EXTRACTED_DIR,
         repo_root: Path | None = None,
         config_path: Path | None = None,
         stamp: bool = False,
         provenance: str | None = None,
         strict: bool = False) -> int:
    if not ledger_dir.is_dir():
        print(f"[ERROR] ledger dir not found: {ledger_dir}")
        return 2

    ledgers = sorted(p for p in ledger_dir.glob("*.md") if p.stem != "TEMPLATE")
    if not ledgers:
        # An empty ledger directory is a valid project state (fresh subject,
        # nothing cited yet) — warn, don't abort the commit.
        print(f"[WARNING] no ledgers in {ledger_dir} yet — nothing to verify")
        return 0

    # Strict (configured) projects may not commit ledgers with the corpus gone:
    # without any extracted text there is nothing to verify the quotes against,
    # so a "no extracts" state that silently passes (the pristine path) becomes a
    # hard failure here. ledger_doctor decides strictness; this receives the bool.
    if strict and not stamp and not any(
            (extracted_dir / f"{led.stem}.txt").exists() for led in ledgers):
        print(f"[ERROR] configured project has {len(ledgers)} ledger(s) but no "
              f"extracted text in {extracted_dir} — rebuild the corpus "
              "(fetch_paper.sh + extract_text.py) before committing; quotes "
              "cannot be verified without it.", file=sys.stderr)
        return 1

    repo_root = repo_root or LITERATURE_DIR.parent
    config_path = config_path or (repo_root / "ledger.config.md")
    mode = provenance or provenance_mode(config_path)

    totals = {"pass": 0, "pass_star": 0, "pass_tilde": 0,
              "fail": 0, "skip": 0, "notes": 0}
    binding_problems: list[str] = []
    command = " ".join(sys.argv) if sys.argv else "verify_quotes.py"
    for ledger in ledgers:
        transcript: list[str] = []
        tally = check_ledger(ledger.stem, ledger, extracted_dir, log=transcript)
        for k, v in tally.items():
            totals[k] += v
        extract = extracted_dir / f"{ledger.stem}.txt"
        source = ledger_source_path(ledger, repo_root)
        if stamp:
            if source and source.exists() and extract.exists():
                kv = stamp_ledger(ledger, extract, source, verdict_for(tally))
                rec = write_run_record(ledger, kv, transcript, repo_root, command)
                print(f"  [STAMP] {ledger.stem}: verdict={kv['verified_verdict']} "
                      f"source={kv['source_sha256'][:12]}… "
                      f"extract={kv['extract_sha256'][:12]}…")
                print(f"  [RUN]   {ledger.stem}: run-record {rec.parent.name}/{rec.name}")
            else:
                print(f"  [WARNING] {ledger.stem}: cannot stamp — missing source "
                      f"({source}) or extract ({extract})")
        elif mode != "off":
            # Under provenance: required the source-identity fields are checked
            # too (hashes prove byte-continuity; identity proves it's the paper).
            binding_problems.extend(
                check_binding(ledger, extract, source, require_identity=(mode == "required")))

    print(f"[SUMMARY] {len(ledgers)} ledgers | {totals['pass']} PASS exact | "
          f"{totals['pass_star']} PASS* (letters-only fallback) | "
          f"{totals['pass_tilde']} PASS~ (maths fallback) | "
          f"{totals['fail']} FAIL | {totals['skip']} SKIP (short) | "
          f"{totals['notes']} editorial notes")

    if binding_problems and not stamp:
        header = ("[ERROR] provenance binding failed (provenance: required) — a "
                  "stamp is missing, stale, or not pass:" if mode == "required"
                  else "[WARNING] provenance not bound (provenance: warn) — run "
                  "verify_quotes.py --stamp to record/refresh:")
        print(header, file=sys.stderr)
        for problem in binding_problems:
            print(f"  - {problem}", file=sys.stderr)

    fired = bool(totals["fail"]
                 or (mode == "required" and binding_problems and not stamp))
    return 1 if fired else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Verify ledger quotes are verbatim; stamp/bind provenance.")
    ap.add_argument("--stamp", action="store_true",
                    help="compute + write source/extract sha256 + verdict into each "
                    "ledger's frontmatter (the explicit step; the git hook never mutates files)")
    ap.add_argument("--provenance", choices=("off", "warn", "required"), default=None,
                    help="override the provenance posture (default: provenance: in ledger.config.md)")
    ap.add_argument("--strict", action="store_true",
                    help="configured-project mode: fail if ledgers exist but no extracted "
                    "corpus is present to verify them against (pre-commit passes this when "
                    "ledger_doctor reports the project is configured)")
    args = ap.parse_args()
    sys.exit(main(stamp=args.stamp, provenance=args.provenance, strict=args.strict))
