---
last_updated: 20260614
curator: van_songhai
status: active
---
# Source Register — eggs / dietary cholesterol and CVD

Records *why* each source is in the corpus and *how* it was found, names the viewpoints the
question space contains, and lists what is knowingly missing. The `selection_audit` gate (set
`required` here) enforces that every stamped ledger is registered and that **no declared
position is left empty** — covered by a source or named under Known gaps. It does *not* prove
the position set is complete; that judgement is surfaced here and in semantic health.

This is the messy-evidence case, scaled to a corpus that lets the machinery surface **cohort
overlap** (studies pooled by meta-analyses as if independent while re-using the same underlying
cohorts). The corpus is entirely observational; the meta-analyses re-analyse a small number of
repeatedly-used cohorts. See `content/finding.md` for the structural read-out.

## Positions

The viewpoints on the egg/cholesterol–CVD sub-question. Each must be covered by a source below,
or named under Known gaps.

**Position:** harmful — higher egg / dietary-cholesterol intake is associated with higher CVD or
mortality risk (a dose-response positive association in pooled cohorts).
**Position:** no-association — moderate egg consumption (up to one per day) shows no association
with CVD risk overall.
**Position:** protective — moderate egg consumption is associated with *lower* CVD risk (seen in
several cohorts, notably Asian populations).
**Position:** subgroup-dependent — the overall null does not extend to people with diabetes, where
a harmful coronary signal appears.

## Sources

One block per ingested source. `**Source:**` matches a `literature/verified_claims/<key>.md`.
The corpus has two strata: the four meta-analyses / systematic reviews under examination
(Drouin, Zhao, Godos, Darooghegi), and the primary cohort studies they pool (the rest).

### Drouin-Chartier et al. (2020)
**Source:** drouin_2020
**Discovery:** the most recent large meta-analysis, the popularly-cited "eggs are fine" reference.
**Rationale:** the no-association anchor and the crux node; the cold baseline whose cohort-overlap handling the case examines (it pools 28 studies without a stated de-duplication protocol).
**Position:** no-association
**Quality:** peer-reviewed cohorts + systematic review / meta-analysis, BMJ (2020); observational.
**Addresses:** eggs-cvd

