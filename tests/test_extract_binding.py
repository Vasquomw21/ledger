# The extract, not the source, is what the verbatim run greps. These pin the
# field that ties the two together — and the compatibility rules that let it
# ship beside ledgers which can never carry it.
from __future__ import annotations  # PEP 604 `str | None` on the 3.9 intake interpreter

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "literature"))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_manifest  # noqa: E402
from verify_quotes import (EXTRACT_SOURCE_KEY, EXTRACT_SOURCE_SUFFIX,  # noqa: E402
                           binding_problems, extract_source_sidecar,
                           read_extract_source, stamp_ledger, unbound_keys)

HASH_A = "a" * 64
HASH_B = "b" * 64

LEDGER = """---
file: "literature/x_2020.pdf"
---

## Claim — a
> "quoted words"
"""


def _extract(tmp_path: Path, source_hash: str | None) -> Path:
    extract = tmp_path / "x_2020.txt"
    extract.write_text("quoted words", encoding="utf-8")
    if source_hash is not None:
        (tmp_path / f"x_2020{EXTRACT_SOURCE_SUFFIX}").write_text(
            f"{source_hash}  x_2020.pdf\n", encoding="utf-8")
    return extract


def test_sidecar_sits_beside_the_extract(tmp_path):
    assert extract_source_sidecar(tmp_path / "x_2020.txt").name == \
        f"x_2020{EXTRACT_SOURCE_SUFFIX}"


def test_reads_the_hash_and_ignores_the_diagnostic_name(tmp_path):
    assert read_extract_source(_extract(tmp_path, HASH_A)) == HASH_A


def test_absent_sidecar_reads_as_none(tmp_path):
    assert read_extract_source(_extract(tmp_path, None)) is None


def test_malformed_sidecar_reads_as_none(tmp_path):
    _extract(tmp_path, None)
    (tmp_path / f"x_2020{EXTRACT_SOURCE_SUFFIX}").write_text("nonsense\n",
                                                             encoding="utf-8")
    assert read_extract_source(tmp_path / "x_2020.txt") is None


# The defect this exists for: an extract built from bytes the ledger does not name.
def test_extract_built_from_another_source_is_caught():
    fm = {"source_sha256": HASH_A, EXTRACT_SOURCE_KEY: HASH_B}
    assert binding_problems(fm, "x_2020"), "a mis-bound extract must not pass"


def test_matching_binding_passes():
    fm = {"source_sha256": HASH_A, EXTRACT_SOURCE_KEY: HASH_A}
    assert binding_problems(fm, "x_2020") == []


def test_absent_binding_is_not_a_failure():
    assert binding_problems({"source_sha256": HASH_A}, "x_2020") == []


def test_non_hex_binding_is_rejected():
    fm = {"source_sha256": HASH_A, EXTRACT_SOURCE_KEY: "not-a-hash"}
    assert binding_problems(fm, "x_2020")


def test_stamp_records_the_binding(tmp_path):
    ledger = tmp_path / "x_2020.md"
    ledger.write_text(LEDGER, encoding="utf-8")
    source = tmp_path / "x_2020.pdf"
    source.write_text("quoted words", encoding="utf-8")
    extract = _extract(tmp_path, None)
    (tmp_path / f"x_2020{EXTRACT_SOURCE_SUFFIX}").write_text(
        f"{check_manifest.sha256_file(source)}  x_2020.pdf\n", encoding="utf-8")
    kv = stamp_ledger(ledger, extract, source, "pass", today="20260717")
    assert kv[EXTRACT_SOURCE_KEY] == kv["source_sha256"]
    assert binding_problems(kv, "x_2020") == []


# Without the sidecar the binding must be absent, never inferred from the source.
def test_stamp_without_a_sidecar_records_no_binding(tmp_path):
    ledger = tmp_path / "x_2020.md"
    ledger.write_text(LEDGER, encoding="utf-8")
    source = tmp_path / "x_2020.pdf"
    source.write_text("quoted words", encoding="utf-8")
    kv = stamp_ledger(ledger, _extract(tmp_path, None), source, "pass",
                      today="20260717")
    assert EXTRACT_SOURCE_KEY not in kv


def test_stamp_catches_an_extract_from_the_wrong_file(tmp_path):
    ledger = tmp_path / "x_2020.md"
    ledger.write_text(LEDGER, encoding="utf-8")
    source = tmp_path / "x_2020.pdf"
    source.write_text("the real paper", encoding="utf-8")
    kv = stamp_ledger(ledger, _extract(tmp_path, HASH_B), source, "pass",
                      today="20260717")
    assert binding_problems(kv, "x_2020"), "stamping must not launder a bad bind"


def test_unbound_stamped_ledgers_are_reported(tmp_path):
    (tmp_path / "bound.md").write_text(
        f"---\nsource_sha256: {HASH_A}\n{EXTRACT_SOURCE_KEY}: {HASH_A}\n---\n",
        encoding="utf-8")
    (tmp_path / "unbound.md").write_text(f"---\nsource_sha256: {HASH_A}\n---\n",
                                         encoding="utf-8")
    (tmp_path / "unstamped.md").write_text("---\nfile: x\n---\n", encoding="utf-8")
    assert unbound_keys(tmp_path) == ["unbound"]


# Old ledgers cannot acquire a sidecar without a corpus they no longer have, so
# a required field or a version bump would fail every one of them permanently.
def test_binding_is_not_a_required_stamp_field():
    assert EXTRACT_SOURCE_KEY not in check_manifest.STAMP_FIELDS


def test_ci_rejects_a_mis_bound_stamp():
    fm = {"source_sha256": HASH_A, "extract_sha256": HASH_A,
          "body_sha256": HASH_A, "verifier_version": "2",
          "verified_verdict": "pass", "verified_date": "20260717",
          EXTRACT_SOURCE_KEY: HASH_B}
    assert any("not bound" in p for p in check_manifest.stamp_problems(fm, "x_2020"))


def test_ci_accepts_a_stamp_with_no_binding():
    fm = {"source_sha256": HASH_A, "extract_sha256": HASH_A,
          "body_sha256": HASH_A, "verifier_version": "2",
          "verified_verdict": "pass", "verified_date": "20260717"}
    assert check_manifest.stamp_problems(fm, "x_2020") == []
