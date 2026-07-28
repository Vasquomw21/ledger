---
paper: "John Jumper, Richard Evans, Alexander Pritzel, et al. (2021)"
title: "Highly accurate protein structure prediction with AlphaFold"
doi: "10.1038/s41586-021-03819-2"
url: "https://doi.org/10.1038/s41586-021-03819-2"
source_version: "Nature 596, 583–589; PMC8371605"
file: "literature/jumper_2021.pdf"
retrieved: "20260603"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "6eae057a9faf4f671c3101e0745ed704460c6d3dec77243dfd3a9f2d2ab68970"
extract_sha256: "fa8492ee46782c16c17516209080ae2ebbe6f7b98ef412b9fae8d2ee95479d8d"
body_sha256: "a6f131bea778a18f3f1d9dc46c20adfcd5ba9a3ad06885502823efd9000d25eb"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "6eae057a9faf4f671c3101e0745ed704460c6d3dec77243dfd3a9f2d2ab68970"
---

# Verified Claims — Jumper et al. (2021), "Highly accurate protein structure prediction with AlphaFold"

The classical deep-learning breakthrough that substantially solved practical protein structure
prediction — essential context for the honest protein-folding verdict. Quotes read from the
downloaded full text (Europe PMC PDF, PMC8371605) and confirmed verbatim against
`literature/extracted/jumper_2021.txt`.

## Claim 1: A classical method predicts structure with atomic accuracy, even without a homologous template

> "Here we provide the first computational method that can regularly predict protein structures with atomic accuracy even in cases in which no similar structure is known."

**ID:** alphafold-atomic-accuracy
**Location:** Abstract.
**Addresses:** qc-genomics-advantage

---

## Claim 2: The accuracy is near-experimental and far ahead of competitors (CASP14)

> "AlphaFold structures had a median backbone accuracy of 0.96 Å r.m.s.d.95 ... whereas the next best performing method had a median backbone accuracy of 2.8 Å r.m.s.d.95"

**ID:** casp14-accuracy-lead
**Location:** Results (p. 584).
**Addresses:** qc-genomics-advantage

---

## Claim 3: The motivation — experimental structure determination is a slow bottleneck

> "Structural coverage is bottlenecked by the months to years of painstaking effort required to determine a single protein structure."

**ID:** experimental-bottleneck
**Location:** Abstract.
**Addresses:** qc-genomics-advantage
