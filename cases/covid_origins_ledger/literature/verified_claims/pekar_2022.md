---
paper: "Pekar et al. (2022)"
title: "The molecular epidemiology of multiple zoonotic origins of SARS-CoV-2"
doi: "10.1126/science.abp8337"
pmcid: "PMC9348752"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9348752/"
source_version: "published"
file: "literature/pekar_2022.html"
retrieved: "20260614"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "b7904887109aade9205bd59a26896a214d90fda8b40639e92fad53dcfabe178e"
extract_sha256: "97910a3d6132b28a57fe57867c6eb9ea883f579be67e3c2993fb0a7d5fd1654d"
body_sha256: "8edb212d646a16867df29842dbfb1356b74499d675ca616ce297e05bd0cebea1"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "b7904887109aade9205bd59a26896a214d90fda8b40639e92fad53dcfabe178e"
---

# Verified Claims — Pekar et al. (2022)

Each quote was read from the downloaded PMC HTML and grepped against the extracted
text. This is the **molecular-epidemiology** anchor for the origin-locus
sub-question: the early genomic diversity implies more than one introduction.

## Claim 1: pre-February-2020 diversity comprised two distinct lineages A and B

> "We show that SARS-CoV-2 genomic diversity before February 2020 likely comprised only two distinct viral lineages, denoted A and B."

**ID:** two-lineages
**Location:** Abstract / Results summary
**Grep command used:** `grep "two distinct viral lineages" extracted/pekar_2022.txt`
**Addresses:** origin-locus

---

## Claim 2: the pandemic most likely began with at least two separate zoonotic transmissions

> "the pandemic most likely began with at least two separate zoonotic transmissions starting in November 2019."

**ID:** multiple-introductions
**Location:** Discussion
**Grep command used:** `grep "two separate zoonotic transmissions" extracted/pekar_2022.txt`
**Addresses:** origin-locus
**Supports:** andersen_2020:no-lab-scenario (grounded by #multiple-introductions) [rec: pekar-supports-nolab-apt]
