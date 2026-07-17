---
paper: "Aurora Maurizio & Guglielmo Mazzola (2025)"
title: "Quantum computing for genomics: conceptual challenges and practical perspectives"
doi: "10.1103/h49j-bsc6"
url: "https://doi.org/10.1103/h49j-bsc6"
source_version: "arXiv:2507.04111v1; PRX Life 3, 047001"
file: "literature/maurizio_2025.html"
retrieved: "20260603"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "a4a53c75068d6354f096b76474d658b0629e126f807a4ba8fb87d7e4d276d075"
extract_sha256: "2ea0b5ba7883bd0c476839a7a84240973219770dd93be9ca2da20be6c6c41b41"
body_sha256: "04856b5aa9a066916a626d728d99472e35d1f61e3b037e29f10b19a4357513bc"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "a4a53c75068d6354f096b76474d658b0629e126f807a4ba8fb87d7e4d276d075"
---

# Verified Claims — Maurizio & Mazzola (2025), "Quantum computing for genomics: conceptual challenges and practical perspectives"

Quotes read from the arXiv full-text HTML (arXiv:2507.04111v1, the open-access version of
PRX Life 3, 047001) and confirmed verbatim against `literature/extracted/maurizio_2025.txt`.
This is the closest peer-reviewed analogue to our own genomics mapping: same remit (where a
quantum advantage is real for genomics), same method (a practicality test on speed-up class,
data-loading and classical baselines). It both corroborates our honest negatives and
identifies a near-term opportunity class our Layer 3 did not surface — small, hard discrete
optimisation. Drives the Gap-1 correction to [[20260603_genomics_mapping_lit]].

## Claim 1: The genuine near-term genomics opportunity is a narrow class of small, hard optimisation problems

> "Given the competition from excellent classical approximate solvers, quantum computing could offer a speedup in the near future only for a specific subset of hard enough tasks in assembly, gene selection, and inference."

**ID:** near-term-narrow-optimisation
**Location:** Abstract / Conclusion (the paper's central verdict). The condition — hard for classical methods *and* relatively few variables — is the same as our Layer-1 practicality test ([[20260603_quantum_advantage]]): small input + a hard structured problem.
**Addresses:** qc-genomics-advantage

---

## Claim 2: The condition is hard for classical methods AND relatively few variables

> "These tasks need to be characterized by core optimization problems that are particularly challenging for classical methods while requiring relatively limited variables."

**ID:** hard-and-few-variables
**Location:** Abstract / Conclusion (the paper's central verdict). The condition — hard for classical methods *and* relatively few variables — is the same as our Layer-1 practicality test ([[20260603_quantum_advantage]]): small input + a hard structured problem.
**Addresses:** qc-genomics-advantage

---

## Claim 3: Specific genomics optimisation problems are the candidate mappings

> "Among these, we identify the following optimization problems: Max-Cut, Maximum Independent Set, Knapsack, and Quadratic Assignment Problems to be relevant for (or possibly connected to) genomics."

**ID:** candidate-optimisation-mappings
**Location:** Sect. IV (Optimization problems in genomics and quantum advantage).
**Addresses:** qc-genomics-advantage

---

## Claim 4: Quantum-enhanced Markov chain can accelerate inference tasks

> "the quantum-enhanced Markov chain algorithm, [ 150 ,  39 ] , a new quantum algorithm devised to speed up Monte Carlo simulations, can be beneficial for accelerating inference tasks."

**ID:** quantum-markov-chain-inference
**Location:** Sect. IV (Optimization problems in genomics and quantum advantage).
**Addresses:** qc-genomics-advantage

---

## Claim 5: Gene selection maps to Maximum Independent Set

> "Further, MIS has also been proposed in gene selection."

**ID:** gene-selection-mis
**Location:** Sect. IV (gene selection / panel design).
**Addresses:** qc-genomics-advantage

---

## Claim 6: MIS framework selects maximally informative, non-overlapping genes

> "one can use the MIS framework to select a subset of genes that are maximally informative and non-overlapping in their biological roles."

**ID:** mis-informative-genes
**Location:** Sect. IV (gene selection / panel design).
**Addresses:** qc-genomics-advantage

---

## Claim 7: Haplotype phasing is determining the most likely phase configuration

> "The optimization problem in haplotype phasing is determining the most likely phase configuration for each heterozygous variant along the chromosome."

**ID:** haplotype-phasing-problem
**Location:** Sect. IV (haplotype phasing). Exactly the shape our test rewards — small input (heterozygous sites only), exponential hardness, weak classical guarantees.
**Addresses:** qc-genomics-advantage

---

## Claim 8: Haplotype combinations grow exponentially with heterozygous sites

> "the number of possible haplotype combinations grows exponentially with the number of heterozygous sites."

**ID:** haplotype-exponential-growth
**Location:** Sect. IV (haplotype phasing). Exactly the shape our test rewards — small input (heterozygous sites only), exponential hardness, weak classical guarantees.
**Addresses:** qc-genomics-advantage

---

## Claim 9: Data-loading remains the disqualifier for big-data genomics tasks

> "Unfortunately, given that the genome data does not follow any deterministic pattern, the depth of the circuit needed to load the data cannot scale more favorably than"

**ID:** data-loading-disqualifier
**Location:** Sect. III (Quantum search in genomics). Corroborates the data-loading verdict in [[20260603_sequence_search]] and [[20260603_genomic_ml]].
**Addresses:** qc-genomics-advantage

---

## Claim 10: Gate-time realism — estimates suggest around 10 kHz

> "The typical quantum gate frequency will depend on the architecture and error correction code implemented in the future, but estimates suggest around 10 kHz"

**ID:** gate-frequency-10khz
**Location:** Sect. II.2 (Scaling advantage vs gate time) and the "Myths" appendix. A concrete quantitative basis for "quadratic is not enough" beyond Hoefler — strengthens Layer 1/2.
**Addresses:** qc-genomics-advantage

---

## Claim 11: Quantum gates cannot operate faster than their classical control electronics

> "Quantum digital gates cannot operate faster than the classical electronics that controls them"

**ID:** gates-bounded-by-electronics
**Location:** Sect. II.2 (Scaling advantage vs gate time) and the "Myths" appendix. A concrete quantitative basis for "quadratic is not enough" beyond Hoefler — strengthens Layer 1/2.
**Addresses:** qc-genomics-advantage

---

## Claim 12: No quantum speed-up for ML on real-world data has been observed

> "no quantum speed-up for machine learning on  real-world  datasets has been observed or even postulated. Any scalability advantages have only been demonstrated on artificial datasets."

**ID:** no-qml-real-world-speedup
**Location:** Sect. V (Quantum Machine Learning). Corroborates [[20260603_genomic_ml]].
**Addresses:** qc-genomics-advantage

---

> **Use in the white paper (Gap-1 correction):** this peer-reviewed review confirms our honest
> negatives (sequence search, QML, data-loading) and our practicality test, but adds a near-term
> opportunity class we had landed as negative/data-bound: small, hard *discrete optimisation* —
> haplotype phasing (Max-Cut), gene-panel selection (MIS/Knapsack), and inference/phylogenetics
> (quantum-enhanced Monte Carlo). The honest verdict shifts from "the only genomics opportunity is
> fault-tolerant biomolecular chemistry" to "...plus a NISQ-era discrete-optimisation niche on small,
> classically-hard instances — candidate, not demonstrated." Feeds [[20260603_genomics_mapping_lit]],
> [[20260603_variant_calling_popgen]] and [[20260603_sequence_search]].
