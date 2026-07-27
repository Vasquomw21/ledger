# Head-to-head — a real deep-research baseline vs the Ledger artefact

One sub-question, two ways of holding it. The question: **does the early evidence locate
SARS-CoV-2's origin at the Huanan market (zoonotic), rather than an introduced point source?**
(sub-question `origin-locus`.)

**How this was produced (so it is reproducible, not asserted).** The baseline is a *real*
artefact, not a characterisation: a strong general-purpose LLM with live web search was given this
exact sub-question, told to research the open web, and run **blind to this ledger**. Its full,
unedited output — every figure and citation — is committed verbatim at
[`../baseline_research_raw.md`](../baseline_research_raw.md). The comparison below quotes only that
captured output and this corpus's own stamped quotes.

> **An honesty correction.** An earlier version of this file *characterised* a weaker baseline that
> "silently drops the methodological objection." That was a strawman: the real baseline is **good**.
> It independently surfaced the proximity-ascertainment-bias critique, the Pekar Bayes-factor
> erratum (~60 → ~4), the streetlight effect, and the missing intermediate animal, and it correctly
> down-weighted the genomic argument. The point is therefore *not* that the baseline is sloppy.
> The uplift is narrower, sharper, and survives a strong opponent — which is the only kind worth
> claiming.

## A. What the baseline does well

The captured baseline reaches a calibrated bottom line — *"the most strongly supported hypothesis,
consistent across multiple independent data types, but not dispositive"* — names the central
missing link (no infected animal ever sampled), and raises the strongest statistical objection on
its own. A reader who wants a fluent, current survey of the question is well served by it. Any
honest comparison has to start there.

## B. The measured delta

Same question, scored on what each artefact lets a reader actually *do*. Each Ledger cell points
to a mechanically-checkable object in this repo, not a promise.

| What the reader can do | Deep-research baseline | Ledger artefact |
|---|---|---|
| **Re-check any figure to source** (~4 km clustering, p=0.004, "~3 infections at tMRCA", "60 → 4") | No — sources are linked, but the *numbers* are the model's paraphrase; you must trust it or re-read every paper by hand | **Yes** — every claim is a stamped verbatim quote; `ledger verify` re-proves the bytes on disk |
| **See that the two key papers are not independent** | Partial — it raises ascertainment bias *and* calls the evidence "multiple independent data types," but never reconciles the two, so the shared dependency stays invisible | **Yes** — Worobey and Pekar are a `Correlated-with` edge; the derived **double-count finding fires** on `andersen_2020:no-lab-scenario`, flagging "two independent pillars" as over-counting |
| **Find the exact inference under challenge** | Prose caveats, not attached to any specific claim | **Yes** — a sealed `faithfulness` dispute pins the challenge to the verbatim span *"the Huanan market was the early epicenter"* and to the specific edge it contests |
| **Inherit a confidence with its reasons** | Qualitative ("moderate-to-high"), discounts in prose | **Yes** — a calibration record: inside view 0.9 → 0.7, the two discounts named (unmodelled ascertainment bias; shared-data correlation) |
| **Read off what would move the question** | Good — names the missing animal and missing data in prose | **Yes** — source-register `## Known gaps`: intermediate host, ascertainment bias unquantified, DEFUSE docs |
| **Breadth / recency of the corpus** | **Broader** — surfaces 2023–25 follow-ups (the erratum, a 2024 metagenomics re-analysis, the ascertainment-bias exchange, the WHO assessment) | **Narrower by design** — 5 open-access sources; those follow-ups are *declared* as gaps, not hidden |

## C. Where the baseline wins — stated plainly

The baseline is **broader and more current** than this scoped five-source ledger. It cites
2024–2025 work the corpus has not ingested. Ledger does not claim to know more; it claims that what
it does hold is *verifiable, related, and interrogable*. On a question this active, a survey and an
audit are different tools, and the honest framing names both. (Two of the baseline's leads — the
ascertainment-bias paper and the erratum — are exactly the items this corpus already lists under
Known gaps as named, un-ingested debt; the baseline confirms the gap register was pointing at real
things.)

## D. The uplift, and why it survives the baseline being good

The table's last row read with the first is the point: **none of the Ledger machinery requires
trusting the model.** The quotes are verbatim on disk, the double-count is derived by code, the
dispute is sealed and re-judgeable. The baseline asks a reader to trust its reading of twelve
sources; the Ledger artefact asks a reader to trust nothing and check everything. For anyone who
must *act* on the answer — weigh it, find its weakest joint, defend it to a sceptic — that is the
uplift, shown against a strong baseline rather than asserted against a weak one.
