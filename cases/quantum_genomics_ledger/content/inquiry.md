---
authored_by: ai
generated_by: claude
generated_date: 20260615
reviewed_by:
status: draft
---

# Inquiry — quantum computing for genomics

The question tree this knowledge base is organised around. Each sub-question declares a stable
`**id:**`; claims opt in with `**Addresses:** <id>`, and an assessment may mark one claim as the
`**Crux-of:**` a sub-question. The framing-agnostic structural read-out across these sub-questions
is in [[finding]].

## Q1 — Is there a genuine quantum advantage for genomics and biology?

**id:** qc-genomics-advantage
**parent:** quantum-genomics

The honest answer is mixed and depends on the problem. Simulating quantum chemistry — ground-state
energies of small molecules relevant to drug and enzyme design — is the credible medium-to-long-term
case, but it is positioned by its own proponents as *projected*, conditional on fault-tolerant
hardware (Reiher et al. 2017 #classically-intractable-projected;
Babbush et al. 2021 #quadratic-insufficient). Protein structure prediction, once floated as a
quantum target, has been settled by classical machine learning instead
(Jumper et al. 2021 #alphafold-atomic-accuracy, AlphaFold;
Baek et al. 2021 #rosettafold-approaches-alphafold). A narrower near-term candidate is small,
classically-hard combinatorial sub-problems in genomics
(Maurizio et al. 2025 #near-term-narrow-optimisation). Big-data steps — sequence search, variant calling, population
genetics — are bottlenecked on loading classical data into a quantum device, the same caveat that
governs Q2.

**Positions.** real-advantage (quantum chemistry, projected): Reiher 2017, Babbush 2021. overtaken
(protein folding solved classically): Jumper 2021, Baek 2021. near-term-niche (discrete optimisation):
Maurizio 2025. The framing rests on the speedup question below.

## Q2 — Do the claimed "exponential speedups" survive their own caveats and dequantisation?

**id:** speedup-robustness

This is the load-bearing sub-question and the one the machinery is built to surface. Many
quantum-machine-learning speedup claims descend from one primitive — the HHL linear-systems algorithm
(Harrow, Hassidim & Lloyd 2009 #exponential-speedup) — which advertises a logarithmic-time solve.
Aaronson (2015 #four-caveats-thesis) sets out four caveats (state preparation, readout, condition
number, comparison to the best classical algorithm), each of which can erase the speedup in
practice. The dequantisation results (Tang 2019 #classical-matches-quantum;
Chia et al. 2020 #svt-no-exponential-speedup) go further: for several flagship cases a classical
algorithm matches the quantum one once the input assumptions are made equal. Separately, a hardware
"quantum supremacy" demonstration (Arute et al. 2019 #experimental-supremacy-realization) was
contested by a classical-simulation rebuttal (Pednault et al. 2019 #rebuttal-days-not-years), and
variational NISQ approaches carry their own trainability caveat
(Cerezo et al. 2021 #barren-plateaus, barren plateaus).

**The crux.** Whether an advertised exponential speedup survives the state-preparation, readout, and
condition-number assumptions, compared against the best classical algorithm for the same restricted
task. Harrow 2009's speedup claim is the crux node; Aaronson 2015 and Tang 2019 contest it.

**Positions.** speedup-real (under stated assumptions): Harrow 2009, Arute 2019. caveated-or-erased
(the assumptions bite): Aaronson 2015, Cerezo 2021. dequantised (classical matches it): Tang 2019,
Chia 2020, Pednault 2019.

## Q3 — Is the cryptographic threat to genomic data present and permanent?

**id:** crypto-threat

Genomic data is maximally sensitive and effectively permanent, so its confidentiality horizon is
decades. Shor's algorithm (Shor 1997 #breaks-rsa) breaks the public-key cryptography protecting it,
and the "harvest-now, decrypt-later" posture makes the threat present even before a
cryptographically-relevant machine exists (Mosca 2018 #harvest-now-decrypt-later). Resource
estimates put that machine years away and large (Gidney & Ekerå 2021 #resource-estimate), and
standardised post-quantum replacements already exist (NIST 2024 #pqc-standardised, FIPS 203),
so the gap is migration, not invention.

**Positions.** threat-present (harvest-now): Shor 1997, Mosca 2018. threat-bounded (large resources,
defence exists): Gidney 2021, NIST 2024.
