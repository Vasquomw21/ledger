# Configuring a Ledger project

Everything a project decides lives in one file, `ledger.config.md`. It is plain `key: value`
Markdown: read it, diff it, edit it by hand. This page is the reference; the
[README](../README.md) is the introduction.

Run `ledger config effective` to see how your config is actually being read, `ledger doctor` for
project health, and `ledger profiles` to print a whole coherent posture set you can paste in.

## Setting up: `ledger init`

```
ledger init [DIR] [--set key=value] [--rule TEXT] [--reconfigure] [--dry-run] [--yes]
```

Fills the per-subject fields below and, if you give it any rules, writes them into the subject
skin. It previews both, asks, then makes one atomic write per file. Anything you do not answer it
asks for; with no terminal to ask at, give it with `--set` and pass `--yes` — a pipe is never
consent. Ctrl-C at any prompt abandons the run and writes nothing.

**init replaces the kit's own scaffold and creates nothing.** A missing `ledger.config.md`, skin,
or declared directory is a refusal, not something init makes for you: a file it created could not
be un-made if a later step failed, and this kit never deletes. Everything it does write is
therefore recoverable by putting the retained bytes back.

**The skin is yours.** Once it holds rules, init never rewrites it — `--reconfigure` re-answers the
config only.

A first run lands `drafted`, and says so. Finishing it takes four more steps, which init prints:

1. Sharpen the skin into rules you stand behind.
2. Arm the gates: `ledger config set profile strict-local`.
3. Declare it finished: set `skin_state: confirmed`, `project_state: configured`.
4. Confirm it all agrees: `ledger doctor`.
5. See which gates hold: `ledger check`.

Step 2 is not bookkeeping. A configured project is strict by definition, and init adopts no
postures on your behalf — so declaring it finished without arming the gates leaves a project
`ledger doctor` rejects. The two halves are deliberately separate: adopting postures is a claim
about how strict you want to be, declaring the state is a claim that the work is done, and neither
should be inferred from the other.

## Project identity

Filled once, at setup. `ledger init` asks for the six marked ★ (`skill-ledger-bootstrap` is the
Claude Code equivalent); the rest you edit directly.

| key | what it is |
| --- | --- |
| ★ `project_name` | short slug for the subject |
| `project_root` | absolute path on disk |
| ★ `deliverable` | what you are writing (thesis chapter, white paper, report…) |
| ★ `source_of_truth` | where the prose finally lives |
| ★ `the_reader` | who you are writing for — the skin rules turn on this |
| ★ `source_types` | what counts as a primary source here |
| ★ `unpaywall_email` | used by one rung of the download ladder (optional) |
| `skin_rules_file` | subject-specific writing rules (default `content/_ledger/skin_rules.md`) |
| `writing_skill` | the optional Claude Code writing frontend (default `skill-ledger-write`) |
| `shared_with` | solo, or co-authors via git |

`writing_skill` names an ergonomic frontend, not a gate. No enforcement reads it: the mechanical
checks are agent-neutral, and [`AGENTS.md`](../AGENTS.md) carries the same discipline for any agent
or a careful human. A project that never opens Claude Code loses nothing enforced by leaving it set.

## Project state — the strictness keystone

Two declared fields:

```
project_state:       pristine | configured
skin_state:          draft | confirmed
```

`ledger_doctor` reconciles what you declare against what the files actually show, and reports one
of four states:

| state | what it means |
| --- | --- |
| `pristine` | the untouched starter kit: placeholders everywhere, no skin, nothing to prove yet — the gates run soft |
| `drafted` | set up, but the skin holds rules nobody has stood behind yet (`skin_state: draft`). Nothing contradicts, so it is not broken; not finished either, so the gates stay lenient |
| `configured` | filled in, skin written and stood behind. **Strict by definition** |
| `broken` | what you declare contradicts what the files show. Blocks until they agree |

**A configured project is strict by definition.** `ledger_doctor` runs at every gate and hard-fails
a `configured` project that has not adopted all five strict postures (`claim_ids: required`,
`numeric_citations: block`, `provenance: required`, `structure_layer: required`,
`assessment_layer: required`). To run softer, a project must stay pristine or drafted — the point is
that "configured but lax" cannot exist quietly.

`drafted` exists so a project can be *honestly* half-finished. A skin of filler is worse than a skin
that admits it is empty, so declining to write rules is a supported answer, not a failure:
`ledger init` records `skin_state: draft`, the project reads as `drafted`, and the gates stay
lenient until you sharpen the rules and confirm them.

