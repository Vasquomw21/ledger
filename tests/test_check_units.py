# Tests for tools/check_units.py — the quote-within-unit gate. Corpus-free: hand-built
# manifest + ledger pairs assert the core unit_problems() logic (hard vs soft buckets).
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))
sys.path.insert(0, str(REPO_ROOT / "literature"))
import check_units as cu
from enumerate_units import manifest_digest
from verify_quotes import norm, sha256_text


def write_manifest(units_dir: Path, key: str, units, fully=True, source_sha="0" * 64):
    units_dir.mkdir(parents=True, exist_ok=True)
    m = {
        "key": key, "source_type": "essay", "source_sha256": source_sha,
        "enumerator_version": "1", "enumerated_date": "x", "addressing": "html-block",
        "fully_enumerable": fully,
        "units": [{"locus": loc, "text": t, "unit_sha256": sha256_text(norm(t))}
                  for loc, t in units],
    }
    m["manifest_sha256"] = manifest_digest(m)
    (units_dir / f"{key}.units.json").write_text(
        json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_ledger(claims_dir: Path, key: str, claims, source_sha=None):
    """claims = [(locus, quote_or_None)] -> a ledger with **Locus:** + blockquote."""
    claims_dir.mkdir(parents=True, exist_ok=True)
    fm = f"---\nsource_sha256: {source_sha}\n---\n\n" if source_sha else ""
    blocks = []
    for n, (locus, quote) in enumerate(claims, start=1):
        q = f'> "{quote}"\n\n' if quote is not None else ""
        blocks.append(f"## Claim {n}: c{n}\n\n{q}**ID:** {locus}\n**Locus:** {locus}\n")
    (claims_dir / f"{key}.md").write_text(fm + "\n".join(blocks), encoding="utf-8")


def test_quote_within_unit_passes(tmp_path):
    units, claims = tmp_path / "units", tmp_path / "claims"
    write_manifest(units, "foo", [("p1", "I get 96% zoonosis after watching the debate.")])
    write_ledger(claims, "foo", [("p1", "I get 96% zoonosis")])
    hard, soft = cu.unit_problems(claims, units)
    assert hard == [] and soft == []


def test_quote_not_in_unit_is_hard(tmp_path):
    units, claims = tmp_path / "units", tmp_path / "claims"
    write_manifest(units, "foo", [("p1", "I get 96% zoonosis after watching the debate.")])
    write_ledger(claims, "foo", [("p1", "the market is the load-bearing update")])
    hard, soft = cu.unit_problems(claims, units)
    assert any("not a span within that unit" in p for p in hard)


def test_unknown_locus_is_hard(tmp_path):
    units, claims = tmp_path / "units", tmp_path / "claims"
    write_manifest(units, "foo", [("p1", "I get 96% zoonosis after watching the debate.")])
    write_ledger(claims, "foo", [("p9", "I get 96% zoonosis")])
    hard, _ = cu.unit_problems(claims, units)
    assert any("not in manifest" in p for p in hard)


def test_coarse_pdf_degrades_to_soft(tmp_path):
    units, claims = tmp_path / "units", tmp_path / "claims"
    write_manifest(units, "foo", [("page1-p1", "I get 96% zoonosis after the debate.")],
                   fully=False)
    write_ledger(claims, "foo", [("page1-p1", "an entirely different quote here")])
    hard, soft = cu.unit_problems(claims, units)
    assert hard == [] and any("not a span" in p for p in soft)


def test_source_sha_mismatch_is_hard(tmp_path):
    units, claims = tmp_path / "units", tmp_path / "claims"
    write_manifest(units, "foo", [("p1", "I get 96% zoonosis after the debate.")],
                   source_sha="a" * 64)
    write_ledger(claims, "foo", [("p1", "I get 96% zoonosis")], source_sha="b" * 64)
    hard, _ = cu.unit_problems(claims, units)
    assert any("source_sha256 != ledger stamp" in p for p in hard)


def test_no_locus_no_check(tmp_path):
    """A ledger with no **Locus:** is simply not on the grid — nothing to check."""
    units, claims = tmp_path / "units", tmp_path / "claims"
    claims.mkdir(parents=True)
    (claims / "foo.md").write_text('## Claim 1: c1\n\n> "x"\n\n**ID:** s1\n', encoding="utf-8")
    hard, soft = cu.unit_problems(claims, units)
    assert hard == [] and soft == []
