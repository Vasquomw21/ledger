# === SCRIPT: Sign run-records — detached SSH signatures for remote attestation ===
# The authoring half of the optional attestation layer. For each
# committed verification run-record it writes a detached SSH signature
# (<record>.sig) with the author's SSH signing key, scoped to the ledger-run-record
# namespace, so a clone / CI can confirm an allow-listed signer vouched for those
# exact bytes (check_attestation.py). Uses ssh-keygen -Y sign — no new dependency.
#
# One-time setup for a signer:
#   1. have an SSH key (e.g. ~/.ssh/id_ed25519);
#   2. add its public key to .ledger/allowed_signers in the
#      ssh allowed_signers format:  <your-git-email> namespaces="ledger-run-record" <ssh-ed25519 AAAA...>
#   3. python3 tools/sign_records.py --key ~/.ssh/id_ed25519
# The principal verified against is the run-record's host_user (the git committer
# email captured when it was written), so it must match the allowed_signers line.
# Run    : python3 tools/sign_records.py --key <ssh-private-key>
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "literature"))
from verify_quotes import RUN_DIR_NAME  # noqa: E402
from check_attestation import NAMESPACE  # noqa: E402

RUNS_DIR = REPO_ROOT / "literature" / "verified_claims" / RUN_DIR_NAME


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def sign_record(record_path: Path, key_path: Path) -> Path:
    """Write a detached signature <record>.sig via ssh-keygen -Y sign. Raises
    CalledProcessError on failure (no key, bad key) so the caller reports it."""
    subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(key_path), "-n", NAMESPACE,
         str(record_path)],
        check=True, capture_output=True)
    return record_path.with_name(record_path.name + ".sig")


def main() -> int:
    ap = argparse.ArgumentParser(description="Sign verification run-records.")
    ap.add_argument("--key", required=True, help="path to the SSH signing private key")
    ap.add_argument("--runs-dir", default=str(RUNS_DIR))
    args = ap.parse_args()

    runs_dir = Path(args.runs_dir)
    records = sorted(runs_dir.glob("*.run.json")) if runs_dir.is_dir() else []
    if not records:
        log_info("no run-records to sign.")
        return 0
    signed = 0
    for rec in records:
        try:
            sig = sign_record(rec, Path(args.key))
        except (OSError, subprocess.CalledProcessError) as exc:
            stderr = getattr(exc, "stderr", b"")
            detail = stderr.decode("utf-8", "ignore").strip() if stderr else str(exc)
            log_error(f"{rec.name}: signing failed — {detail}")
            return 1
        log_info(f"signed {rec.name} → {sig.name}")
        signed += 1
    log_info(f"done — {signed} run-record(s) signed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
