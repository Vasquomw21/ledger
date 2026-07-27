# Tests for the faithfulness-eval harness (corpus-free). A tiny in-memory benchmark +
# verdicts exercises the confusion matrix and rates; the class-balance guard fires on a
# one-sided benchmark; --emit-blind hides the gold label and rationale; verdict synonyms
# normalise; an unscored case is reported, never silently counted correct. The shipped
# spec/examples/faithfulness_bench.jsonl is also loaded to confirm it parses + balances.
import json

import faithfulness_eval as fe


def _bench():
    # 2 out-of-context, 2 apt — the smallest balanced benchmark.
    return [
        {"id": "a", "source_key": "s1", "slug": "x", "quote": "q a", "inference": "i a",
         "gold": "out-of-context", "rationale": "r"},
        {"id": "b", "source_key": "s1", "slug": "y", "quote": "q b", "inference": "i b",
         "gold": "out-of-context", "rationale": "r"},
        {"id": "c", "source_key": "s2", "slug": "z", "quote": "q c", "inference": "i c",
         "gold": "apt", "rationale": "r"},
        {"id": "d", "source_key": "s2", "slug": "w", "quote": "q d", "inference": "i d",
         "gold": "apt", "rationale": "r"},
    ]


def test_class_balance_counts():
    assert fe.class_balance(_bench()) == {"out-of-context": 2, "apt": 2}


def test_perfect_detector_scores_unity():
    verdicts = {"a": "out-of-context", "b": "out-of-context", "c": "apt", "d": "apt"}
    r = fe.score(_bench(), verdicts)
    assert r["confusion"] == {"tp": 2, "fp": 0, "tn": 2, "fn": 0}
    assert r["recall"] == 1.0 and r["specificity"] == 1.0
    assert r["precision"] == 1.0 and r["accuracy"] == 1.0
    assert r["unscored"] == []


def test_missed_misuse_lowers_recall_not_specificity():
    # Detector passes one true misuse (a) as apt: one false negative.
    verdicts = {"a": "apt", "b": "out-of-context", "c": "apt", "d": "apt"}
    r = fe.score(_bench(), verdicts)
    assert r["confusion"] == {"tp": 1, "fp": 0, "tn": 2, "fn": 1}
    assert r["recall"] == 0.5
    assert r["specificity"] == 1.0


def test_false_alarm_lowers_specificity_not_recall():
    # Detector flags an apt case (c) as out-of-context: one false positive.
    verdicts = {"a": "out-of-context", "b": "out-of-context", "c": "out-of-context", "d": "apt"}
    r = fe.score(_bench(), verdicts)
    assert r["confusion"] == {"tp": 2, "fp": 1, "tn": 1, "fn": 0}
    assert r["recall"] == 1.0
    assert r["specificity"] == 0.5


def test_unscored_case_is_reported_not_counted():
    verdicts = {"a": "out-of-context", "b": "out-of-context", "c": "apt"}  # d missing
    r = fe.score(_bench(), verdicts)
    assert r["unscored"] == ["d"]
    assert r["n_scored"] == 3


def test_blind_view_hides_gold_and_rationale():
    for case in fe.blind_view(_bench()):
        assert "gold" not in case and "rationale" not in case
        assert set(case) == {"id", "source", "slug", "quote", "inference"}


def test_verdict_normalisation_synonyms():
    assert fe.normalise_verdict("OOC") == "out-of-context"
    assert fe.normalise_verdict("misuse") == "out-of-context"
    assert fe.normalise_verdict("faithful") == "apt"
    assert fe.normalise_verdict("in context") == "apt"
    assert fe.normalise_verdict("maybe?") is None


def test_load_bench_rejects_bad_gold(tmp_path):
    p = tmp_path / "b.jsonl"
    p.write_text(json.dumps({"id": "x", "quote": "q", "inference": "i", "gold": "huh"}) + "\n",
                 encoding="utf-8")
    try:
        fe.load_bench(p)
        assert False, "expected ValueError on bad gold label"
    except ValueError:
        pass


def test_shipped_benchmark_parses_and_balances():
    bench = fe.load_bench(fe.BENCH)
    balance = fe.class_balance(bench)
    assert balance["out-of-context"] > 0 and balance["apt"] > 0
    # IDs are unique (a duplicate would let one verdict score two cases).
    ids = [c["id"] for c in bench]
    assert len(ids) == len(set(ids))
