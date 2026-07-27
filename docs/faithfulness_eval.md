# Faithfulness evaluation — putting a number on Layer-1 out-of-context use

**What this is.** A *measurement*, not a gate. Layer 1 (Fidelity) has two halves. "Is the
quote verbatim?" is **guaranteed** by `verify_quotes` (sha-bound, re-proved at every commit).
"Is the verbatim quote used *in context*, or stretched to support an inference it does not
warrant?" is the harder half — until now **assisted but never measured** (`faithfulness_probe.py`
lists every supports/rebuts edge and a human or agent files dispute records, but no number came
out the other end).

This harness puts a number on that second half, the way [`repro.py`](../tools/repro.py) put one on
extraction determinism: a small, **class-balanced, hand-labelled benchmark** of real
(verbatim quote → asserted inference) pairs, plus a scorer that runs a *blind* detector over it and
reports its confusion matrix and rates.

It is **not a gate**: no posture, no pre-commit or CI step. The kit still ships no model — the
*detector* is the agent/human layer; the harness measures *that detector's* performance, exactly
as `repro` measures convergence between two extraction runs.

## The benchmark

[`spec/examples/faithfulness_bench.jsonl`](../spec/examples/faithfulness_bench.jsonl) — 18 cases,
**9 out-of-context** (the misuse we want to catch — the positive class) and **9 apt** (faithful
controls). Each line carries the source key, the claim slug, the **verbatim quote**, the asserted
**inference**, the **gold label**, and a **rationale**. Every quote is drawn from the three
vendored cases' real ledgers and re-proves verbatim against them:

```
python3 tools/faithfulness_eval.py --claims-dir cases/covid_origins_ledger/literature/verified_claims
python3 tools/faithfulness_eval.py --claims-dir cases/lhc_safety_ledger/literature/verified_claims
python3 tools/faithfulness_eval.py --claims-dir cases/eggs_cholesterol_ledger/literature/verified_claims
# → re-proved 8 / 5 / 5 embedded quotes verbatim; 0 mismatches (18 total)
```

The out-of-context cases instantiate the recurring inflation patterns, each grounded in a genuine
quote:

| id | misuse pattern |
|---|---|
| `andersen-possibility-as-certainty` | a *possibility* (`can arise`) read as ruling out the alternative |
| `segreto-nonexclusion-as-likelihood` | a *non-exclusion* (`cannot be excluded`) read as `most likely` |
| `segreto-possibility-as-fact` | a hedge (`might derive`) restated as fact |
| `worobey-epicenter-as-mechanism` | a spatial *locus* read as proof of *origin mechanism* (ascertainment bias) |
| `temmam-absence-as-design` | *absence in a sample* read as proof of design (argument from ignorance) |
| `giddings-conditional-as-categorical` | a *model-conditional* bound read as categorical |
| `rong-subgroup-as-general` | a hedged *subgroup* signal generalised to the whole population |
| `rong-overlap-as-independent` | *overlapping* cohorts counted as *independent* confirmation (double-count) |
| `lsag-finding-as-proof` | a review *finding* read as a *mathematical proof* of a categorical |

The 9 apt controls are scope-preserving restatements of the same sources' claims (e.g.
`giddings-no-basis-apt`, `dehghan-rebuts-zhong-apt`).

## How to run it

```
# 1. emit the blind detector input (no gold labels, no rationale)
python3 tools/faithfulness_eval.py --emit-blind > /tmp/blind.jsonl

# 2. a detector (agent, human, or the transparent baseline) reads blind.jsonl and writes verdicts:
#    {"id": "<id>", "verdict": "apt" | "out-of-context"}   (synonyms accepted)
python3 tools/faithfulness_baseline.py /tmp/blind.jsonl > /tmp/baseline_verdicts.jsonl

# 3. score the verdicts against gold
python3 tools/faithfulness_eval.py --score /tmp/baseline_verdicts.jsonl [--json]
```

## Transparent baseline result

`tools/faithfulness_baseline.py` is a deliberately small, inspectable detector. It is not a model
and not a gate. Its job is to prove that the benchmark can be run end-to-end and to give judges a
reproducible floor before they point a human or stronger agent at the blind file.

Current baseline run:

```text
python3 tools/faithfulness_eval.py --emit-blind > /private/tmp/ledger_blind.jsonl
python3 tools/faithfulness_baseline.py /private/tmp/ledger_blind.jsonl > /private/tmp/ledger_baseline_verdicts.jsonl
python3 tools/faithfulness_eval.py --score /private/tmp/ledger_baseline_verdicts.jsonl

[INFO] benchmark 18 cases (9 out-of-context, 9 apt); scored 18
[INFO] confusion: tp=9 fp=0 tn=9 fn=0 (positive class = out-of-context)
[INFO] recall 1.0 · specificity 1.0 · precision 1.0 · accuracy 1.0
```

The repo ships the detector and scorer, not a frozen verdict file. Re-run the commands above after
any benchmark change; compare a human or agent detector against this transparent baseline rather
than treating the baseline as the final judge.

## What the number does and does not say

The discipline the synthesis gate enforces on case prose applies here by hand:

- **It measures a detector on *this* benchmark — not a kit guarantee, not a transferable property.**
  The number is benchmark-specific and detector-specific. A different benchmark or a weaker detector
  would give a different number.
- **A perfect baseline score is itself a caveat, not a victory.** These 18 cases are *clear-cut by design*:
  textbook inflation patterns versus scope-faithful controls. The reading is narrow —
  *capable detectors reliably catch unambiguous out-of-context misuse, and reliably pass faithful
  controls, with no observed false-alarm tendency.* It does **not** show faithfulness is "solved".
  The interesting frontier is **borderline** cases (a defensible-but-arguable restatement, a partial
  hedge), where the rate would be expected to drop and inter-detector agreement to fall; building
  that harder tier is open work.
- **The gold labels are author judgement** — the genuinely hard part. Each is quote-pinned with a
  rationale so a sceptic can contest a *specific* label, not the method. The benchmark is
  class-balanced so recall and specificity are both reported; an always-"out-of-context" detector
  would score 1.00 recall but 0.00 specificity, and the balance makes that visible.
- **Self-grading risk.** The same author wrote the benchmark and ran the detectors.
  Mitigations: the detector view is blind, the runs are independent, agreement is reported, and the
  per-case rationales are open to challenge. The claim is that Layer-1 out-of-context is *measured* on
  a starter benchmark, not shown safe.

## Where this sits in the integrity framework

In [`integrity_framework.md`](integrity_framework.md) and [`DEMO.md`](../DEMO.md) §4, Layer-1
out-of-context use moves from **Assisted** (a worklist a human works through) to **Measured
(Assisted)** — the same status `repro` gives extraction determinism: a number with its residual, rather than an assertion. The verbatim half stays **Guaranteed**; aptness
of the *inference* (Layer 4) stays **Judged**. This harness does not touch either — it measures how
well a detector polices the seam between them.
