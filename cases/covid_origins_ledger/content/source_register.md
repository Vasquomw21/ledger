---
last_updated: 20260613
curator: van_songhai
status: active
---
# Source Register — COVID-19 origins (FCS + origin-locus sub-questions)

Records *why* each source is in the corpus and *how* it was found, names the viewpoints the
question space contains, and lists what is knowingly missing. The `selection_audit` gate (set
`required` here) enforces that every stamped ledger is registered and that **no declared
position is left empty** — covered by a source or named under Known gaps. It does *not* prove
the position set is complete; that judgement is surfaced here and in semantic health, never
claimed as proven. The two known gaps below are the corpus's incompleteness stated in the open.

## Positions

The viewpoints across both sub-questions (FCS engineering, and origin-locus). Each must be
covered by a source below, or named under Known gaps.

**Position:** natural-origin — the genomic features, including the FCS, are consistent with
ordinary natural evolutionary processes; no laboratory scenario is needed to explain them.
**Position:** lab-origin — the same features cannot exclude laboratory manipulation; the FCS's
novelty is compatible with engineering that would leave no trace.
**Position:** zoonotic-market — the early spatial and genomic evidence locates emergence at the
Huanan live-wildlife market via one or more natural spillovers, not an introduced point source.

## Sources

One block per ingested source. `**Source:**` matches a `literature/verified_claims/<key>.md`.

### Andersen et al. (2020)
**Source:** andersen_2020
**Discovery:** the case prompt; the canonical "proximal origin" analysis and the most-cited
natural-origin paper on SARS-CoV-2.
**Rationale:** the natural-origin anchor for the FCS sub-question — states the features are
consistent with natural processes and that no laboratory scenario is plausible.
**Position:** natural-origin
**Quality:** peer-reviewed correspondence, Nature Medicine (2020).
**Addresses:** fcs-engineering

### Segreto & Deigin (2021)
**Source:** segreto_2021
**Discovery:** citation-chase from the published responses engaging Andersen et al. (2020).
**Rationale:** the most-cited published engineering-leaning counterpoint that engages the *same*
FCS evidence — the symmetric other side of the crux.
**Position:** lab-origin
**Quality:** peer-reviewed hypothesis paper, BioEssays (2021).
**Addresses:** fcs-engineering

### Worobey et al. (2022)
**Source:** worobey_2022
**Discovery:** the eval named the market-epidemiology case as the missing zoonotic viewpoint;
the canonical spatial-epidemiology analysis of the earliest cases.
**Rationale:** the spatial anchor for origin-locus — the earliest cases cluster on the Huanan
market, read as evidence of zoonotic emergence there.
**Position:** zoonotic-market
**Quality:** peer-reviewed research article, Science (2022).
**Addresses:** origin-locus

### Pekar et al. (2022)
**Source:** pekar_2022
**Discovery:** companion paper to Worobey et al. (2022) in the same issue; the molecular-clock
counterpart to the spatial analysis.
**Rationale:** the molecular anchor for origin-locus — two early lineages imply at least two
separate zoonotic introductions, against a single point-source introduction.
**Position:** zoonotic-market
**Quality:** peer-reviewed research article, Science (2022).
**Addresses:** origin-locus

### Temmam et al. (2022)
**Source:** temmam_2022
**Discovery:** citation-chase for the closest sampled natural relatives bearing on FCS rarity.
**Rationale:** the BANAL bat coronaviruses — closest relatives by RBD, infectious for human
cells, yet still carrying no furin cleavage site: a qualifier on the FCS crux and support for
natural-spillover plausibility.
**Position:** natural-origin
**Quality:** peer-reviewed research article, Nature (2022).
**Addresses:** fcs-engineering

## Known gaps

Viewpoints or sources known to exist but not yet ingested.

**Gap:** the intermediate host itself — no infected market animal was ever sampled; the
zoonotic-market case rests on spatial/genomic proxies, not a recovered animal reservoir.
**Gap:** ascertainment bias — early case-finding was itself centred on the market, so the
"epicenter" signal may partly reflect *where testing looked*. This is the open methodological
counter to Worobey/Pekar and is the subject of the recorded faithfulness dispute; no source
quantifying the bias is yet ingested.
**Gap:** lab-leak primary documents — grant and proposal materials (e.g. the DEFUSE proposal) are
not yet ingested as primary sources. They would bear on the means/opportunity side of the
engineering reading, which the current lab-origin source argues only from genomic structure.
