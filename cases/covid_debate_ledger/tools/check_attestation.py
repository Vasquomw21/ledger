# === SCRIPT: Attestation gate — run-records are signed by an allowed signer ===
# Addresses the "self-attested across machines" limit:
# run-records improve attribution and tamper-evidence, but a forged LOCAL
# verification is still possible because CI cannot re-hash the git-ignored source.
# This OPT-IN gate raises the bar for teams that need stronger remote proof: each
# committed run-record must carry a DETACHED SSH SIGNATURE from a key on the
# project's allow-list, verified with `ssh-keygen -Y verify`. CI (and any clone)
# can then confirm WHO attested each verification over the exact committed bytes —
# no new infrastructure or Python dependency, just the ssh-keygen every dev has.
#
# HONEST LIMIT (stated, not hidden): a signature proves an allowed signer vouched
# for THESE record bytes; it does NOT independently re-hash the source (the corpus
# is git-ignored, absent in CI). It closes "anyone can forge a run-record in a PR",
# NOT "the local machine could have mis-verified". Source truth stays local; this
# makes every remote attestation attributable to a held key. Default off → no-op.
# INPUTS : literature/verified_claims/_runs/*.run.json (+ .sig siblings);
#          the allow-list (attestation_signers: in config, default .ledger/
#          allowed_signers); attestation: in config.
# OUTPUTS: [INFO]/[WARNING]/[ERROR]; exit 0 = ok or posture off/warn; 1 = a missing
#          or invalid signature under attestation: required.
# Run    : python3 tools/check_attestation.py
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from check_citations import parse_config

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "literature"))
from verify_quotes import RUN_DIR_NAME  # noqa: E402

RUNS_DIR = REPO_ROOT / "literature" / "verified_claims" / RUN_DIR_NAME
DEFAULT_SIGNERS = ".ledger/allowed_signers"
# The ssh signature namespace — scopes a signature to this purpose so a ledger
# run-record signature can't be replayed as, say, a git commit signature.
NAMESPACE = "ledger-run-record"


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_warning(msg: str) -> None:
    print(f"[WARNING] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def attestation_mode(config: dict[str, str]) -> str:
    """attestation: off | warn | required (default off — opt-in)."""
    raw = config.get("attestation", "").split("#", 1)[0].strip().lower()
    return raw if raw in ("off", "warn", "required") else "off"


def signers_path(config: dict[str, str], repo_root: Path) -> Path:
    raw = config.get("attestation_signers", "").split("#", 1)[0].strip()
    return repo_root / (raw if raw and not raw.startswith("<") else DEFAULT_SIGNERS)


def verify_signature(record_path: Path, sig_path: Path, signers: Path,
                     principal: str) -> tuple[bool, str]:
    """Verify a detached SSH signature over the record bytes via `ssh-keygen -Y
    verify`. (ok, reason). Isolated so tests can monkeypatch it without real keys."""
    if not signers.is_file():
        return False, f"no allowed_signers at {signers}"
    if not principal:
        return False, "no signer principal recorded"
    try:
        proc = subprocess.run(
            ["ssh-keygen", "-Y", "verify", "-f", str(signers), "-I", principal,
             "-n", NAMESPACE, "-s", str(sig_path)],
            input=record_path.read_bytes(), capture_output=True, timeout=15)
    except FileNotFoundError:
        return False, "ssh-keygen not available"
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if proc.returncode == 0:
        return True, ""
    return False, (proc.stderr.decode("utf-8", "ignore").strip() or "verify failed")


def attestation_problems(runs_dir: Path, signers: Path, verify=None) -> list[str]:
    """Run-records lacking a valid detached signature ([] = all signed + verified).
    verify defaults to verify_signature, resolved at call time so a test (or main)
    can substitute it without real keys."""
    verify = verify or verify_signature
    problems: list[str] = []
    if not runs_dir.is_dir():
        return problems
    for rec_path in sorted(runs_dir.glob("*.run.json")):
        sig_path = rec_path.with_name(rec_path.name + ".sig")
        if not sig_path.is_file():
            problems.append(f"{rec_path.name}: no detached signature "
                            f"({sig_path.name}) — run tools/sign_records.py")
            continue
        try:
            principal = json.loads(rec_path.read_text(encoding="utf-8")).get("host_user", "")
        except (OSError, ValueError) as exc:
            problems.append(f"{rec_path.name}: unreadable ({exc})")
            continue
        ok, reason = verify(rec_path, sig_path, signers, str(principal))
        if not ok:
            problems.append(f"{rec_path.name}: signature did not verify — {reason}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Attest run-records carry a valid allowed-signer signature.")
    ap.add_argument("--runs-dir", default=str(RUNS_DIR))
    ap.add_argument("--config", default=str(REPO_ROOT / "ledger.config.md"))
    ap.add_argument("--repo-root", default=str(REPO_ROOT))
    ap.add_argument("--attestation", choices=("off", "warn", "required"), default=None,
                    help="override the posture (default: attestation: in config)")
    args = ap.parse_args()

    config = parse_config(Path(args.config))
    mode = args.attestation or attestation_mode(config)
    if mode == "off":
        log_info("attestation: off — signature attestation skipped.")
        return 0

    problems = attestation_problems(Path(args.runs_dir),
                                    signers_path(config, Path(args.repo_root)))
    if not problems:
        log_info("attestation ok — every run-record carries a verified signature.")
        return 0
    message = ("run-record attestation problems (missing/invalid signature):\n  - "
               + "\n  - ".join(problems))
    if mode == "required":
        log_error(message)
        return 1
    log_warning(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
