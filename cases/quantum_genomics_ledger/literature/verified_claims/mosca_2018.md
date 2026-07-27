---
paper: "Michele Mosca (2018)"
title: "Cybersecurity in an era with quantum computers: will we be ready?"
doi: "10.1109/MSP.2018.3761723"
url: "https://doi.org/10.1109/MSP.2018.3761723"
source_version: "IEEE Security & Privacy 16(5); author version IACR ePrint 2015/1075"
file: "literature/mosca_2018.pdf"
retrieved: "20260603"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "6752a95b970fd0f762967689a8eff0da741078b88dd714c82fee5b027762bdbd"
extract_sha256: "b041b32e4e9566417ec17c28f85e6d735fb1d5b62c8e40a8457db342e54c4cde"
body_sha256: "f74347de1d111e11aa544c29e3e7dcd0afe17134d14c029585c97fc44900ab26"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260615"
---

# Verified Claims — Mosca (2018), "Cybersecurity in an era with quantum computers"

Quotes read from the downloaded author version (IACR ePrint 2015/1075) and
confirmed verbatim against `literature/extracted/mosca_2018.txt`. Ligature glyphs
in the PDF (e.g. "scientific", "five") are rendered as their true words below.
This is the canonical statement of the harvest-now-decrypt-later problem.

## Claim 1: Quantum computing breaks essentially all deployed public-key cryptography

> "Two decades ago, we learned that the quantum paradigm implies that essentially all the deployed public key cryptography will be completely broken by a quantum computer"

**ID:** breaks-deployed-pubkey
**Location:** §1 "The Problem"
**Addresses:** crypto-threat

---

## Claim 2: Mosca's inequality — the harvest-now-decrypt-later theorem (x + y > z)

The threat is framed by three durations: the security shelf-life **x**, the
migration time **y**, and the collapse time **z** (when a quantum computer breaks
today's public-key cryptography).

> "Denote this number by x, the security shelf-life"

> "Denote this number by y, the migration time"

> "Let z denote this number, the collapse time"

> "If x + y > z , we have a serious problem today"

**ID:** harvest-now-decrypt-later
**Location:** §1 "The Problem" (the three questions and the inequality)
**Addresses:** crypto-threat

---

## Claim 3: A dated, quantified estimate of the collapse time for RSA-2048

> "I estimate a 1/7 chance of breaking RSA-2048 by 2026 and a 1/2 chance by 2031."

**ID:** collapse-time-estimate
**Location:** §1 (author's projection; rendered "1=7"/"1=2" in the PDF fractions)
**Addresses:** crypto-threat
