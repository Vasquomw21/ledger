---
paper: "Alexander (2024)"
title: "Practically-A-Book Review: Rootclaim $100,000 Lab Leak Debate"
url: "https://www.astralcodexten.com/p/practically-a-book-review-rootclaim"
source_version: "published"
file: "literature/alexander_2024.html"
retrieved: "20260614"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "1ad43d4178162b502095bbf4231b9327d01968a14617bfbb9895d41ccb99de0e"
extract_sha256: "12507e956703249903005906059ca1056a1d5642150c0f357e82cd190e955d66"
body_sha256: "4b70718cfb2b148e055e052e65b9dbe9f86692405c6b74b398d9043379db18a5"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260614"
---

# Verified Claims — Alexander (2024)

The popular-synthesis voice: Scott Alexander watched the full Rootclaim debate and wrote it up.
Extracted under the `essay` source-type (low structure → the convergence residual is expected to be
higher here than for the judge decisions). Each quote was grepped verbatim from the downloaded post.

## Claim 1: both judges decided for the zoonosis side

> "Both judges decided in favor of Peter."

**ID:** judges-favoured-peter
**Location:** §VI (the verdict)
**Grep command used:** `grep "Both judges decided in favor of Peter" extracted/alexander_2024.txt`
**Addresses:** verdict

---

## Claim 2: the adjudication was itself probabilistic

> "Both judges included a probabilistic analysis in their written decision."

**ID:** judges-used-probability
**Location:** §VI (the verdict)
**Grep command used:** `grep "included a probabilistic analysis" extracted/alexander_2024.txt`
**Addresses:** verdict

---

## Claim 3: the market's positive samples cluster where the wildlife was sold

> "The southwest corner is where most of the wildlife was being sold."

**ID:** wildlife-southwest-corner
**Location:** §III (the market evidence)
**Grep command used:** `grep "southwest corner is where most of the wildlife" extracted/alexander_2024.txt`
**Addresses:** market-evidence

---

## Claim 4: the market is the load-bearing Bayesian update, and a fragile one

> "I started with a 10,000x Bayes factor on the market, but it was extremely lightly considered and not really adjusted for out-of-model error."

**ID:** market-bayes-factor
**Location:** §V (Alexander's own analysis)
**Grep command used:** `grep "10,000x Bayes factor on the market" extracted/alexander_2024.txt`
**Addresses:** market-evidence

---

## Claim 5: the methodological lesson — strict Bayesian aggregation overreached

> "I think Saar has two options: Abandon the Rootclaim methodology, and go back to normal boring impure reasoning like the rest of us, where you vaguely gesture at Bayesian math but certainly don’t try anything as extreme as actually using it."

**ID:** abandon-or-fix-rootclaim
**Location:** §VII (the lesson)
**Grep command used:** `grep "Abandon the Rootclaim methodology" extracted/alexander_2024.txt`
**Addresses:** methodology

---

## Claim 6: losing the bet is not the same as the method being pseudoscience

> "I think the zoonosis side has plenty of things to feel bad about (eg the conspiracies), but pseudoscience probably isn’t the right descriptor."

**ID:** zoonosis-not-pseudoscience
**Location:** §VII (the lesson)
**Grep command used:** `grep "pseudoscience probably isn" extracted/alexander_2024.txt`
**Addresses:** methodology
