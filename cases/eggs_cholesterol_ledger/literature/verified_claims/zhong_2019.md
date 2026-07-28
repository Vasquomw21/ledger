---
paper: "Zhong et al. (2019)"
title: "Associations of Dietary Cholesterol or Egg Consumption With Incident Cardiovascular Disease and Mortality"
doi: "10.1001/jama.2019.1572"
pmcid: "PMC6439941"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC6439941/"
source_version: "published (JAMA 2019; PMC author manuscript)"
file: "literature/zhong_2019.html"
retrieved: "20260613"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "35c7202169629d86a200137891a73bf697b449a3de4d76cfb5aab1e1c8a233ff"
extract_sha256: "31f7d3a8e8b8c864217f41dafd5c5aa36f80cff36a974f6150b51fb61995d701"
body_sha256: "1cae3e0f735472bbf6427ba9afa3f78731fac40b8597215726000a295dcf7b45"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "35c7202169629d86a200137891a73bf697b449a3de4d76cfb5aab1e1c8a233ff"
---

# Verified Claims — Zhong et al. (2019)

Each quote was read from the PMC HTML and grep-verified against the extracted text. This is the
positive-association (harmful) position — a pooled US-cohort analysis finding a dose-response
association between dietary cholesterol / egg consumption and CVD. It pools the same six harmonised
US cohorts later re-analysed by Zhong 2021 (ARIC, CARDIA, CHS, FHS, FOS, MESA).

## Claim 1: dietary cholesterol / egg consumption is associated with higher CVD risk

> "Among US adults, higher consumption of dietary cholesterol or eggs was significantly associated with higher risk of incident CVD and all-cause mortality in a dose-response manner."

**ID:** cholesterol-eggs-harmful
**Location:** Abstract (Conclusions)
**Grep command used:** `grep "in a dose-response manner" extracted/zhong_2019.txt`
**Addresses:** eggs-cvd
**Supports:** zhao_2022:harmful-mortality (grounded by #cholesterol-eggs-harmful)
**Rebuts:** drouin_2020:no-association-overall (grounded by #cholesterol-eggs-harmful) [rec: zhong-rebuts-drouin-apt]
