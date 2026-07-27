---
paper: "Godos et al. (2021)"
title: "Egg consumption and cardiovascular risk: a dose–response meta-analysis of prospective cohort studies"
doi: "10.1007/s00394-020-02345-7"
pmcid: "PMC8137614"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC8137614/"
source_version: "published (Eur J Nutr 2021, open access CC-BY)"
file: "literature/godos_2021.html"
retrieved: "20260614"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "210a81d9a040b9ea774c9d40dd9d684985b87eef17ebd0c5033402b32332b7ba"
extract_sha256: "74c94e13d2c0576edbf11dfa98208b5d5241c859f8489809c5797a822533b479"
body_sha256: "b5552bb8f91ce0fd115efabde30d7a7e8052d257981ffb19231184a854dbda4b"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260614"
---

# Verified Claims — Godos et al. (2021)

Each quote was read from the PMC HTML and grep-verified against the extracted text. A dose–response
meta-analysis that **explicitly de-duplicates overlapping cohorts** and reaches a hedged conclusion —
one of the two methodological controls for the cohort-overlap finding.

## Claim 1: studies on the same cohort were de-duplicated (one dataset kept per cohort)

> "If more than one study was conducted on the same cohort, only the dataset including the larger number of individuals, the longest follow-up, or the most comprehensive data"

**ID:** dedup-method
**Location:** Methods — study selection / inclusion criteria
**Grep command used:** `grep "same cohort" extracted/godos_2021.txt`
**Addresses:** eggs-cvd

---

## Claim 2: no conclusive evidence on the role of egg in CVD risk

> "There is no conclusive evidence on the role of egg in CVD risk"

**ID:** no-conclusive-evidence
**Location:** Abstract (Conclusion)
**Grep command used:** `grep "no conclusive evidence" extracted/godos_2021.txt`
**Addresses:** eggs-cvd
