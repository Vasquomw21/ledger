---
last_review: 20260614
reviewer: van_songhai
---

# Semantic health

A mechanically-clean wiki can still be intellectually stale: contradictions
between notes, claims overtaken by newer sources, and gaps where a concept is
referenced but never grounded are NOT caught by the citation/provenance gates.
This file is the tracked record of the last semantic pass. `ledger_doctor` nudges
— non-fatally — when it is missing or its `last_review` is stale; it never blocks
a commit.

Review of 20260614 covered all seven ledgers, the Q1/Q2 inquiry, the claim graph,
the four assessment records, and the calibration note (performed while building
the dependency structure: every claim read, every edge resolved, the double-count
checked by hand against the code).

## Unresolved contradictions

_None unresolved._ The substantive tension — Plaga (2008) vs Giddings & Mangano —
is **captured, not open**: `plaga_2008:evades-exclusion` rebuts
`giddings_2008:astro-bound`, and `giddings_reply_2008:scenario-inconsistent`
rebuts back. The exchange is recorded as edges, so the disagreement is navigable
rather than silently resolved or silently ignored.

## Stale sources

The corpus is 2008–2009 (plus the 1946 precedent). The conclusion has not been
overturned since, but the *endorsement base* has grown (see Missing sources). No
ingested claim is contradicted by a newer source; none is marked stale.

## Concept gaps

The **Hawking-evaporation branch** (`lsag_2008:bh-hawking-decay`) is referenced as
one arm of the safety disjunction but is grounded only from the review's own text,
not from Hawking (1975). This is deliberate and is the point of the Q2 finding (the
popularly-cited arm is theoretical/unobserved), but it remains a grounding gap —
tracked in the source register's Known gaps.

## Missing sources / perspectives

- **Hawking (1975)** — the evaporation derivation; would let the graph carry the
  Hawking arm from its origin.
- **The LSAG sub-cases** (strangelets, vacuum bubbles, magnetic monopoles) — the
  review is a portfolio of sub-arguments; only the black-hole sub-case is modelled.
- **Post-2011 endorsement / update layer** — the captured baseline surfaces the
  endorsing physics societies, Nobel-laureate statements, and later reviews that
  this 2008–2009 corpus has not ingested. They strengthen the consensus but do not
  change the dependency structure; named here so the breadth gap is visible.

---

_Mechanical gates being green does not mean the knowledge base is current; this
pass records the human read behind that claim for 20260614._
