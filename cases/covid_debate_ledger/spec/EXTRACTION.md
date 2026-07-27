# Ledger extraction method — v0.1

**Status:** versioned, tool-independent. The step-by-step human-AI workflow that turns a raw text
base into Ledger claim ledgers (the Markdown grammar of `INTERCHANGE.md` §2), **near-deterministically
and without fabrication**. `INTERCHANGE.md` specifies the *output*; this specifies the *process* that
produces it. Any agent — or a person — can run it, and two runs converge.

The problem it solves: the verbatim gate (`verify_quotes.py`) guarantees no claim is *fabricated*, but
*which* spans become claims has been ad-hoc judgement — not reproducible, not portable across corpus
types. This method makes selection a defined procedure anchored to two fixed coordinates, so a second
run (or a second person, with different beliefs) picks up where the first left off.

## The two anchors

Determinism comes from anchoring selection to coordinates **external to the reader**:

- **Anchor A — the source's own structure.** A claim's unit is the source's smallest addressable unit
  that *asserts* something — and what that unit is depends on the source type (the table below).
  Atomisation is source-driven, not reader-chosen.
- **Anchor B — the inquiry's sub-questions** (`content/inquiry.md`, the `**id:**` lines). A candidate
  unit becomes a claim **iff** it bears on a declared sub-question.

Selection is therefore source-driven (A) and question-driven (B), never vibe-driven. The one
non-mechanical step is the Anchor-B filter ("does this unit bear on a sub-question?"); it is bounded
and **measured** (§Reproducibility).

## Who authors Anchor B (inquiry provenance)

Anchor B is the highest-leverage, least-constrained input in the whole method: the sub-question tree
frames what the corpus is *about*, and unlike the address and the span it is not mechanised. So its
**origin is recorded, not assumed**. `content/inquiry.md` carries a frontmatter block:

```
---
authored_by: ai            # ai | human — who drafted the question tree
generated_by: claude       # the drafting model, when authored_by: ai
generated_date: 20260614
reviewed_by:               # operator identity once a human has vetted it
status: draft              # draft | reviewed
---
```

**The default is `authored_by: ai`, `status: draft`.** Drafting the inquiry is a good default job for
the model — a non-expert operator often does not know what to ask, and an AI-drafted tree gives them a
starting point to react to. An expert may instead author or overwrite it (`authored_by: human`). Either
way the frame is a **committed, diffable fact**: a judge or a forking operator sees at a glance whether
the questions were model-drafted and whether a human has reviewed them, and `git log` shows every
subsequent edit. This is the same move as the source provenance stamp — it does not make the frame
*correct*, it makes its authorship *transparent and contestable*. Promotion to `status: reviewed`
requires a `reviewed_by`. The block is advisory metadata; the structure gate reads the `**id:**` lines,
not the frontmatter.

## The procedure (one source per run)

1. **Acquire + extract** — `fetch_paper.sh` → `extract_text.py` (the existing intake, unchanged).
2. **Pick the source-type row** — from `source_types:` in `ledger.config.md`, or by inspection. If no
   row fits, **STOP and ask**; never guess a structure.
3. **Enumerate units** (Anchor A) — walk the source by its row's structural unit; each asserting unit
   is a candidate with a **locus** (its structural address).
4. **Filter** (Anchor B) — keep a candidate iff it bears on a declared `**id:**` sub-question; drop the
   rest (out of scope, not wrong).
5. **Lift** — copy the **verbatim** span into a `> "…"` blockquote; derive `**ID:**` from the locus
   (§Slug); set `**Location:**` to the locus; add `**Addresses:** <qid>`; route to the ledger named by
   the row's attribution (**one ledger per voice**).
6. **Verify** — run `verify_quotes.py`; a span that is not verbatim is dropped or re-lifted, **never
   paraphrased**. Fidelity is the existing guarantee; this method adds selection only.
7. **Propose, don't apply** — present the ledgers for human approval; the write-time hook, pre-commit,
   and CI are the mechanical floor.

## Source-type table (Anchor A)

The procedure is universal; only the row changes. Attribution reuses the existing
**one-ledger-per-source** model, so "who said it" is the ledger key — no new field.

| Source type | Structural unit (a candidate) | Attribution → ledger key | Slug locus |
|---|---|---|---|
| `journal-paper` | a finding/conclusion in Abstract/Results/Discussion | the authors → `<author>_<year>` | `<section>-<n>` |
| `news` | a sentence asserting a fact, with its in-text source | the article → `<outlet>_<year>` | `p<para>-<n>` |
| `debate-transcript` | a speaker turn's distinct asserted position | the speaker → `<speaker>` | `t<turn>-<n>` |
| `adjudication` | a numbered finding/conclusion of a ruling | the adjudicator → `<judge>` | `finding-<n>` |
| `probabilistic-analysis` | a named `(hypothesis, probability)` estimate | the analyst → `<analyst>` | `<hyp>-p<n>` |
| `essay` | the thesis sentence of each argued point (low structure → paragraph) | the author → `<author>` | `p<para>-<n>` |
| `legislation` | an operative clause/section | the instrument → `<instrument>` | `s<section>-<n>` |

