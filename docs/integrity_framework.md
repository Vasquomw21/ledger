# Knowledge-Work Failure Modes — the Ledger integrity framework

The lens for what Ledger **guarantees**, **assists**, and **leaves to the user**. This is the full
version of the five-layer summary in [`../DEMO.md`](../DEMO.md) §4.

## What this is for

Ledger is a research toolkit for people and AI working together. It keeps a growing knowledge base
tied to its evidence: every citation in gated, authored prose must point to a quotation checked
against the original source, while the claims, their connections, and human judgements remain
visible and reviewable.

Ledger does not establish that the sources are complete, the reasoning is sound, or the conclusion
is true. When the source files are unavailable, it attests the committed proof rather than
re-checking the bytes.

Trustworthiness is not one property — knowledge work fails in several distinct ways, and a tool can
only honestly claim to address the ones it actually catches. This document is the map: the classes
of failure, ordered as a dependency chain, crossed with how strongly each can be caught. Every
claim Ledger makes about itself is scoped to a specific cell of this map.

Two axes structure it:

- **The hierarchy** — five integrity layers, foundation to delivery. Each only matters if the
  layers beneath it hold; a failure low in the stack poisons everything above it.
- **Detectability** — how strongly a failure in a layer can be caught, from a mechanical guarantee
  down to nothing at all.

**Enforcement strength is inversely
correlated with how far up the stack you go.** The most foundational failure is the most
mechanically checkable; the higher-order failures — which depend on the lower ones being right —
are progressively matters of judgement.

## The five layers (foundation → delivery)

1. **Fidelity** — does each atom faithfully represent its source? If the quotes are wrong, nothing
   above survives. This is bedrock.
2. **Completeness** — do you have the *right* atoms? No critical source missing, no biased
   selection of which sources entered the corpus.
3. **Coherence** — are the atoms correctly *related*? Connected where they should be, no silent
   contradictions, nothing stale or duplicated.
4. **Validity** — do the *conclusions* drawn over the atoms actually follow from them?
5. **Clarity** — does the reader receive the result intact?

## Detectability levels

- **Guarantee** — mechanical and deterministic; the failure cannot pass. (e.g. a fabricated quote
  is blocked by `verify_quotes.py`.)
- **Structural** — code catches a structural proxy but not the meaning. (e.g. an orphan wikilink
  is found; whether the missing link *should* exist is not judged.)
- **Assisted** — an LLM / semantic pass surfaces candidates; detection probability is below one and
  a human confirms. (e.g. a contradiction between two notes.)
- **Measured** — an Assisted detector's hit-rate is *quantified* on a hand-labelled benchmark, so
  the "detection probability below one" is a number with its residual, not a hope. (e.g. the
  out-of-context detection rate from `faithfulness_eval.py`; the extraction convergence from
  `repro.py`.) Measurement reports how good the assistance is; it does not upgrade it to a guarantee.
- **Judgement** — a human applies a rule inside the writing loop; no automation. (e.g. the
  bored-reader readability test.)
- **Uncovered** — nothing addresses it.

## Coverage matrix

