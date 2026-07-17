---
paper: "Frank Arute et al. (Google AI Quantum) (2019)"
title: "Quantum supremacy using a programmable superconducting processor"
doi: "10.1038/s41586-019-1666-5"
url: "https://doi.org/10.1038/s41586-019-1666-5"
source_version: "Nature 574, 505–510"
file: "literature/arute_2019.pdf"
retrieved: "20260603"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "97d2dd6528350d7c8c2d8222798ecc579f54f28d84316569a719f2f521cf382a"
extract_sha256: "6cea503e70286dee981fef09b66631f19617847be6dc44869617eb61fc69fc5d"
body_sha256: "e121eb08f2a6011da3d6d16a129889673f694e390c88a9f1356a5babc8dc8e61"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "97d2dd6528350d7c8c2d8222798ecc579f54f28d84316569a719f2f521cf382a"
---

# Verified Claims — Arute et al. (2019), "Quantum supremacy using a programmable superconducting processor"

Quotes read from the downloaded full text (OSTI accepted-manuscript record 1607005,
the *Nature* article) and confirmed verbatim against
`literature/extracted/arute_2019.txt`. This is the first claimed experimental
demonstration of quantum supremacy — to be reported alongside its contestation
(see note at the foot).

## Claim 1: 53 qubits, a computational state-space of ~2⁵³ ≈ 10¹⁶

> "Here, we report using a processor with programmable superconducting qubits to create quantum states on 53 qubits, corresponding to a computational state-space of dimension 2⁵³ ∼ 10¹⁶."

**ID:** 53-qubit-state-space
**Location:** Abstract
**Addresses:** speedup-robustness

---

## Claim 2: ~200 seconds vs ~10,000 years — the headline speedup claim

> "While our processor takes about 200 seconds to sample one instance of a quantum circuit 1 million times, our benchmarks currently indicate the equivalent task for a state-of-the-art supercomputer takes approximately 10,000 years."

**ID:** 200s-vs-10000-years
**Location:** Abstract
**Addresses:** speedup-robustness

---

## Claim 3: The explicit claim of "an experimental realization of quantum supremacy"

> "This dramatic speedup relative to all known classical algorithms provides an experimental realization of quantum supremacy on a computational task and heralds the advent of a much-anticipated computing paradigm."

**ID:** experimental-supremacy-realization
**Location:** Abstract
**Addresses:** speedup-robustness

---

## Claim 4: The task is random circuit sampling — NOT a useful application

> "To demonstrate quantum supremacy, we compare our quantum processor against state-of-the-art classical computers in the task of sampling the output of a pseudo-random quantum circuit."

**ID:** task-is-random-circuit-sampling
**Location:** §"A computational task to demonstrate quantum supremacy"
**Addresses:** speedup-robustness

---

## Claim 5: Fidelity is small but statistically resolved (the result lives at low fidelity)

> "For the largest elided data (n = 53, m = 20, total Ns = 30 M), we find an average F_XEB > 0.1% with 5σ confidence, where σ includes both systematic and statistical uncertainties."

**ID:** low-fidelity-5sigma
**Location:** §"Fidelity estimation in the supremacy regime"
**Addresses:** speedup-robustness

---

## Claim 6: Forward-looking — error correction is required for useful algorithms

> "To sustain the double exponential growth rate and to eventually offer the computational volume needed to run well-known quantum algorithms, such as the Shor or Grover algorithms, the engineering of quantum error correction will have to become a focus of attention."

> "We are only one creative algorithm away from valuable near-term applications."

**ID:** error-correction-required-future
**Location:** §"What does the future hold?"
**Addresses:** speedup-robustness

---

> **Contestation note (for the review, needs its own ledger before citing):** IBM
> researchers (Pednault et al., 2019, arXiv:1910.09534) argued the classical estimate
> of 10,000 years was far too high — that an optimized classical simulation could
> perform the task in ~2.5 days. This contestation must be fetched and quote-logged
> separately before the white paper states it; it is recorded here only as a pointer,
> not as a verified claim.
