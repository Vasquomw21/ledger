# End-to-end smoke test on REAL extractor output (the other suites use synthetic
# haystacks). tests/smoke/sandve_2013.txt is a real excerpt extract_text.py
# produced from Sandve et al. 2013 (PLOS Comp Biol, CC-BY, PMC3812051);
# sandve_2013.md is a genuine verbatim ledger. Proves a real quote PASSes and a
# paraphrase of the same passage FAILs. Corpus-free fixture, so it runs in CI.
from pathlib import Path

import verify_quotes as vq

SMOKE = Path(__file__).resolve().parent / "smoke"
KEY = "sandve_2013"


def test_real_verbatim_quote_passes():
    # The committed genuine ledger verifies clean against the real extract.
    tally = vq.check_ledger(KEY, SMOKE / f"{KEY}.md", extracted_dir=SMOKE)
    assert tally["pass"] >= 1
    assert tally["fail"] == 0


def test_paraphrase_of_same_passage_fails(tmp_path):
    # Same real extract, but a ledger whose quote paraphrases the source rather
    # than lifting it verbatim — must FAIL every stage (the anti-hallucination
    # property, demonstrated on real text).
    paraphrase = (
        "# Verified Claims — Sandve et al. (2013)\n\n"
        "## Claim 1: paraphrase\n\n"
        "> \"The authors advise using automated programs rather than manually "
        "editing data whenever feasible.\"\n\n"
        "**Location:** Rule 2\n"
    )
    ledger = tmp_path / f"{KEY}.md"
    ledger.write_text(paraphrase, encoding="utf-8")
    tally = vq.check_ledger(KEY, ledger, extracted_dir=SMOKE)
    assert tally["fail"] >= 1
    assert tally["pass"] == 0


def test_extract_fixture_is_real_and_present():
    # Guard: the committed fixture exists and still holds the verbatim quote, so
    # an edit that breaks the fixture is caught here rather than silently.
    txt = (SMOKE / f"{KEY}.txt").read_text(encoding="utf-8")
    assert "rely on the execution of programs instead of manual procedures" in txt
