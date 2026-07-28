---
paper: "Andersen et al. (2020)"
title: "The proximal origin of SARS-CoV-2"
doi: "10.1038/s41591-020-0820-9"
pmcid: "PMC7095063"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC7095063/"
source_version: "published"
file: "literature/andersen_2020.html"
retrieved: "20260613"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "a916f055010de149f7b2945528c92ffb66e1d1e5f869727f93fe614588abc3c1"
extract_sha256: "1cacda4735368fcd0ca655b8a3c5fc2e2875e180ce1529be9f4c756058a24839"
body_sha256: "df7236e2f7194089dd50650fa6ab26f258fbadea3f9253c258738afa5b44ce03"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "a916f055010de149f7b2945528c92ffb66e1d1e5f869727f93fe614588abc3c1"
---

# Verified Claims — Andersen et al. (2020)

Each quote was read from the downloaded PMC HTML, grepped against the extracted
text, and confirmed in context. This is the natural-origin anchor for the
furin-cleavage-site (FCS) sub-question.

## Claim 1: SARS-CoV-2 is not a laboratory construct

> "Our analyses clearly show that SARS-CoV-2 is not a laboratory construct or a purposefully manipulated virus."

**ID:** not-laboratory-construct
**Location:** Abstract / opening summary
**Grep command used:** `grep "laboratory construct" extracted/andersen_2020.txt`

---

## Claim 2: SARS-CoV-2 is not derived from a known virus backbone

> "Furthermore, if genetic manipulation had been performed, one of the several reverse-genetic systems available for betacoronaviruses would probably have been used"

> "However, the genetic data irrefutably show that SARS-CoV-2 is not derived from any previously used virus backbone"

**ID:** not-from-known-backbone
**Location:** "Theories of SARS-CoV-2 origins" section
**Grep command used:** `grep "virus backbone" extracted/andersen_2020.txt`
**Assess-rhetorical:** "irrefutably show" — asserts a certainty an absence-of-known-backbone argument cannot carry; the data are consistent with, not proof against, undocumented engineering (grounded by #not-from-known-backbone) [rec: andersen-irrefutably]

---

## Claim 3: a polybasic (furin) cleavage site can arise by natural evolution

> "the polybasic cleavage site can arise by a natural evolutionary process"

**ID:** fcs-natural-process
**Location:** "Theories of SARS-CoV-2 origins" section
**Grep command used:** `grep "natural evolutionary process" extracted/andersen_2020.txt`
**Addresses:** fcs-engineering
**Rebuts:** segreto_2021:fcs-implies-engineering (grounded by #fcs-natural-process)
**Crux-of:** fcs-engineering (grounded by #fcs-natural-process) [if-resolved: whether FCS apparent rarity implies design rather than under-sampling]

---

## Claim 4: the FCS and its O-linked glycans are unique to SARS-CoV-2 among lineage B

> "Both the polybasic cleavage site and the three adjacent predicted O-linked glycans are unique to SARS-CoV-2 and were not previously seen in lineage B betacoronaviruses."

**ID:** fcs-unique-to-sars2
**Location:** "Notable features of the SARS-CoV-2 genome" section
**Grep command used:** `grep "unique to SARS-CoV-2" extracted/andersen_2020.txt`

---

## Claim 5: no laboratory-based scenario is considered plausible

> "we do not believe that any type of laboratory-based scenario is plausible"

**ID:** no-lab-scenario
**Location:** "Theories of SARS-CoV-2 origins" section
**Grep command used:** `grep "laboratory-based scenario" extracted/andersen_2020.txt`
