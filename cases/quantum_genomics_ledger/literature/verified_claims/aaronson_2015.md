---
paper: "Scott Aaronson (2015)"
title: "Quantum Machine Learning Algorithms: Read the Fine Print"
doi: "10.1038/nphys3272"
url: "https://doi.org/10.1038/nphys3272"
source_version: "Nature Physics 11, 291–293 (2015)"
file: "literature/aaronson_2015.pdf"
retrieved: "20260603"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "871734c175d555199e8314311c295a2bfbe7030b2afa293aee04bd0d6c639fba"
extract_sha256: "54ebc87fd261b5fd57ec63581cfe2a5f55e78c200bec5b732f7eae013116f34d"
body_sha256: "95540b9a00e3fa81bd96d3afcfdbebb792c22dd96661270917bc200f577b18a2"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "871734c175d555199e8314311c295a2bfbe7030b2afa293aee04bd0d6c639fba"
---

# Verified Claims — Aaronson (2015), "Read the Fine Print"

Quotes read from the downloaded author-hosted full text (scottaaronson.com/papers/qml.pdf,
the expanded version of the *Nature Physics* commentary) and confirmed verbatim against
`literature/extracted/aaronson_2015.txt`. Ligature/symbol glyphs are rendered as their
true characters below.

## Claim 1: HHL is the engine behind the quantum-machine-learning speedup claims

> "The algorithm at the center of the 'quantum machine learning' mini-revolution is called HHL [9], after my colleagues Aram Harrow, Avinatan Hassidim, and Seth Lloyd, who invented it in 2008. Many of the subsequent quantum learning algorithms extend HHL or use it as a subroutine, so it's important to understand HHL first."

> "Given an n × n real matrix A and a vector b, the goal of HHL is to (approximately) solve the system Ax = b for x, and to do so in an amount of time that scales only logarithmically with n, the number of equations and unknowns."

**ID:** hhl-engine
**Location:** Opening (the HHL algorithm)
**Addresses:** speedup-robustness

---

## Claim 2: Caveat 1 — data loading / state preparation can negate the speedup

> "The vector b = (b1, . . . , bn) somehow needs to be loaded quickly into the quantum computer's memory, so that we can prepare a quantum state |b⟩ ... At least in theory, this can be done using a 'quantum RAM'".

> "if preparing |b⟩ already takes nᶜ steps for some constant c, then the exponential speedup of HHL vanishes in the very first step."

**ID:** caveat-state-preparation
**Location:** "Caveats" (caveat 1, state preparation)
**Addresses:** speedup-robustness

---

## Claim 3: Caveat 2 — readout: the output is a quantum state; you cannot read out all of x

> "When HHL is finished, its output is not x itself, but rather a quantum state |x⟩ of log₂ n qubits, which (approximately) encodes the entries of x in its amplitudes."

> "learning the value of any specific entry xi will, in general, require repeating the algorithm roughly n times, which would once again kill the exponential speedup."

**ID:** caveat-readout
**Location:** "Caveats" (readout caveat)
**Addresses:** speedup-robustness

---

## Claim 4: Caveat 3 — condition number κ and sparsity assumptions are required

> "let κ = |λmax/λmin| be the ratio in magnitude between A's largest and smallest eigenvalues. Then the amount of time needed by HHL grows nearly linearly with κ. If κ grows like nᶜ, then the exponential speedup is gone."

**ID:** caveat-condition-number
**Location:** "Caveats" (condition-number caveat)
**Addresses:** speedup-robustness

---

## Claim 5: The thesis — the speedup holds only under all four caveats simultaneously

> "Briefly, the HHL algorithm 'solves Ax = b in logarithmic time,' but it does so only with the following four caveats, each of which can be crucial in practice."

> "To summarize, HHL is not exactly an algorithm for solving a system of linear equations in logarithmic time."

**ID:** four-caveats-thesis
**Location:** Introduction to the caveats; summary
**Addresses:** speedup-robustness
**Qualifies:** harrow_2009:exponential-speedup (grounded by #four-caveats-thesis) [why: Aaronson does not deny the HHL speedup — he conditions it on four caveats (state preparation, readout, condition number, comparison to the best classical algorithm), each of which can erase it in practice]

---

## Claim 6: Honest comparison must be against the best classical algorithm for the same restricted task

> "in quantum algorithms research, we always want to compare against the fastest possible classical algorithm that performs the same task."

> "The most they could say was that they couldn't find such a classical algorithm."

**ID:** honest-classical-comparison
**Location:** Discussion of dequantization risk / Clader et al.
**Addresses:** speedup-robustness
