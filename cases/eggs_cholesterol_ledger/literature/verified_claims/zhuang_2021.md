---
paper: "Zhuang et al. (2021)"
title: "Egg and cholesterol consumption and mortality: the NIH-AARP Diet and Health Study"
doi: "10.1371/journal.pmed.1003508"
pmcid: "PMC7872242"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC7872242/"
source_version: "published (PLoS Med 2021, open access)"
file: "literature/zhuang_2021.html"
retrieved: "20260614"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "3a3fc2ad8440757803d7c07ca38f346d208b2d48d5d83431e1fc693aed5ead6c"
extract_sha256: "e3bb210cd26ad7139f351727ba6b6f972df32b1ff3e03a1af4dbef5a6574e599"
body_sha256: "ead726e9336c5fb431821792e3154dcdaef8770d69cf2bbbf1e1239ab4a23981"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "3a3fc2ad8440757803d7c07ca38f346d208b2d48d5d83431e1fc693aed5ead6c"
---

# Verified Claims — Zhuang et al. (2021)

US population-based prospective cohort (NIH-AARP Diet and Health Study) examining egg and cholesterol intake against all-cause, CVD, and cause-specific mortality. An independent cohort — distinct from NHANES, WHI, and the 6-cohort pool — so it is genuine non-overlapping evidence.

## Claim 1: study population / data source
> "we assessed the associations of egg and dietary cholesterol intake with all-cause and cause-specific mortality in the NIH-AARP Diet and Health Study"
**ID:** cohort-nih-aarp
**Location:** Methods
**Grep command used:** `grep "in the NIH-AARP Diet and Health Study" extracted/zhuang_2021.txt`
**Addresses:** eggs-cvd

## Claim 2: eggs and cholesterol linked to higher mortality
> "In this study, intakes of eggs and cholesterol were associated with higher all-cause, CVD, and cancer mortality."
**ID:** egg-cholesterol-higher-mortality
**Location:** Abstract (Conclusions)
**Grep command used:** `grep "intakes of eggs and cholesterol were associated with higher all-cause, CVD, and cancer mortality" extracted/zhuang_2021.txt`
**Addresses:** eggs-cvd
**Supports:** zhao_2022:harmful-mortality (grounded by #egg-cholesterol-higher-mortality)
