# cases/ — the worked demonstrations (vendored for one-clone review)

Each subdirectory is a **complete, standalone Ledger project** — its own kernel, config, quote
ledgers, claim graph, and assessment records — built as a separate repo and **vendored in** (tracked
files only, no `.git`, no raw corpus) so a judge cloning the kit gets the whole demonstration in one
offline clone. The kernel repeats across them: the same machinery travels
unchanged to different kinds of question, including one subject — **quantum computing for genomics**,
entirely outside the three provided case topics (COVID origins, LHC black holes, dietary cholesterol).

| Directory | Question | Kind | Inspect |
|---|---|---|---|
| `covid_origins_ledger` | FCS engineering? **and** does early evidence locate origin at the market? | contested, multi-source (5 sources, 2 sub-questions) | the **double-count** (Worobey + Pekar correlated); the sealed **faithfulness dispute** |
| `covid_debate_ledger` | Lab leak vs zoonosis, as argued in a recorded multi-party debate | recorded debate — **one ledger per voice**, four source-types (the `EXTRACTION.md` demo) | re-derive the `ledger repro` extraction-**convergence** across two fresh runs |
| `lhc_safety_ledger` | Could LHC collisions make a dangerous black hole? | closed technical | the `depends-on`/`supports` spine on the crux astrophysical bound |
| `eggs_cholesterol_ledger` | Do eggs / dietary cholesterol raise CVD risk? | messy, confounded — **16 sources at corpus scale** | **`content/finding.md`**: the cohort-overlap read-out — three same-cohort **double-counts** the machinery flags on *both* sides (WHI: Sun+Chen; six-US-cohort: Zhong 2019+2021; null: Dehghan+Rong), and that confidence tracks whether a meta-analysis de-duplicates. Reproducible: `ledger graph` / `ledger inspect analysis` |
| `quantum_genomics_ledger` | Is there a real quantum-computing advantage for genomics — and what does it mean for genomic-data security? | **out-of-domain** generalisability proof (outside the three provided topics); 17 sources | **`content/finding.md`**: the QML-speedup case turns on one contested primitive (HHL); the **double-count** flags Tang+Chia (shared dequantisation *method*, not independent) while the independent Cerezo supporting the same claim is **not** flagged; a sealed **faithfulness dispute** on Tang's scope. Reproducible: `ledger graph` / `ledger inspect analysis` |

```bash
make demo DIR=cases/covid_origins_ledger      # or lhc_safety_ledger / eggs_cholesterol_ledger
# without make:  ./ledger_demo.sh cases/covid_origins_ledger
```

The raw corpus is git-ignored everywhere (it keeps repos lean and avoids committing copyrighted full
text), so the demo's verbatim step here **attests** each ledger's committed stamp + body-hash — the
same check CI runs on a fresh clone (§4 trust boundary in [`../DEMO.md`](../DEMO.md)). Rebuild a
case's corpus with its `literature/fetch_paper.sh` to re-prove quotes byte-for-byte.

## The baseline files

Two cases (`covid_origins_ledger`, `lhc_safety_ledger`) ship a pair of baseline artefacts. They are
the evidence for Ledger's claimed uplift, which cannot be assessed with the comparison withheld.
Read them with two limits in view.

**The baseline is self-generated, not an independent evaluation.** It is what a model produced on
the same question without Ledger, run by the same author. That is the standing objection to every
uplift claim here, and it is not answered by the comparison being detailed.

**The two files play different roles, and only one is citation-gated.**

- `baseline_research_raw.md` — captured model output. It is evidence *of* what an ungated answer
  looks like, not authored prose, so it is deliberately **not** gated: of the seven sources
  `covid_origins`' copy cites, five have no ledger in the project, and that unverified quality is
  the demonstration rather than a defect. Gating it would demand ledgers for text the case is
  exhibiting, not asserting.
- `content/baseline_comparison.md` — Ledger's own interpretation of that output. Its claims are
  the author's, so it **is** gated like any other authored prose.

Measured results are not shipped: no reproduction run directories, no faithfulness-eval verdict
archive. The apparatus travels; the numbers are yours to reproduce.
