# Criticising a source's certainty language means restating it. The gate must read the
# quoted words as the source's and the rest of the line as the author's.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from check_synthesis import flagged_lines, unquoted  # noqa: E402


def _flag(tmp_path: Path, body: str):
    p = tmp_path / "finding.md"
    p.write_text(body, encoding="utf-8")
    return flagged_lines(p)


def test_quoted_span_is_blanked_and_length_preserved():
    line = 'marks "irrefutably show" as overreach'
    masked, still_open = unquoted(line)
    assert "irrefutably" not in masked
    assert len(masked) == len(line)
    assert not still_open


def test_curly_quotes_are_blanked():
    assert "dispositive" not in unquoted('the paper says “not dispositive” here')[0]


def test_an_open_quote_is_reported_so_the_caller_can_carry_it():
    assert unquoted('he wrote "the result is')[1] is True


# The real shape: a quoted sentence wrapped across two lines. The closing line carries the
# certainty word but no opening quote of its own.
def test_a_quote_spanning_lines_is_blanked_on_the_closing_line():
    _, open_after = unquoted('the baseline says *"the most supported hypothesis,')
    masked, _ = unquoted('consistent across data types, but not dispositive"* — and stops', open_after)
    assert "dispositive" not in masked


def test_a_blank_line_resets_the_quote_state(tmp_path):
    body = 'he wrote "an unclosed quote\n\nThis proves our reading.\n'
    assert [c for _, c, _ in _flag(tmp_path, body)] == ["certainty"]


# The defect: the author quoting a source's certainty word to criticise it was flagged.
def test_criticising_a_quoted_certainty_word_is_not_flagged(tmp_path):
    assert _flag(tmp_path, 'The record marks "irrefutably show" as more than the argument carries.\n') == []


def test_quoting_a_hedged_baseline_line_is_not_flagged(tmp_path):
    assert _flag(tmp_path, 'The baseline says *"supported, but not dispositive"* and stops there.\n') == []


# The gate must still bite where the author makes the claim in their own voice.
def test_authors_own_certainty_claim_is_still_flagged(tmp_path):
    hits = _flag(tmp_path, "This proves the lab-leak hypothesis is dead.\n")
    assert [c for _, c, _ in hits] == ["certainty"]


def test_authors_claim_outside_a_quote_on_a_quoting_line_is_flagged(tmp_path):
    hits = _flag(tmp_path, 'He wrote "a modest result", which proves our reading.\n')
    assert [c for _, c, _ in hits] == ["certainty"], "text outside the quote is still the author's"


def test_anchored_claim_still_passes(tmp_path):
    assert _flag(tmp_path, "This proves it (`verify_quotes.py`).\n") == []
