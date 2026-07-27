---
paper: "Worobey et al. (2022)"
title: "The Huanan Seafood Wholesale Market in Wuhan was the early epicenter of the COVID-19 pandemic"
doi: "10.1126/science.abp8715"
pmcid: "PMC9348750"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9348750/"
source_version: "published"
file: "literature/worobey_2022.html"
retrieved: "20260614"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "debf0de11f3b51f0c002108481b3a1a506c8e9e993bb6bf7e344ec65aaa393a8"
extract_sha256: "08d653c7323a6b31d44ec64033361245f8e202b6e99e7121b19cf990c747b548"
body_sha256: "80033a6ecdcf41e73557b9d819009fd70d8ade6210587f4afdaac1c2a1c54fd6"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260614"
---

# Verified Claims — Worobey et al. (2022)

Each quote was read from the downloaded PMC HTML and grepped against the extracted
text. This is the **spatial-epidemiology** anchor for the origin-locus sub-question
(zoonotic emergence at the market vs an introduced point source).

## Claim 1: the Huanan market was the early epicenter; emergence via the live wildlife trade

> "our results provide evidence that the Huanan market was the early epicenter of the COVID-19 pandemic and suggest that SARS-CoV-2 likely emerged from the live wildlife trade in China."

**ID:** market-early-epicenter
**Location:** Discussion / concluding summary
**Grep command used:** `grep "early epicenter of the COVID-19 pandemic" extracted/worobey_2022.txt`
**Addresses:** origin-locus
**Supports:** andersen_2020:no-lab-scenario (grounded by #market-early-epicenter) [rec: worobey-supports-nolab-apt]
**Correlated-with:** pekar_2022:multiple-introductions (grounded by #market-early-epicenter)

---

## Claim 2: live susceptible mammals were sold at the market and spatially associated with positive samples

> "live SARS-CoV-2 susceptible mammals were sold at the market in late 2019 and, within the market, SARS-CoV-2-positive environmental samples were spatially associated with vendors selling live mammals."

**ID:** live-mammals-spatial
**Location:** Abstract / Results summary
**Grep command used:** `grep "susceptible mammals were sold" extracted/worobey_2022.txt`
**Addresses:** origin-locus

---

## Claim 3: the epicenter hypothesis is a spatial prediction about where early cases fall

> "We hypothesized that if the Huanan market epicenter of the pandemic then early cases should fall not just unexpectedly near to it but should also be unexpectedly centered on it"

**ID:** epicenter-spatial-test
**Location:** Results — spatial analysis
**Grep command used:** `grep "unexpectedly centered on it" extracted/worobey_2022.txt`
**Addresses:** origin-locus
