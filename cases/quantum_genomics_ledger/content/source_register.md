---
last_updated: 20260615
curator: van_songhai
status: active
---
# Source Register — quantum computing for genomics

Records *why* each source is in the corpus and *how* it was found, names the viewpoints the
question space contains, and lists what is knowingly missing. The `selection_audit` gate
(`required` here) enforces that every stamped ledger is registered and that **no declared position
is left empty** — covered by a source or named under Known gaps. It does *not* prove the position
set is complete; that judgement is surfaced here and in semantic health.

The corpus is seeded from the standalone `quantum_revolution_ke` white-paper project (its verbatim
quotes + raw sources), rebuilt to the current kit grammar. It spans three sub-questions
(`content/inquiry.md`): a genomics/biology advantage (Q1), the robustness of the claimed speedups
(Q2 — the load-bearing one), and the cryptographic threat to genomic data (Q3).

## Positions

The viewpoints the question space contains. Each must be covered by a source below or named under
Known gaps.

**Position:** real-advantage — quantum simulation of chemistry is a genuine (projected, fault-tolerant)
advantage for molecular/biochemical problems.
**Position:** overtaken — a problem once floated as a quantum target has been settled by classical
methods instead (protein structure prediction).
**Position:** near-term-niche — small, classically-hard combinatorial sub-problems are a plausible
near-term (NISQ) candidate.
**Position:** limited-nisq — near-term devices are fundamentally constrained; broad advantage is not
near.
**Position:** speedup-real — an advertised quantum speedup is real under its stated assumptions.
**Position:** caveated-or-erased — the speedup's own caveats (state preparation, readout, condition
number) can erase it in practice.
**Position:** dequantised — a classical algorithm matches the quantum one once input assumptions are
equalised.
**Position:** threat-present — the cryptographic threat to long-lived data is present now
(harvest-now-decrypt-later).
**Position:** threat-bounded — the threat is bounded by large resource requirements, and standardised
defences already exist.

## Sources

One block per ingested source. `**Source:**` matches a `literature/verified_claims/<key>.md`.

### Harrow, Hassidim & Lloyd (2009) — HHL
**Source:** harrow_2009
**Discovery:** the linear-systems primitive at the root of the quantum-machine-learning speedup claims.
**Rationale:** the speedup claim under test — the crux node of Q2; many later QML algorithms extend it.
**Position:** speedup-real
**Quality:** peer-reviewed, Phys. Rev. Lett. (2009); arXiv:0811.3171.
**Addresses:** speedup-robustness

### Aaronson (2015) — Read the Fine Print
**Source:** aaronson_2015
**Discovery:** the canonical caveat commentary on quantum machine learning.
**Rationale:** sets out the four caveats that can erase HHL's speedup; the primary rebuttal of the bare speedup claim.
**Position:** caveated-or-erased
**Quality:** peer-reviewed, Nature Physics (2015).
**Addresses:** speedup-robustness

### Tang (2019) — dequantisation
**Source:** tang_2019
**Discovery:** the canonical "dequantisation" result.
**Rationale:** a classical algorithm matching a flagship quantum-ML algorithm, erasing its claimed exponential speedup.
**Position:** dequantised
**Quality:** peer-reviewed, STOC 2019; arXiv:1807.04271.
**Addresses:** speedup-robustness

### Chia et al. (2020) — dequantisation framework
**Source:** chia_2020
**Discovery:** the generalisation of Tang's result to a framework.
**Rationale:** shows the dequantisation is not a one-off — a sampling-and-low-rank framework removes the speedup across several QML algorithms.
**Position:** dequantised
**Quality:** peer-reviewed, STOC 2020; arXiv:1910.06151.
**Addresses:** speedup-robustness

### Cerezo et al. (2021) — variational algorithms
**Source:** cerezo_2021
**Discovery:** the standard review of variational quantum algorithms (the NISQ workhorse).
**Rationale:** names the trainability caveat (barren plateaus) and the unproven scaling of the near-term approach.
**Position:** caveated-or-erased
**Quality:** peer-reviewed review, Nature Reviews Physics (2021).
**Addresses:** speedup-robustness

### Arute et al. (2019) — quantum supremacy
**Source:** arute_2019
**Discovery:** the headline hardware "quantum supremacy" demonstration.
**Rationale:** the demonstrated-advantage anchor (a sampling task), whose independence from practical advantage is examined.
**Position:** speedup-real
**Quality:** peer-reviewed, Nature (2019).
**Addresses:** speedup-robustness

### Pednault et al. (2019) — classical rebuttal
**Source:** pednault_2019
**Discovery:** IBM's classical-simulation response to Arute.
**Rationale:** rebuts the strength of the supremacy claim by simulating the task classically — a same-question counter.
**Position:** dequantised
**Quality:** technical report / preprint, IBM (2019); arXiv:1910.09534.
**Addresses:** speedup-robustness

