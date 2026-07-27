---
paper: "Darooghegi Mofrad et al. (2022)"
title: "Egg and Dietary Cholesterol Intake and Risk of All-Cause, Cardiovascular, and Cancer Mortality: A Systematic Review and Dose-Response Meta-Analysis of Prospective Cohort Studies"
doi: "10.3389/fnut.2022.878979"
pmcid: "PMC9195585"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9195585/"
source_version: "published (Front Nutr 2022, open access)"
file: "literature/darooghegi_2022.html"
retrieved: "20260614"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "96e1b1b07f4306a5c27c4bb8d009946e140a1c62146be96cc33f1a30c7f14deb"
extract_sha256: "391327e110f7a602127387e79829f9a9fb2039869acf7b2d7e43888933a9f897"
body_sha256: "2a60132ec43d1b67e841bd6cd966b960aa775207d1b38b46ea448e979806681f"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260614"
---

# Verified Claims — Darooghegi Mofrad et al. (2022)

Each quote was read from the PMC HTML and grep-verified against the extracted text. A dose–response
meta-analysis that **explicitly identifies and removes overlapping-cohort duplicate publications**
(naming HPFS, NHANES, CHNS) — the second, sharper methodological control: it de-duplicates the very
HPFS family that Drouin (2020) re-pools, and reaches a non-null conclusion.

## Claim 1: overlapping-cohort duplicate publications were identified and excluded

> "we found studies with significant participant overlap"

> "the Health Professionals Follow-Up Study (HPFS)"

> "Since these studies reported risk estimates for similar exposure and outcome variables, we included only the one with higher quality or with the highest number of cases and excluded the duplicate publications"

**ID:** overlap-excluded
**Location:** Results — study selection (PRISMA narrative)
**Grep command used:** `grep "participant overlap" extracted/darooghegi_2022.txt`
**Addresses:** eggs-cvd

---

## Claim 2: high egg/cholesterol intake associated with all-cause and cancer mortality (above thresholds)

> "High-dietary intake of eggs and cholesterol was associated with all-cause and cancer mortality. Little evidence for elevated risks was seen for intakes below 0.5 egg/day or 250 mg/day of dietary cholesterol."

**ID:** harmful-above-threshold
**Location:** Abstract (Conclusions and Relevance)
**Grep command used:** `grep "all-cause and cancer mortality" extracted/darooghegi_2022.txt`
**Addresses:** eggs-cvd
