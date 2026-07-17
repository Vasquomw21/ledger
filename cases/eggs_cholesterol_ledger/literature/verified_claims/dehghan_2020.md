---
paper: "Dehghan et al. (2020)"
title: "Association of egg intake with blood lipids, cardiovascular disease, and mortality in 177,000 people in 50 countries"
doi: "10.1093/ajcn/nqz348"
pmcid: "PMC7138651"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC7138651/"
source_version: "published (Am J Clin Nutr 2020; PMC author manuscript)"
file: "literature/dehghan_2020.html"
retrieved: "20260613"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "064717cf0a1e4f2631fab4a759314c49870f906dfad0dc4ffd79ae3dfc34045b"
extract_sha256: "90134cfe4b55709a75d9340012827ce3c0fb00bdaa71226797fc1c2205fac820"
body_sha256: "2ffd39f8c61071d2c14ce2b74086095e6fbde7da97206d35f802fbf96ed91458"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "064717cf0a1e4f2631fab4a759314c49870f906dfad0dc4ffd79ae3dfc34045b"
---

# Verified Claims — Dehghan et al. (2020), PURE study

Each quote was read from the PMC HTML and grep-verified against the extracted text. A large
multinational (PURE) analysis finding no association — a second null-finding cohort that supports
the meta-analytic null and directly rebuts the positive-association cohort.

## Claim 1: moderate egg intake is not associated with CVD or mortality

> "we found that moderate egg intake (1/d) was not associated with an increased risk of mortality or major CVD"

**ID:** pure-no-association
**Location:** Discussion (conclusion)
**Grep command used:** `grep "not associated with an increased risk of mortality or major CVD" extracted/dehghan_2020.txt`
**Addresses:** eggs-cvd
**Supports:** drouin_2020:no-association-overall (grounded by #pure-no-association)
**Rebuts:** zhong_2019:cholesterol-eggs-harmful (grounded by #pure-no-association)