Declaring `configured` while the config is half-filled — or while `skin_state` is still `draft` — is
`broken`, and blocks. `confirmed` on a skin that does not exist is broken too: it is a claim about
rules, and it cannot conjure them.

A config written before `skin_state` existed simply omits it; a written-looking skin still reads as
`configured`, so older projects are unaffected.

## `gated_paths` — what the citation gate reads

```
gated_paths:         content/concept_notes/, content/literature_reviews/, content/inquiry.md
```

Directories or individual files. A path matches by prefix, so naming a directory covers
everything under it, and naming one file gates exactly that file — useful when authored prose
sits beside prose you do not gate.

A `configured` project whose `gated_paths` matches **none** of its authored prose is blocked: a gate
that reads nothing reports success having checked nothing, which is the failure this whole system
exists to prevent. Bookkeeping (`log.md`, `crosswalk.md`, `source_register.md`, `source_flow.md`,
`_ledger/`) does not count as prose — a project that has not been written yet is not misconfigured.

To gate nothing on purpose, say so:

```
gated_paths:         none
```

Silence is the bug; a declaration is not.

## `citation_aliases` — cite the author, not the filename

```
citation_aliases:    drouin-chartier_2020 -> drouin_2020
```

A cite resolves to a ledger by filename convention (`<author>_<year>`), and punctuation is handled
already (`la-602` finds `la602_1946.md`). What it cannot bridge is a key that *abbreviates* the
surname: cite `Drouin-Chartier et al. (2020)` against a ledger keyed `drouin_2020` and the resolver
misses.

The cheap fix — clipping the surname in your prose — lets an internal filename dictate your
bibliography. An alias fixes it the right way round: the ledger key stays canonical (it is what
graph edges and sealed assessment records address), and the prose names the author accurately.

Aliases must resolve one way only. Shadowing a real ledger, aliasing the same key twice, or pointing
at a ledger that does not exist all block. An alias points at a real ledger, never at another alias,
so chains cannot form.

## Postures — what each gate does when it fires

Each gate reads one key. The kit's defaults are **not uniformly off**: six default to
`optional`/`warn`, so an absent key does not mean an inactive gate.

### The five strict postures

Required of any `configured` project.

| key | values | what it governs |
| --- | --- | --- |
| `claim_ids` | `off` · `optional` · `required` | must a cite name the *claim* it rests on (`Smith 2020 #slug`), not just the paper? Under `required`, bare ordinals (`#c1`) are rejected — they silently re-point when claims are reordered |
| `numeric_citations` | `ignore` · `warn` · `block` | numeric/superscript styles (`[42]`, `method.⁵⁴`) cannot be mapped to a ledger without a references map, so they are detected, not resolved |
| `provenance` | `off` · `warn` · `required` | must each ledger carry its source identity (`file`, `source_version`, `retrieved`, and a `doi`/`pmcid`/`url`) alongside its stamp? |
| `structure_layer` | `off` · `optional` · `required` | must every claim-graph edge resolve cross-ledger and carry a resolvable `(grounded by #slug)`? |
| `assessment_layer` | `off` · `optional` · `required` | must judgement records be sealed, grounded, and fresh? |

### Opt-in postures

Default off or warn. Turn them on as a project earns them.

| key | values | what it adds |
| --- | --- | --- |
| `graph_coverage` | `off` · `warn` · `required` | every claim cited with a `#ref` must have a role in the argument graph |
| `edge_assessments` | `off` · `warn` · `required` | supports/rebuts edges must carry a judgement |
| `selection_audit` | `off` · `warn` · `required` | every stamped ledger registered in `content/source_register.md` with a discovery trail, and every declared position covered or named as a gap |
| `source_flow` | `off` · `warn` · `required` | a PRISMA-like route into the corpus per ledger, in `content/source_flow.md` |
| `units_layer` | `off` · `warn` · `required` | quotes fall within their declared unit manifest |
| `synthesis_claims` | `off` · `warn` · `required` | significance/novelty claims in synthesis prose are anchored or hedged — enforces *form*, not truth |
| `attestation` | `off` · `warn` · `required` | run-records carry a detached SSH signature (`attestation_signers`) |
| `semantic_health` | `off` · `warn` · `required` | a semantic review exists and is fresher than `semantic_max_age_days` (default 180) |

## Profiles

A profile is a whole coherent posture set under one name. `ledger profiles <name>` prints the
block; you paste it in. Nothing is auto-applied — a config edit is yours to make.

