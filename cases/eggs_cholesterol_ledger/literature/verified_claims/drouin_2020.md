---
paper: "Drouin-Chartier et al. (2020)"
title: "Egg consumption and risk of cardiovascular disease: three large prospective US cohort studies, systematic review, and updated meta-analysis"
doi: "10.1136/bmj.m513"
url: "https://doi.org/10.1136/bmj.m513"
source_version: "published (BMJ 2020, open access)"
file: "literature/drouin_2020.html"
retrieved: "20260613"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "a09b08350d42f20eaa1cf257b8c4937e7651a4a5ce3d83aec8a878daac26b075"
extract_sha256: "fe83266b7c0f9ef133c835e1f673ecb28f0f51af7d630540e571a818e02ca843"
body_sha256: "e4778810c5e898e7a578df1da3b16fc5b09507954eb7776d67cc66e9df73eab5"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "a09b08350d42f20eaa1cf257b8c4937e7651a4a5ce3d83aec8a878daac26b075"
---

# Verified Claims — Drouin-Chartier et al. (2020)

Each quote was read from the BMJ HTML and grep-verified against the extracted text. This is the
no-association position and the most recent large meta-analysis — it *performs the settling* of
the question (claims it resolved to a null), which the dissenting cohort (Zhong 2019) contests.

## Claim 1: moderate egg consumption is not associated with CVD risk overall

> "moderate egg consumption (up to one egg per day) is not associated with cardiovascular disease risk overall"

**ID:** no-association-overall
**Location:** Abstract (Conclusions) / Discussion
**Grep command used:** `grep "not associated with cardiovascular disease risk overall" extracted/drouin_2020.txt`
**Addresses:** eggs-cvd
**Crux-of:** eggs-cvd (grounded by #no-association-overall) [if-resolved: whether the positive cohort associations survive adjustment for dietary confounding and study quality]
**Status:** performed-settling

---

## Claim 2: the meta-analysis pooled 27 prior studies plus the current study

> "27 studies (28 including the current study) met inclusion criteria"

**ID:** pooled-28-studies
**Location:** Results — systematic review / meta-analysis
**Grep command used:** `grep "met inclusion criteria" extracted/drouin_2020.txt`
**Addresses:** eggs-cvd

---

## Claim 3: the analysis re-pools the same Harvard cohorts and updates Hu et al. 1999

> "Our analyses included men and women from three large US cohorts: the Nurses' Health Study (NHS), NHS II, and the Health Professionals' Follow-Up Study (HPFS)."

> "Our study is an updated analysis of the study published in 1999 by Hu and colleagues"

**ID:** updates-hu-1999
**Location:** Introduction / Methods
**Grep command used:** `grep "updated analysis of the study published in 1999" extracted/drouin_2020.txt`
**Addresses:** eggs-cvd
**Correlated-with:** dehghan_2020:pure-no-association (grounded by #updates-hu-1999) [shared: the no-association meta-analyses re-pool overlapping observational cohorts — Drouin's own NHS/NHS II/HPFS analysis plus the Hu 1999 update of the same cohorts are counted as separate inputs, with no de-duplication stated]

