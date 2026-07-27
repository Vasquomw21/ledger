# Assessment — the speedup crux and its contested evidence (Q2)

The judgement layer behind [[finding]] for the speedup-robustness sub-question. Each judgement is
sealed as a record under `_records/` and grounded in a verbatim claim; the reasoning the JSON does
not carry is here. Anchors are `key:slug` claim addresses.

## The crux

The load-bearing claim is `harrow_2009:exponential-speedup` (record `hhl-speedup-crux`). Per
`aaronson_2015:hhl-engine`, the quantum-machine-learning speedup family extends HHL or uses it as a
subroutine, so whether the HHL speedup survives its assumptions governs the wider Q2 question rather
than any one downstream algorithm.

## Aptness of the rebuttals, and a correlation the machinery flags

`tang_2019:no-exponential-speedup`, `chia_2020:svt-no-exponential-speedup`, and
`cerezo_2021:vqa-unproven-scaling` each support the claim that there is no real-world QML speedup
(`maurizio_2025:no-qml-real-world-speedup`), each with an edge-aptness record. They reach the same
conclusion, but the machinery flags that Tang and Chia are correlated — Chia generalises Tang's
sampling-based dequantisation — so their agreement is not two independent results (the derived
double-count). Cerezo's barren-plateau result rests on a different obstruction and is not flagged.
The skeptical side therefore has one method-family counted twice and one genuinely separate line.

## A faithfulness dispute

Record `tang-rebuts-hhl-faithfulness` contests `tang-rebuts-hhl-apt`. Tang's quote is scoped to
"Kerenidis and Prakash's algorithm"; reading it as rebutting the *general* HHL speedup
(`harrow_2009:exponential-over-classical`) reaches further than the quote licenses, because HHL for
sparse, well-conditioned systems is not dequantised by Tang's result. The rebuttal is apt against the
specific QML-recommendation claim, and is hedged accordingly rather than treated as a refutation of
every HHL application.

## Calibration

Record `chemistry-advantage-calibration` marks `reiher_2017:classically-intractable-projected` as
*projected*, not demonstrated: the resource estimate (`reiher_2017:resource-estimate-feasible`) is
conditional on fault-tolerant hardware that does not yet exist. The advantage is real in kind and
unrealised in fact, and is stated with that hedge.
