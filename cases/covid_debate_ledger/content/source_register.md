---
last_updated: 20260614
curator: van_songhai
status: active
---
# Source Register — the recorded Rootclaim COVID-origins debate

Records *why* each source is in the corpus and *how* it was found, names the viewpoints the
debate contains, and lists what is knowingly missing. The `selection_audit` gate (set `required`
here) enforces that every stamped ledger is registered and that **no declared position is left
empty** — covered by a source or named under Known gaps. It does *not* prove the position set is
complete; that judgement is surfaced here and in semantic health, never claimed as proven.

The *case* is the recorded debate, so a "position" is a stance held within it, not a verdict on
the virus. The corpus is built one voice at a time (EXTRACTION.md, one ledger per voice), across
four source-types: `essay` (Alexander), `adjudication` (the two judges), and
`probabilistic-analysis` (the Bayesian write-ups on both sides).

## Positions

The viewpoints the debate's question space contains. Each must be covered by a source below, or
named under Known gaps.

**Position:** zoonosis — the natural-spillover side (Peter Miller); SARS-CoV-2 emerged at the
Huanan live-wildlife market via one or more animal-to-human spillovers. The side both judges
favoured.
**Position:** lab-leak — the laboratory-origin side (Saar Wilf / Rootclaim); the genome and
circumstances are better explained by escape or engineering than by natural spillover.
**Position:** method-critique — the meta-position that the debate's real lesson is about
*reasoning method* (strict Bayesian aggregation vs ordinary expert judgement), independent of
which origin is true.

## Sources

One block per ingested source. `**Source:**` matches a `literature/verified_claims/<key>.md`.

### Alexander (2024) — the synthesis voice (essay)

**Source:** alexander_2024
**Discovery:** the widely-read long-form write-up of the debate (Astral Codex Ten); the entry
point most readers reach the case through, and the source that names the debate's structure
(judges, stake, probabilistic decisions) plainly. It links the judge decisions and the Bayesian
analyses ingested below.
**Rationale:** the popular-synthesis voice — a neutral reviewer who relays the judges' verdict and
the load-bearing market evidence, and contributes the method critique. Ingested under the `essay`
source-type (low structure → a higher convergence residual is expected here).
**Position:** zoonosis
**Position:** method-critique
**Quality:** long-form blog review, not peer-reviewed; cited for the debate's *structure and
outcome* and Alexander's *own* analysis, never as a primary virology source.
**Addresses:** verdict
**Addresses:** market-evidence
**Addresses:** methodology

### Stansifer (2023) — judge 1 (adjudication)

**Source:** stansifer
**Discovery:** linked from Alexander's write-up as the first judge's written decision (Google
Drive PDF); the 83-page "Final decision".
**Rationale:** the primary adjudication voice — a debate judge's own reasoning for ruling, in his
words, rather than relayed through a commentator. Names the load-bearing basis (epidemiological
proximity) and concedes the genomic case was real but insufficient.
**Position:** zoonosis
**Quality:** primary adjudication document, one of the two binding judge decisions.
**Addresses:** verdict
**Addresses:** market-evidence
**Addresses:** genomic-engineering

### van Treuren (2024) — judge 2 (adjudication)

**Source:** van_treuren
**Discovery:** linked from Alexander's write-up as the second judge's written decision (Google
Drive PDF).
**Rationale:** the second binding adjudication, independently reached — a microbiologist's
decision, citing internal inconsistency in the lab-leak case. Pairs with Stansifer to show the
verdict was a consensus of two independent judges.
**Position:** zoonosis
**Quality:** primary adjudication document, one of the two binding judge decisions.
**Addresses:** verdict
**Addresses:** methodology

### Daniel (2024) — spectator Bayesian (probabilistic-analysis)

**Source:** daniel
**Discovery:** linked from Alexander's write-up ("[Daniel] did one too") as one of the spectator
Bayesian analyses; a public Google Doc.
**Rationale:** a zoonosis-leaning Bayesian write-up (~96% zoonosis) with explicit per-factor
likelihood ratios — the structured probabilistic counterpart to Weissman's lab-leak analysis, and
a clean target for the convergence measure.
**Position:** zoonosis
**Quality:** informal spectator analysis (self-described as not having read the primary
literature); cited for its *stated estimates*, not as authority on the virology.
**Addresses:** prior-odds
**Addresses:** market-evidence
**Addresses:** genomic-engineering
**Addresses:** methodology

### Weissman (2024) — lab-leak Bayesian (probabilistic-analysis)

**Source:** weissman
**Discovery:** linked from Alexander's write-up as a Bayesian analysis reaching the opposite
conclusion; Michael Weissman's "An Inconvenient Probability" (Substack).
**Rationale:** the lab-leak position's primary quantitative voice — a Bayesian posterior strongly
favouring laboratory origin. The symmetric other side of the probabilistic-analysis source-type,
so the lab-leak position is covered by a source that argues it, not only named as a gap.
**Position:** lab-leak
**Quality:** detailed independent Bayesian analysis, frequently revised; cited for its stated
posterior and reasoning.
**Addresses:** prior-odds
**Addresses:** methodology

### Good Judgment (2024) — superforecaster survey (probabilistic-analysis)

**Source:** goodjudgment
**Discovery:** linked from Alexander's write-up as the superforecasters' aggregate estimate
(Good Judgment Substack).
**Rationale:** an aggregated-forecaster estimate (74% zoonosis), methodologically independent of
Daniel and the judges — a third zoonosis-leaning probabilistic voice with explicit
(hypothesis, probability) estimates.
**Position:** zoonosis
**Quality:** survey of 50+ professional superforecasters; cited for the reported aggregate
probabilities.
**Addresses:** prior-odds
**Addresses:** methodology

## Known gaps

Voices or sources known to exist but not yet ingested.

**Gap:** the full debate transcript — the recorded debate exists only as ~20 hours of YouTube
video, with no clean text transcript document. Verbatim quote-first extraction needs an on-disk
text source, so Saar Wilf's and Peter Miller's own debate turns (the `debate-transcript`
source-type) are not yet ingested as primary voices. The lab-leak and zoonosis positions are
currently carried by the judges and the Bayesian analyses, not the debaters' own words.
**Gap:** Rootclaim's / Saar Wilf's own Bayesian calculation — the lab-leak side's primary
spreadsheet and write-up are seen here only secondhand (through the judges' summaries and the
spectator analyses), not ingested directly. Weissman covers the lab-leak position, but not Saar's
specific numbers.
**Gap:** the primary market epidemiology — the Worobey/Pekar spatial and molecular-clock papers
the zoonosis side leaned on are relayed here through the debate, not ingested as primary sources
(they are ingested directly in the sibling `covid_origins_ledger` case).
