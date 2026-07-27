# Ledger

A portable system for **source-faithful deep thinking in unfamiliar domains** — no cited
claim reaches prose without a verbatim, on-disk, mechanically-verified quote from a primary
source. It does not prove the source set is complete or the interpretation correct; it makes
those judgements explicit and reviewable.

Ledger began as the literature-review and concept-note system for my **PhD thesis**. It matured
when I carried that discipline into unfamiliar territory — contributing genomics insight to a
**quantum-computing white paper** (still unpublished), well outside my own field. I then
generalised the system into this standalone tool.

Only afterwards, while generalising this system, did I find that Andrej Karpathy had described
the same compounding-knowledge pattern — his [*LLM Wiki*](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f),
where an LLM incrementally builds an interlinked Markdown knowledge base from your sources. 
We seem to have arrived at our systems by optimising for different
things (compared below). 

What sets Ledger apart is that it leaves nothing to trust: every claim
that reaches prose is traceable to a verbatim quote from a primary source, enforced mechanically —
not by the model's good intentions. Like a double-entry ledger, nothing is posted without a matching
quoted entry.

## How Ledger relates to Karpathy's LLM Wiki

I built Ledger around **verification**. Nothing reaches the page without a verbatim
quote saved on disk (`verified_claims/`), checked by a script (`verify_quotes.py`) and blocked by a
hook if the quote is missing — so a confident invention cannot slip through. This was the spine from
the start, and it is precisely the part Karpathy's wiki leaves to trust: his lets the model
summarise and synthesise freely, which would not survive expert scrutiny unchanged.

What his wiki had that mine lacked was the **flywheel**: low-friction ingest, so knowledge piles up
and links itself, where mine moved sources into notes by hand. So I have also incorporated his system here — a
one-pass **ingest** that spreads a source across the wiki, **saving good answers back** as notes, a
per-source log, and a **semantic lint** for contradictions, stale claims, and orphans (now
`skill-ledger-curate`). Each borrowed piece sits on the verification spine: ingest cannot invent,
every fix still routes through `verified_claims/`, and the result is a report a human approves —
never an auto-applied edit.

## The starter kit

This is the **reusable machinery**: copy it to begin a _Ledgered_ project on any subject:

```
literature/                  # intake — verify before you trust
  check.sh                   # is this source already on disk?
  fetch_paper.sh             # download ladder: PMC / DOI / Unpaywall / OpenAlex / web
  build_register.py          # build the source register from disk + ledgers
  extract_text.py            # greppable text from PDF/HTML
  verify_quotes.py           # check every cited quote is verbatim in the source
  verified_claims/TEMPLATE.md
content/                     # the knowledge base (starts empty)
  concept_notes/  literature_reviews/
  crosswalk.md               # the index (note ↔ review ↔ source ↔ §)
  log.md                     # append-only, greppable activity log
  _ledger/skin_rules.md      # subject-specific writing rules (filled at setup)
.claude/
  hooks/verify-citations.sh  # the travelling guard — blocks unverified citations
  settings.json              # registers the guard (self-locating via $CLAUDE_PROJECT_DIR)
.githooks/
  pre-commit                 # agent-neutral gate — same checks at COMMIT time (any editor/agent)
.github/workflows/
  ci.yml                     # fresh-clone CI — citation coverage + wiki lint + tests + no-raw-papers
tools/
  check_citations.py         # citation coverage gate (paper + ledger per cite) — shared by all 3 points
  check_manifest.py          # provenance attestation — every committed ledger carries a valid stamp
  ledger_doctor.py           # project health — pristine kit / configured / half-bootstrapped
  lint_wiki.py               # mechanical wiki health-check (dead links, orphans, uncatalogued)
tests/                       # enforcement-layer suite (corpus-free; runs in CI)
  smoke/                     # one real open-access extract + ledger — proves the verify loop end-to-end
AGENTS.md                    # portable authoring discipline — any agent or by hand (the skills, in-repo)
ledger.config.md             # the few per-project settings
environment.yml              # conda toolchain (bs4/lxml/pypdf, node, gh, jq, curl)
```

