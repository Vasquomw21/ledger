# Tests for the provenance attestation gate (corpus-free; tmp fixtures).
import json
import sys

import check_manifest as cm
import verify_quotes as vq


def _write(tmp_path, name="smith_2020.md", body='> "a verbatim quote"\n',
           drop=(), **overrides):
    """Write a stamped ledger into tmp verified_claims/. body_sha256 is set to
    the real hash of the canonical body unless the caller overrides it (to forge
    a mismatch). Other fields default to a valid v-current stamp with complete
    source-identity metadata; pass drop=(fields…) to omit identity fields."""
    d = tmp_path / "verified_claims"
    d.mkdir(parents=True, exist_ok=True)
    fields = {
        "file": "literature/smith_2020.html",
        "source_version": "published",
        "retrieved": "20260101",
        "doi": "10.1234/example",
        "source_sha256": "a" * 64,
        "extract_sha256": "b" * 64,
        "body_sha256": "c" * 64,
        "verifier_version": cm.VERIFIER_VERSION,
        "verified_verdict": "pass",
        "verified_date": "20260612",
    }
    for field in drop:
        fields.pop(field, None)
    fields.update(overrides)
    front = "".join(f'{k}: "{v}"\n' for k, v in fields.items())
    p = d / name
    p.write_text(f"---\n{front}---\n\n{body}", encoding="utf-8")
    if "body_sha256" not in overrides:
        vq.upsert_frontmatter(p, {"body_sha256": cm.sha256_text(cm.ledger_body(p))})
    return d


def _write_run(claims_dir, key="smith_2020", **over):
    """Write a valid run-record next to a ledger built by _write(); its hashes
    mirror the ledger's stamp so the three-way body cross-check passes. Pass
    field overrides to forge a divergence; record_sha256 is resealed each time."""
    fm = cm.read_frontmatter(claims_dir / f"{key}.md")
    record = {
        "key": key,
        "verified_date": fm.get("verified_date", ""),
        "verified_verdict": "pass",
        "verifier_version": cm.VERIFIER_VERSION,
        "source_sha256": fm.get("source_sha256", ""),
        "extract_sha256": fm.get("extract_sha256", ""),
        "body_sha256": fm.get("body_sha256", ""),
        "extract_tool": "extract_text.py",
        "extract_tool_version": "pypdf=5.1.0;beautifulsoup4=4.12;lxml=5.2",
        "file": fm.get("file", ""),
        "doi": fm.get("doi", ""),
        "pmcid": fm.get("pmcid", ""),
        "url": fm.get("url", ""),
        "retrieved": fm.get("retrieved", ""),
        "command": "verify_quotes.py --stamp",
        "transcript_sha256": "d" * 64,
        "host_user": "tester@example.com",
    }
    record.update(over)
    record["record_sha256"] = vq.run_record_digest(record)
    runs = claims_dir / cm.RUN_DIR_NAME
    runs.mkdir(exist_ok=True)
    p = runs / f"{key}.run.json"
    p.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return p


def test_provenance_mode_default_and_parse():
    assert cm.provenance_mode({}) == "warn"
    assert cm.provenance_mode({"provenance": "required  # note"}) == "required"
    assert cm.provenance_mode({"provenance": "off"}) == "off"
    assert cm.provenance_mode({"provenance": "<placeholder>"}) == "warn"


def test_valid_stamp_has_no_problems(tmp_path):
    assert cm.check_dir(_write(tmp_path)) == []


def test_missing_field_flagged(tmp_path):
    d = _write(tmp_path, verifier_version="")
    assert any("verifier_version" in p for p in cm.check_dir(d))


def test_short_hash_flagged(tmp_path):
    d = _write(tmp_path, source_sha256="abc")
    assert any("source_sha256" in p and "64-hex" in p for p in cm.check_dir(d))


def test_fail_verdict_flagged(tmp_path):
    d = _write(tmp_path, verified_verdict="fail")
    assert any("verified_verdict" in p for p in cm.check_dir(d))


def test_body_mismatch_flagged(tmp_path):
    # Edit the quoted text after the body hash was stamped — the corpus-free
    # recompute must catch it (the push-gate quote-integrity check).
    d = _write(tmp_path)
    ledger = d / "smith_2020.md"
    ledger.write_text(ledger.read_text(encoding="utf-8").replace(
        "verbatim quote", "edited quote"), encoding="utf-8")
    assert any("body_sha256 mismatch" in p for p in cm.check_dir(d))


