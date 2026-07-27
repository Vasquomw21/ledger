---
paper: "Goldberg et al. (2014)"
title: "Egg consumption and carotid atherosclerosis in the Northern Manhattan Study"
doi: "10.1016/j.atherosclerosis.2014.04.019"
pmcid: "PMC4136506"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC4136506/"
source_version: "published (Atherosclerosis 2014)"
file: "literature/goldberg_2014.html"
retrieved: "20260614"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "2dbc684ba4c0a30bf28ad7924caf952270e7bc3c87771908ddc0320fc5731ac0"
extract_sha256: "5efd94122dde98ee8e6a7903bbeb88813268c3a6f08a229f3d7177fb78573942"
body_sha256: "00e9194ed21a306eaed157bb1dfe6552b7ecbe00b3edb1ad5462f6538de6e4de"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260614"
---

# Verified Claims — Goldberg et al. (2014)

A single independent cohort (the Northern Manhattan Study, a multi-ethnic urban population)
reporting an inverse relationship between egg consumption and carotid atherosclerosis and no
association with clinical vascular events.

## Claim 1: study cohort / population

> "NOMAS is a prospective cohort study designed to determine stroke incidence, risk factors, and prognosis in a multi-ethnic urban population."

**ID:** cohort-nomas
**Location:** Methods
**Grep command used:** `grep "NOMAS is a prospective cohort study designed to determine stroke incidence" extracted/goldberg_2014.txt`
**Addresses:** eggs-cvd

## Claim 2: egg consumption inversely related to atherosclerosis, no event association

> "the results of this study showed an inverse relationship between the frequency of egg consumption in the low to moderate range and several markers of carotid atherosclerosis, and no association with clinical vascular events, including stroke."

**ID:** eggs-inverse-atherosclerosis-nomas
**Location:** Abstract (Conclusions)
**Grep command used:** `grep "an inverse relationship between the frequency of egg consumption in the low to moderate range" extracted/goldberg_2014.txt`
**Addresses:** eggs-cvd