| Layer | Representative failure modes | What Ledger does | Strength |
|---|---|---|---|
| **1. Fidelity** | fabricated quote · wrong paper fetched · quote mined out of context | `verify_quotes.py` (fabrication) · `fetch_paper.sh` `validate()` (wrong paper) · claim-ID granularity (right paper, right claim) · `faithfulness_probe.py` + `kind: faithfulness` dispute records (out-of-context) · `faithfulness_eval.py` (a measured detection rate on a benchmark) | **Guarantee** for fabrication; Structural for wrong-paper; **Measured + Assisted** for out-of-context |
| **2. Completeness** | selection bias in the corpus · missing key source · concept mentioned but never noted | `check_selection.py` (no silent empty position) · `lint_wiki.py` (uncatalogued notes) · curate semantic pass | Structural + Assisted; selection audit is a **floor against silent one-sidedness**, not a representativeness proof |
| **3. Coherence** | non-connection · contradiction between notes · stale claim · duplication | `check_structure.py` (edges resolve + grounded) · `lint_wiki.py` (orphans, dead links) · curate semantic pass | Structural (links) + Assisted (meaning) |
| **4. Validity** | unsupported inference · cherry-picking within the corpus · misweighting consensus vs fringe | `analyze_graph.py` (load-bearing claims, dependency closure, double-counts — read-only assistance) · assessment records (crux, calibration, correlated-with) · bored-reader discipline | **Judgement, with assistance — the frontier** |
| **5. Clarity** | opacity (reader can't follow on first pass) · undefined jargon | bored-reader test (G0) · skin rule: define on first use | Judgement, enforced in the loop |

## What the matrix exposes

- **One hard guarantee exists, at the bottom layer.** Even there it covers only
  *fabrication*. A verbatim quote of a strawman that the source then demolishes passes the gate
  cleanly — the words are real, the use is not. That is the honest ceiling of "no fabricated
  citations": it certifies the words were said, not that they were used faithfully. Claim-ID
  granularity narrows this (a cite binds to a specific quoted claim, so it can no longer point at a
  paper for a claim it has no quote for); the **adversarial-faithfulness mechanism** narrows it
  further — `faithfulness_probe.py` walks every inference and a reviewer files a sealed,
  quote-pinned `faithfulness` **dispute** where the grounding quote does not warrant the inference,
  so out-of-context use moves from Uncovered to **Assisted**. `faithfulness_eval.py` then takes one
  step further — it *measures* how reliably a blind detector catches out-of-context misuse on a
  class-balanced hand-labelled benchmark (a confusion matrix + recall/specificity), moving the seam
  to **Measured + Assisted** (see [`faithfulness_eval.md`](faithfulness_eval.md)). None of this
  proves the prose's *interpretation* is faithful — faithful use stays judgement (the dispute is a
  recorded challenge, the rate is a detector's hit-rate on a starter benchmark, neither is a
  verdict). The ceiling is lowered and now quantified, not removed.
- **The two most damaging failures are nearly uncovered.** Selection bias (layer 2) and unsupported
  inference (layer 4) are worse than a fabricated quote because they are *invisible*: every
  individual citation checks out, yet the corpus is skewed or the conclusion does not follow. For
  serious research these are where the real risk lives. Ledger's answers here are a *floor*
  (selection audit) and *assistance* (`analyze_graph.py`), not guarantees.
- **Ledger over-invests at the two ends and is building out the middle-top.** Fidelity has a
  guarantee; Clarity has an enforced discipline; Coherence is now structurally checked (the claim
  graph) plus assisted; Validity is the active frontier (assessment records + read-only analysis).

## What this means for design and naming

- **The standalone tool is layer 1.** Unbundling the gate isolates the one cell that is a guarantee. Its narrow claim is
  *no fabricated citations*, with the out-of-context caveat. The shared coverage
  checker (`tools/check_citations.py`) runs that gate at all three enforcement points; the verbatim
  check (`verify_quotes.py`) is digit-strict; numeric citation styles are detected-and-warned, not
  silently passed.
- **The wiki and curation machinery are Ledger's layer 2–3 instruments**, and the authoring
  discipline is its layer 5 instrument. They are separate, weaker instruments aimed at separate,
  harder failures — aids, not guarantees.
- **The frontier is layer 4 (Validity).** Almost no tool checks whether a conclusion follows from
  its cited evidence, and it is the failure that matters most. Any move to make Ledger more than a
  fidelity guarantee aims here — accepting that the result is an *assisted* check, not a guarantee.

## What Ledger claims

Against the map:

- **Guarantees:** no claim reaches gated, authored prose carrying a quotation that is not
  verbatim in a primary source on disk (layer 1, fabrication). `gated_paths` declares that scope;
  archived third-party material, such as a captured model transcript, is not gated.
- **Assists:** surfacing missing notes, broken or absent connections, contradictions, and stale
  claims for a human to confirm (layers 2–3); the adversarial-faithfulness worklist + dispute
  records for out-of-context use (layer 1, context); read-only validity analysis (layer 4);
  enforcing readability and definition discipline in the writing loop (layer 5).
- **Leaves to the user:** whether the corpus is representative (layer 2, selection bias); the final
  call on whether a quotation is used in keeping with the source's actual position (layer 1,
  context — now adversarially assisted, not settled); and whether the conclusions are warranted by
  the evidence assembled (layer 4).

Only layer-1 fabrication is mechanically prevented. The rest is graded confidence.