### Preskill (2018) — NISQ era
**Source:** preskill_2018
**Discovery:** the paper that named the NISQ era.
**Rationale:** frames the near-term limits within which any genomics advantage must be claimed.
**Position:** limited-nisq
**Quality:** peer-reviewed, Quantum (2018); arXiv:1801.00862.
**Addresses:** qc-genomics-advantage

### Reiher et al. (2017) — reaction mechanisms
**Source:** reiher_2017
**Discovery:** the canonical quantum-chemistry-on-a-quantum-computer resource study.
**Rationale:** the real-advantage anchor — ground-state energetics of a biochemically relevant catalyst, with explicit fault-tolerant resource estimates.
**Position:** real-advantage
**Quality:** peer-reviewed, PNAS (2017).
**Addresses:** qc-genomics-advantage

### Babbush et al. (2021) — resource estimates
**Source:** babbush_2021
**Discovery:** the updated resource-estimate study for quantum chemistry / materials.
**Rationale:** quantifies what fault-tolerant advantage would require — supports real-advantage while bounding it as projected.
**Position:** real-advantage
**Quality:** peer-reviewed, PRX Quantum (2021).
**Addresses:** qc-genomics-advantage

### Jumper et al. (2021) — AlphaFold
**Source:** jumper_2021
**Discovery:** the protein-structure-prediction breakthrough — by classical deep learning.
**Rationale:** the overtaken anchor — a problem once floated as a quantum target, solved classically; rebuts the quantum-protein-folding hope.
**Position:** overtaken
**Quality:** peer-reviewed, Nature (2021).
**Addresses:** qc-genomics-advantage

### Baek et al. (2021) — RoseTTAFold
**Source:** baek_2021
**Discovery:** the independent classical-ML structure-prediction result.
**Rationale:** a second classical datapoint on the overtaken position — structure prediction is a classical-ML domain.
**Position:** overtaken
**Quality:** peer-reviewed, Science (2021).
**Addresses:** qc-genomics-advantage

### Maurizio et al. (2025) — discrete optimisation
**Source:** maurizio_2025
**Discovery:** a recent survey of combinatorial-optimisation niches in genomics.
**Rationale:** the near-term-niche anchor — small, classically-hard sub-problems (phasing, phylogenetics) as plausible NISQ candidates.
**Position:** near-term-niche
**Quality:** peer-reviewed (2025).
**Addresses:** qc-genomics-advantage

### Shor (1997) — factoring
**Source:** shor_1997
**Discovery:** the foundational algorithm for the cryptographic threat.
**Rationale:** polynomial-time factoring/discrete-log — breaks the public-key cryptography protecting genomic data.
**Position:** threat-present
**Quality:** peer-reviewed, SIAM J. Comput. (1997).
**Addresses:** crypto-threat

### Mosca (2018) — cybersecurity timeline
**Source:** mosca_2018
**Discovery:** the standard statement of the harvest-now-decrypt-later risk.
**Rationale:** makes the threat present for long-lived data even before a machine exists — the reason genomic confidentiality is exposed now.
**Position:** threat-present
**Quality:** peer-reviewed, IEEE Security & Privacy (2018).
**Addresses:** crypto-threat

### Gidney & Ekerå (2021) — resource estimate
**Source:** gidney_2021
**Discovery:** the most-cited estimate of the hardware needed to run Shor on RSA-2048.
**Rationale:** bounds the threat — 20 million noisy qubits / 8 hours — large but finite; the threat-bounded anchor.
**Position:** threat-bounded
**Quality:** peer-reviewed, Quantum (2021); arXiv:1905.09749.
**Addresses:** crypto-threat

### NIST (2024) — FIPS 203
**Source:** nist_2024
**Discovery:** the finalised post-quantum cryptography standard.
**Rationale:** the standardised defence — the gap is migration, not invention; completes the threat-bounded position.
**Position:** threat-bounded
**Quality:** official standard, NIST FIPS 203 (2024).
**Addresses:** crypto-threat

## Known gaps

Viewpoints or sources known to exist but not yet ingested.

**Gap:** the specific quantum-ML algorithms the dequantisation results overturn (Kerenidis & Prakash
2017 and the other HHL-derived QML papers) are not each ingested individually — the dequantisation is
shown via Tang's and Chia's own characterisation of what they match, not by quoting every dequantised
algorithm. This bounds how directly the "rests on one primitive" structure can be traced to each
descendant paper.
**Gap:** no source demonstrating a *realised* (not projected) quantum advantage on a genuine genomics
problem is ingested — because, on this corpus, none exists. The absence is itself part of the finding,
not a hole to be backfilled with a weaker source.
**Gap:** competing fault-tolerant resource estimates beyond Gidney & Ekerå 2021 (e.g. later
error-correction-overhead revisions) are not ingested; the threat-bounded timeline rests on one estimate.
**Gap:** the Kenya/Africa policy and capacity layer of the source white paper (data-protection law,
genomics-sovereignty initiatives) is deliberately out of scope for this case, which is the
generalisability demonstration on the *technical* question, not the full policy paper.
