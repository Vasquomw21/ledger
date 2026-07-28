---
paper: "Edwin Pednault, John A. Gunnels, Giacomo Nannicini, Lior Horesh & Robert Wisnieff (IBM) (2019)"
title: "Leveraging Secondary Storage to Simulate Deep 54-qubit Sycamore Circuits"
doi: "10.48550/arXiv.1910.09534"
url: "https://doi.org/10.48550/arXiv.1910.09534"
source_version: "arXiv:1910.09534 (IBM T.J. Watson Research Center)"
file: "literature/pednault_2019.pdf"
retrieved: "20260603"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "1e173f6301fab652424a5b10c733aa336e0fbe41b91ef99a26dd35a86e2de1dc"
extract_sha256: "666335dde137d4b91d7c6670fed17ae35b6415a27ed6919bee157f885201712c"
body_sha256: "96ee2db24b29c1aa065e9e2e91dfc4302f4818225104b50a30924333d14f07cf"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "1e173f6301fab652424a5b10c733aa336e0fbe41b91ef99a26dd35a86e2de1dc"
---

# Verified Claims — Pednault et al. (IBM, 2019), "Leveraging Secondary Storage to Simulate Deep 54-qubit Sycamore Circuits"

The IBM contestation of Arute et al. (2019)'s classical-runtime estimate. Quotes read
from the downloaded full text (arXiv:1910.09534) and confirmed verbatim against
`literature/extracted/pednault_2019.txt`. This is the source for the statement that
Google's "10,000 years" classical estimate was contested.

## Claim 1: The rebuttal — the same task is classically simulable "in a matter of days", not 10,000 years

> "Our analysis shows that on the Summit supercomputer at Oak Ridge National Laboratories, such circuits can be simulated with high fidelity to arbitrary depth in a matter of days, outputting all the amplitudes."

**ID:** rebuttal-days-not-years
**Location:** Abstract
**Addresses:** speedup-robustness
**Rebuts:** arute_2019:200s-vs-10000-years (grounded by #rebuttal-days-not-years) [rec: pednault-rebuts-supremacy-apt]

---

## Claim 2: The quantified estimate — approximately 2.5 days for the 53-qubit Sycamore circuit

> "for 20 cycles of the entanglement pattern ABCDCDAB, which is specifically designed to challenge classical simulation algorithms, we estimate that the computations would take approximately two and a half days."

> "we obtain an overall estimate of 2.55 days to compute all 2⁵³ amplitudes of a 20-cycle, 53-qubit, Sycamore ABCDCDAB circuit with all amplitudes stored on disk, and 5.80 days for the corresponding 54-qubit circuit."

**ID:** quantified-2.55-days
**Location:** §1 Introduction; §"performance model" (Tabs. 1 and 2)
**Addresses:** speedup-robustness

---

## Claim 3: Honest caveat — the estimate was modelled, not executed (and it does MORE than Google's task)

> "While we did not carry out these computations, we provide a detailed description of the proposed simulation strategy as well as the time estimation methodology, which is based on published results and on internal benchmarks."

**ID:** modelled-not-executed-caveat
**Location:** §1 Introduction. NB: the classical task here outputs *all amplitudes* with high fidelity — a strictly harder task than Google's noisy sampling — so the two runtimes are not a like-for-like comparison; this nuance must be stated in the review.
**Addresses:** speedup-robustness
