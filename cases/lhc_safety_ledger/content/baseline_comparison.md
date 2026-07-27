# Head-to-head — a web-research baseline vs the Ledger artefact

One question, two ways of holding it. The question: **Is the LHC safe from creating a dangerous
black hole, and what is that conclusion based on?** This case is framed as *probing the
argument for its dependencies and weakest points* — so the test is not "what is the answer" (both
agree: safe) but "does the artefact let a reader see what the answer rests on."

**How the baseline was produced (so this is reproducible, not asserted).** A strong web-search-grounded
survey answer was captured verbatim at [[baseline_research_raw]]
([`baseline_research_raw.md`](baseline_research_raw.md)), with an honest provenance header (it is a
fair strong-survey opponent, not a commercial deep-research product, and not blind). The comparison
below quotes only that captured output and this corpus's own stamped quotes.

## A. What the baseline does well

The baseline is **good**, and any honest comparison starts there. It correctly states the consensus,
lays out *both* arms of the argument (Hawking evaporation and the cosmic-ray / white-dwarf /
neutron-star bound), gets the Giddings & Mangano structure right (including the
captured-vs-fast-moving-black-hole loophole and how the dense-star argument closes it), and is
**broader and more current** than this seven-source ledger — it surfaces the endorsing physics
societies, the Nobel-laureate statements, and the legal-injunction history, none of which the corpus
has ingested. A reader who wants a fluent, correct, current survey is well served by it.

## B. The measured delta

Same question, scored on what each artefact lets a reader actually *do* with the argument. Each
Ledger cell points to a mechanically-checkable object in this repo, not a promise.

| What the reader can do | Web-research baseline | Ledger artefact |
|---|---|---|
| **Re-check any claim to source** | No — the argument is paraphrased; you trust the summary or re-read the papers | **Yes** — every claim is a stamped verbatim quote; `ledger verify` re-proves the bytes on disk (locally) |
| **See which arm is load-bearing** | Presents Hawking + cosmic-ray as "two main pillars", additively, as if mutually reinforcing | **Yes** — Q2 (`arg-structure`) + the graph show a **disjunction**: Hawking (`lsag_2008:bh-hawking-decay`) is an *isolated node* (theoretical, unobserved, grounds nothing), so the worst-case arm rests **entirely** on the conditional `giddings_2008:astro-bound` crux |
| **See that the "independent" confirmations aren't** | Lists LSAG, Giddings, Koch and societies as a stack of endorsements | **Yes** — the derived **double-count finding fires**: Koch (which says "we independently present" a safety argument) shares Giddings' white-dwarf/neutron-star evidence base; record `koch-giddings-correlated` judges it not a fully independent confirmation |
| **Find the exact inference under challenge** | Does not mention that any step is contested | **Yes** — `plaga_2008:evades-exclusion` **rebuts** `giddings_2008:astro-bound`; the reply rebuts back. The crux is shown as contested-then-answered, not silently settled |
| **Tell confidence-in-conclusion from confidence-in-rhetoric** | States the LHC is "completely safe" | **Yes** — rhetorical records pin the categorical framing (`giddings-whatsoever` on "no risk of any significance whatsoever"; `cern-perfectly-safe` on the public FAQ's mechanism-free "would be perfectly safe"); the calibration note holds 0.97→0.95, conclusion not rhetoric |
| **Connect to how such questions were reasoned before** | No historical precedent | **Yes** — LA-602 (1946 #further-work-desirable) ingested as a *calibration analogue*: it reached a reassuring bottom line yet flagged "the absence of satisfactory experimental foundations" (`la602_1946:further-work-desirable`) |
| **Breadth / recency of the corpus** | **Broader** — societies, Nobel laureates, the injunction case, later updates | **Narrower by design** — seven sources; those are *declared* as gaps, not hidden |

## C. Where the baseline wins — stated plainly

The baseline is **broader and more current** than this scoped ledger. On a settled question, a fluent
survey is a perfectly good tool, and the baseline is one. Ledger does not claim to know more; it
claims that what it holds is *verifiable, structured, and interrogable* — and, specifically for this
case, that it makes the argument's **dependency structure** legible in a way the survey does not.

## D. The uplift, and why it survives the baseline being good

The brief asked, for this case, to *probe the argument for its dependencies and weakest points*. The
baseline answers "is it safe?" well; it does not answer "what does the safety rest on, and where is
it conditional?" The Ledger artefact does, and **none of it requires trusting the model**: the quotes
are verbatim on disk, the disjunction is in the graph (`tools/analyze_graph.py`), the double-count is
derived by code, the contested crux is a resolvable edge, the categorical framing is pinned to sealed
records. We **do not claim** the structural point itself is a discovery — *that the Hawking arm is not
load-bearing and the worst case rests on the conditional bound* is stated in the primary sources'
own framing (Giddings & Mangano's title; the LSAG abstract's two-tier "if some were stable…"). The
uplift is narrower and honest: Ledger makes that known-but-popularly-flattened dependency
**mechanically checkable and contestable** (`giddings_2008:astro-bound`, the `plaga`↔reply edges, the
`koch-giddings-correlated` record), where a fluent survey states the reassurance and moves on.

## E. Curated pointers (start here)

- The inversion, in one place: `content/inquiry.md` §Q2 + `python3 tools/analyze_graph.py` (the
  Hawking claim is referenced by no edge — it grounds nothing in `content/graph.json`; `astro-bound`
  is the load-bearing crux).
- The finding the code found on its own: the double-count line in `analyze_graph.py` / `check_assessment.py`
  (Giddings ↔ Koch), and record `koch-giddings-correlated`.
- The honesty boundary, made concrete: `literature/verified_claims/la602_1946.md` — a degraded 1946
  scan where the system quotes only what verifies and refuses to reconstruct the OCR-garbled tail.
- The calibration: `content/assessments/safety_calibration.md` (conclusion 0.95, not the rhetoric's 1.0).
