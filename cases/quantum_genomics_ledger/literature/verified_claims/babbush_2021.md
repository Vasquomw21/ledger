---
paper: "Ryan Babbush, Jarrod R. McClean, Michael Newman, Craig Gidney, Sergio Boixo & Hartmut Neven (2021)"
title: "Focus beyond quadratic speedups for error-corrected quantum advantage"
doi: "10.1103/PRXQuantum.2.010103"
url: "https://doi.org/10.1103/PRXQuantum.2.010103"
source_version: "arXiv:2011.04149; PRX Quantum 2, 010103"
file: "literature/babbush_2021.pdf"
retrieved: "20260603"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "41459329be11c551d308e3de30ee335a690e9e334a0fcf6af49b2a4196a8058b"
extract_sha256: "492206662f8b7a64c29d92ce9d4bd31e8d87d25f793367538c7a136e3618db30"
body_sha256: "151e3333e135b2739c8095a72d8ec6d7385aeb2c97d1fc3936ffe703a425aa95"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260615"
---

# Verified Claims — Babbush et al. (2021), "Focus beyond quadratic speedups for error-corrected quantum advantage"

Independent corroboration of the Hoefler et al. 2023 "quadratic is insufficient" thesis, from the
Google Quantum AI team. Quotes read from the downloaded full text (arXiv:2011.04149) and confirmed
verbatim against `literature/extracted/babbush_2021.txt`.

## Claim 1: Quadratic speed-ups will not enable advantage on early fault-tolerant devices

> "We conclude that quadratic speedups will not enable quantum advantage on early generations of such fault-tolerant devices unless there is a significant improvement in how we would realize quantum error-correction."

**ID:** quadratic-insufficient
**Location:** Abstract. Corroborates [[20260603_grover_search]] / the Hoefler verdict in [[20260603_quantum_advantage_lit]].
**Addresses:** qc-genomics-advantage

---

## Claim 2: The conclusion is robust, and higher-degree (quartic) speed-ups look more practical

> "While this conclusion persists even if we were to increase the rate of logical gates in the surface code by more than an order of magnitude, we also repeat this analysis for speedups by other polynomial degrees and find that quartic speedups look significantly more practical."

**ID:** quartic-more-practical
**Location:** Abstract. Refines the test: the bar is not just "super-quadratic" loosely but, on early hardware, closer to quartic-or-exponential.
**Addresses:** qc-genomics-advantage