def test_old_verifier_version_flagged(tmp_path):
    d = _write(tmp_path, verifier_version="1")
    assert any("predates current" in p for p in cm.check_dir(d))


def test_template_skipped(tmp_path):
    d = tmp_path / "verified_claims"
    d.mkdir()
    (d / "TEMPLATE.md").write_text("---\nfoo: bar\n---\n", encoding="utf-8")
    assert cm.check_dir(d) == []


def _run(claims_dir, mode):
    argv = sys.argv
    sys.argv = ["check_manifest.py", "--claims-dir", str(claims_dir), "--provenance", mode]
    try:
        return cm.main()
    finally:
        sys.argv = argv


def test_required_fails_warn_off_pass_on_bad_stamp(tmp_path):
    d = _write(tmp_path, verified_verdict="fail")
    assert _run(d, "required") == 1
    assert _run(d, "warn") == 0
    assert _run(d, "off") == 0


def test_required_passes_on_valid(tmp_path):
    # provenance: required now needs identity AND a run-record (both present here).
    d = _write(tmp_path)
    _write_run(d)
    assert _run(d, "required") == 0


# --- source-identity metadata: required only under require_identity ---

def test_identity_not_checked_by_default(tmp_path):
    # A stamp with NO identity fields is shape-valid; check_dir ignores identity
    # unless asked (the warn-mode / pre-v2 back-compat path).
    d = _write(tmp_path, drop=("file", "source_version", "retrieved", "doi"))
    assert cm.check_dir(d) == []


def test_identity_field_flagged_under_require(tmp_path):
    d = _write(tmp_path, drop=("file",))
    assert cm.check_dir(d) == []                                  # default: off
    assert any("file" in p for p in cm.check_dir(d, require_identity=True))


def test_identity_locator_rule(tmp_path):
    # doi is the only default locator; drop it → no locator → flagged. A pmcid
    # (or url) instead satisfies the at-least-one rule.
    d = _write(tmp_path, drop=("doi",))
    assert any("locator" in p for p in cm.check_dir(d, require_identity=True))
    d2 = _write(tmp_path / "p2", drop=("doi",), pmcid="PMC123456")
    assert cm.check_dir(d2, require_identity=True) == []


def test_identity_required_fails_warn_off_pass(tmp_path):
    # Missing identity blocks under provenance: required, but warn/off pass —
    # so a pre-existing v2 stamp without identity is not retroactively broken.
    d = _write(tmp_path, drop=("file", "source_version", "retrieved", "doi"))
    assert _run(d, "required") == 1
    assert _run(d, "warn") == 0
    assert _run(d, "off") == 0


# --- verification run-record attestation ---

def test_run_record_valid_passes(tmp_path):
    d = _write(tmp_path)
    _write_run(d)
    assert cm.check_dir(d, require_run_record=True) == []


def test_run_record_missing_flagged_only_when_required(tmp_path):
    d = _write(tmp_path)
    assert cm.check_dir(d) == []                                    # default: not required
    assert any("run-record" in p for p in cm.check_dir(d, require_run_record=True))


def test_run_record_tampered_seal_flagged(tmp_path):
    # Edit a field after writing without resealing → record_sha256 no longer
    # matches the content. Caught corpus-free.
    d = _write(tmp_path)
    rec_path = _write_run(d)
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    rec["host_user"] = "attacker@example.com"
    rec_path.write_text(json.dumps(rec, indent=2, sort_keys=True), encoding="utf-8")
    assert any("record_sha256 inconsistent" in p
               for p in cm.check_dir(d, require_run_record=True))


def test_run_record_body_mismatch_flagged(tmp_path):
    # A resealed record whose body_sha256 disagrees with the ledger/stamp is
    # caught by the three-way cross-check.
    d = _write(tmp_path)
    _write_run(d, body_sha256="e" * 64)
    assert any("body_sha256 !=" in p for p in cm.check_dir(d, require_run_record=True))


def test_run_record_identity_mismatch_flagged(tmp_path):
    d = _write(tmp_path)
    _write_run(d, doi="10.9999/wrong")
    assert any("run-record 'doi'" in p for p in cm.check_dir(d, require_run_record=True))


def test_run_record_required_end_to_end(tmp_path):
    d = _write(tmp_path)
    assert _run(d, "required") == 1     # identity present but no run-record
    assert _run(d, "warn") == 0         # warn never requires it
    _write_run(d)
    assert _run(d, "required") == 0     # now complete
