---
paper: "Temmam et al. (2022)"
title: "Bat coronaviruses related to SARS-CoV-2 and infectious for human cells"
doi: "10.1038/s41586-022-04532-4"
url: "https://www.nature.com/articles/s41586-022-04532-4"
source_version: "published"
file: "literature/temmam_2022.html"
retrieved: "20260614"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "56cc6616fa3478be4eb1c9fecd9169222d8c385728f2a07b506bb91c4c3a47fe"
extract_sha256: "11094db3937d81c37f9644b751d65b520a2ac3d4de038518c07472bad1b56c25"
body_sha256: "86c000be0b1e78e6ce0c2d081669a090cea8117f8c7dcf92bf4606c9f8e7bf4e"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260614"
---

# Verified Claims — Temmam et al. (2022)

Each quote was read from the downloaded Nature HTML and grepped against the
extracted text. This is the **closest-natural-relatives** source: the BANAL bat
coronaviruses bear on the FCS-rarity crux (the nearest sampled relatives still
lack the cleavage site) and on natural-spillover plausibility.

## Claim 1: none of the closest bat relatives carries a furin cleavage site

> "None of these bat viruses contains a furin cleavage site in the spike protein."

**ID:** no-fcs-in-relatives
**Location:** Results / discussion of the BANAL spike
**Grep command used:** `grep "furin cleavage site in the spike protein" extracted/temmam_2022.txt`
**Addresses:** fcs-engineering
**Qualifies:** andersen_2020:fcs-natural-process (grounded by #no-fcs-in-relatives)

---

## Claim 2: BANAL bat viruses enter and replicate in human cells via hACE2

> "mediate hACE2-dependent entry and replication in human cells"

**ID:** banal-infectious-humans
**Location:** Results — hACE2 entry assays
**Grep command used:** `grep "hACE2-dependent entry and replication" extracted/temmam_2022.txt`
**Addresses:** origin-locus
**Supports:** andersen_2020:no-lab-scenario (grounded by #banal-infectious-humans)
