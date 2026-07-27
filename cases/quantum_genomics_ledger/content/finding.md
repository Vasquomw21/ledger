# Finding — quantum computing for genomics

The framing-agnostic structural read-out of the corpus, reproducible from the committed ledgers via
`ledger graph` (the typed edges + derived double-count) and `ledger inspect analysis` (the load-bearing
claims and dependency closure). It reports what the machinery makes auditable, with the honest
boundary stated. The judgement layer behind it is in [[speedup_assessment]].

## The question

Across three sub-questions ([[inquiry]]): is there a genuine quantum advantage for genomics/biology
(Q1), do the claimed "exponential speedups" survive their caveats and dequantisation (Q2, the
load-bearing one), and is the cryptographic threat to genomic data present and permanent (Q3)?

## What the machinery surfaces (Q2 — the speedup is one contested joint, not a broad front)

A fluent survey states "HHL gives an exponential speedup" and moves on. The claim graph shows the
popular advantage case turning on a single contested claim and resting, by the proponent's own
account, on one primitive:

- **One crux, not many.** `harrow_2009:exponential-speedup` is marked the crux of speedup-robustness
  (`hhl-speedup-crux`). Per `aaronson_2015:hhl-engine`, "many of the subsequent quantum learning
  algorithms extend HHL or use it as a subroutine" — so the apparent breadth of QML-speedup results
  is not independent breadth; it descends from the one primitive whose caveats are under test.
- **The headline is qualified and rebutted.** Aaronson qualifies it (`four-caveats-thesis`: the
  speedup holds only under four caveats); Tang rebuts the general-classical version
  (`tang_2019:no-exponential-speedup → harrow_2009:exponential-over-classical`); the supremacy
  demonstration is contested (`pednault_2019:rebuttal-days-not-years → arute_2019:200s-vs-10000-years`).
- **A non-independence the machinery flags — on the skeptic side.** Tang, Chia, and Cerezo all
  support "no real-world QML speedup" (`maurizio_2025:no-qml-real-world-speedup`), but the derived
  double-count fires on **Tang + Chia** (Chia generalises Tang's dequantisation method — one family,
  counted twice) and **not** on Cerezo (an independent barren-plateau obstruction). The detector is
  framing-agnostic: it flags a correlated pair on the *skeptical* conclusion, not the hyped one.
- **A faithfulness limit, recorded.** `tang-rebuts-hhl-faithfulness` disputes that Tang's
  algorithm-specific quote licenses a rebuttal of *every* HHL application; HHL for sparse,
  well-conditioned systems is not dequantised by that result.

## The honest answer on Q1 and Q3

- **Q1 — narrow and mostly projected.** Quantum chemistry is the genuine candidate advantage
  (`reiher_2017`, `babbush_2021`), but it is *projected*, conditional on fault-tolerant hardware that
  does not yet exist (`chemistry-advantage-calibration`). Protein structure prediction — once floated
  as a quantum target — was settled by classical machine learning instead (`jumper_2021`, with
  `baek_2021` corroborating, and flagged as not wholly independent of it). The near-term niche is
  small classically-hard combinatorial sub-problems (`maurizio_2025`).
- **Q3 — present and bounded.** Shor's algorithm breaks the public-key cryptography protecting
  genomic data (`shor_1997`), and "harvest-now, decrypt-later" makes the threat present now for
  long-lived data (`mosca_2018`). It is bounded by large resource requirements (`gidney_2021`) and by
  standardised post-quantum defences that already exist (`nist_2024`) — the gap is migration, not
  invention.

## Honest boundary

This does not claim quantum computing is useless for biology: quantum chemistry is named as a real
projected advantage, and the cryptographic threat as real. It does not claim the machinery
*discovered* the speedup caveats — those are Aaronson's, Tang's, and Chia's own theses; what the
machinery adds is that the dependency of the advantage case on one contested primitive, and the
non-independence of the dequantisation evidence, become mechanically auditable rather than matters of
each reader's trust. And it fires only the one double-count its corpus supports: the broader family
of HHL-descendant QML papers is a Known gap (`source_register.md`), so this is the auditable-overlap
result, not an overturning of the field's verdict.