### Zhao et al. (2022)
**Source:** zhao_2022
**Discovery:** the confident harmful-direction meta-analysis, identified as the mirror of Drouin.
**Rationale:** the harmful-position meta-analytic anchor; pools 49 risk estimates with **no** cohort-overlap de-duplication stated (the harmful-side counterpart to Drouin's un-de-duplicated null).
**Position:** harmful
**Quality:** peer-reviewed cohort + systematic review / meta-analysis, Circulation (2022); observational.
**Addresses:** eggs-cvd

### Godos et al. (2021)
**Source:** godos_2021
**Discovery:** identified as a meta-analysis that explicitly de-duplicates overlapping cohorts.
**Rationale:** methodological control — explicitly keeps one dataset per cohort, and reaches a hedged ("no conclusive evidence") conclusion.
**Position:** no-association
**Quality:** peer-reviewed dose-response meta-analysis, Eur J Nutr (2021); observational.
**Addresses:** eggs-cvd

### Darooghegi Mofrad et al. (2022)
**Source:** darooghegi_2022
**Discovery:** identified as a meta-analysis that explicitly names and removes overlapping-cohort duplicates.
**Rationale:** sharper methodological control — de-duplicates the HPFS/NHANES/CHNS overlaps by name and reaches a non-null (harmful above thresholds) conclusion.
**Position:** harmful
**Quality:** peer-reviewed dose-response meta-analysis, Front Nutr (2022); observational.
**Addresses:** eggs-cvd

### Zhong et al. (2019)
**Source:** zhong_2019
**Discovery:** the most-cited recent positive-association analysis.
**Rationale:** harmful-position primary — a pooled six-US-cohort dose-response association.
**Position:** harmful
**Quality:** peer-reviewed pooled IPD cohort analysis, JAMA (2019); observational.
**Addresses:** eggs-cvd

### Zhong et al. (2021)
**Source:** zhong_2021
**Discovery:** a re-analysis of the SAME six US cohorts as Zhong 2019.
**Rationale:** demonstrates within-author cohort reuse — re-analyses ARIC/CARDIA/CHS/FHS/FOS/MESA, so its agreement with Zhong 2019 is not independent.
**Position:** harmful
**Quality:** peer-reviewed pooled cohort re-analysis, Int J Epidemiol (2021); observational.
**Addresses:** eggs-cvd

### Sun et al. (2021)
**Source:** sun_2021
**Discovery:** a Women's Health Initiative (WHI) egg/protein analysis.
**Rationale:** harmful-direction WHI primary; pairs with Chen 2021 (same WHI cohort) to show a same-cohort overlap retained by a published meta-analysis.
**Position:** harmful
**Quality:** peer-reviewed prospective cohort, J Am Heart Assoc (2021); observational.
**Addresses:** eggs-cvd

### Chen et al. (2021)
**Source:** chen_2021
**Discovery:** a WHI egg/cholesterol mortality analysis.
**Rationale:** the WHI overlap partner to Sun 2021 — same cohort, separate publication.
**Position:** harmful
**Quality:** peer-reviewed prospective cohort, Am J Clin Nutr (2021); observational.
**Addresses:** eggs-cvd

### Zhuang et al. (2021)
**Source:** zhuang_2021
**Discovery:** the NIH-AARP Diet and Health Study egg/cholesterol mortality analysis.
**Rationale:** a large *independent* US cohort (NIH-AARP) on the harmful side — genuine non-overlapping evidence.
**Position:** harmful
**Quality:** peer-reviewed prospective cohort, PLoS Med (2021); observational.
**Addresses:** eggs-cvd

### Dehghan et al. (2020), PURE
**Source:** dehghan_2020
**Discovery:** the large multinational (50-country) PURE cohort.
**Rationale:** a geographically diverse null-finding cohort — supports the meta-analytic null and rebuts the positive association.
**Position:** no-association
**Quality:** peer-reviewed multinational cohort, Am J Clin Nutr (2020); observational.
**Addresses:** eggs-cvd

### Rong et al. (2013)
**Source:** rong_2013
**Discovery:** the earlier dose-response meta-analysis the later work builds on.
**Rationale:** establishes the overall null AND the diabetic-subgroup harm.
**Position:** no-association
**Position:** subgroup-dependent
**Quality:** peer-reviewed dose-response meta-analysis, BMJ (2013); observational, subgroup findings exploratory.
**Addresses:** eggs-cvd

### Xia et al. (2020)
**Source:** xia_2020
**Discovery:** an NHANES egg/mortality analysis.
**Rationale:** an independent US national-survey cohort (NHANES) finding no association — null-side evidence distinct from the WHI/NIH-AARP/6-cohort frames.
**Position:** no-association
**Quality:** peer-reviewed prospective cohort, J Am Heart Assoc (2020); observational.
**Addresses:** eggs-cvd

### Djoussé & Gaziano (2008)
**Source:** djousse_2008
**Discovery:** the Physicians' Health Study egg / heart-failure analysis.
**Rationale:** an independent US male-physician cohort; no CVD effect at infrequent intake (a near-null primary).
**Position:** no-association
**Quality:** peer-reviewed prospective cohort, Am J Clin Nutr (2008); observational.
**Addresses:** eggs-cvd

### Key et al. (2019)
**Source:** key_2019
**Discovery:** the pan-European EPIC analysis of animal foods and ischaemic heart disease.
**Rationale:** a large independent European cohort; eggs inversely associated with IHD (with a reverse-causation caveat).
**Position:** protective
**Quality:** peer-reviewed prospective cohort, Circulation (2019); observational.
**Addresses:** eggs-cvd

### Qin et al. (2018)
**Source:** qin_2018
**Discovery:** the China Kadoorie Biobank egg/CVD analysis (~0.5 million adults).
**Rationale:** a large independent Chinese cohort; moderate egg intake associated with *lower* CVD risk (the protective-position anchor).
**Position:** protective
**Quality:** peer-reviewed prospective cohort, Heart (2018); observational.
**Addresses:** eggs-cvd

### Goldberg et al. (2014)
**Source:** goldberg_2014
**Discovery:** the Northern Manhattan Study (NOMAS) egg/carotid-atherosclerosis analysis.
**Rationale:** an independent multi-ethnic urban cohort; inverse association with subclinical atherosclerosis, no association with events.
**Position:** protective
**Quality:** peer-reviewed prospective cohort, Atherosclerosis (2014); observational.
**Addresses:** eggs-cvd

## Known gaps

Viewpoints or sources known to exist but not yet ingested.

**Gap:** the overlapping-cohort specimens that are paywalled / have no open full text — **Hu et al.
1999** (the keystone NHS/HPFS egg study Drouin updates), the **KIHD pair Virtanen 2016 + Abdollahi
2019** (both the same Finnish cohort, pooled by Drouin as if independent — provable from Drouin's
own included-study citations, but full text unavailable to quote), **Mazidi 2019** (NHANES), the
**CHNS pair Zhuang 2020 + Hou 2021**, and the **NIPPON DATA** papers. These are recorded, never
stubbed (paywall rule). Their absence limits how many overlap clusters can be shown with both
members ingested; the WHI and six-US-cohort clusters carry the demonstration with all members open.
**Gap:** randomised-trial evidence — the corpus is entirely observational; no large RCT of egg
consumption with hard CVD endpoints is ingested, the evidence that would settle the confounding
question the crux turns on.
**Gap:** mechanism / hyper-responder biomarker studies — the heterogeneous LDL response to dietary
cholesterol (hyper- vs hypo-responders) is not represented; it would bear on who, if anyone, the
harmful position applies to.