| profile | for |
| --- | --- |
| `pristine` | the untouched starter kit — lax by design, nothing to prove yet |
| `strict-local` | a configured subject: all five strict postures bite locally |
| `submission` | everything on — a reviewed, shareable artefact |

## Reading your config back

```
ledger config effective [DIR]
```

Prints the declared `project_state`, the derived health (`pristine` / `configured` / `broken`),
whether the gates run strict or lenient, and — for each of the 13 postures — the value it resolves
to and whether that came from your config or the kernel default. The six postures that default to
`optional`/`warn` are why this matters: an absent key is not an inactive gate, and the report names
which is which.

Health and strictness are reported separately because they come apart. A `broken` project — one
declaring `configured` whose config or skin is unfinished — runs **lenient**, which is the opposite
of what its declaration promises. The report says so and prints `ledger doctor`'s diagnosis
verbatim, rather than filing it under the same "nothing to prove yet" gloss a pristine kit gets.

It then says which profile your postures sit closest to, and lists every difference. That is
**description, not resolution**. There is no `profile:` field, so nothing is resolved *through* a
profile: each posture resolves `explicit → kernel default` on its own, and the nearest-profile line
is a summary computed afterwards. `project_state` is excluded from the comparison — it declares
strictness rather than configuring a gate. Where a project sits equally close to two profiles, both
are named rather than one picked.

Read-only. It never edits `ledger.config.md`.

## Adopting a profile

```
ledger config diff profile <name>          # what would change — read-only
ledger config set profile <name>           # preview, confirm, then write
```

`set` previews the exact diff, asks, then makes one atomic write. Everything outside the changed
values is preserved byte-for-byte — comments, padding, inline notes, a missing trailing newline, and
the file's permissions. Re-running is a no-op. `--dry-run` previews without writing; `--yes` skips
the prompt and is **required** when not run from a terminal, so a pipe or a CI job can never be
mistaken for consent.

**The write is bound to the diff you were shown.** If the file changes while you are deciding, the
write is refused and you get a fresh preview — otherwise you would be consenting to one change and
getting another.

Two shapes of config are refused rather than edited, both because the file already means something
other than it looks:

- **a duplicated key** — readers keep the last occurrence, so editing one occurrence writes into an
  ambiguity;
- **a line that is neither a comment nor a `key: value` declaration** — `claim_ids required`, with
  the colon dropped, is skipped by every reader, so the posture silently falls to its kernel default
  while the line still reads as a declaration.

Indented declarations are fine: every reader strips before parsing, so `  claim_ids: required` is
read normally. Validation runs before anything is written, so a rejected change never reaches the
disk and there is no partial write to undo.

The write stages through a sibling file (`.ledger.config.md.ledger-new`) before an atomic swap. If
something is already at that path, the write is refused and the file is left exactly as found —
never opened, truncated, or removed for you. Deciding whether it is a leftover from an interrupted
run or something of your own is your call, not the tool's.

**`project_state` is never written.** A profile block carries it for you to paste once your config
is genuinely finished; stamping `configured` onto a half-filled project makes `ledger doctor` report
`broken`, and a broken project's gates run lenient while its config claims strictness. Adopt the
postures with `set`, declare `project_state` yourself, then check the result with
`ledger config effective`.

The config is git-tracked: review an applied change with `git diff ledger.config.md`. To undo it,
revert the value changes shown, or use `git restore -p ledger.config.md` to pick them out — a plain
`git restore` would also discard any unrelated edits of your own in that file. `ledger profiles
<name>` still prints a block to paste in by hand if you would rather not let a command touch the
file at all.

## Where the gates run

Citation coverage is enforced from one shared checker (`tools/check_citations.py`) at write, commit
and CI, so it cannot drift between them. The broader gate set runs at commit and in CI wherever its
required inputs are available. Source-byte verification stays local, because the corpus is
git-ignored.

- **write-time** — `.claude/hooks/verify-citations.sh` blocks an unverified citation as you write.
  It sees one file, not the project, so it runs the coverage check alone.
- **commit-time** — `.githooks/pre-commit` runs the full set, including the verbatim re-proof
  against the sources on disk (activate once per clone: `git config core.hooksPath .githooks`).
- **push-time** — CI runs the same set minus the verbatim check: with no corpus to re-hash it
  attests each committed stamp instead — auditable attestation, not independent proof.

See [DEMO.md](../DEMO.md) for that boundary in full.
