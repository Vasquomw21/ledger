---
paper: "Craig Gidney & Martin Ekerå (2021)"
title: "How to factor 2048 bit RSA integers in 8 hours using 20 million noisy qubits"
doi: "10.22331/q-2021-04-15-433"
url: "https://doi.org/10.22331/q-2021-04-15-433"
source_version: "Quantum 5, 433"
file: "literature/gidney_2021.html"
retrieved: "20260603"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "a6284a7b2aaf4af88973eb027f14d229691489783305fba2860c1f794535ecf0"
extract_sha256: "dae17f6d6a9ca303ec61ce36dc5efceaefe322cb4d116710fbf86c794ffc2901"
body_sha256: "9c89dacd2add25b02cc8f80f1c69d7a5d6d62c596fca6847cb27e5c2d77f1ef3"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "a6284a7b2aaf4af88973eb027f14d229691489783305fba2860c1f794535ecf0"
---

# Verified Claims — Gidney & Ekerå (2021), "How to factor 2048-bit RSA…"

Quotes read from the downloaded open-access *Quantum* version of record and
confirmed verbatim against `literature/extracted/gidney_2021.txt`. This paper is
the canonical concrete resource estimate for the cryptographic quantum threat —
it puts a number on Shor's algorithm against real RSA.

## Claim 1: A concrete resource estimate for breaking RSA-2048 with Shor's algorithm

> "How to factor 2048 bit RSA integers in 8 hours using 20 million noisy qubits"

**ID:** resource-estimate
**Location:** Title
**Addresses:** crypto-threat

---

## Claim 2: The estimate combines known speed-ups under explicit hardware assumptions

> "We significantly reduce the cost of factoring integers and computing discrete logarithms in finite fields on a quantum computer by combining techniques from Shor 1994, Griffiths-Niu 1996, Zalka"

> "We estimate the approximate cost of our construction using plausible physical assumptions for large-scale superconducting qubit platforms: a planar grid of qubits with nearest-neighbor connectivity"

**ID:** hardware-assumptions
**Location:** Abstract
**Addresses:** crypto-threat
