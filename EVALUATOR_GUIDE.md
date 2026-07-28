# Ledger — evaluator guide

## What Ledger is

Ledger is a research toolkit for people and AI working together. It keeps a growing knowledge base
tied to its evidence: every citation in gated, authored prose must point to a quotation checked
against the original source, while the claims, their connections, and human judgements remain
visible and reviewable.

Ledger does not establish that the sources are complete, the reasoning is sound, or the conclusion
is true. When the source files are unavailable, it attests the committed proof rather than
re-checking the bytes.

The guarantee is narrow and exact:

> Ledger prevents a citation in gated, authored prose from pointing to a quotation that has not been
> verified verbatim against its source. It does not prove that the source set is complete or the
> interpretation correct; it makes those judgements explicit and reviewable.

That check is only as strong as the sources on the machine running it. On your own machine the script
re-reads the source files and re-proves every quote. In a fresh clone or in continuous integration
the source files are not shipped, so the system attests the stored proof rather than re-running it —
an audit trail, not an independent re-proof.

## Start here

Start with the COVID-origins case. Open its pack — `packs/covid_origins/index.html` in the
submission bundle, or run `make demo DIR=cases/covid_origins_ledger` from a clone — and read the
finding on the first screen.

The case shows how the machinery exposes a weak spot in an argument that looks strong. The claim most
other claims lean on is a statement of belief, not a result: Andersen and colleagues wrote that they
"do not believe that any type of laboratory-based scenario is plausible." Ledger stores that exact
wording, so a reader can see that three supporting claims are aimed at a belief. One of the three is
formally disputed, and two more are marked as potentially correlated — so the apparent agreement of
three independent sources is weaker than it first looks.

## Five-minute runnable path

You can run the whole thing from a fresh clone in about five minutes. It needs only Python 3.10 or
newer for the demo; the tests and the intake tools need a one-line `pip install`. From the repository
root:

```
python3 -m pytest -q                          # all tests pass
python3 tools/ledger_doctor.py                # exit 0 on the empty starter kit
python3 ledger_cli.py check                   # the applicable gates pass, exit 0
make demo DIR=cases/covid_origins_ledger      # the guided tour, exit 0
python3 ledger_cli.py pack cases/covid_origins_ledger --out /tmp/pack
```

Each command exits 0. `pytest` reports every test passing (a dated snapshot: 887 passed on
2026-07-16). The demo runs without the source files, so it confirms each stored proof rather than
re-reading the sources — the tour says so as it goes.

## What to inspect

Inside the pack, follow one claim from the finding down to its evidence. The trail is the point of
the system: every step is a link you can click, and nothing between the finding and the source is
asserted without a stored quotation.

The finding names one claim: Andersen's "no laboratory-based scenario is plausible." Click it and you
reach the stored quotation, shown character-for-character as it appears in the source, with the
SHA-256 stamp the verbatim check produced.

One supporting inference is formally disputed. Worobey's quotation locates where the earliest cases
clustered; the claim it is used to support is about how the virus arose. A sealed record marks that
gap between what the quote says and what it is used to prove. The dispute is recorded, not resolved —
Ledger shows the disagreement rather than settling it.

Two of the three supporting claims may not be independent. Pekar's claim is declared correlated with
Worobey's, so the graph marks the pair with a possible-dependence warning. If two sources share
evidence, they may not be independent confirmations; the warning makes that possible dependence
visible.

Not every inference is disputed. The third supporting claim, from Temmam, rests on a separate line of
evidence, and its use was adversarially reviewed and held.

A separate record flags overstated certainty. Ledger marks Andersen's phrase "irrefutably show" as
claiming more than an argument from the absence of a known backbone can support.

One gate underwrites all of this. Where the source corpus is present — on your machine, as you write
and before each commit — the verbatim-quote check re-reads each source and confirms every quotation,
so a citation whose quotation does not match cannot pass. In a clone without the sources, including
CI, the same shared checker attests the stored proof rather than re-reading the bytes. That gate is
the guarantee in the first section, doing its work on this case.

## What remains human judgement

Four judgements stay with the reader.

Whether the sources are the right ones is yours. Ledger makes the corpus and its declared gaps
auditable, but it cannot tell you what you never looked for.

Whether a verbatim quote is used fairly is yours. Ledger shows every quote against the inference it
supports, but it does not settle whether the use is apt.

Whether the argument follows is yours. The claim graph makes the structure explicit — what is
load-bearing, what rests on a single source — and stops there.

What the answer is stays yours. Ledger surfaces these judgements; it does not decide them.

## Other worked cases

The other four cases each show a different reason the system earns its keep. Each has a pack at
`packs/<name>/` in the bundle, or generate one with `ledger pack cases/<name>_ledger --out <dir>`.

- [COVID-origins](packs/covid_origins/index.html) — a belief presented as a result, one disputed
  support, and two supporters marked as potentially correlated.
- [Eggs and cholesterol](packs/eggs_cholesterol/index.html) — sixteen studies reduce to a handful of
  reused patient cohorts, and the detector raises three possible-dependence warnings, on both sides
  of the question.
- [LHC safety](packs/lhc_safety/index.html) — the safety argument traced from its headline claim down
  to the exact sentence and reply it rests on.
- [Quantum computing for genomics](packs/quantum_genomics/index.html) — a subject outside the author's
  field, where the claimed speed-up turns on a single contested result, and the double-count detector
  flags two of the sceptical sources as potentially dependent rather than independent.
- [COVID debate](packs/covid_debate/index.html) — a recorded public debate with no authored finding,
  shown as an empty interpretation layer, with the missing transcript declared as a gap rather than
  papered over.

## Method and architecture

If you want the machinery itself, hold three boundaries in mind. The low-level tools are the
enforcement layer — the gates that pass or fail. The `ledger` command is the researcher's workflow
over those gates. The plain Markdown and JSON files are the interchange format, so the artefacts can
be read and rebuilt without any of Ledger's own code.

Read more: the authoring discipline (`AGENTS.md`), the interchange spec
(`spec/INTERCHANGE.md`), the five-layer trust model
(`docs/integrity_framework.md`), and the configuration reference
(`docs/configuration.md`).

## Reproduction and limitations

The demo runs on Python 3.10 or newer with nothing installed; the tests and download tools need the
pip extras, and only the source-fetching toolchain needs conda. The raw sources are not shipped —
they are git-ignored — so a fresh clone re-proves nothing until you supply them. On the machine that
holds the sources the quotes are re-proved; everywhere else the stored proof is attested. A pack that
does not travel with its sources says "Attested", never "reproduced".

Four limits are worth stating plainly. The comparison baselines in the cases were written by the same
author, not by an independent evaluator. The citation parser cannot yet tell apart two papers by the
same author in the same year (a "Smith 2008a" versus "Smith 2008b"). The source-coverage checks prove
that each source has a declared route into the corpus and that no side of a question is silently empty
— not that the corpus is complete or representative. And whether any inference is apt stays a human
judgement, assisted but not decided by the machinery.
