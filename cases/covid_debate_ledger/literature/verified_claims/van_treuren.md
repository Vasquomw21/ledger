---
paper: "van Treuren (2024)"
title: "Rootclaim covid-19 origins debate: judge's written decision"
url: "https://drive.google.com/file/d/1YhmkYB32RpGsXvQTsX4xZ0Yul1wiwh8Z/view"
source_version: "published"
file: "literature/van_treuren.pdf"
retrieved: "20260614"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "a3840e689ba567bfc44f6cbc0533f48bd7c52e60506dff295e752eb3edbdff31"
extract_sha256: "427b1abc2a7a53ca115e7ad948175d8244c6805b6598e10980ae3f4dcd0cdd3b"
body_sha256: "f42b80522f1c4ea4115eba4ad73b86dc7a9ec0a09d2f9fd69223b4f8e2dde13f"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260614"
---

# Verified Claims — van Treuren (2024)

The second adjudicator's voice. Will van Treuren, the other debate judge (a microbiologist),
also ruled for the zoonosis side. Extracted under the `adjudication` source-type. The source PDF
extracts with collapsed word-spacing, but `verify_quotes` strips whitespace before matching, so
the verbatim spans below (written with correct spacing, as authored) verify against the extract.

## Claim 1: the ruling — zoonotic origin substantially more likely

> "I find that SARS-CoV-2 is substantially more likely to be of zoonotic origin than a product of intentional engineering."

**ID:** verdict
**Location:** §1 ("What did I decide?")
**Grep command used:** `grep "substantially more likely to be of zoonotic origin" extracted/van_treuren.txt`
**Addresses:** verdict

---

## Claim 2: Peter (zoonosis) presented the superior case

> "I believe that Peter, for the zoonosis side, presented the superior case, and is the winner of the debate."

**ID:** superior-case
**Location:** §1 ("What did I decide?")
**Grep command used:** `grep "presented the superior case" extracted/van_treuren.txt`
**Addresses:** verdict
**Supports:** stansifer:verdict (grounded by #superior-case)

---

## Claim 3: the reason — internal inconsistency in the lab-leak case

> "I ended up being more skeptical of the evidence that LL provided for two reasons. First, there were multiple instances of internal inconsistency."

**ID:** ll-inconsistency
**Location:** §2 (evidence assessment)
**Grep command used:** `grep "more skeptical of the evidence that LL provided" extracted/van_treuren.txt`
**Addresses:** methodology

---

## Claim 4: the third section used the lab-leak side's own Bayesian method

> "Section 3 summarizes the evidence and arguments of each side through the Bayesian analysis method preferred by the LL side."

**ID:** bayesian-section
**Location:** Summary
**Grep command used:** `grep "Bayesian analysis method preferred by the LL side" extracted/van_treuren.txt`
**Addresses:** methodology
