---
curator: Vasquomw21
date: 20260716
status: active
---

# Finding — cohort reuse and double-counting in the egg–CVD evidence base

Four meta-analyses of this literature re-analyse an overlapping set of primary cohorts, and three
possible-dependence warnings fire: two exact same-cohort pairs on the harmful side and one broader
overlapping-pool pair on the null. The detector operates on cohort relationships recorded from each
study's methods, so it flags the harmful side's WHI pair [rec: whi-double-count] and six-US-cohort
pair [rec: sixus-double-count] alongside the null side's overlapping pools. This does not overturn
the answer. It turns "are these pooled studies independent?" from a step the reader must trust each
author to have taken into a declaration that is written down, addressable, and open to challenge.
The dependence itself is read off each study's methods by a human and recorded in the ledger; what
the machinery does is carry that declaration across the graph and show where it bites.

**What this is.** The framing-agnostic read-out of applying the Ledger machinery to a 16-source
egg/dietary-cholesterol–CVD corpus. We did not set out to prove eggs are safe or harmful; we
ingested the major syntheses and primary cohort studies, recorded each study's underlying cohort
neutrally, and report what the double-count detector surfaces. The result is **reproducible by the
reader** — the counts are derived from running the tools over the committed ledgers, while source
claims remain verbatim quotations.

## Reproduce it

```
python3 tools/build_graph.py        # writes content/graph.json incl. findings.double_count
python3 tools/analyze_graph.py      # prints the shared-premise / double-count findings
python3 tools/check_structure.py --structure required   # 11 edges resolve + grounded
```

## What the machinery surfaces

1. **The corpus rests on a handful of repeatedly-reused cohorts.** Across the four meta-analyses
   (`drouin_2020`, `zhao_2022`, `godos_2021`, `darooghegi_2022`) and the primaries, the same cohorts
   recur — the Harvard NHS/HPFS family, the six harmonised US cohorts (`zhong_2019:cohort-6us-pool`
   re-used by `zhong_2021:cohort-6us-pool`), the Women's Health Initiative (`sun_2021:cohort-whi` and
   `chen_2021:cohort-whi`), NHANES, NIH-AARP, KIHD, China Kadoorie. The "independent" syntheses
   therefore re-analyse a largely overlapping set of primary data.

2. **Three possible-dependence warnings fire** (`analyze_graph.py`), on *both* sides of the
   question — the detector is framing-agnostic. The first two identify exact cohort reuse; the third
   records a broader overlapping-pool relationship:
   - `sun_2021` + `chen_2021` both support the harmful conclusion (`zhao_2022:harmful-mortality`) yet
     are the **same WHI cohort** [rec: whi-double-count] — and a published meta-analysis
     (Darooghegi 2022 #overlap-excluded) retained both, against its own stated method.
   - `zhong_2019` + `zhong_2021` both support the harmful conclusion yet **re-analyse the same six US
     cohorts** [rec: sixus-double-count].
   - `dehghan_2020` + `rong_2013` both support the null (`drouin_2020:no-association-overall`) and
     pool overlapping observational cohorts of the same design. This pair is declared correlated in
     the ledgers and fires the same derived warning, but carries no sealed record of its own — the
     two above do.

   Every supports/rebuts edge in this corpus has been adversarially reviewed and held — the aptness
   of the WHI support [rec: sun-supports-zhao-apt-pass] and of the null's
   [rec: dehghan-supports-drouin-apt-pass] alike. A double-count warns about *independence*, not
   about whether either inference reads its source correctly.

3. **The meta-analyses differ in what the verified claims establish about de-duplication, alongside
   different conclusion strength.** From each source's own methods:
   - De-duplication reported → hedged: Godos (`godos_2021:dedup-method`) keeps one dataset per
     cohort and concludes `godos_2021:no-conclusive-evidence`; Darooghegi
     (`darooghegi_2022:overlap-excluded`) names and removes HPFS/NHANES/CHNS duplicates and reaches
     a threshold-dependent result (`darooghegi_2022:harmful-above-threshold`).
   - Overlap handling unestablished here → confident: Drouin-Chartier
     (`drouin_2020:pooled-28-studies`) and Zhao
     (`zhao_2022:pooled-studies`) identify the studies they pool, but the verified claims do not
     establish whether either checked for cohort overlap — that is unestablished here, not a
     reported absence. Both reach *confident* conclusions in opposite directions
     (`drouin_2020:no-association-overall`; `zhao_2022:harmful-mortality`).

## What this finding is NOT

- **The cohort-overlap problem is not novel science.** It is a known methodological hazard — indeed
  two sources here (`godos_2021:dedup-method`, `darooghegi_2022:overlap-excluded`) handle it
  explicitly. The contribution is not the discovery; it is that the overlap each author found is
  **written down, addressable, and auditable** across a corpus, instead of living in prose a reader
  must trust each author to have written.
- **The confident null is not simply an artefact of double-counting.** Drouin-Chartier handles its
  single biggest overlap *correctly*: it `drouin_2020:updates-hu-1999` by **replacing** the old NHS/HPFS
  data rather than pooling both, so we do not claim its conclusion collapses. The double-counts the
  machinery flags (WHI; six-US-cohort) are real but are a minority of the pooled evidence, and we do
  not claim they reverse any pooled estimate — establishing that would need the effect sizes
  re-pooled, which is out of scope here.
- **What it does change is *confidence calibration*.** The apparent consilience of multiple
  "independent" meta-analyses is weaker than it looks, because they re-analyse overlapping cohorts;
  and the two confident conclusions come from analyses for which the verified claims do not establish
  a de-duplication step. That is a hedged, structural observation, not a verdict on whether eggs
  raise CVD risk.
- **Coverage is partial.** Several overlap specimens (Hu 1999; the KIHD pair; the CHNS pair) are
  paywalled and recorded under `source_register.md` Known gaps, never stubbed — so the demonstration
  rests on the clusters whose members are all open (WHI, six-US-cohort).

## Bottom line

Applied without a thumb on the scale, the machinery turns "are these pooled studies independent?"
from a manual, trust-the-author step into a declared relationship anyone can address and dispute,
and the warnings it derives land on both sides of a contested question, including two exact
same-cohort reuse findings on the harmful side. The overlap is read from each study's methods by a
human, not discovered by the tool; the tool is what makes that reading carry, and fail loudly if it
is wrong. It does **not** overturn the answer; it makes the evidence base's dependence on a few
reused cohorts legible and contestable.
