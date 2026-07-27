import faithfulness_baseline as fb
import faithfulness_eval as fe


def test_baseline_scores_benchmark_above_trivial():
    bench = fe.load_bench(fe.BENCH)
    verdicts = {}
    for case in fe.blind_view(bench):
        verdict, _rationale = fb.verdict(case)
        verdicts[case["id"]] = verdict
    score = fe.score(bench, verdicts)
    assert score["n_scored"] == 18
    assert score["recall"] >= 0.8
    assert score["specificity"] >= 0.8


def test_baseline_main_emits_jsonl(tmp_path, capsys):
    blind = tmp_path / "blind.jsonl"
    blind.write_text('{"id":"x","quote":"might derive","inference":"It was produced."}\n',
                     encoding="utf-8")
    assert fb.main([str(blind)]) == 0
    out = capsys.readouterr().out
    assert '"id": "x"' in out
    assert '"verdict": "out-of-context"' in out
