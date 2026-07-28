---
paper: "Segreto & Deigin (2021)"
title: "The genetic structure of SARS-CoV-2 does not rule out a laboratory origin"
doi: "10.1002/bies.202000240"
pmcid: "PMC7744920"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC7744920/"
source_version: "published"
file: "literature/segreto_2021.html"
retrieved: "20260613"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "9652d815423ce5ffce6579914d406ae3f46346858eca13ac99e6470c26871a11"
extract_sha256: "41ecce69e239abf076f9e7cd5fe32e7ac1169c90a8621ec54ee7593059b0759f"
body_sha256: "3ed6a633fe9785751dc7acad16e02b5892fcaff254c5e5f1af97ac8c7f3990c6"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "9652d815423ce5ffce6579914d406ae3f46346858eca13ac99e6470c26871a11"
---

# Verified Claims — Segreto & Deigin (2021)

Each quote was read from the downloaded PMC HTML and grep-verified against the
extracted text. This is the engineering-leaning side of the FCS sub-question; it
explicitly engages Andersen et al. (2020).

## Claim 1: a laboratory origin cannot be excluded

> "a possible synthetic origin by laboratory engineering of SARS‐CoV‐2 cannot be excluded."

**ID:** lab-origin-not-excluded
**Location:** Discussion
**Grep command used:** `grep "cannot be excluded" extracted/segreto_2021.txt`

---

## Claim 2: the FCS might derive from genetic manipulation

> "The perfect binding ability of SARS‐CoV‐2 to human cells and the presence of the furin cleavage site, which is new for SARS‐like coronaviruses, might derive from genetic manipulation performed during evolutionary studies."

**ID:** fcs-implies-engineering
**Location:** Abstract / Introduction
**Grep command used:** `grep "might derive from genetic manipulation" extracted/segreto_2021.txt`
**Addresses:** fcs-engineering

---

## Claim 3: the FCS was previously unseen in other SARS-like CoVs

> "The furin cleavage site in the spike protein of SARS‐CoV‐2 confers to the virus the ability to cross species and tissue barriers, but was previously unseen in other SARS‐like CoVs."

**ID:** fcs-previously-unseen
**Location:** Abstract
**Grep command used:** `grep "previously unseen" extracted/segreto_2021.txt`
**Correlated-with:** andersen_2020:fcs-unique-to-sars2 (grounded by #fcs-previously-unseen) [shared premise: the FCS is unseen in related CoVs — both sides lean on the same rarity observation]

---

## Claim 4: site-directed mutagenesis would leave no trace

> "Both cleavage site and specific RBD could result from site‐directed mutagenesis, a procedure that does not leave a trace."

**ID:** mutagenesis-no-trace
**Location:** Introduction
**Grep command used:** `grep "does not leave a trace" extracted/segreto_2021.txt`
**Rebuts:** andersen_2020:not-from-known-backbone (grounded by #mutagenesis-no-trace)
