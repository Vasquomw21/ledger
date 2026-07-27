---
paper: "Daniel (2024)"
title: "Daniel's Bayesian analysis of COVID origins"
url: "https://docs.google.com/document/d/1qzLC55jRfdS55oSqXJZTFItsvFsawWgNlgLxWqhCuyo/edit"
source_version: "published"
file: "literature/daniel.html"
retrieved: "20260614"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "1fc057ae3181e65c4496a2bfce69e4c379592f244e0220d688db3b975025ba36"
extract_sha256: "089df72e43c4067f92ff8a3585fb624ffb52ccca96487d0bcfedb409a883167d"
body_sha256: "b9c4eeec8eed56d0b0a9a8eed0b1e338c75f54007234613820b2ad4508815608"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260614"
---

# Verified Claims — Daniel (2024)

A spectator's Bayesian write-up of the debate (the Google Doc Alexander links). Extracted under
the `probabilistic-analysis` source-type (named (hypothesis, probability) estimates). The
zoonosis-leaning counterpart to Weissman's lab-leak analysis. **Locus:** lines bind each claim to
a unit in `literature/units/daniel.units.json` (the committed coordinate system).

## Claim 1: the posterior — ~96% zoonosis

> "I get 96% zoonosis (not 98% as in an early tweet)."

**ID:** zoonosis-posterior
**Locus:** p2
**Location:** tl;dr
**Grep command used:** `grep "I get 96% zoonosis" extracted/daniel.txt`
**Addresses:** prior-odds

---

## Claim 2: the prior favours lab leak slightly before evidence

> "So p(lab leak in Wuhan in 2020) = 1 / (4 * 6 * 100 * 2) = 1 / 5,000 So: prior ratio is 1:5"

**ID:** prior-ratio
**Location:** Priors section
**Grep command used:** `grep "prior ratio is 1:5" extracted/daniel.txt`
**Addresses:** prior-odds

<!-- No **Locus:** — this quote SPANS two enumerated units (the per-factor prior lines and the
"So: prior ratio is 1:5" summary are separate blocks in the manifest), so no single locus contains
it. An honest, visible limitation of the coordinate system: a cross-unit quote is left off the grid
rather than mis-addressed. -->

---

## Claim 3: the market location is the biggest update, and the biggest disagreement

> "NB: this is by far my biggest disagreement with Rootclaim."

**ID:** market-hsm
**Locus:** p14
**Location:** "First known outbreak is centred at HSM"
**Grep command used:** `grep "by far my biggest disagreement with Rootclaim" extracted/daniel.txt`
**Addresses:** market-evidence
**Supports:** stansifer:proximity (grounded by #market-hsm)

---

## Claim 4: the furin cleavage site cuts only mildly toward lab leak

> "FCS is great: you do expect messing around with cleavage sites under DEFUSE. But you also could see this in nature."

**ID:** fcs-factor
**Locus:** p38
**Location:** "FCS insert with CGGs"
**Grep command used:** `grep "you do expect messing around with cleavage sites under DEFUSE" extracted/daniel.txt`
**Addresses:** genomic-engineering

---

## Claim 5: the analyst's own methodological caveat

> "you should be aware that I haven’t actually read the primary literature here."

**ID:** caveat-unread
**Locus:** p3
**Location:** Note (preamble)
**Grep command used:** `grep "haven.t actually read the primary literature here" extracted/daniel.txt`
**Addresses:** methodology
