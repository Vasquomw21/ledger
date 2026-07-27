# Tests for the optional attestation gate (corpus-free). Most cases use a
# stub verifier so no real keys are needed; one live round-trip runs only if
# ssh-keygen is present (skipped otherwise).
import json
import shutil
import subprocess

import pytest

import check_attestation as cat
import sign_records as sr


def _record(runs_dir, key="andersen_2020", host_user="dev@example.com", sig=True):
    runs_dir.mkdir(parents=True, exist_ok=True)
    rec = runs_dir / f"{key}.run.json"
    rec.write_text(json.dumps({"key": key, "host_user": host_user}), encoding="utf-8")
    if sig:
        (runs_dir / f"{key}.run.json.sig").write_text("dummy-sig", encoding="utf-8")
    return rec


def _ok(*a, **k):
    return True, ""


def _bad(*a, **k):
    return False, "bad signature"


# --- logic (stub verifier) -------------------------------------------------

def test_empty_runs_dir_passes(tmp_path):
    assert cat.attestation_problems(tmp_path / "_runs", tmp_path / "signers") == []


def test_missing_signature_flagged(tmp_path):
    runs = tmp_path / "_runs"
    _record(runs, sig=False)
    problems = cat.attestation_problems(runs, tmp_path / "signers", verify=_ok)
    assert any("no detached signature" in p for p in problems)


def test_valid_signature_passes(tmp_path):
    runs = tmp_path / "_runs"
    _record(runs)
    assert cat.attestation_problems(runs, tmp_path / "signers", verify=_ok) == []


def test_invalid_signature_flagged(tmp_path):
    runs = tmp_path / "_runs"
    _record(runs)
    problems = cat.attestation_problems(runs, tmp_path / "signers", verify=_bad)
    assert any("did not verify" in p for p in problems)


# --- posture exit codes (main, stub verifier via monkeypatch) --------------

def test_off_skips(tmp_path, monkeypatch, capsys):
    runs = tmp_path / "_runs"
    _record(runs, sig=False)
    assert _run_main(monkeypatch, runs, "off") == 0
    assert "off" in capsys.readouterr().out


def test_required_fails_warn_passes(tmp_path, monkeypatch):
    runs = tmp_path / "_runs"
    _record(runs, sig=False)
    monkeypatch.setattr(cat, "verify_signature", _ok)
    assert _run_main(monkeypatch, runs, "required") == 1   # missing .sig
    assert _run_main(monkeypatch, runs, "warn") == 0


# --- live round-trip (only if ssh-keygen exists) ---------------------------

@pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="ssh-keygen absent")
def test_live_sign_and_verify(tmp_path):
    key = tmp_path / "id_ed25519"
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-C", "dev@example.com",
                    "-f", str(key)], check=True, capture_output=True)
    pub = (tmp_path / "id_ed25519.pub").read_text().strip()
    signers = tmp_path / "allowed_signers"
    signers.write_text(f'dev@example.com namespaces="{cat.NAMESPACE}" {pub}\n',
                       encoding="utf-8")
    runs = tmp_path / "_runs"
    rec = _record(runs, sig=False)
    sr.sign_record(rec, key)
    problems = cat.attestation_problems(runs, signers)
    assert problems == []
    # Tamper the record after signing → signature must fail.
    rec.write_text(json.dumps({"key": "andersen_2020", "host_user": "dev@example.com",
                               "x": "tampered"}), encoding="utf-8")
    assert cat.attestation_problems(runs, signers) != []


def _run_main(monkeypatch, runs_dir, mode):
    argv = ["check_attestation.py", "--runs-dir", str(runs_dir), "--attestation", mode]
    monkeypatch.setattr("sys.argv", argv)
    return cat.main()
