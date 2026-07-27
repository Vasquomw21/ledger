---
paper: "CERN — Frequently Asked Questions"
title: "Will CERN generate a black hole?"
url: "https://home.cern/resources/faqs/will-cern-generate-black-hole"
source_version: "home.cern FAQ, archived 2026-03-13 (Wayback id_ snapshot 20260313145713)"
file: "literature/cern_faq.html"
retrieved: "20260614"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "1db53ce37a016b1902dac2748f76c69f77b58d51163fb5a7d97a73ef9d49d5b3"
extract_sha256: "3e9509610e1a86c260e1644d309c7fa79b53b545b2603812b12a1a057faf6e53"
body_sha256: "2135d100de11b3098547e04ed2fbaad352a788e23614b41417acf3cabd16d90d"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260614"
---

# Verified Claims — CERN public FAQ, "Will CERN generate a black hole?"

The competition's LHC starting material links the CERN FAQ as the **public-facing** answer. The
page the URL now resolves to is a generic LHC landing page, so the exact resource was captured from
the Wayback Machine snapshot of the URL the brief linked (the `id_` form, original bytes, no archive
toolbar). It matters here as the *public* voice in the dependency structure: what a non-expert reader
is actually told, versus what does the load-bearing work in the technical literature.

## Claim 1: a cosmological black hole is ruled out; only tiny "quantum" ones are even hypothesised

> "The LHC will not generate black holes in the cosmological sense. However, some theories suggest that the formation of tiny 'quantum' black holes may be possible."

**ID:** quantum-bh-possible
**Location:** FAQ answer body
**Grep command used:** `grep "cosmological sense" extracted/cern_faq.txt`
**Addresses:** lhc-bh-risk

---

## Claim 2: the categorical public assurance — "perfectly safe" — with no mechanism given

> "The observation of such an event would be thrilling in terms of our understanding of the Universe; and would be perfectly safe."

**ID:** perfectly-safe
**Location:** FAQ answer body
**Grep command used:** `grep "perfectly safe" extracted/cern_faq.txt`
**Addresses:** lhc-bh-risk
**Correlated-with:** lsag_2008:no-associated-risks (grounded by #perfectly-safe) [the public FAQ restates the LSAG conclusion as a bare assurance and defers the entire basis to a linked "More information" report — it shares LSAG's conclusion node, it is not independent evidence for it]
**Assess-rhetorical:** "would be perfectly safe" — a categorical public assurance that states *no* mechanism (not Hawking evaporation, not the astrophysical bound) and routes the reader to a linked report; it performs reassurance while the load-bearing argument lives elsewhere (grounded by #perfectly-safe) [rec: cern-perfectly-safe]
