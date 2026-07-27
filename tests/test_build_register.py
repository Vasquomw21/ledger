# Tests for build_register's ledger-as-identity-authority check. build_register
# imports bs4/pypdf at module load; skipped unless the intake extra is installed
# (pip `intake`, or conda).
import hashlib

import pytest

pytest.importorskip("bs4")
pytest.importorskip("pypdf")

import build_register as br


def _project(tmp_path, monkeypatch, frontmatter, content="real source bytes " * 40):
    claims = tmp_path / "verified_claims"
    claims.mkdir()
    source = tmp_path / "smith_2020.html"
    source.write_text(content, encoding="utf-8")
    (claims / "smith_2020.md").write_text(
        f"---\n{frontmatter}\n---\n\n> \"a quote\"\n", encoding="utf-8")
    monkeypatch.setattr(br, "CLAIMS_DIR", claims)
    return source


def _record(source, meta_doi=""):
    return {"key": "smith_2020", "status": "verified", "path": source,
            "meta_doi": meta_doi, "notes": []}


def test_hash_mismatch_flagged(tmp_path, monkeypatch):
    source = _project(tmp_path, monkeypatch, f'source_sha256: "{"0" * 64}"')
    rec = _record(source)
    assert br.flag_ledger_divergence([rec]) == 1
    assert rec["status"] == "mismatch"
    assert any("source_bytes_differ" in n for n in rec["notes"])


def test_hash_match_not_flagged(tmp_path, monkeypatch):
    content = "real source bytes " * 40
    good = hashlib.sha256(content.encode()).hexdigest()
    source = _project(tmp_path, monkeypatch, f'source_sha256: "{good}"', content=content)
    rec = _record(source)
    assert br.flag_ledger_divergence([rec]) == 0
    assert rec["status"] == "verified"


def test_doi_mismatch_flagged(tmp_path, monkeypatch):
    source = _project(tmp_path, monkeypatch, 'doi: "10.1/correct"')
    rec = _record(source, meta_doi="10.1/wrong")
    assert br.flag_ledger_divergence([rec]) == 1
    assert any("doi_differs_from_ledger" in n for n in rec["notes"])
