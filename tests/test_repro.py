# Tests for tools/repro.py — the extraction-convergence harness. Build two synthetic
# ledger dirs with a known overlap and assert the metrics. Corpus-free, runs in CI.
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))
import repro


def write_ledger(run_dir: Path, key: str, claims: list[tuple[str, str]]) -> None:
    """claims = [(slug, qid), …] → a minimal valid ledger file <key>.md."""
    run_dir.mkdir(parents=True, exist_ok=True)
    blocks = []
    for n, (slug, qid) in enumerate(claims, start=1):
        blocks.append(f'## Claim {n}: c{n}\n\n> "quote {n}"\n\n'
                      f'**ID:** {slug}\n**Addresses:** {qid}\n')
    (run_dir / f"{key}.md").write_text("\n".join(blocks), encoding="utf-8")


def test_partial_overlap(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    write_ledger(a, "wilf", [("t1-1", "prior"), ("t1-2", "market")])
    write_ledger(a, "miller", [("t2-1", "lab")])
    write_ledger(b, "wilf", [("t1-1", "prior"), ("t1-3", "lab")])
    write_ledger(b, "miller", [("t2-1", "lab")])
    m = repro.compare(a, b)
    # addresses: A={wilf:t1-1,wilf:t1-2,miller:t2-1} B={wilf:t1-1,wilf:t1-3,miller:t2-1}
    assert m["claim_agreement"] == 0.5          # shared 2 / union 4
    assert m["coverage_match"] == 0.667         # {prior,lab} / {prior,market,lab}
    assert m["attribution_match"] == 1.0        # shared slugs t1-1,t2-1 same keys
    assert m["shared_claims"] == 2
    assert m["residual"] == ["wilf:t1-2", "wilf:t1-3"]


def test_identical_runs_converge(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for d in (a, b):
        write_ledger(d, "wilf", [("t1-1", "prior")])
        write_ledger(d, "miller", [("t2-1", "lab")])
    m = repro.compare(a, b)
    assert m["claim_agreement"] == 1.0
    assert m["coverage_match"] == 1.0
    assert m["attribution_match"] == 1.0
    assert m["residual"] == []


def write_quoted(run_dir: Path, key: str, claims: list[tuple[str, str, str]]) -> None:
    """claims = [(slug, qid, quote), …] → a ledger with controlled quote spans."""
    run_dir.mkdir(parents=True, exist_ok=True)
    blocks = []
    for n, (slug, qid, quote) in enumerate(claims, start=1):
        blocks.append(f'## Claim {n}: c{n}\n\n> "{quote}"\n\n'
                      f'**ID:** {slug}\n**Addresses:** {qid}\n')
    (run_dir / f"{key}.md").write_text("\n".join(blocks), encoding="utf-8")


def test_selection_agreement_is_naming_independent(tmp_path):
    """The same span lifted under DIFFERENT slugs counts as selection agreement but not
    claim agreement — the eggs-case finding (descriptive vs locus-template slugs)."""
    a, b = tmp_path / "a", tmp_path / "b"
    # Same first span, different slug; second span differs between runs.
    write_quoted(a, "wilf", [("descriptive-verdict", "q1", "the verdict is zoonosis"),
                             ("extra-a", "q1", "only in run A")])
    write_quoted(b, "wilf", [("finding-1", "q1", "the verdict is zoonosis"),
                             ("extra-b", "q1", "only in run B")])
    m = repro.compare(a, b)
    # spans: A={wilf:theverdictiszoonosis, wilf:onlyinruna}
    #        B={wilf:theverdictiszoonosis, wilf:onlyinrunb}  -> shared 1 / union 3
    assert m["selection_agreement"] == 0.333
    assert m["shared_spans"] == 1
    # slugs never collide (descriptive vs locus-template), so claim_agreement is 0.
    assert m["claim_agreement"] == 0.0
    # but both touch the same sub-question.
    assert m["coverage_match"] == 1.0


def test_misattribution_is_caught(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    write_ledger(a, "wilf", [("t1-1", "prior")])
    write_ledger(a, "miller", [("t2-1", "lab")])
    # run B routes the same locus t2-1 to the WRONG voice (wilf, not miller)
    write_ledger(b, "wilf", [("t1-1", "prior"), ("t2-1", "lab")])
    m = repro.compare(a, b)
    # shared slugs by locus: t1-1 (same key), t2-1 (wilf vs miller) → 1/2
    assert m["attribution_match"] == 0.5
