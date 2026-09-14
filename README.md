# Ledger

Ledger is a research toolkit for people and AI working together. It keeps a growing knowledge base
tied to its evidence: every citation in gated, authored prose must point to a quotation checked
against the original source, while the claims, their connections, and human judgements remain
visible and reviewable.

Ledger does not establish that the sources are complete, the reasoning is sound, or the conclusion
is true. When the source files are unavailable, it attests the committed proof rather than
re-checking the bytes.

> **Website:** [vasquomw21.github.io/ledger](https://vasquomw21.github.io/ledger/) — what Ledger
> does, and the five worked cases in your browser with nothing to install.
>
> **Evaluating rather than using it?** [`DEMO.md`](DEMO.md) is the audit path: a one-command
> read-only tour, five worked cases, and the trust boundary.

## What it guarantees

> Ledger prevents a citation in gated, authored prose from pointing to a quotation that has not
> been verified verbatim against its source. It does not prove that the source set is complete or
> the interpretation correct; it makes those judgements explicit and reviewable.

Before citing a source you save its quotes to a ledger on disk
(`literature/verified_claims/<key>.md`). A script extracts the source's text, confirms each quote
character for character against it, and stamps the ledger with the SHA-256 of the source, the
extract, the quotes, and the source bytes the extract was built from — so the quotation is tied to
the paper itself, not merely to a text file sitting beside it. Only then does a citation pass — and
a cite can name the claim it rests on, `(Smith 2020 #the-slug)`, so "right paper, wrong claim" fails
too.

You declare which prose this covers (`gated_paths`), and a configured project that gates none of its
prose is blocked — a gate reading nothing reports success having checked nothing. Material you
archive rather than assert, such as a captured model transcript, stays ungated
([`cases/README.md`](cases/README.md)).

Citation coverage runs from one shared checker at three points — as you write, at commit, and in CI
— so it cannot drift. It depends on no particular editor, agent, or model; the kit ships none.

## What it does not guarantee

The mechanical part is narrow on purpose; everything above it is scoped, not proved:

- **Not completeness.** Whether your sources are the right ones, or whether you missed the
  literature that would change your mind, is a judgement. Ledger makes the corpus and its declared
  gaps auditable; it cannot tell you what you never looked for.
- **Not context.** A quote can be verbatim and still be used in a way its author would reject.
  Ledger surfaces every quote against the inference it grounds, and ships a benchmark to measure
  detection — but does not settle aptness.
- **Not the conclusion.** Whether your argument follows is yours. The claim graph makes the
  structure explicit — what is load-bearing, what rests on one source, where two "independent"
  sources share a premise — and stops there.
- **Not in CI.** The verbatim check needs the sources, which are git-ignored. Locally it re-proves
  the bytes; CI attests the committed stamp — auditable attestation, not independent proof.

Freedom from fabrication is a claim about layer 1 only. The rest is graded confidence:
[`docs/integrity_framework.md`](docs/integrity_framework.md) lays out all five layers.

## Try it in five minutes

Needs only `python3` ≥3.10 — the demo tools are pure stdlib, no installs:

```bash
make demo                                  # tour this repo (empty by design)
make demo DIR=cases/covid_origins_ledger   # tour a worked case
```

Five worked cases are vendored under [`cases/`](cases/), each a standalone project:
contested debate, closed technical, messy confounded, a recorded debate, and one outside the
author's field. They ship ledgers but not sources, so the tour attests committed stamps rather than
re-proving bytes — that boundary visible in the run.

## Use Ledger today

1. Copy this kit to a new folder and `git init`.
2. Activate the commit gate once: `git config core.hooksPath .githooks`.
3. Fill in `ledger.config.md` — `ledger init` interviews you and writes it (preview, then confirm);
   `skill-ledger-bootstrap` does the same in Claude Code and proves the loop on one real source; or
   edit it by hand ([`docs/extending.md`](docs/extending.md#1-stand-up-a-new-subject-by-hand)).
4. Add sources and write. The gate refuses anything unverified.

`ledger check` is the one verb: every applicable gate, inactive ones hidden, the corpus ceiling
stated once, exactly one next action. `ledger inspect <area>` runs a single gate or view. Tests and
intake need the pip extras (`pip install -r requirements.txt`); the download toolchain is an
optional conda env (`make conda-env`).

## Configuration

One plain-Markdown file, `ledger.config.md`. The keys that matter most: `project_state`
(`pristine` or `configured` — **a configured project is strict by definition**; `ledger doctor`
enforces it), `skin_state` (`draft` until you stand behind the subject's writing rules, which reads
as `drafted` and keeps the gates lenient — a half-finished project can say so), `gated_paths`, and a
posture per gate (`off` / `warn` / `required`).
`ledger profiles strict-local` prints a coherent set to paste in. Full reference:
[`docs/configuration.md`](docs/configuration.md).

## Where to go next

| you want | read |
| --- | --- |
| to evaluate or audit it | [`DEMO.md`](DEMO.md) |
| a guided evaluator walk-through | [`EVALUATOR_GUIDE.md`](EVALUATOR_GUIDE.md) |
| the trust model in full | [`docs/integrity_framework.md`](docs/integrity_framework.md) |
| every config key | [`docs/configuration.md`](docs/configuration.md) |
| to extend it, or use it without Claude Code | [`docs/extending.md`](docs/extending.md) |
| the interchange format | [`spec/INTERCHANGE.md`](spec/INTERCHANGE.md) |
| how context misuse is measured | [`docs/faithfulness_eval.md`](docs/faithfulness_eval.md) |

The authoring discipline ships as [`AGENTS.md`](AGENTS.md), readable by any agent or a careful
human. Claude Code also installs it as skills; the discipline is identical either way.

## Background

Ledger began as the literature-review system for my PhD thesis, maturing when I carried that
discipline into unfamiliar territory — contributing genomics insight to a quantum-computing white
paper, well outside my field. I generalised it into this kit.

I later found Andrej Karpathy had described the same compounding-knowledge pattern in his
[*LLM Wiki*](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). We optimised for
different things: I built around verification, where his lets the model summarise freely; his had
the flywheel mine lacked — low-friction ingest. That ingest now sits on the verification spine as
`skill-ledger-curate`: it cannot invent, and a human approves its output.

## Licence

The kit is [Apache-2.0](LICENSE); the case content under `cases/` is
[CC BY 4.0](LICENSES/CC-BY-4.0.txt). Quotations from published works stay with their authors and
are licensed by neither. [LICENSING.md](LICENSING.md) says which files fall under which licence.
