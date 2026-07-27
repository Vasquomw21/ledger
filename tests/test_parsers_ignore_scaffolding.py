# A ledger documents its own markers as well as carrying them: a header sentence
# beginning **Locus:**, a fenced example showing **ID:**, a field named inside a
# quoted span. A parser that scans the whole file counts the documentation as data
# and fails silently — an inflated claim-id set lets a bogus #slug citation resolve,
# and an inflated locus set inflates every convergence score computed from it.
#
# Every marker parser is fed one decoy ledger here. A new parser that scans the file
# instead of resolving through ledger_md fails this file.
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_structure  # noqa: E402
import check_units  # noqa: E402
import claim_graph  # noqa: E402
import repro  # noqa: E402
from check_citations import claim_header_issues, ledger_claim_id_sets  # noqa: E402
from ledger_md import claim_blocks  # noqa: E402

LEGIT_SLUG = "p4"
LEGIT_QID = "q-real"

# Every decoy below is a shape that occurs in this repo's own ledgers.
DECOY_LEDGER = f"""# voice

A ledger's header explains its conventions, and those sentences begin with the very
markers they describe.

**ID:** decoy-in-header names the claim this file addresses.
**Locus:** decoy-in-header lines bind each claim to a unit.
**Addresses:** decoy-in-header points at a sub-question.

```
**ID:** decoy-in-fence
**Locus:** decoy-in-fence
**Addresses:** decoy-in-fence
## Claim 9: a fenced example that must not open a block
```

## Claim 1: the only real claim

> "a quoted span that mentions **ID:** decoy-in-quote and
> **Locus:** decoy-in-quote inline"

**ID:** {LEGIT_SLUG}
**Locus:** {LEGIT_SLUG}
**Addresses:** {LEGIT_QID}

```
**Locus:** decoy-in-block-fence
```
"""


def _ledger(tmp_path: Path) -> Path:
    claims = tmp_path / "verified_claims"
    claims.mkdir(parents=True, exist_ok=True)
    path = claims / "voice.md"
    path.write_text(DECOY_LEDGER, encoding="utf-8")
    return path


def test_claim_blocks_sees_exactly_one_claim(tmp_path):
    """The fenced `## Claim 9` must not open a block: it would shift every ordinal
    that a positional #cN citation resolves through."""
    blocks = claim_blocks(_ledger(tmp_path))
    assert len(blocks) == 1
    assert blocks[0].ordinal == 1


def test_claim_ids_ignore_header_and_fenced_decoys(tmp_path):
    """An inflated slug set is a FALSE PASS on the citation gate — a #slug ref that
    names no claim would resolve against a slug lifted from documentation."""
    ordinals, slugs = ledger_claim_id_sets(_ledger(tmp_path))
    assert slugs == {LEGIT_SLUG}
    assert ordinals == {"c1"}


def test_loci_ignore_decoys(tmp_path):
    loci = [locus for locus, _quote in check_units.claim_loci(_ledger(tmp_path))]
    assert loci == [LEGIT_SLUG]


def test_repro_loci_ignore_decoys(tmp_path):
    """An inflated locus set inflates locus_agreement: header prose is identical in
    both runs, so a phantom lands in the intersection of every comparison."""
    path = _ledger(tmp_path)
    assert repro.run_loci(path.parent) == {f"voice:{LEGIT_SLUG}"}


def test_qid_refs_ignore_decoys(tmp_path):
    refs = check_structure.parse_qid_refs(_ledger(tmp_path).parent)
    assert {r.qid for r in refs} == {LEGIT_QID}


def test_claim_aliases_ignore_decoys(tmp_path):
    assert claim_graph.claim_aliases(_ledger(tmp_path), LEGIT_SLUG) == {"c1", LEGIT_SLUG}


def test_claim_body_excludes_the_preamble(tmp_path):
    body = claim_graph.claim_body(_ledger(tmp_path), LEGIT_SLUG)
    assert body is not None
    assert "decoy-in-header" not in body


def test_header_numbering_ignores_a_fenced_claim(tmp_path):
    """`## Claim 9` in an example must not read as a numbering error."""
    assert claim_header_issues(_ledger(tmp_path)) is None
