---
subject: lsag_2008:no-associated-risks
inside_view: 0.97
out_of_model_discount: 0.05
adversarial_discount: 0.05
calibrated_confidence: 0.95
---
# Calibration — confidence in the LHC "no associated risks" conclusion

A confidence note on the LSAG safety conclusion. This is, unlike the COVID case, a
genuinely *closed* and *safe* question — the point of the discounts is **not** that the
LHC is dangerous, but that the categorical public framing ("would be perfectly safe",
"no risk of any significance whatsoever") states a notch more certainty than the
*structure* of the argument can strictly carry. The magnitudes are not endorsed by any
gate; only the discount shape is checked (`calibrated ≤ inside_view`).

- **Inside view (0.97).** The mainstream-safe conclusion is supported by the official
  review (LSAG), the detailed astrophysical bound (Giddings & Mangano), and a second
  exclusion (Koch et al.); the risk-raised side (Plaga) was engaged and rebutted in the
  peer-reviewed literature. The consensus is real and strong.
- **Out-of-model discount (0.05).** The conclusion is a **disjunction**, and its arms
  are not equally secure. The popularly-cited arm — Hawking evaporation
  (`lsag_2008:bh-hawking-decay`) — is theoretical and has never been observed, so it
  cannot be *assumed*; it is referenced by no edge in `content/graph.json`, grounding nothing
  in the support structure. The
  worst-case (stable) arm therefore rests entirely on the astrophysical bound
  (`giddings_2008:astro-bound`), which is itself **conditional** on specific TeV-scale
  gravity models. This is exactly the lesson of the methodological precedent LA-602
  (1946 #ignition-unreasonable): its authors reached a reassuring bottom line yet flagged
  "the absence of satisfactory experimental foundations" and called for further work
  (`la602_1946:further-work-desirable`).
- **Adversarial discount (0.05).** Two over-statements of independence. Plaga
  (2008 #evades-exclusion)
  constructs a metastable scenario the published exclusion did not originally cover (the
  reply rebuts it, but the crux assumption is contested, not closed). And Koch et al.
  present an "independent" argument that nonetheless rests on the **same** white-dwarf /
  neutron-star evidence as Giddings — the derived double-count finding fires, so the two
  are not 2× one independent confirmation.
- **Calibrated (0.95).** Still overwhelmingly safe — the right action is to run the
  collider — but held just below the categorical certainty the public framing asserts,
  to reflect that the load-bearing arm is conditional and that the "independent"
  confirmations are partly correlated. Confidence in the *conclusion*, not in the
  *rhetoric*.
