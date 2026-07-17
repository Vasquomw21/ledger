# Finding — COVID-19 origins

The most-targeted claim in this graph is (Andersen 2020 #no-lab-scenario) — three
`supports` edges are aimed at it, more than at any other claim. Its verbatim text is "we do
not believe that any type of laboratory-based scenario is plausible": a statement of belief,
not a result. The stored quotation preserves that distinction for review. The verbatim gate
(`verify_quotes.py`) proves what Andersen wrote; the faithfulness layer is what exposes a
stronger paraphrase — "Andersen et al. ruled out a lab origin" reads as a faithful summary
while promoting a belief into a demonstrated finding.

## The question

Two sub-questions ([[inquiry]]): does the furin cleavage site indicate engineering (Q1),
and does the early evidence locate the origin at the market (Q2)?

## What the machinery surfaces

The three support edges should not be read automatically as three independent lines of
evidence. (Worobey 2022 #market-early-epicenter) is contested by a sealed faithfulness
record [rec: worobey-faithfulness]: its quote locates where early cases clustered, while the
claim it supports is a modal statement about mechanism. (Pekar 2022 #multiple-introductions)
is declared correlated-with Worobey, so Ledger warns that the two support edges may not be
independent. (Temmam 2022 #banal-infectious-humans) rests on a different line, hACE2 entry
by sampled bat relatives, and its aptness was adversarially reviewed and held
[rec: temmam-supports-nolab-apt-pass]. Of the three, one support edge is disputed and two
form a marked correlated pair.

Andersen's certainty language is flagged where it outruns its argument: [rec: andersen-irrefutably]
marks "irrefutably show" on (Andersen 2020 #not-from-known-backbone) — see `ledger inspect
assessments` — as asserting a certainty that an absence-of-known-backbone argument cannot carry.

## What this does not show

This says nothing about whether SARS-CoV-2 had a laboratory origin, and does not show
Andersen's belief to be wrong. The natural-origin case rests on far more evidence than the
five sources here. What is auditable is narrower: in this corpus, the graph's most-targeted
no-lab claim is framed as a belief statement; one of its three support edges is disputed,
and two form a marked correlated pair. Correlation marks possible dependence — it does not
establish that two edges collapse into one, and no sealed assessment here makes that
collapse. The machinery displays these judgements; it does not settle them.
