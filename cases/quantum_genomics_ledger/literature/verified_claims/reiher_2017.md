---
paper: "Markus Reiher, Nathan Wiebe, Krysta M. Svore, Dave Wecker & Matthias Troyer (2017)"
title: "Elucidating Reaction Mechanisms on Quantum Computers"
doi: "10.1073/pnas.1619152114"
url: "https://doi.org/10.1073/pnas.1619152114"
source_version: "arXiv:1605.03590; PNAS 114(29), 7555–7560"
file: "literature/reiher_2017.pdf"
retrieved: "20260603"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "34343e00ffd4ea98f9b120e99b71586785d8ae4af984f3630b1133681508e1d8"
extract_sha256: "ca695668b5ed2fc773829675b49e96b94f643fd8e4f59341abf92fea3fb0f3ef"
body_sha256: "ac6ee26c6119efd011cddfd7cfb6002cd5879863742ca5c4d585be9505543b2d"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "34343e00ffd4ea98f9b120e99b71586785d8ae4af984f3630b1133681508e1d8"
---

# Verified Claims — Reiher et al. (2017), "Elucidating Reaction Mechanisms on Quantum Computers"

The canonical resource-estimate paper for a *biologically meaningful* quantum-chemistry target:
the FeMo cofactor (FeMoco) of nitrogenase, the active site of biological nitrogen fixation.
Quotes read from the downloaded full text (arXiv:1605.03590) and confirmed verbatim against
`literature/extracted/reiher_2017.txt` (ligature glyphs rendered as their true letters).

## Claim 1: A quantum computer can elucidate a reaction mechanism intractable for classical simulation — nitrogenase/FeMoco as the worked example

> "We show how a quantum computer can be employed to elucidate reaction mechanisms in complex chemical systems, using the open problem of biological nitrogen fixation in nitrogenase as an example."

**ID:** elucidate-reaction-mechanism
**Location:** Abstract
**Addresses:** qc-genomics-advantage

---

## Claim 2: The central demonstrated-in-resource-estimate claim — projected, not yet run on hardware

> "While at present a quantitative understanding of chemical processes involving complex open-shell species such as FeMoco in biological nitrogen fixation remains beyond the capability of classical-computer simulations, our work shows that quantum computers used as accelerators to classical computers could be used to elucidate this mechanism using a manageable amount of memory and time."

**ID:** classically-intractable-projected
**Location:** Discussion. This is the central "demonstrated-in-resource-estimate" claim — projected, not yet run on hardware.
**Addresses:** qc-genomics-advantage

---

## Claim 3: The input is SMALL — a molecular active space of a few tens of orbitals (satisfies the small-data criterion)

> "Structure 1 is for spin state S = 0 and charge +3 elementary charges with 54 electrons in 54 spatial orbitals."

**ID:** small-active-space
**Location:** Table I caption (a second FeMoco structure uses 65 electrons in 57 spatial orbitals). The entire classically-intractable calculation fits in an active space of order ~50 orbitals — the defining feature that makes quantum chemistry a *small-input* problem.
**Addresses:** qc-genomics-advantage

---

## Claim 4: Exact classical methods scale exponentially — why this is classically intractable

> "CASSCF is traditionally implemented as an exact diagonalization method, which limits its applicability to 18 electrons in 18 (spatial) orbitals because of the steep scaling of many-electron basis states with the number of electrons and orbitals"

**ID:** exact-diagonalisation-scaling
**Location:** Methods (exact-diagonalisation discussion)
**Addresses:** qc-genomics-advantage

---

## Claim 5: Strongly correlated electrons are out of reach for classical ab initio methods

> "On classical computers, molecules with much less than a hundred strongly correlated electrons are already out of reach for systematically improvable ab initio methods that could achieve the required accuracy."

**ID:** classical-ab-initio-out-of-reach
**Location:** Introduction
**Addresses:** qc-genomics-advantage

---

## Claim 6: Resource estimate — feasible on a small quantum computer even with error-correction overhead

> "Detailed resource estimates show that, even when taking into account the substantial overhead of quantum error correction, and the need to compile into discrete gate sets, the necessary computations can be performed in reasonable time on small quantum computers."

**ID:** resource-estimate-feasible
**Location:** Abstract
**Addresses:** qc-genomics-advantage

---

## Claim 7: Serial runtime estimate — under a year on a small number of logical qubits

> "If all gates are executed in series then we estimate that the simulation will complete in under a year and use a small number of logical qubits."

**ID:** serial-runtime-logical-qubits
**Location:** Resource Estimates section. (Parallelisation trades qubits for wall-clock time; the serial estimate is ~hundreds of days on ~100+ logical qubits per Table I.) NB: these are *logical*-qubit counts assuming fault tolerance — far beyond NISQ hardware; the claim is projected feasibility, not a present capability.
**Addresses:** qc-genomics-advantage
