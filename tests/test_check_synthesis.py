# Tests for the synthesis-claim gate (corpus-free). An unanchored significance/superiority
# claim is flagged; the same claim anchored to a key:slug / `tool` / [[link]] / hedge passes;
# a superlative inside a blockquote (the SOURCE's rhetoric) is skipped; headings and code
# fences are skipped; the empty/pristine case passes. Off posture is not exercised here.
import check_synthesis as cs


def _content(tmp_path, body, name="baseline_comparison.md"):
    content = tmp_path / "content"
    content.mkdir(parents=True, exist_ok=True)
    (content / name).write_text(body, encoding="utf-8")
    return content


def test_unanchored_significance_claim_is_flagged(tmp_path):
    content = _content(tmp_path, "This is the one genuinely non-obvious result here.\n")
    probs = cs.synthesis_problems(content)
    assert len(probs) == 1
    assert "novelty" in probs[0]


def test_keyslug_anchor_passes(tmp_path):
    content = _content(tmp_path, "A non-obvious result, see giddings_2008:astro-bound here.\n")
    assert cs.synthesis_problems(content) == []


def test_code_anchor_passes(tmp_path):
    content = _content(tmp_path, "This beats the baseline — re-run `analyze_graph.py` to check.\n")
    assert cs.synthesis_problems(content) == []


def test_hedge_passes(tmp_path):
    content = _content(tmp_path, "This is novel, though we do not claim it is unprecedented.\n")
    assert cs.synthesis_problems(content) == []


def test_superlative_inside_blockquote_is_skipped(tmp_path):
    # A superlative in a verbatim source quote is the SOURCE's rhetoric, not the author's claim.
    content = _content(tmp_path, '> "there is no risk of any significance whatsoever"\n')
    assert cs.synthesis_problems(content) == []


def test_heading_and_code_fence_skipped(tmp_path):
    body = "# A non-obvious heading\n\n```\nthis proves nothing in a code block\n```\n"
    assert cs.synthesis_problems(_content(tmp_path, body)) == []


def test_empty_content_passes(tmp_path):
    (tmp_path / "content").mkdir(parents=True, exist_ok=True)
    assert cs.synthesis_problems(tmp_path / "content") == []


def test_saturated_completeness_claim_flagged(tmp_path):
    content = _content(tmp_path, "We saturated every edge with assessments.\n")
    probs = cs.synthesis_problems(content)
    assert any("completeness" in p for p in probs)


def test_synthesis_mode_default_off():
    assert cs.synthesis_mode({}) == "off"
    assert cs.synthesis_mode({"synthesis_claims": "required"}) == "required"
    assert cs.synthesis_mode({"synthesis_claims": "warn # note"}) == "warn"


def test_has_anchor():
    assert cs.has_anchor("see foo_2020:bar-baz")
    assert cs.has_anchor("run `tool.py`")
    assert cs.has_anchor("see [[note]]")
    assert cs.has_anchor("a [link](http://x)")
    assert cs.has_anchor("we concede the baseline is broader")
    assert not cs.has_anchor("this is plainly the best result")
