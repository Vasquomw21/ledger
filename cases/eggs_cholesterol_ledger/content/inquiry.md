---
authored_by: ai
generated_by: claude
generated_date: 20260614
reviewed_by:
status: draft
---

# Inquiry — eggs, dietary cholesterol, and cardiovascular disease

The question tree this knowledge base is organised around. Each sub-question declares a
stable `**id:**`; claims opt in with `**Addresses:** <id>`, and an assessment may mark one
claim as the `**Crux-of:**` a sub-question.

## Q1 — Does egg / dietary-cholesterol consumption increase cardiovascular disease risk?

**id:** eggs-cvd
**parent:** diet-cvd

The evidence is observational and genuinely conflicting. Large pooled US cohorts (Zhong et al.
2019 #cholesterol-eggs-harmful) report a dose-response association between dietary cholesterol /
egg intake and incident CVD; large meta-analyses and multinational cohorts (Drouin-Chartier et al.
2020 #no-association-overall; Dehghan et al. 2020 #pure-no-association, PURE; Rong et al.
2013 #rong-overall-null) find no association for moderate intake. A subgroup signal — higher
coronary-heart-disease risk among people with diabetes (Rong et al. 2013 #rong-diabetic-harm) —
qualifies the overall null. Because the studies are observational and share confounding structure
(egg eaters differ in diet and lifestyle), the disagreement turns on confounding and study quality,
not on a single decisive trial.

**Sources by emphasis.** Harmful / positive association: Zhong et al.
(2019 #cholesterol-eggs-harmful). No association: Drouin-Chartier et al.
(2020 #no-association-overall) (meta-analysis), Dehghan et al. (2020 #pure-no-association, PURE),
Rong et al. (2013 #rong-overall-null, overall). Subgroup-dependent: Rong et al.
(2013 #rong-diabetic-harm, diabetic populations).

**The crux.** Whether the positive cohort associations survive adjustment for dietary confounding
and study quality. Drouin-Chartier's meta-analytic null is marked the crux: it *performs the
settling* of the question, yet remains contested by the positive-association cohort — a clear case
of "performed settling" rather than a settled consensus.

## Q2 — How independent is the pooled evidence each meta-analysis rests on?

**id:** meta-independence

A meta-analysis's confidence depends on pooling *independent* studies. In this literature a small
set of cohorts (NHS/HPFS, the six harmonised US cohorts, WHI, NHANES, NIH-AARP, KIHD, China
Kadoorie) is re-used across many "separate" publications, so two pooled studies can re-count the
same participants. The meta-analyses **differ in what they report about this**. Godos
(2021 #dedup-method) and Darooghegi (2022 #overlap-excluded) state an explicit de-duplication
step, and reach hedged or threshold-bounded conclusions (Godos 2021 #no-conclusive-evidence;
Darooghegi 2022 #harmful-above-threshold). Drouin-Chartier (2020 #pooled-28-studies) and Zhao
(2022 #pooled-studies) identify the studies they pooled, but the verified claims do not establish
whether overlapping cohorts were de-duplicated: de-duplication is an **unresolved methodological
gap** for these two, not a reported absence. Both nonetheless reach *confident* conclusions, in
opposite directions (Drouin-Chartier 2020 #no-association-overall; Zhao 2022 #harmful-mortality).
This sub-question is **methodological, framing-agnostic**: the
machinery maps each primary study to its cohort and flags same-cohort studies pooled as independent,
wherever they occur — see `content/finding.md`.

**The bound.** Drouin-Chartier (2020 #updates-hu-1999) handles its biggest overlap correctly (it
*replaces* the Hu 1999 NHS/HPFS data rather than pooling both), so the confident null is **not** simply an artefact of
double-counting; the machinery does, however, surface genuine same-cohort pairs pooled as
independent (e.g. Sun + Chen on WHI; Zhong 2019 + Zhong 2021 on the six US cohorts), on both the
harmful and null sides.
