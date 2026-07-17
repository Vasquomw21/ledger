---
paper: "Weissman (2024)"
title: "An Inconvenient Probability v5.6 — Bayesian analysis of the probable origins of Covid"
url: "https://michaelweissman.substack.com/p/an-inconvenient-probability-v50"
source_version: "published"
file: "literature/weissman.html"
retrieved: "20260614"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "f012610800dc69e462f6f4f134566869e5b8623c917598a15b0531045031cfe9"
extract_sha256: "2f328367cb002436b127c811585fe84a8cde8cc51ca594d11e4f92a20d42a5d7"
body_sha256: "a05c99c889fef99209a298601063ba3b76172ccfcd4ef4452ff69c13d4f04f00"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260717"
extract_source_sha256: "f012610800dc69e462f6f4f134566869e5b8623c917598a15b0531045031cfe9"
---

# Verified Claims — Weissman (2024)

The lab-leak-leaning Bayesian voice. Michael Weissman's "An Inconvenient Probability" reaches a
posterior strongly favouring laboratory origin — the symmetric counterpart to the zoonosis-leaning
analyses (Daniel, GoodJudgment). Extracted under the `probabilistic-analysis` source-type.

## Claim 1: the posterior — point estimate strongly favours lab leak

> "Combining that likelihood ratio with the point estimate of the prior logit would still give extreme odds, P(LL)/P(ZW) = ~66,000."

**ID:** posterior-ll
**Location:** Bottom-line odds
**Grep command used:** `grep "P(LL)/P(ZW) = ~66,000" extracted/weissman.txt`
**Addresses:** prior-odds

---

## Claim 2: the qualitative conclusion — odds strongly favour LL

> "the conclusion that the odds strongly favor LL just means that prior guesses that LL was highly improbable should be ignored in the future."

**ID:** odds-favor-ll
**Location:** Conclusion
**Grep command used:** `grep "the odds strongly favor LL" extracted/weissman.txt`
**Addresses:** methodology
**Rebuts:** stansifer:verdict (grounded by #odds-favor-ll)

---

## Claim 3: the prior — Wuhan location leaves the two origins comparable

> "the start in Wuhan where the suspect lab work was concentrated left the two possibilities with comparable probabilities."

**ID:** prior-comparable
**Location:** Introduction
**Grep command used:** `grep "left the two possibilities with comparable probabilities" extracted/weissman.txt`
**Addresses:** prior-odds
