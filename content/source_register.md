---
last_updated: <YYYYMMDD>
curator: <name>
status: draft
---
# Source Register — the selection audit

Records *why* each source is in the corpus and *how* it was found, names the viewpoints
("positions") the question space contains, and lists what is knowingly missing. Layer 2
(completeness) lives here: the `selection_audit` gate enforces that the corpus is fully
registered and that **no declared position is left empty** — every position is covered by a
source or named under Known gaps. It does *not* prove the position set is complete; that is
judgement, surfaced here and in semantic health, never claimed as proven.

The writing assistant updates this on every ingest, alongside the crosswalk.

## Positions

The viewpoints in this question space. Each must be covered by a source below, or named under
Known gaps.

_(empty — declared as the question space is mapped)_

<!-- **Position:** <slug> — <one-line description of the viewpoint> -->

## Sources

One block per ingested source. `**Source:**` must match a `literature/verified_claims/<key>.md`.

_(empty — populated as the corpus grows)_

<!--
### <Author> et al. (<Year>)
**Source:** <ledger_key>
**Discovery:** <search query / citation-chase / recommendation that found it>
**Rationale:** <why it is in the corpus>
**Position:** <declared-position-slug>
**Quality:** <study design / peer-review tier>
**Addresses:** <qid>            # optional; validated against inquiry.md
-->

## Known gaps

Viewpoints or sources known to exist but not yet ingested.

_(empty — list what would change the conclusion as it surfaces)_

<!-- **Gap:** <viewpoint-or-source> — <what is missing and why it matters> -->