Setup: `conda env create -f environment.yml && conda activate ledger_env` before running the
intake pipeline (the scripts need `bs4`/`pypdf`/`lxml`; system python won't have them). Then
activate the commit-time gate once per clone: `git config core.hooksPath .githooks`.

The citation gate is **mechanical, not advisory**, enforced at three points by one shared
checker (`tools/check_citations.py`), so it cannot drift between agents. What runs where differs
by what each point can see:

- **Write-time** — the Claude Code `PreToolUse` hook blocks a citation with no paper on disk and
  no verified-claims ledger as you write.
- **Commit-time** — `.githooks/pre-commit` re-runs that coverage check, plus `verify_quotes.py`
  (every ledger quote is *verbatim* in its source — needs the local corpus) and the wiki lint —
  whatever drives the edit (Claude Code, Codex via `AGENTS.md`, or hand-editing).
- **Push-time** — CI re-checks citation→ledger coverage (`--no-corpus`: the corpus is git-ignored,
  so paper-on-disk and the verbatim check can't run here), the wiki lint, the unit tests, and the
  no-raw-sources / ledger-shape contract.

The verbatim guarantee is therefore local (it needs the sources); the *coverage* guarantee —
no citation without a committed ledger — holds everywhere, on any path. The gate does not depend
on any one tool.

**Provenance.** Each ledger's frontmatter carries a stamp — the sha256 of the source, of the
extract, and of the ledger's own body (the quotes themselves), plus the verifier version, the
verdict, and the date — written by `verify_quotes.py --stamp`. Because the stamp travels with the
committed ledger, the verbatim result is no longer invisible outside one machine: pre-commit
**re-binds** it (recomputes the hashes and compares — a changed source, a stale stamp, or a
non-pass verdict blocks the commit), and CI **attests** it (`check_manifest.py` checks every
committed ledger's stamp is well-formed and passing). CI can't re-prove the *source* bytes — the
corpus is git-ignored — but it **can** recompute the body hash from the committed ledger, so a quote
edited after stamping is caught at the push gate, not only locally. The honest line is *source
binding at commit, body + shape attestation in CI*. The stamp is also the source-identity authority:
`build_register.py` flags any file whose DOI or bytes disagree with the ledger that attests it, and
under `required` every ledger must name its source (`file`, `source_version`, `retrieved`, and at
least one durable locator — `doi`/`pmcid`/`url`): hashes prove the bytes are unchanged, identity
proves they are the *intended* paper. `--stamp` also writes an auditable **run-record** next to each
ledger (`verified_claims/_runs/<key>.run.json`) capturing the extraction toolchain, the committer,
the verbatim transcript hash, and a self-seal; CI cross-checks the body hash across the ledger, the
stamp, and the run-record. This is *auditable, attributable attestation* — it raises the cost and
traceability of forgery — not independent proof (CI has no corpus to re-hash). Posture is
`provenance:` in `ledger.config.md` (`off`/`warn`/`required`; the kit ships `warn`, bootstrap sets
`required`). A tracked `project_state: pristine|configured` lets `ledger_doctor` assert that a real
project actually adopted the strict postures, rather than silently running the permissive kit
defaults.

One scoped caveat: the gate resolves **author–date** citations (`Surname YYYY`, `et al.`, `&`).
**Numeric / superscript** styles (`[42]`, `method.⁵⁴`) can't be mapped to a ledger without a
references map, so by default they are *detected and warned*, not blocked. Set
`numeric_citations: block` in `ledger.config.md` to fail the gate on them everywhere (all three
points honour it — no need to hand-edit the hook/pre-commit/CI), or keep author–date where the
guarantee is absolute. A `--numeric` flag overrides the config posture for a one-off run.

A cite can also point at a *specific* claim, not just the paper: `(Smith 2020 #c1)`, where `#c1`
is the claim's ordinal in its ledger (or an explicit `**ID:**` alias). A ref that names a
non-existent claim fails the gate. This closes the **"right paper, wrong claim"** gap — a bare
`(Smith 2020)` passes as long as the paper has *any* ledger, even if the sentence doesn't match
what the paper actually says. So **`skill-ledger-bootstrap` sets `claim_ids: required` by default**
for a real project (the starter kit ships `optional`, since it has no prose), forcing every cite
to name its quoted claim; `ledger_doctor --require-configured` asserts a configured project kept
that default. Under `required`, a **bare ordinal** (`#c1`) is also rejected — ordinals silently
re-point if claims are reordered, so prose must use the stable `**ID:**` slug (`--allow-ordinal-refs`
overrides). Set `claim_ids: optional` or `off` in `ledger.config.md` to deliberately relax it.

**Synthesis** (turning verified claims into prose, one section at a time) and the **curation**
loop (ingest · save-good-answers · health-check) ship in the repo as **`AGENTS.md`** — the
agent-neutral authoring discipline any agent, or a careful human, can follow. So a clone gets
the whole system, not just the verification guarantee.

In Claude Code the same discipline is delivered as installed skills — the **writing assistant**
`skill-ledger-write`, the **curator** `skill-ledger-curate`, and the **setup helper**
`skill-ledger-bootstrap` — for nicer ergonomics; they live once in `~/.claude/skills/`, not per
repo. The discipline is identical either way: `AGENTS.md` is the portable copy, the skills are the
Claude Code frontend.

## Starting a new subject

1. Copy this starter kit to a new project folder and `git init`.
2. Invoke `skill-ledger-bootstrap` — it interviews you (subject, reader, format, source types,
   sharing), drafts your subject-specific writing rules for you to refine, fills `ledger.config.md`
   and `CLAUDE.md`, and proves the loop end-to-end on one real source.
3. Start sourcing and writing. The guard makes sure nothing unverified reaches the page.
