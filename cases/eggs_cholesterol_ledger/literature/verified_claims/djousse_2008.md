---
paper: "Djoussé & Gaziano (2008)"
title: "Egg consumption and risk of heart failure in the Physicians' Health Study"
doi: "10.1093/ajcn/87.4.964"
pmcid: "PMC2386667"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC2386667/"
source_version: "published (Am J Clin Nutr 2008)"
file: "literature/djousse_2008.html"
retrieved: "20260614"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "1448697033fec00df229ecb7db6f6b549fda0cb17ef0c9c3b4cc6fd6bbf6e9bf"
extract_sha256: "e8a0020caeac240a5debdf1b7f6b0ed58cc8fd8e5051179bcf012fd7e67560ee"
body_sha256: "ff480162e8c1d7183aaae3529fb9099747e5fa2e40304c4a612d4c1c8826c6d2"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "1448697033fec00df229ecb7db6f6b549fda0cb17ef0c9c3b4cc6fd6bbf6e9bf"
---

# Verified Claims — Djoussé & Gaziano (2008)

A single independent cohort (the Physicians' Health Study I, US male physicians) reporting that
infrequent egg consumption does not influence CVD risk while frequent consumption confers a modest
mortality increase.

## Claim 1: study cohort / population

> "The current project used data from the Physicians' Health Study (PHS) I, which was a randomized, double-blind, placebo-controlled trial using a 2×2 factorial design to study low-dose aspirin and beta-carotene for the primary prevention of cardiovascular disease and cancer among US male physicians."

**ID:** cohort-phs
**Location:** Methods
**Grep command used:** `grep "which was a randomized, double-blind, placebo-controlled trial using a" extracted/djousse_2008.txt`
**Addresses:** eggs-cvd

## Claim 2: infrequent eggs do not influence CVD; only a modest mortality increase

> "Our data suggest that infrequent egg consumption does not influence the risk of CVD and only confers a modest increased risk for total mortality in male physicians."

**ID:** eggs-modest-mortality-phs
**Location:** Abstract (Conclusions)
**Grep command used:** `grep "Our data suggest that infrequent egg consumption does not influence" extracted/djousse_2008.txt`
**Addresses:** eggs-cvd
