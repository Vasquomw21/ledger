---
last_updated: 20260613
curator: van_songhai
status: active
---
# Source Register — LHC collision safety (black-hole sub-question)

Records *why* each source is in the corpus and *how* it was found, names the viewpoints the
question space contains, and lists what is knowingly missing. The `selection_audit` gate (set
`required` here) enforces that every stamped ledger is registered and that **no declared
position is left empty** — covered by a source or named under Known gaps. It does *not* prove
the position set is complete; that judgement is surfaced here and in semantic health.

## Positions

The viewpoints on the LHC black-hole-risk sub-question. Each must be covered by a source below,
or named under Known gaps.

**Position:** mainstream-safe — the collisions present no associated risk: micro black holes
evaporate by Hawking radiation, and even hypothetically stable ones are ruled out by
astrophysical bounds.
**Position:** risk-raised — a metastable scenario can be constructed that the published
exclusions do not cover, so a catastrophic risk cannot be fully excluded.
**Position:** methodological-precedent — how a prior existential-safety question was reasoned
about (whether a nuclear detonation could ignite the atmosphere): a calibration analogue for how
categorically such a conclusion may honestly be stated, not evidence about the LHC itself.

## Sources

One block per ingested source. `**Source:**` matches a `literature/verified_claims/<key>.md`.

### LHC Safety Assessment Group (2008)
**Source:** lsag_2008
**Discovery:** the canonical CERN safety review on which the technical safety case rests.
**Rationale:** the official position that *performs the settling* — the conclusion node the analysis supports.
**Position:** mainstream-safe
**Quality:** peer-reviewed review, J. Phys. G (2008); authored by the CERN LHC Safety Assessment Group.
**Addresses:** lhc-bh-risk

### Giddings & Mangano (2008)
**Source:** giddings_2008
**Discovery:** the detailed astrophysical analysis the LSAG review cites for the stable-black-hole case.
**Rationale:** supplies the crux bound (white-dwarf / neutron-star constraint) on which the stable-case safety claim rests.
**Position:** mainstream-safe
**Quality:** peer-reviewed, Phys. Rev. D (2008).
**Addresses:** lhc-bh-risk

### Plaga (2008)
**Source:** plaga_2008
**Discovery:** citation-chase from the Giddings & Mangano reply, which responds directly to it.
**Rationale:** the most-cited published risk-raising counter-position engaging the same exclusion — the symmetric other side.
**Position:** risk-raised
**Quality:** arXiv preprint (physics.gen-ph); engaged and rebutted in the peer-reviewed literature.
**Addresses:** lhc-bh-risk

### Giddings & Mangano reply (2008b)
**Source:** giddings_reply_2008
**Discovery:** the authors' direct reply to Plaga (2008), found alongside it on arXiv.
**Rationale:** completes the exchange — rebuts the risk scenario as internally inconsistent.
**Position:** mainstream-safe
**Quality:** arXiv preprint / CERN-PH-TH note (2008).
**Addresses:** lhc-bh-risk

### Koch, Bleicher & Stöcker (2009)
**Source:** koch_2009
**Discovery:** the Known-gap item on *independent* safety analyses — an exclusion that Plaga also
engages — fetched from arXiv (0807.3349).
**Rationale:** tests whether the mainstream-safe position rests on more than the LSAG / Giddings
analysis. Koch et al. present an explicitly "independent" argument, but cite Giddings and rest on the
same white-dwarf / neutron-star evidence — so it is the case's worked example of the
correlated-vs-independent-supports question (the derived double-count finding fires on it).
**Position:** mainstream-safe
**Quality:** peer-reviewed, Phys. Lett. B (2009).
**Addresses:** lhc-bh-risk

### CERN public FAQ — "Will CERN generate a black hole?"
**Source:** cern_faq
**Discovery:** the competition's LHC starting material links the CERN FAQ as the public-facing
answer; the live URL now redirects, so the exact resource was captured from the Wayback Machine.
**Rationale:** the *public* voice — what a non-expert reader is told. It asserts the collisions
"would be perfectly safe" with no mechanism given, deferring the basis to a linked report: the gap
between communicated assurance and load-bearing argument, made concrete.
**Position:** mainstream-safe
**Quality:** institutional FAQ (CERN), public explainer; cited for the *public framing*, not as a
technical source.
**Addresses:** lhc-bh-risk

### Konopinski, Marvin & Teller — LA-602 (1946)
**Source:** la602_1946
**Discovery:** the competition's LHC brief links LA-602 explicitly as the historical existential-
safety precedent (could a nuclear detonation ignite the atmosphere?).
**Rationale:** a calibration analogue, not LHC physics — a prior "could this destroy the world?"
analysis that reached a reassuring bottom line yet flagged its own incomplete foundations and called
for further work. Ingested from a 1946 scanned typescript; the OCR-degraded tail is handled honestly
(only verbatim-verifiable spans are quoted).
**Position:** methodological-precedent
**Quality:** declassified Los Alamos report (1946); cited for its stated conclusion and its
self-flagged limitation, not as current physics.
**Addresses:** arg-structure

## Known gaps

Viewpoints or sources known to exist but not yet ingested.

**Gap:** Hawking-radiation primary source — Hawking (1975) is not ingested; the evaporation
branch is currently grounded only from the review text, not the originating derivation. This is the
*point* of the dependency finding (Q2): the popularly-cited Hawking arm is theoretical and
unobserved, so the worst-case safety rests on the astrophysical bound, not on it. Ingesting Hawking
(1975) would let the graph carry the evaporation branch from its origin and show its evidential
status explicitly.
**Gap:** other hypothetical objects — the strangelet, vacuum-bubble and magnetic-monopole
sub-cases of the LSAG review are not yet modelled as their own claims.
