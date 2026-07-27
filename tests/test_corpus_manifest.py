"""Corpus inventory + licence triage across the five cases."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import corpus_manifest as cm  # noqa: E402


def _rows():
    return cm.build_rows(REPO)


def test_covers_every_case_and_excludes_templates():
    rows = _rows()
    cases = {r["case"] for r in rows}
    assert cases == set(cm.CASES)
    # the scaffolding TEMPLATE ledger in each case is not a source
    assert not any(r["source_key"].upper() == "TEMPLATE" for r in rows)
    assert not any(r["locator"].startswith("<") for r in rows)


def test_nothing_includable_without_bytes_on_disk():
    # this kit ships no source bytes, so no row may be marked includable
    rows = _rows()
    assert all(r["corpus_present"] == "no" for r in rows)
    assert all(r["included_in_submission"] == "no" for r in rows)


def test_every_status_is_a_contract_value():
    allowed = cm.CLEARED | {"restricted", "unknown"}
    assert {r["redistribution_status"] for r in _rows()} <= allowed


def test_status_follows_authoritative_registrant():
    by_key = {r["source_key"]: r for r in _rows()}
    # uniformly-CC publishers are permissive
    assert by_key["darooghegi_2022"]["redistribution_status"] == "permissive-licence"  # Frontiers
    assert by_key["gidney_2021"]["redistribution_status"] == "permissive-licence"      # Quantum
    # US-Government work is public domain
    assert by_key["nist_2024"]["redistribution_status"] == "public-domain"             # NIST
    # a closed publisher defaults to restricted, never silently cleared
    assert by_key["andersen_2020"]["redistribution_status"] == "restricted"            # Springer Nature


def test_deterministic():
    assert cm.render_tsv(_rows()) == cm.render_tsv(_rows())


def test_tsv_header_matches_columns():
    header = cm.render_tsv(_rows()).splitlines()[0].split("\t")
    assert header == list(cm.COLUMNS)
