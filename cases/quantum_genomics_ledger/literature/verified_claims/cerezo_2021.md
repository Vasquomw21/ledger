---
paper: "M. Cerezo, Akira Sone, Tyler Volkoff, Lukasz Cincio & Patrick J. Coles (2021)"
title: "Cost Function Dependent Barren Plateaus in Shallow Parametrized Quantum Circuits"
doi: "10.1038/s41467-021-21728-w"
url: "https://doi.org/10.1038/s41467-021-21728-w"
source_version: "Nature Communications 12, 1791 (2021); arXiv:2001.00550"
file: "literature/cerezo_2021.pdf"
retrieved: "20260603"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "598131d3d16e8f754ebf690cd9c91e194818e2702f10d6fc9dc5c64675a62de9"
extract_sha256: "e607ebc670e881c6059e8699e9a2386bd33764844194e6f6071dd81ce17dd4f0"
body_sha256: "9f260430ec17a4cd91125f6486266cd3441b4f53f4a75a1e517578bbb45649d8"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "598131d3d16e8f754ebf690cd9c91e194818e2702f10d6fc9dc5c64675a62de9"
---

# Verified Claims — Cerezo et al. (2021), "Cost Function Dependent Barren Plateaus in Shallow Parametrized Quantum Circuits"

Extends the barren-plateau obstruction to shallow circuits and ties trainability to cost-function
locality. Quotes read from the downloaded full text (arXiv:2001.00550) and confirmed verbatim
against `literature/extracted/cerezo_2021.txt`.

## Claim 1: Variational quantum algorithms are heuristics with unproven scaling

> "While VQAs may enable practical applications of noisy quantum computers, they are nevertheless heuristic methods with unproven scaling."

**ID:** vqa-unproven-scaling
**Location:** Abstract. The direct, citable statement that VQE/QAOA have no proven quantum speed-up.
**Addresses:** speedup-robustness
**Supports:** maurizio_2025:no-qml-real-world-speedup (grounded by #vqa-unproven-scaling) [rec: cerezo-supports-noqml-apt]

---

## Claim 2: Global cost functions give barren plateaus even for shallow circuits; local costs are trainable only to logarithmic depth

> "Our first result states that defining C in terms of global observables leads to exponentially vanishing gradients (i.e., barren plateaus) even when V(θ) is shallow."

> "our second result states that defining C with local observables leads to at worst a polynomially vanishing gradient, so long as the depth of V(θ) is O(log n)."

**ID:** barren-plateaus
**Location:** Abstract. Establishes that trainability survives only in a narrow (shallow, local-cost) regime.
**Addresses:** speedup-robustness