A new corpus type is a new row — added explicitly, not improvised. The taxonomy stays small for the
same reason the edge taxonomy does (bloat is a generalisability risk and a gaming surface).

## Slug derivation (deterministic)

`**ID:**` is **derived** from the unit's locus, not chosen: fill the row's slug-locus template from the
unit's structural address, lower-case it, collapse any non-`[a-z0-9-]` to `-`. Two runs that select the
same unit derive the **same slug** — which is what makes claim-set agreement a true measure of
selection convergence, and what makes the slug stable under reorder (unlike the ordinal `cN`).

## Reproducibility (measured)

The method is *near*-deterministic: Anchor A and the slug are deterministic; the Anchor-B filter is
judgement. `tools/repro.py` (`ledger repro <run-A>/ <run-B>/`) measures convergence between two runs
over the same source:

- **selection agreement** — Jaccard over the lifted **spans** (each normalised the way the
  verbatim gate normalises), keyed by voice. This is the naming-INDEPENDENT measure: did both runs
  lift the same span, regardless of the slug each chose for it?
- **claim-set agreement** — Jaccard over the derived `**ID:**` slugs. This adds the slug-naming
  layer on top of selection, so it can *under*-count (same span, different slug) AND *over*-count
  (same slug on different spans); read it against selection agreement, never alone.
- **sub-question coverage match** — agreement on which `**id:**`s have ≥1 claim;
- **attribution match** — of the shared slugs, the fraction landing in the same ledger key;
- **residual** — the slugs in exactly one run: the bounded disagreement, **named**.

The three convergence numbers form a hierarchy from coarse to fine: **coverage** (same sub-questions)
≥ **selection** (same spans) ≥ **claim-set** (same spans, same slugs). Measured across the worked
cases, coverage converges robustly while selection and claim-set are only moderate — two honest runs
agree on *what the corpus is about* far more than on *which exact sentence* carries a finding or
*what to call it*. That is the real shape of the near-determinism: strong at the finding level,
bounded at the span/slug level.

Run the method twice (two models, or one model + a re-ordered source) and report the tuple. A
structured source (`adjudication`, `journal-paper`) converges tightly; a low-structure `essay`
converges less. Determinism is a function of source structure, and the method declares the residual
where structure runs out.

## Coordinate addressing (determinism enforced, not just measured)

The reproducibility numbers above exposed the gap: free-form slug derivation leaves the *address* a
reader choice, so two runs that select the same unit still disagree on its name (and on which exact
span to quote). The fix makes the address **mechanical** by giving each source a committed
**coordinate system**.

- **Enumerate** (`tools/enumerate_units.py`): parse the **raw** source and emit a committed manifest
  `literature/units/<key>.units.json` — every structural unit with an **absolute locus** (e.g. `p3`,
  `page2-p1`), its verbatim text, and a content hash, sealed by `manifest_sha256` and bound to the
  source `source_sha256`. The enumerator is pure: same bytes → byte-identical manifest (`--check`
  self-tests this). It emits the candidate *universe* only; it never applies keep/drop.
- **Address by locus**: a claim carries `**Locus:** <locus>` and its `**ID:**` *is* that locus. The
  slug is no longer chosen — collapsing the slug-naming layer to zero.
- **Bound span**: the quote must be a verbatim span *within* the addressed unit. `tools/check_units.py`
  (posture `units_layer: off|warn|required`, default off) attests this **offline** against the
  committed manifest (the raw source is git-ignored, so the manifest carries the unit text). Span
  choice is thus decoupled from identity: a different pithy quote of the same unit is the same claim.
- **Measure what's left**: `repro.py` reports `locus_agreement` (Jaccard over `key:locus`). With the
  address mechanical, this isolates the **one** irreducible judgement — Anchor-B keep/drop. On the
  worked `covid_debate` HTML sources it rose from `claim_agreement` 0.05 (free slug) to **0.98**
  locus-keyed; the residual was a single kept/dropped unit plus sub-question attribution — genuine
  judgement, isolated from naming noise.

**Limits.** The coordinate system mechanises the *address* and *span*; **unit boundary** is
mechanical only where the source is structurally parseable. Clean HTML enumerates fully; a
collapsed-space PDF degrades to coarse `page-p` loci and sets `fully_enumerable: false`, which
downgrades any `required` finding to a warning — the gate never blocks on structure it cannot read. A
quote that legitimately **spans** two units is left off the grid (no `**Locus:**`) rather than
mis-addressed. The manifest is a committed write-time attestation: CI attests it, it does not re-parse
raw bytes — the same local-vs-CI boundary as the provenance stamp.

## What this does NOT change

Fidelity is `verify_quotes.py`, untouched: every span is lifted verbatim and gate-checked; nothing is
summarised or composed. This adds selection, not a second fidelity path. Determinism is bounded and
measured, not identity. The method guarantees *form and provenance* and names the judgement it
cannot mechanise (`INTERCHANGE.md` §8).
