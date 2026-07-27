# === SCRIPT: Provenance attestation — every committed ledger carries a stamp ===
# The corpus-less half of the provenance guarantee. verify_quotes.py BINDS the
# stamp locally (recompute + compare; needs the git-ignored corpus); this checks
# at pre-commit and in CI that each committed ledger's frontmatter carries a
# well-formed stamp with a pass verdict. It attests shape, not bytes — CI has no
# corpus to re-hash, so it trusts the local bind.
# INPUTS : literature/verified_claims/*.md frontmatter; provenance: in ledger.config.md.
# OUTPUTS: [INFO]/[WARNING]/[ERROR]; exit 0 = ok or posture off/warn; 1 = required gap.
# Run    : python3 tools/check_manifest.py
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from check_citations import parse_config

REPO_ROOT = Path(__file__).resolve().parents[1]
# The verbatim verifier owns the stamp schema; import its version + body-hash
# helpers so this corpus-free attestor recomputes body_sha256 identically, plus
# the run-record schema (digest + dir name) so the two read one definition.
sys.path.insert(0, str(REPO_ROOT / "literature"))
from verify_quotes import (FRONTMATTER_LINE_RE, RUN_DIR_NAME,  # noqa: E402
                           VERIFIER_VERSION, identity_problems, ledger_body,
                           read_frontmatter, run_record_digest, sha256_file,
                           sha256_text)

CLAIMS_DIR = REPO_ROOT / "literature" / "verified_claims"

STAMP_FIELDS = ("source_sha256", "extract_sha256", "body_sha256",
                "verifier_version", "verified_verdict", "verified_date")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_warning(msg: str) -> None:
    print(f"[WARNING] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def provenance_mode(config: dict[str, str]) -> str:
    """provenance: off | warn | required (default warn)."""
    raw = config.get("provenance", "").split("#", 1)[0].strip().lower()
    return raw if raw in ("off", "warn", "required") else "warn"


def stamp_problems(fm: dict[str, str], key: str) -> list[str]:
    """Shape problems with one ledger's stamp ([] = valid)."""
    problems = [f"{key}: missing {field}" for field in STAMP_FIELDS if not fm.get(field)]
    for field in ("source_sha256", "extract_sha256", "body_sha256"):
        value = fm.get(field, "")
        if value and not HEX64_RE.match(value):
            problems.append(f"{key}: {field} is not a 64-hex sha256")
    verdict = fm.get("verified_verdict", "")
    if verdict and verdict != "pass":
        problems.append(f"{key}: verified_verdict is '{verdict}', not pass")
    version = fm.get("verifier_version", "")
    if version.isdigit() and int(version) < int(VERIFIER_VERSION):
        problems.append(f"{key}: verifier_version {version} predates current "
                        f"{VERIFIER_VERSION} — re-verify and re-run --stamp")
    return problems


def run_record_problems(claims_dir: Path, key: str, fm: dict[str, str],
                        recomputed_body: str) -> list[str]:
    """Corpus-free attestation of a ledger's verification run-record: it exists,
    its record_sha256 is internally consistent, its body_sha256 agrees with BOTH
    the recomputed ledger body and the stamp (three-way cross-check), its source
    identity matches the frontmatter, and it is not a pre-record verifier. CI
    cannot re-hash the source, but a forged record must now also be internally
    consistent across all three copies of the body hash and the frontmatter."""
    rec_path = claims_dir / RUN_DIR_NAME / f"{key}.run.json"
    if not rec_path.is_file():
        return [f"{key}: no verification run-record ({RUN_DIR_NAME}/{key}.run.json)"
                " — run verify_quotes.py --stamp"]
    try:
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{key}: run-record unreadable ({exc})"]
    problems: list[str] = []
    if rec.get("record_sha256") != run_record_digest(rec):
        problems.append(f"{key}: run-record record_sha256 inconsistent — edited "
                        "after it was written (re-run --stamp)")
    if recomputed_body and rec.get("body_sha256") != recomputed_body:
        problems.append(f"{key}: run-record body_sha256 != the committed ledger body")
    if rec.get("body_sha256") != fm.get("body_sha256"):
        problems.append(f"{key}: run-record body_sha256 != the stamp's body_sha256")
    for field in ("file", "doi", "pmcid", "url", "retrieved"):
        if (rec.get(field) or "") != (fm.get(field) or ""):
            problems.append(f"{key}: run-record '{field}' disagrees with the ledger")
    if str(rec.get("verifier_version", "")) != str(fm.get("verifier_version", "")):
        problems.append(f"{key}: run-record verifier_version != the stamp's")
    if not (rec.get("extract_tool_version") or "").strip():
        problems.append(f"{key}: run-record has no extract_tool_version")
    return problems


def check_dir(claims_dir: Path, require_identity: bool = False,
              require_run_record: bool = False) -> list[str]:
    """All stamp problems across the ledgers in claims_dir (TEMPLATE skipped).
    Recomputes body_sha256 from each committed ledger — the corpus-free check
    that a quote was not edited after the stamp was written. Under
    require_identity (provenance: required) also asserts the source-identity
    fields (file / version / retrieved / a locator) are present; under
    require_run_record, every ledger must carry a consistent run-record."""
    problems: list[str] = []
    for ledger in sorted(claims_dir.glob("*.md")):
        if ledger.stem == "TEMPLATE":
            continue
        fm = read_frontmatter(ledger)
        problems.extend(stamp_problems(fm, ledger.stem))
        if require_identity:
            problems.extend(identity_problems(fm, ledger.stem))
        recomputed = sha256_text(ledger_body(ledger))
        recorded = fm.get("body_sha256", "")
        if HEX64_RE.match(recorded) and recomputed != recorded:
            problems.append(f"{ledger.stem}: body_sha256 mismatch — the ledger's "
                            "quoted text was edited after --stamp")
        if require_run_record:
            problems.extend(run_record_problems(claims_dir, ledger.stem, fm, recomputed))
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Attest every committed ledger carries a valid provenance stamp.")
    ap.add_argument("--claims-dir", default=str(CLAIMS_DIR),
                    help="override verified_claims/ location (tests)")
    ap.add_argument("--config", default=str(REPO_ROOT / "ledger.config.md"),
                    help="override ledger.config.md location (tests)")
    ap.add_argument("--provenance", choices=("off", "warn", "required"), default=None,
                    help="override the posture (default: provenance: in config)")
    args = ap.parse_args()

    mode = args.provenance or provenance_mode(parse_config(Path(args.config)))
    if mode == "off":
        log_info("provenance: off — manifest attestation skipped.")
        return 0

    claims_dir = Path(args.claims_dir)
    ledgers = [p for p in claims_dir.glob("*.md") if p.stem != "TEMPLATE"] \
        if claims_dir.is_dir() else []
    if not ledgers:
        log_info("no ledgers yet — nothing to attest.")
        return 0

    problems = check_dir(claims_dir, require_identity=(mode == "required"),
                         require_run_record=(mode == "required"))
    if not problems:
        log_info(f"provenance ok — {len(ledgers)} ledger(s) carry a valid stamp.")
        return 0
    message = ("provenance stamps missing/invalid (run verify_quotes.py --stamp):\n  - "
               + "\n  - ".join(problems))
    if mode == "required":
        log_error(message)
        return 1
    log_warning(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
