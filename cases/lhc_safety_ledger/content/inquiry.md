---
authored_by: ai
generated_by: claude
generated_date: 20260614
reviewed_by:
status: draft
---

# Inquiry — LHC collision safety

The question tree this knowledge base is organised around. Each sub-question declares a
stable `**id:**`; claims opt in with `**Addresses:** <id>`, and an assessment may mark one
claim as the `**Crux-of:**` a sub-question.

## Q1 — Could LHC collisions produce a dangerous (stable) microscopic black hole?

**id:** lhc-bh-risk
**parent:** lhc-safety

High-energy proton collisions at the LHC could, in some TeV-scale gravity scenarios, produce
microscopic black holes. The safety question turns on a disjunction: either such black holes
evaporate harmlessly by Hawking radiation, or — in the extremely hypothetical case that they
are stable — they could in principle be trapped in the Earth and accrete matter. The official
review (LSAG 2008 #no-associated-risks) concludes there is no associated risk; the detailed
stable-case argument (Giddings & Mangano 2008 #astro-bound) bounds accretion using astrophysical
observations.

**Sources by emphasis.** Mainstream-safe: LSAG (2008 #no-associated-risks), "Review of the Safety
of LHC Collisions" (performs the settling); Giddings & Mangano (2008 #astro-bound), "Astrophysical
implications of hypothetical stable TeV-scale black holes" (the crux bound) and their reply (2008b)
to Plaga. Risk-raised: Plaga (2008 #evades-exclusion), "On the potential catastrophic risk from
metastable quantum-black holes…" — argues a scenario exists that the exclusion does not cover.

**The crux.** Whether a hypothetically stable TeV black hole could accrete dangerously before
the Earth's natural lifetime. Giddings & Mangano's bound — that cosmic-ray-produced black
holes impinging on white dwarfs and neutron stars would have catalysed their decay if such
accretion were possible — is marked the crux of this sub-question: if it holds, the stable
case is ruled out and the safety conclusion follows.

## Q2 — How is the existential-safety argument structured, and what does it depend on?

**id:** arg-structure
**parent:** lhc-safety

A separate question from "is it safe?": *what does the safety conclusion actually rest on, and
which of its arms is load-bearing?* The conclusion is not one claim but a **disjunction**. Either
any micro black hole evaporates by Hawking radiation (the popularly-cited mechanism), or — in the
hypothetical case that it is stable — the astrophysical-survival bound rules out dangerous
accretion. The two arms are not equally secure: Hawking radiation is theoretical and has never been
observed, so it cannot be *assumed*; that is precisely why Giddings & Mangano devote a detailed
paper to the stable case. The worst-case arm therefore leans entirely on the conditional
astrophysical bound — the crux of Q1 and exactly the assumption Plaga
(2008 #evades-exclusion) contests.

**Public vs load-bearing.** The public CERN FAQ asserts the collisions "would be perfectly safe"
and gives *no* mechanism, deferring the basis to a linked report. So the communicated argument
(bare assurance), the popularly-cited mechanism (Hawking evaporation, unobserved), and the actually
load-bearing argument (the conditional astrophysical bound) are three different things — a gap this
sub-question makes explicit.

**The methodological mirror.** LA-602 — the 1946 Los Alamos report by Konopinski, Marvin and
Teller — asked the structurally identical question for a prior experiment: could a nuclear
detonation ignite the atmosphere? It reached a reassuring bottom line
(LA-602 1946 #ignition-unreasonable) yet explicitly flagged "the absence of satisfactory
experimental foundations" and called for further work (LA-602 1946 #further-work-desirable). It is
ingested as a *calibration precedent* — how categorically an existential-safety conclusion ought to
be stated — not as evidence about the LHC.

See [[safety_calibration]] for the calibrated-confidence note (with the LA-602 parallel).
