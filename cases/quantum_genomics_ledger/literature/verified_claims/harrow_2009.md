---
paper: "Aram W. Harrow, Avinatan Hassidim & Seth Lloyd (2009)"
title: "Quantum algorithm for linear systems of equations"
doi: "10.1103/PhysRevLett.103.150502"
url: "https://doi.org/10.1103/PhysRevLett.103.150502"
source_version: "arXiv:0811.3171; Phys. Rev. Lett. 103, 150502 (2009)"
file: "literature/harrow_2009.pdf"
retrieved: "20260603"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "a15b70b8123984a650cc3f3df2476edb7d381c29d8406297ba3d048ae5915c24"
extract_sha256: "29162f779215c3c437d14ae9dc08e8bbe2219fee2e2763ba69e54811695107eb"
body_sha256: "9f2610d065b20e1d4960c271b52c1783f5a7b730bfd74cfedaaf9b3297fd7925"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "a15b70b8123984a650cc3f3df2476edb7d381c29d8406297ba3d048ae5915c24"
---

# Verified Claims — Harrow, Hassidim & Lloyd (2009), "Quantum algorithm for linear systems of equations"

The HHL primitive itself (its caveats are separately logged from Aaronson 2015). Quotes read
from the downloaded full text (arXiv:0811.3171) and confirmed verbatim against
`literature/extracted/harrow_2009.txt`. Symbols rendered as their true characters.

## Claim 1: The headline result — solve Ax=b in poly(log N) time, an exponential improvement

> "Here, we exhibit a quantum algorithm for this task that runs in poly(log N, κ) time, an exponential improvement over the best classical algorithm."

**ID:** exponential-speedup
**Location:** Abstract
**Addresses:** speedup-robustness
**Crux-of:** speedup-robustness (grounded by #exponential-speedup) [if-resolved: whether an advertised exponential speedup survives the state-preparation, readout, and condition-number assumptions, compared against the best classical algorithm for the same restricted task]

---

## Claim 2: The runtime depends on the condition number κ and error ε

> "our runtime will scale as κ² log(N)/ε, where ε is the additive error achieved in the output state |x⟩."

**ID:** kappa-runtime
**Location:** Introduction. The κ-dependence and sparsity assumptions are the caveats Aaronson (2015) expands on.
**Addresses:** speedup-robustness

---

## Claim 3: The crucial caveat — the output is a quantum state; you read out expectation values, not all of x

> "Clearly, to read out all the components of x would require one to perform the procedure at least N times. However, often one is interested not in x itself, but in some expectation value ... we obtain an estimate of the expectation value ⟨x|M|x⟩"

**ID:** readout-expectation
**Location:** Introduction
**Addresses:** speedup-robustness

---

## Claim 4: The explicit exponential-speed-up claim over classical matrix inversion

> "we will prove that in fact any classical algorithm requires in general exponentially more time than our quantum algorithms to perform the same matrix inversion task."

**ID:** exponential-over-classical
**Location:** Introduction
**Addresses:** speedup-robustness
