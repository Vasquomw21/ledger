---
paper: "Plaga (2008)"
title: "On the potential catastrophic risk from metastable quantum-black holes produced at particle colliders"
url: "https://arxiv.org/abs/0808.1415"
source_version: "arXiv:0808.1415v3"
file: "literature/plaga_2008.pdf"
retrieved: "20260613"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "0f41a2c1385df8e03d9d05bc23f011aeb03a888836cb02638875db5dfa88260a"
extract_sha256: "ff86331ce9bc8a17f3315b8e4be5de759a0d4fa4d3b3b6ab23bd2e53d141d0ec"
body_sha256: "94c4aca40169f4ec71ddc29bb45883a9a1e5eb79377df5a3f254ab3284e4c338"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260614"
---

# Verified Claims — Plaga (2008)

Each quote was read from the arXiv PDF and grep-verified against the extracted text. This is
the risk-raising counter-position: it argues a scenario exists that the Giddings & Mangano
exclusion does not cover.

## Claim 1: a plausible scenario yields Hawking radiation harmful to Earth

> "these black holes accrete ambient matter at the Eddington limit shortly after their production, thereby emitting Hawking radiation that would be harmful to Earth and/or CERN and its surroundings"

**ID:** harmful-scenario
**Location:** Abstract
**Grep command used:** `grep "harmful to Earth" extracted/plaga_2008.txt`
**Addresses:** lhc-bh-risk

---

## Claim 2: the scenario evades the Giddings & Mangano exclusion

> "Such black holes are shown to remain undetectable in existing astrophysical observations and thus evade a recent exclusion of risks from subnuclear black holes by Giddings & Mangano"

**ID:** evades-exclusion
**Location:** Abstract
**Grep command used:** `grep "evade a recent exclusion" extracted/plaga_2008.txt`
**Rebuts:** giddings_2008:astro-bound (grounded by #evades-exclusion) [rec: plaga-rebuts-astro-apt]
