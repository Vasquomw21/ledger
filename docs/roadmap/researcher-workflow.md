# Ledger 0.2 researcher-workflow and kernel redesign

## Status

> This tracked file is the LIVE plan of record and is now self-sufficient: every section of the
> original scratch copy `LEDGER_0_2_REDESIGN_ROADMAP.md` is present here (verified by heading diff
> on 20260716, after E1 was found missing), plus the per-milestone "As built" records. The root
> copy is git-ignored (`.gitignore:53`), is NOT kept in sync, and is now only a historical working
> copy — read this file.

- Current phase: Phase 1 - surface compression
- Last completed milestone: C5 - safe configuration mutation, **merged to main at `b9b1ba8`**.
  `config diff|set profile <name>` on shared primitives (`tools/config_edit.py`): validated parse,
  duplicate detection, preview bound to the write by digest, confirmed write, byte + permission
  preservation, idempotence, no partial writes, staging path never followed.
- **Last completed milestone: C6 - safe `ledger init`** (COMPLETE on `feature/safe-init`, not yet
  merged), split five ways: C6a kernel foundation · C6b `tools/init_plan.py` (pure construction) ·
  C6c `tools/init_apply.py` (the replace-only writer) · C6d the `ledger init` workflow + routing ·
  C6e docs, tracking and the re-vendor decision — **all landed**. `ledger init` is live and
  advertised; `add`/`review`/`publish` are not. See "As built (C6a/C6b/C6c/C6d/C6e)".
- **E1 - evaluator experience pass: COMPLETE** on `feature/evaluator-experience` (not yet merged).
  Three-layer trust model (derived / recorded judgements / authored interpretation from one shared
  model both surfaces consume), Stage-3 typed correlations (`content/correlation_kinds.md`, never in
  stamped bodies), the eggs `finding.md`, and the tracked judge-doc sync all landed; mechanical
  closeout green (887 tests, 13 gates, 5 demos/dashboards/packs, vendor+gate parity, offline/contrast)
  and the release-blocking manual browser pass PASSED on 20260716 (covid primary + four smoke cases;
  light/dark, desktop/narrow, JS off, tab order + visible focus).
- Merged to main: C1-C4 at `4874d78` (read-only slice), C5 at `b9b1ba8`. Nothing pushed —
  `origin/main` is still `f904444`.
- Compatibility baseline: 616 tests green at the C5 merge (353 at Step 0 + 263 across
  C1/C2/C2.1/C4/C5); gates, hooks and CI unchanged; all 5 demos exit 0; pristine root doctor +
  check exit 0; 12 gated files across the five cases; pack + dashboard build

This file is the durable source of truth for the redesign. After a context reset, read this file
before continuing. Update this status block whenever a milestone lands.

## 1. Scope

This roadmap improves the complete Ledger repository:

- researcher-facing workflow;
- command-line interface;
- configuration and profiles;
- diagnostics and error recovery;
- internal architecture;
- evidence acquisition and intake;
- judgement and review workflow;
- publication readiness;
- packaging;
- worked cases;
- documentation.

Existing evaluator surfaces, including `ledger demo`, dashboards and judge packs, are compatibility
constraints rather than the scope of the redesign.

Ledger's evidence model remains intact. The redesign preserves every enforcement gate and the
plain-file protocol while reorganising the interface around:

```text
init -> add -> check -> review -> publish
```

A workflow verb is introduced only when Ledger can complete the action it promises. Until then, the
existing lower-level command retains its honest name.

## 2. Product diagnosis

Ledger's epistemic architecture is strong, but its interface exposes that architecture too early. A
researcher currently encounters more than 26 CLI verbs, a 17-stage evaluator tour, 13 postures and a
119-line configuration template before seeing an ordinary research workflow.

The redesign does not remove this machinery. It progressively discloses it:

1. normal research work;
2. advanced inspection;
3. enforcement and protocol development.

## 3. Standing boundary

The repository has three distinct public layers:

- **Low-level tools are the enforcement API.** Hooks and continuous integration invoke stable tool
  files directly.
- **The CLI is the researcher workflow.** It organises tools around research intentions and
  recovery paths.
- **Plain files are the interoperability protocol.** Markdown and JSON remain inspectable,
  portable sources of truth.

## 4. Governing principles

1. High-level verbs must fulfil their semantic promise.
2. Working drafts must never masquerade as committed evidence artefacts.
3. Structured diagnostic semantics are stable; human-readable wording may improve.
4. The normal interface hides inactive machinery; advanced inspection remains complete.
5. Profiles determine defaults; explicit project overrides remain auditable.
6. The repository kernel is called in-process only when version compatibility is known.
7. Every mutation is previewable, idempotent where possible and recoverable on failure.
8. The roadmap itself is tracked and reviewable.
9. Mechanical guarantees must not be weakened for convenience.
10. A judgement-dependent result must never be presented as a mechanical verdict.

## 5. Compatibility baseline

At the start of the redesign:

- 353 tests pass.
- CI and pre-commit invoke tools by file path, not through CLI verbs.
- Tool filenames are therefore frozen compatibility interfaces.
- Tests import tools through `tests/conftest.py`.
- `tests/test_postures.py` requires all 13 posture keys in the current root template.
- Existing CLI tests monkeypatch `_run(root, rel, args)`; that signature remains stable in Phase 1.
- Gates emit `[INFO]`, `[WARNING]` and `[ERROR]` lines and return `0`, `1`, or `2`.
- There is no structured JSON diagnostic output.
- Configuration parsing is currently centralised in `tools/check_citations.py`.
- `check_citations.py` already supports `--no-corpus`.
- Kernel posture defaults are not uniformly off.
- `tools/audit_pack.py` and its test are untracked user-owned work and must not be staged blindly.

## 6. Phase 1 - compress the researcher-facing surface

### Definition of done

A researcher can run `ledger check` and receive a concise account of every applicable enforcement
gate, the project's corpus-dependent verification ceiling, any blocking failure, one concrete
remediation and exactly one existing next action.

Inactive mechanisms remain hidden by default. The evaluator tour, low-level tools, hooks, CI, cases
and plain-file protocol continue to behave as before.

### C1 - add `ledger check`

#### Canonical step metadata

Replace parallel command lists with one registry:

```python
@dataclass(frozen=True)
class Step:
    label: str
    command: str
    gate: bool
    demo: bool
    posture: str | None
    corpus_policy: CorpusPolicy
    extra_args: tuple[str, ...]
```

Derive both gate and legacy demo views:

```python
STEPS: tuple[Step, ...] = (...)
GATE_STEPS = tuple(step for step in STEPS if step.gate)
DEMO_STEPS = [
    (step.label, step.command, list(step.extra_args))
    for step in STEPS
    if step.demo
]
```

Retain the legacy `DEMO_STEPS` tuple shape. Test that `GATE_STEPS` matches the pre-commit gate set.

#### Preserve CLI execution compatibility

Keep `_run(root, rel, args)` with its existing signature. Extract command construction into
`_command(root, rel, args)` and add `_capture(root, rel, args)`, returning stdout, stderr, the raw
return code and a combined presentation stream as reliably as practical.

#### Effective posture resolution

During Phase 1:

```text
explicit value -> kernel default
```

There is no authoritative profile field yet. Inferred profile resemblance never affects resolution.
Define `POSTURE_DEFAULTS` centrally in `ledger_cli.py` and test it against existing gate readers.

During Phase 2, after a declared profile exists:

```text
explicit override -> declared profile default -> kernel default
```

#### Corpus policy

```python
class CorpusPolicy(Enum):
    NONE = "none"
    REQUIRED_FOR_EXISTING_LEDGERS = "required-for-existing-ledgers"
    DEGRADES_WITHOUT_CORPUS = "degrades-without-corpus"
```

- `NONE`: invoke normally.
- `REQUIRED_FOR_EXISTING_LEDGERS`: no ledgers means nothing to re-prove; with ledgers and corpus,
  re-prove quotations; with ledgers but no corpus, report `UNAVAILABLE`.
- `DEGRADES_WITHOUT_CORPUS`: invoke normally with a corpus and explicitly with `--no-corpus`
  without one.

Citation checking therefore continues enforcing committed-ledger coverage without source bytes.

#### Exit semantics

```python
def normalise_exit(rc: int) -> int:
    if rc == 0:
        return 0
    if rc == 1:
        return 1
    return 2
```

- `0`: completed without blocking findings;
- `1`: completed and found a blocking project or research issue;
- `2`: could not execute correctly.

Preserve the raw return code in verbose diagnostics.

#### Unavailable-proof policy

`UNAVAILABLE` has no universal exit contribution.

For `ledger check`:

- no ledgers: no unavailable result;
- lenient or pristine project with unavailable corpus proof: advisory, exit contribution `0`;
- configured strict project with real ledgers but no corpus: blocking, exit contribution `1`.

For `ledger demo`, preserve the current non-blocking evaluator-tour behaviour and explain that
committed stamps are attested rather than source bytes re-proved.

#### Output

Default output shows applicable gates only, hides inactive gates, prints captured tool output only
on failure or error, states the corpus ceiling once, distinguishes `FAIL`, `ERROR` and
`unavailable`, and prints only non-empty summary categories. `--verbose` shows inactive gates and
underlying output.

Warning counts are display metadata only. Return codes determine blocking status. The transitional
warning parser strips recognised ANSI sequences and counts only lines matching:

```python
WARNING_LINE = re.compile(r"^\s*\[WARNING\](?:\s|$)")
```

Return exactly one next action and name an existing command:

- first blocking gate: its concrete remediation;
- lenient, all green: `ledger profiles strict-local`;
- strict, all green: `ledger analyze` initially, `ledger inspect analysis` after C2 and
  `ledger review` after Phase 4.

Update `LEDGER_MAP.md`, its required snapshot and `PROGRESS_LOG.md` with the shape change.

#### As built (C1)

Landed as specified, with these decisions recorded for Phase 2:

- **Inactive gates are hidden, not skipped.** `check` runs every applicable gate and reads the
  postures only to decide what to display. Phase 1 resolves postures in `ledger_cli.py`, so a
  drifted default could mislabel a live gate as inactive; running the gate anyway means such a
  drift costs a hidden line, never a missed failure. A gate that fails is shown whatever its
  posture. Phase 2's `M2.4` may revisit this once `ledger_core` owns one resolution
  (`Inactive gates produce no result` in section 8 assumes that single owner).
- **Exit precedence: error over failure.** Any gate that could not execute yields `2` even
  alongside a real `1` finding, because `check` cannot then claim it ran the full set. Both are
  non-zero, and both are listed in the output.
- **A gate the target kernel lacks is `unavailable`, not `error`**, matching how the evaluator tour
  treats a vendored case with an older kernel. Its blocking contribution is contextual, on the same
  pattern as absent corpus proof: advisory for a lenient project or where the gate's posture is
  `off`; **blocking for a strict project where the gate applies** - that project's own pre-commit
  cannot run the gate either, so nothing about it has been established and an absent tool must not
  read as a satisfied one. `unavailable` therefore carries a cause (`no-corpus` /
  `kernel-missing-tool`), because the two need different remediations; section 8 promotes these to
  stable cause codes.
- **`_capture` loses true stdout/stderr interleaving** (they are captured separately). Gate lines
  are self-labelling, so order across the two streams carries no meaning.
- **Corpus state is reported only once ledgers exist.** The kit ships a smoke-test extract, so
  `corpus present` against an empty project answers a question nobody asked; the header reads
  `no verified sources yet` instead. A coverage count (`5 ledgers · corpus available for 3`) is the
  eventual shape, once `ledger_core.project` owns the ledger inventory.
- **`check` validates its own arguments**: `--verbose`/`-v` and at most one project directory;
  anything else exits `2` with an explanation rather than being silently ignored. Worth settling
  before C2 fixes the CLI grammar.
- **Consequence worth knowing:** `ledger check <case>` exits `1` for every vendored case, which by
  design ships no corpus - the strict-project-without-corpus rule above. `ledger demo <case>` still
  exits `0`. That divergence is intended: the tour attests committed stamps, `check` refuses to call
  unproved quotes proved. The two answer different questions - *can these shipped, corpus-free
  artefacts be audited through their attestations?* versus *can this project's source-byte guarantee
  be established here?* - and documentation must keep saying so, or it reads as inconsistency. A
  later split into `ledger check` (local readiness) and `ledger audit` (corpus-free attestation)
  would carry that distinction in the verb; not now, while `demo` is a compatibility surface.

### C2 - tiered help and `inspect`

Organise top-level help into:

- **Everyday work:** initially `ledger check` and `ledger status`;
- **Audit a project:** `ledger demo`, `ledger dashboard`, `ledger pack`;
- **Advanced inspection:** `ledger inspect <area>`;
- **Protocol development:** specialist evaluation, reproduction, assessment and signing commands.

Map inspection names to existing commands: graph, analysis, faithfulness, quotes, provenance,
citations, structure, assessments, coverage, selection, source-flow, attestation, units, synthesis
and wiki. Unknown names exit `2` and list valid choices.

Keep legacy commands as silent aliases. Do not advertise `init`, `add`, `review`, or `publish` until
each is operational.

#### As built (C2)

Landed as specified, with these decisions recorded:

- **A fifth help group, `Configure a project`** (`profiles`, `doctor`). The four specified groups
  have no home for the two commands that are neither research work nor protocol development, and
  `profiles` is what `check` names in its own next action for every lenient project - burying it
  under "Protocol development" would hide it from exactly the reader it is written for. C4's
  `config effective` joins this group.
- **`doctor` keeps a top-level verb rather than becoming an inspection area**, matching the
  roadmap's own area list (15 areas = 12 gates + graph + analysis + faithfulness; `doctor` is
  absent). It reports project health, not an inspection of the research.
- **`ledger inspect` with no area exits `2` and lists the areas**, like an unknown one. An area is
  a required argument; there is nothing to inspect without it. (`ledger profiles` with no name
  differs deliberately: the list of profiles *is* an answer.)
- **An area with no user arguments passes the project's absolute `content/` path** where the
  registry records one (`__content__`: citations, wiki). Those tools default that positional to a
  CWD-relative `content`, so a bare run from a subdirectory exits `2` (`path not found`) rather
  than inspecting the project. Verified: from the project root the injected invocation is
  byte-identical to the legacy verb's, so the areas stay exact aliases; from a subdirectory the
  legacy verb still fails and `inspect` works. `_takes_content_path` reads this off `STEPS`, so no
  second table records it. No flags are injected (`--strict`, `--mermaid`): `inspect wiki` and
  `ledger lint` must not disagree.
- **Advice now names areas, not legacy verbs** (`ledger inspect structure` / `assessments` / `wiki`,
  and the strict-green next action is `ledger inspect analysis` per the C1 spec). A remediation
  pointing at an unadvertised verb is a dead end for a reader who only has the help text.
  `test_every_advised_inspect_area_is_real` pins every area named in advice to a real area.
- **The map's shape is unchanged**, so no new snapshot: C2 adds no tool, gate, posture, enforcement
  point or fan-out change. Only the `cli` node's description was stale and was corrected in place.
- **Consequence worth knowing:** `DEMO.md` still says `ledger analyze` in four places. It works
  (silent alias) but is no longer the advertised name; C3 rewrites those surfaces.

#### C2 review fixes

- **The content path is injected unless the caller supplied a positional path**, not merely when the
  argument list is empty. The first cut broke the middle case: `ledger inspect wiki --strict` and
  `ledger inspect citations --no-corpus` exited 2 from a subdirectory, because a flag counted as
  "arguments given". Options and their values are not paths, so `VALUE_FLAGS` records which flags
  swallow the next token (`--numeric block` is an option and its value, not a path); it is pinned to
  each tool's real argparse by test. The injected positional leads, preserving flag order. Verified
  by the one test in the suite that spawns the CLI for real, from `content/`.
- **`--help` on every verb this file implements** (`check`, `inspect`, `demo`, `profiles`), so the
  help footer's promise holds. The routed tools already answer `--help` through argparse.
  `ledger demo --help` previously ran the entire tour.

### C2.1 - repair case gating (corrective; blocks C3's public claims)

Found while probing C2: **citation coverage scans zero prose in all five vendored cases.** Each
declares `gated_paths: content/concept_notes/, content/literature_reviews/`, but both directories
are **empty placeholders in every case** - the authored synthesis lives in `content/inquiry.md`,
`content/finding.md` and `content/assessments/*.md`. The demos have reported citation coverage green
while checking nothing. `check_synthesis` does read those files, but it is opt-in and `off` in every
case, so no gate reads the showcase prose at all.

This predates C1/C2 and is exactly the "mechanically green but checked nothing" condition Ledger
exists to prevent, so it is not merely noted.

Gating `inquiry.md` + `finding.md` + `assessments/` surfaces real citation errors in 4 of 5 cases.
Every source cited is already ledgered: no corpus rebuild, and no withdrawn citation, is needed.
The work is of two kinds:

- **Missing claim ref** (the bulk): a cite carries no `#slug`, so under `claim_ids: required` it
  does not name the claim it rests on. Each one is a judgement read against that ledger's claims,
  not a mechanical substitution.
- **Key/alias mismatch** (2): where a ledger's key does not match how prose cites the paper.

#### The parser bug (fixed, `8588639` + `031f3e1`)

The author-list parser misattributed cites, which is what first presented as three "unledgered"
sources. `extract_citations` had **no pattern for 3+ authors**, so the two-author `A & B` pattern
silently matched the **tail pair** of a longer list. Every pattern captures the FIRST author (a
ledger is keyed by first author), so an unsupported author-list form does not fail safe: it falls
through to a narrower pattern that matches a suffix and credits the wrong author. Measured, before
the fix:

| prose | credited | should be |
| --- | --- | --- |
| `Smith & Jones (2020)` | `smith` | smith |
| `(Harrow, Hassidim & Lloyd 2009)` | `hassidim` | harrow |
| `Harrow, Hassidim and Lloyd (2009)` | `lloyd` | harrow |
| `Harrow, Hassidim, and Lloyd (2009)` | `lloyd` | harrow |
| `Harrow, Hassidim, & Lloyd (2009)` | `lloyd` | harrow |
| `Smith and Jones (2020)` | `jones` | smith |
| `Alpha, Beta, Gamma & Delta (2011)` | `gamma` | alpha |

Consequences, for any project and not only the cases: a spurious ledger is demanded for a
middle/last author that first-author convention says will never exist, **and the real ledger is
never checked for that cite**. Fixed with one 3+-author pattern at the right priority (span-overlap
suppression then kills the tail match) and a shared `CONJ` accepting `&` or a whitespace-delimited
`and`, with or without the Oxford comma. False-positive controls hold.

All steps are complete: the gating boundary applied to five cases, 37 claim refs added, both key
mismatches reconciled, and the guard landed with its regression proof.

#### The gating boundary (settled on `covid_origins`, `3d24aa0`)

By file role, not by subject matter:

- `inquiry.md`, `finding.md`, `assessments/*.md` - authored synthesis and judgement: **gated**.
- `baseline_comparison.md` - Ledger's own interpretation of the baseline: **gated**. Its subject
  being an unverified baseline is not a reason to exclude it; the claims *about* that baseline are
  Ledger's own. Currently 0 cites in `covid_origins`, so it is a no-op there - the point is that
  the boundary is principled and any future cite is caught.
- `baseline_research_raw.md` - captured model output, evidence input rather than authored prose:
  **never gated**. `covid_origins`' copy carries 7 cites including sources the case holds no ledger
  for; that unverified quality is the demonstration, so gating it would be a category error.
- `crosswalk.md`, `log.md`, `source_register.md`, `source_flow.md` - machinery: not gated.

`gated_paths` may now name a single file (`ledger_doctor` required a directory, so a correctly
gated project read as `broken`; the gate and its own health check disagreed).

#### Per-case map and remaining work

All five are **done**. Every case now scans its authored prose; each `#ref` was chosen by reading
the sentence against that ledger's claims.

| case | gated | files scanned | refs added | key handling |
| --- | --- | --- | --- | --- |
| `covid_origins` | inquiry, assessments/, baseline_comparison | 3 | 7 | - |
| `covid_debate` | inquiry | 1 | 0 (no cites) | - |
| `eggs_cholesterol` | inquiry, finding | 2 | 9 | alias: `drouin-chartier_2020` |
| `lhc_safety` | inquiry, assessments/, baseline_comparison | 3 | 7 | LA-602 by report ID |
| `quantum_genomics` | inquiry, finding, assessments/ | 3 | 14 | - |

#### The guard (`5f970fa`)

`check_citations` now blocks a project that **declares `configured`** and whose `gated_paths`
matches none of its prose. Verified against the real defect: replaying each case's original
`gated_paths` makes **all five** block; the repaired configs all pass; the pristine kit root (whose
`content/` ships empty by design) still exits 0.

- The discriminator is the **declaration**, not `ledger_doctor.strict_mode` - `ledger_doctor`
  imports `check_citations`, so importing it back would be circular. The declaration is the
  conservative half: a project declaring `configured` while half-filled is `broken`, which doctor
  fails anyway.
- `gated_paths: none` declares "this project gates nothing" and is honoured. Silence is the bug;
  a declaration is not.
- The write-time (`--stdin`) path never raises it: it sees one file, not the project, so it cannot
  tell "nothing gated" from "this file isn't gated".

#### Review fixes (`abca651`)

- **Citation aliases were overwritten inside graph coverage.** Two unrelated concepts were both
  named `aliases` in one loop: the cite→ledger map (passed in, project-wide) and the addresses of
  one claim (recomputed per cite). The second replaced the first after the first resolved cite.
  Worse than a silent skip - `claim_aliases` returns a **set**, and `ledger_path_for` calls `.get()`
  on it, so the next aliased cite raised `AttributeError` (exit 2). Hidden only because
  `graph_coverage` is `off` in every case; reproduced by turning it on for `eggs`. Renamed to
  `citation_aliases` / `claim_ids`, with a regression test that pins the fix rather than the
  iteration order (`extract_citations` returns a set, so "ordinary cite first" is not guaranteed).
- **The zero-prose guard counted bookkeeping as prose.** A freshly configured project holding only
  a log, crosswalk, source register, source flow and `_ledger/` state would have been told its
  gating was broken before it had written anything - `init` would produce a project that
  immediately fails `check`. `is_machinery` now excludes those; everything else (inquiry, finding,
  assessments, concept notes, literature reviews) counts. Verified the filter did not weaken the
  guard: replaying the original `gated_paths` still blocks all five cases.
- **`eggs` overstated what its citations establish.** The prose said Drouin-Chartier and Zhao
  "state no de-duplication protocol" - an **absence**, which no quote can assert. Pinning those
  cites to what each pools did not repair the gap: pooling is compatible with either checking or
  not checking overlap, so the caveat acknowledged the gap while leaving the claim standing. Both
  `inquiry.md` and `finding.md` (which asserted it more strongly, under a "Quote-pinned from each
  source's own methods" heading) now say the verified claims **do not establish** whether either
  checked for overlap - an unresolved methodological gap, not a reported absence - and the
  conclusion-strength claims are separated and cited to the claims that support them
  (`#no-association-overall`, `#harmful-mortality`). A bounded negative finding would need a
  judgement record; it cannot be carried as a quote-supported positive claim.

**The two key mismatches are handled differently, because they are different problems:**

- `eggs`: prose cites `Drouin-Chartier et al. (2020)`; the ledger key is `drouin_2020`.
  `author_variants` strips punctuation (`la-602`→`la602`) but cannot bridge a *truncated* surname.
  Renaming the key is disproportionate: it is load-bearing in **20 files**, including 8 sealed
  `.assess.json` records binding `subject: drouin_2020:<slug>` to a body hash. Clipping the prose to
  `Drouin (2020)` was the first fix and was wrong - it lets an internal identifier dictate the
  reader-facing bibliography, publishing a truncated surname to keep the resolver happy. Solved
  instead with an explicit **citation alias** (below); the prose keeps `Drouin-Chartier`.
- `lhc_safety`: prose cites `LA-602 (Konopinski, Marvin & Teller, 1946)`; the ledger is keyed by
  report ID, `la602_1946`. No alias is needed and none should be added: citing a report by its
  stable report identifier is accurate, `la-602 1946` already resolves via the punctuation-stripped
  variant, and `safety_calibration.md` cites it that way. The inquiry prose is aligned to the same
  form, with the authors named in the sentence. This misstates nobody's surname.

#### Citation aliases (`ab92230`)

`citation_aliases: <as cited> -> <ledger key>[, …]` in `ledger.config.md`. The canonical key (what
graph edges and sealed records address) never moves; the alias only lets prose name the author
accurately where the key abbreviates the surname. Resolution is a **fallback**, tried only when the
filename convention misses, so the common path is unaffected. An alias never chains: it points at a
real ledger, so no cycle can form. Ambiguity blocks the gate whether or not any cite uses it -
shadowing a real ledger, aliasing the same key twice, or pointing at a ledger that does not exist.

Aliases live in the **project config, not ledger frontmatter** (where they would sit more naturally,
being a property of the paper): the `verify-literature-citations.sh` hook measures an Edit's
`new_string` against a 500-char minimum meant to reject stub *files*, so it blocks any small
targeted edit to a real ledger. Padding the edit or scripting around the hook were both refused.
Revisit if that Layer-3 check ever measures the resulting file for an Edit.

#### The vendored-kernel tax

A kernel fix must be re-vendored into all 5 cases (the tour runs each case's OWN copy), so
`check_citations.py` + `ledger_doctor.py` changed in 11 places. Applied as the same asserted hunks
rather than a bulk copy, then verified byte-identical to the kit. This is the concrete cost M5.3
de-vendoring removes.

#### Baseline artefacts: `CLAUDE.md` was wrong

`CLAUDE.md` claimed all result artefacts were "cleared 20260615". True for `repro/` run dirs and the
faithfulness-eval verdict archive (both verified absent); **false for the baselines** - 4 files are
tracked: `covid_origins_ledger/baseline_research_raw.md` (at the case root, outside `content/`) and
`content/baseline_comparison.md`, plus the same pair under `lhc_safety_ledger/content/`. Corrected
in `CLAUDE.md` on 20260715: they are retained because they are the evidence for the claimed uplift,
which cannot be assessed with the comparison withheld; they are **self-generated, not independent**
(the standing reviewer objection); raw output is not verified-claim prose and is not gated; the
authored comparison is. C3's shortened README must not inherit the cleared claim.

### C3 - rewrite researcher documentation

Reduce `README.md` to approximately 850 words:

1. what Ledger is;
2. what it guarantees;
3. what it does not guarantee;
4. try it in five minutes;
5. use Ledger today;
6. configuration;
7. where to go next;
8. brief background.

Canonical wording (as shipped, scoped — see the corrections below):

> Ledger prevents a citation in gated, authored prose from pointing to a quotation that has not been
> verified verbatim against its source. It does not prove that the source set is complete or the
> interpretation correct; it makes those judgements explicit and reviewable.

The detailed trust model also states that Ledger does not prove a quotation is used in context.

Retitle `DEMO.md` as the audit/evaluator path, remove "hallucination-free" from product descriptions
and create `docs/configuration.md` for detailed configuration material removed from the README.

#### As built (C3)

README 1792 -> **893 words**, structured as the eight sections above, leading with the canonical
guarantee and then four things it does **not** guarantee (completeness, context, the conclusion, and
the corpus-free CI ceiling). `docs/configuration.md` takes the displaced detail: `project_state`,
`gated_paths` (incl. `none`), `citation_aliases`, all 13 postures with their values, profiles, and
where the gates run. `DEMO.md` is now "the evaluator's path" and routes a *user* to the README.

- **"hallucination-free" was not in the root README** (already "source-faithful"); it survived in
  three **case** READMEs, which are stale copies of an older root README, and in
  `docs/integrity_framework.md`, where it appeared in the honest disclaimer rather than as a claim.
  The disclaimer now states the limit without resurrecting the slogan ("Only layer-1 fabrication is
  mechanically prevented"). The three case READMEs got the current guarantee sentence; that they are
  root-README copies rather than case descriptions is left for M5.
- **`ledger analyze` -> `ledger inspect analysis`** in all public guidance (4x DEMO.md, 2x
  cases/README.md, 1x a case's `finding.md`). The flat verb still routes as a silent alias.
- **The raw-baseline / authored-comparison boundary was not public at all.** It lived only in
  `CLAUDE.md`, which is git-ignored — so a judge cloning from GitHub saw four baseline files with no
  explanation of what they are, that the baseline is self-generated rather than independent, or why
  one of the pair is gated and the other is not. Now stated in `cases/README.md`, where a judge
  browsing the cases meets it. `covid_origins`' raw transcript cites seven sources, of which
  **five** have no ledger in the project.

#### C3 corrections (closing the milestone; `ec2e115`)

Review found the unscoped guarantee literally false across the repository, because
`baseline_research_raw.md` ships citations with no ledgers, deliberately. Three narrow fixes:

- **The guarantee is scoped to gated, authored prose** in all four places it is claimed: the README
  opening + canonical statement, DEMO's "cannot reach the page" line (now "cannot enter gated,
  Ledger-authored prose through a citation"), and `docs/integrity_framework.md`'s "Guarantees:"
  bullet. Each now points at `gated_paths` as the declaration and names archived material as
  deliberately ungated. **Not** changed: `AGENTS.md`, whose line is a discipline instruction to the
  author rather than a claim about what the machine prevents, and
  `docs/LEDGER_AGNOSTIC_REVIEW_20260615.md`, a dated capture of a reviewer's words — editing it
  would falsify the record.
- **"The same checks at three points" was wrong.** Only citation coverage runs at all three from one
  shared checker; the broader set runs at commit and CI where its inputs exist; source-byte
  verification is local because the corpus is git-ignored. Corrected in `docs/configuration.md` and
  the README's adjacent paragraph.
- **`writing_skill` was undocumented** — the config has 27 keys and the reference named 26. Added,
  with the note that no enforcement reads it: it names the optional Claude Code frontend, and
  `AGENTS.md` carries the same discipline for any agent.

### C4 - add `ledger config effective`

Report `project_state`, effective postures, profile resemblance and explicit differences. Phase 1
resolution remains `explicit -> kernel default`; matching is descriptive only.

Compare posture keys only, excluding `project_state`. Nearest profile means the fewest differing
posture values, with deterministic tie resolution.

#### As built (C4)

`ledger config effective [DIR]` under the `Configure a project` help group, as a `config`
namespace so C5's `config diff profile` / `config set profile` have a home. Read-only: it runs no
gate, returns no verdict, and a test pins that the config file is byte-identical afterwards. Exit
0 once reported, 2 for a non-project / unknown subcommand / stray argument. **511 tests green**
(+21); gates, hooks, CI and all evaluator canaries unchanged.

- **Health and strictness are reported separately** (review fix). The first draft glossed every
  non-strict project as "postures may be softened; nothing to prove yet" — true of a pristine kit,
  misleading for a `broken` one, and `strict_mode()` is false for both. A broken project declared
  `configured` and did not finish, so its gates run lenient exactly when its author believes they
  do not. The report now takes the three-way state from `ledger_doctor.diagnose()`, gives each its
  own gloss, and prints doctor's diagnosis verbatim under a broken verdict. Strictness still comes
  from `strict_mode` (the predicate the gates read), never from the declared word.

- **A tie names every co-nearest profile rather than picking one.** The roadmap asked for
  "deterministic tie resolution"; choosing a single winner deterministically would still invent a
  resemblance the postures do not support — a project equidistant from `pristine` and `submission`
  resembles neither. Both are printed, in PROFILES declaration order (deterministic). This is not
  hypothetical: `covid_debate` and `eggs_cholesterol` tie between `strict-local` and `submission`.
- **Distance is an unweighted count of differing postures.** Nothing establishes that one posture
  matters more than another, so weighting them would be a judgement dressed as a metric.
- **`resolve_posture` returns value + origin; `effective_posture` stays the gate-facing API** and
  now delegates to it, so the report and the gates cannot resolve a posture differently. A test
  asserts they agree across absent/placeholder/invalid values.
- **An unreadable value never reads as `explicit`** — a typo falls back to the kernel default and
  is reported as defaulted, so a misspelt posture cannot look like a deliberate choice.
- **`ledger_cli.POSTURE_KEYS` mirrors `tools/postures.py` rather than importing it** (the CLI must
  not depend on the target project's kernel, which may be an older vendored copy — the same reason
  `POSTURE_DEFAULTS` is mirrored), pinned by a drift test on keys *and* order.
- **`config set` is not routed** — it exits 2 with the subcommand menu until C5 makes it work, per
  the standing rule that a verb appears only when it can complete what it promises.

## 7. Phase 1 follow-on - configuration and initialisation

### C5 - safe configuration mutation

Implement shared mutation primitives before `init`:

- detect duplicate keys;
- reject malformed targets;
- preserve unrelated lines byte-for-byte;
- preserve values containing colons;
- handle absent trailing newlines;
- preview changes;
- make no changes under `--dry-run`;
- apply idempotently;
- stage writes safely;
- restore originals after failed validation.

Add `ledger config diff profile <name>` and `ledger config set profile <name>`. Non-interactive
mutation requires explicit confirmation. Materialise posture values until Phase 2 makes profiles
authoritative.

#### As built (C5)

Primitives in `tools/config_edit.py` (pure scan/plan/render/diff + one writer), the two verbs in
`ledger_cli.py`. **586 tests green** (+75: 43 primitive, 32 command); gates, hooks, CI and every
canary unchanged.

- **Validate in memory, then one atomic replace.** `apply()` re-validates, renders, and swaps via a
  sibling temp + `os.replace`. A rejected change never reaches the disk, so there is no partial
  write to roll back and no original to restore — strictly better than write-then-restore. The
  config is git-tracked, which is the real revert path.
- **`project_state` is never written.** A profile block carries it for a human to paste once the
  config is finished; materialising `configured` onto a half-filled project makes doctor report
  `broken`, whose gates run LENIENT while the config claims strictness — the exact failure C4 was
  built to expose. `set` writes the 13 postures only.
- **A duplicated key refuses the write, even for an unrelated key.** Readers keep the last
  occurrence, so the file is already ambiguous; editing one occurrence writes into that ambiguity.
- **A non-tty is never consent** — `--yes` is required outside a terminal, and only an explicit
  `y`/`yes` applies at the prompt (bare Enter declines).
- **Byte preservation verified against the kit's real config**, not a stub: 13 value-column edits,
  every comment and the alignment intact, `split("\n")` round-tripping a missing trailing newline.
- Mutation-checked: 26 safety assertions each fail against a plausibly-wrong implementation
  (consent-always, writes-project_state, no-validation, dry-run-writes, not-idempotent,
  ignores-digest, drops-mode, ignores-malformed, truncates-staging-path).

Three blockers found in review, all reproduced before fixing:

- **The preview was not bound to the write.** `apply()` re-read the file, so a concurrent edit
  during confirmation applied a change the user never saw (reproduced: preview showed
  `optional -> required`, the write did `off -> required`). Re-validating keeps the OUTPUT
  well-formed; it does not make it the change that was shown. `apply(path, updates, expect_sha256)`
  now takes the previewed digest as a REQUIRED positional — optional could be forgotten, and C6
  consumes this same path.
- **The atomic replace widened permissions** (reproduced: 0600 -> 0644). A fresh temp takes the
  umask. The temp is now created 0600 via `os.open` and given the original's mode before the
  replace — creating it permissively and chmod-ing after would expose the contents for the write's
  duration.
- **A malformed line was invisible.** `claim_ids required` (dropped colon) parsed as nothing, so
  `render` appended a second `claim_ids:` line and the file carried two things that read as
  declarations. Every non-blank, non-comment, non-declaration line is now a diagnostic. Chose the
  strict option over "reject only lines resembling known keys": all 7 real configs in the repo have
  zero non-conforming lines, so it costs nothing and catches the case. **Indented declarations are
  VALID** (`parse_config` strips before partitioning, so every gate reads them) — tested both ways.
- Two smaller corrections: the `os.replace` comment claimed it "crosses [filesystems] silently" —
  false, it raises EXDEV (verified: `NotADirectoryError`, errno 20). And `git checkout
  ledger.config.md` would discard unrelated edits in the same file; the advice is now `git restore
  -p` or revert the shown values.
- **The comment rule moved to `AGENTS.md`** (§ "Code comments — contracts, not history"). `CLAUDE.md`
  and the hook bind Claude only via `.claude/settings.json`, so Codex and other agents inherited
  nothing. AGENTS.md is now the normative statement; the hook is its mechanical assistant for Claude.

A fourth blocker, found on re-review and worse than described: the staging path is predictable, and
`O_TRUNC` without `O_EXCL` FOLLOWED a symlink sitting there. Reproduced: an unrelated `victim.txt`
ended up **containing the config**, the symlink was consumed by the replace, and the command
reported success — an arbitrary-file overwrite with no signal to the user. A pre-existing regular
file was destroyed the same way. Now `O_WRONLY|O_CREAT|O_EXCL` (which refuses a symlink outright,
dangling or not — verified `FileExistsError`, errno 17), and an occupied staging path is a **clear
refusal that leaves the path untouched**: it may be a leftover from an interrupted run or a file
with nothing to do with Ledger, so clearing it is the user's call, not the tool's. Six regressions,
each verified to fail against a reversion to `O_TRUNC`.

#### Comment discipline (adopted during C5)

Review found the redesign preserving its own reasoning inside the implementation. Rule now in
`CLAUDE.md`: *a comment may explain a non-obvious invariant, external constraint, dangerous edge
case or necessary implementation choice; it must not preserve development history, roadmap
sequencing, test-construction history, or prose already expressed by names and control flow.*
Bounded pass over the three hotspots: `ledger_cli.py` **111 → 77** comment lines (-31%), the
21-line preamble cut to 6, 12 milestone section labels renamed in the tests, `tools/config_edit.py`
written to the rule (16 comment lines in 165). `check-self-narration.sh` now enforces the
mechanical subset (milestone labels, phase markers, "the point of C2", "arrives in C5") — verified
to catch all five forms with **zero false positives across 69 tracked non-vendored files**, and
scoped out of `.claude/hooks/` since a watchlist necessarily contains its own watchwords.

### C6 - safe `ledger init`

Initially configure the current starter-kit clone, rather than creating a new directory.

1. retain originals;
2. build proposed outputs in memory;
3. validate with pure functions;
4. write temporary files;
5. replace targets;
6. create directories idempotently;
7. run `ledger doctor`;
8. restore originals after failure.

**C6 splits three ways** (user's call, on review of the C6c design): **C6c** `apply_plan()` — the
writer alone, because filesystem mutation, rollback and path containment deserve an isolated review
unit; **C6d** the complete `ledger init` workflow and routing — prompting, argument parsing, consent
and routing are a separate failure surface; **C6e** documentation, tracking and the re-vendor
decision.

**"Recover completely" + "never delete" together force a precondition, not just a write order.** The
first C6c design proposed creating directories and a missing skin, then rolling back by writing bytes
back. That does not hold: `mkdir` is irreversible here whether or not it is idempotent, and once
`doctor` runs *after* the skin write the skin is no longer the last fallible operation — a created
skin would survive a failed verification with no way back. So **init only ever REPLACES the starter
kit's existing scaffold**: a missing config, a missing skin or a missing declared directory is a
refusal before any write, never a creation. Every mutation is then a replace of a file that existed,
and every one is undone by writing retained bytes back. Creating files and directories belongs to the
eventual `ledger init my-project` workflow, where a whole new project can be staged outside its final
path and published with one directory rename.

#### As built (C6c) — `tools/init_apply.py`, the replace-only writer

Sequence: pure validation + containment + doctor-equivalent preflight → re-read both files →
`init_plan.staleness()` → replace config → replace the existing skin → `ledger_doctor` as
verification → on any failure restore **both** from retained bytes with atomic writes.

- **`escapes_root()` closes what the lexical check cannot see.** `init_plan.path_problems` is
  lexical; a symlinked *parent* would put both C5's staging temp and the replace outside the project
  while every path string still looked relative and clean. The writer resolves each declared path's
  nearest EXISTING ancestor — the parts that do not exist yet cannot be traversed and cannot redirect
  a write.
- **Verification runs the complete doctor contract** (`ledger_doctor.blocking_problems`), not the
  derived state alone. Anything it rejects restores both files.
- **Rollback compares, never replaces**: only bytes init itself wrote are reverted.
- 31 tests; 15 mutations, each caught by exactly its own test.

**Found by the mutation matrix, not by the tests passing:** `_verify` was entirely uncovered — a
mutation that accepted any state passed all 19 tests, because the rollback tests monkeypatch `_verify`
and so exercise the rollback rather than the check. Closed with a project that goes broken
*naturally* (filling the config over a skin someone already wrote leaves it looking configured while
`project_state` still says pristine; init never writes `project_state`, so it cannot resolve that and
must put the file back).

**Four more blockers found in re-review, each reproduced before it was fixed:**

1. **`_verify()` was not `ledger doctor`.** It read `diagnose()` only, so a *configured* project with
   all five postures lax was accepted while a plain doctor run fails it (rc 1) — and so does every
   gate, since a configured project is strict by definition. It also missed
   `semantic_health: required`. Fixed by extracting the contract rather than restating it:
   `ledger_doctor.blocking_problems()` (with `strict_posture_gaps()` and `semantic_blocking()`) is now
   the single statement of what a plain run fails on, `main()` renders it, and `_verify` reads it.
   **One of the kit's own tests was passing only because `_verify` was weak** — its "configured"
   fixture had lax postures.
2. **Target-file symlinks were followed.** Parent escape was covered; the target itself was not. An
   atomic replace swaps the directory ENTRY, so a symlinked `ledger.config.md` or skin became a
   regular file and the link was lost — reproduced with `applied=True`, the rules landing in a new
   regular file while the link's real target kept the old content, a silent split. `escapes_root`
   cannot cover this: the link resolved *inside* the project. Both targets are now refused.
3. **The skin had a write-window gap.** It was checked before the config write and not again before
   its own, so an edit arriving between the two was overwritten. `init_plan.skin_staleness()` is now
   re-checked immediately before the skin write (separate from `staleness()` because by then the
   config digest has deliberately changed). On a moved skin: the skin is left exactly as the editor
   left it and **only the config is restored** — an edit that landed in the window is not init's to
   revert.
4. **Rollback messages claimed success before the restore ran.** The text said the files "have been
   put back" and was then followed by the restore's own failure report. `_rolled_back()` now restores
   first and reports what actually happened — `Put back as it was: <files>` or `Rollback INCOMPLETE:`
   naming each target that could not be restored, by project-relative path.

The pre-write `staleness()` call needed its own test after (3): the window re-check catches the same
cases, so a mutation removing the earlier call passed everything. It earns its place by stopping a
doomed config write before it happens rather than undoing it after — now pinned.

**A fifth blocker, found in the next re-review: rollback could overwrite an edit made AFTER init
wrote.** `_restore` reverted to `before` whatever the file then held, so an edit landing between
init's replacement and a failed verification was destroyed — and the run reported `Put back as it
was`, which was true of init's own change and silently false about the edit it had just eaten. The
skin-window check (3) covers edits *before* init writes the skin; this is the window *after* either
replacement. `Target` now carries **`written`** (the exact bytes init put there) beside `before`, and
rollback compares rather than replaces: `current == before` is already restored, `current == written`
is init's own change and safe to revert, and anything else was changed by someone after init wrote
it — preserved untouched, with `Rollback INCOMPLETE:` naming it. This is what makes the module
header's promise ("a file edited by someone else meanwhile is left as they left it") true; it was
false when written.

Support `--dry-run`; refuse filled projects or non-empty skins without `--reconfigure`; validate
`source_of_truth`; show all mutations. Do not satisfy skin readiness with filler. Ask for a real
subject-specific risk or introduce `skin_state: draft|confirmed`.

#### As built (C6a) — skin_state kernel foundation

The skin question was decided **both ways** (user's call): `init` asks for a real subject rule AND
records `skin_state`, so a user who declines the prompt still lands in an honest state rather than a
configured-looking one.

Why it was needed at all: `skin_is_empty()` is a shape heuristic — "does the file contain bold
text". The kit's shipped skin holds the **quantum white paper's `**W1**–`**W5**` worked example**,
held back from counting only by the `_(empty —` sentinel. So an `init` that merely stripped the
sentinel would have made doctor report `configured` with another project's rules as this project's
skin: filler satisfying the gate, exactly what the roadmap warned against.

- **A 4th derived state, `drafted`** — config filled, skin written, not yet confirmed. Not `broken`
  (nothing contradicts) and not `configured` (the rules are not owned yet), so it exits **0**, runs
  **lenient**, and returns BEFORE the "configured is strict by definition" bundle — a drafted project
  must not be hard-failed for postures it has not adopted. `--require-configured` still rejects it.
- **`skin_state` absent → the old shape guess**, so every project written before the field keeps its
  state. Verified: all 5 vendored cases and the kit root are unchanged.
- **`project_state: configured` + `skin_state: draft` is `broken`** — a project cannot be configured
  on rules its author has not stood behind. Conversely `project_state: pristine` + derived `drafted`
  is NOT broken: `init` never writes project_state (the C5 principle), so a stale `pristine` during
  setup is not a contradiction.
- **Caught in build:** the first cut let `skin_state: confirmed` over an EMPTY skin report
  `configured` — the confirmed-and-empty check sat after an early return, so it was dead code. A
  declaration is believed about rules that exist; it cannot conjure a skin that is not there. Now
  `broken`. Found by probing the full matrix rather than by the tests, which is why the matrix probe
  came first.
- 10 tests; the 5 load-bearing ones each fail against a mutation that trusts any declared
  `skin_state`. 616 → 626 green.

#### As built (C6b) — the pure construction layer

`tools/init_plan.py`: text in, text out, nothing written. Steps 1-3 of the eight above, so a setup
that fails validation cannot leave a half-configured project behind. **No `init` verb is routed** —
a workflow verb is introduced only when Ledger can complete what it promises, and it cannot write
until C6c.

- **`build()` returns an `InitPlan`**: config updates + unified diff + the digest of the bytes it was
  computed from (so C6c's write can refuse a file that moved underneath the preview), the proposed
  skin text, the directories the config declares, notes, problems and blockers.
- **`project_state` is never written** (the C5 principle) and **`skin_state: draft` always is**, so
  declining the rules prompt still lands the project at `drafted` rather than configured-looking.
  Verified end-to-end: the proposed config + skin derive as `drafted` through `ledger_doctor`.
- **The skin is never rewritten once it holds rules** (user's call). `--reconfigure` is consent to
  re-answer a filled *config*; it never extends to the skin, because init cannot tell its own earlier
  output from prose someone wrote. Rules offered for a written skin are *refused*, not silently
  dropped — dropping them would report success while the rules went nowhere.
- **Filler is rejected**: blank, `TBD`/`todo`/`n/a`, `<template>` tokens, and the shipped worked
  example pasted back in. HONEST LIMIT: a fluent sentence that says nothing passes. That judgement is
  exactly what `skin_state` carries, so no quality heuristic was built on top of it.
- **`source_of_truth` is validated** against the config template's own `<markdown+quartz |
  docx+python>` token, drift-tested by parsing the shipped config rather than copying the choices.
  `deliverable`/`source_types`/`the_reader` stay free text — the real cases prove they are. No slug
  rule on `project_name`: it is a display label (`build_judge_pack` falls back to the directory
  name), so constraining it would be invented rigidity.
- **Caught in build (rule-code collision):** the worked cases (L/E/C/D) avoid the shipped example's
  **W1**-**W5** only by luck; a `water_policy_ke` subject would have put a second **W1** under it and
  made any reference to "W1" ambiguous. `rule_code` now passes over a letter the skin already uses.
  Found by probing against the real kit skin, not by the tests.
- **Kernel refactor**: `ledger_doctor.skin_text_is_empty(text)` extracted, with `skin_is_empty(path)`
  delegating, so pure code applies the same emptiness test as the file-facing gates — one definition,
  not two. All 5 vendored cases still derive `configured`/strict and the kit root `pristine`.
- 47 tests; each of 11 plausibly-wrong implementations is caught by exactly the test written for it.
  626 → 673 green.

**Three blockers found in review, each reproduced against the real kit before it was fixed:**

1. **The materialised skin retained another project's rules.** The collision fix stopped a second
   **W1**, but not the contamination under it: against the real kit skin, `render_skin` emitted all
   five quantum **W1**-**W5** rules, the new subject's rules, and no sentinel — so once the skin is
   confirmed, five rules nobody here chose read as this project's. The first cut's test ("every line
   but the sentinel survives") *locked the defect in*. Materialising now removes the whole
   worked-example block (heading + bullets), keeping the shared preamble byte-for-byte. Because the
   example reserves nothing once removed, `rule_code` is computed against what the skin RETAINS — so
   `water_policy_ke` correctly gets **W**, and only a rule that survives into the file reserves a
   letter.
2. **The skin write was not bound to its preview.** `InitPlan` carried `config_sha256` but no
   identity for the skin bytes behind `skin_diff`. Now `skin_sha256` (None when the file did not
   exist, so missing and empty are distinguishable — `skin_text: str | None`), `skin_file`, and
   `staleness(plan, config_text, skin_text)`, which C6c must call immediately before writing
   **either** target: init changes two files, so a plan stale in one is stale entirely. It catches a
   changed config, a changed skin, a skin that appeared since the preview, and one that vanished.
3. **Declared paths could escape the project.** `gated_paths: ../outside/` and
   `skin_rules_file: ../../skin.md` were planned as-is, and `gated_paths: /etc/` (resolving to
   `/private/etc`) gave `plan.ok=True`. `path_problems()` now refuses absolute paths, `..` segments,
   `~` expansion and empty paths, and `dirs_to_ensure` drops them as well as reporting them, so a
   caller ignoring the problems still cannot be handed one.

**A fourth blocker, found in re-review: `skin_file` could bypass the validated config.** `build()`
took the write target as a parameter, so `path_problems()` validated `skin_rules_file` while
`InitPlan.skin_file` carried an unrelated argument: a config declaring a safe path, built with
`skin_file="../../outside.md"`, gave `plan.ok=True` and instructed the writer to leave the project.
The target now derives exclusively from `config_text` via the pure `declared_skin_file()` (absent or
placeholder → `DEFAULT_SKIN_FILE`), and `skin_file` is gone from `build()`'s parameters — C6c calls
the same helper to locate the skin before building. An escaping *declared* path is **refused, not
quietly redirected** to the default: falling back would write to a file the config never named.

**C6c inherits an obligation from (3): `path_problems` is LEXICAL ONLY.** It cannot see a symlinked
parent, so the writer must additionally resolve each existing parent and refuse any whose real
location leaves the project root. Passing the lexical check is not evidence that a path stays inside.

Also fixed while closing (1): the append path (a skin with no sentinel) left a double blank line.
Mutation rows 11 → 19, including a *half-fix* row (bullets stripped, heading kept) that the real-kit
regression catches. Two rows that constructed `InitPlan` positionally were repaired after the field
change — they were failing on a TypeError rather than on the invariant, which is a crash, not a test.
673 → 692 green.

#### As built (C6d) — the `ledger init` workflow, routed

`ledger init [DIR] [--set key=value] [--rule TEXT] [--reconfigure] [--dry-run] [--yes]`, consuming
`init_plan.build` + `init_apply.apply_plan`. **The verb is now advertised and routed** — it can
complete what it promises, which is the whole condition for introducing one. `add`/`review`/`publish`
stay out.

- **`--set key=value` (repeatable) or prompts.** `FIELDS` carries the question text, so the CLI cannot
  ask it differently from any other caller, and `ledger init --help` lists the fields FROM `FIELDS`
  rather than spelling them out — a help that names a field init does not set is impossible.
- **A non-tty is never consent** (the C5 rule): no terminal ⇒ `--yes` is required to apply, and every
  required field must arrive by `--set`, reported together rather than one refusal at a time.
- **A mistyped `--set` key is named, not dropped.** `--set project-name=x` used to be silently
  discarded, leaving the run asking for the field it was meant to answer.
- **The plan is built from bytes read BEFORE the prompts**, so answering slowly cannot land a write on
  a file that moved — `apply_plan`'s staleness check refuses it.
- **Giving up is not an answer.** Ctrl-C or EOF at any prompt aborts the command (exit 2, nothing
  written); an empty line at a rule prompt still means "no more rules". Reading the two alike let a
  cancel fall through to the write, and with `--yes` no confirmation remained to catch it.
- **The handoff names the whole transition, not its first step.** `configured ⟹ strict` and init
  adopts no postures on the author's behalf, so stopping at `skin_state: confirmed` +
  `project_state: configured` produced a project `ledger_doctor` rejects. `HANDOFF` now names all
  five steps; `STRICT_PROFILE` + `CONFIRMED` are shared with the tests that follow it end-to-end to
  `blocking_problems(...) == []`, so the printed lifecycle and the proven one cannot diverge.
- **The success line names the state init actually left**, derived from `ledger_doctor.diagnose`
  rather than assumed. A first run lands `drafted` and says so; `--reconfigure` over a confirmed
  skin lands `configured`, says that instead, and drops the handoff, whose five steps are already
  behind it. Hardcoding "drafted" would have been wrong on the second path.
- 36 tests; 13 mutations, each caught by its own test.

#### As built (C6e) — documentation, tracking, and the re-vendor decision

- **`docs/configuration.md`** gains the `ledger init` lifecycle (exactly the five steps init prints)
  and replaces the two-state account of `project_state` with the four the kernel really reports
  (`pristine` / `drafted` / `configured` / `broken`) plus `skin_state`. `docs/extending.md` §1 now
  names `ledger init` as the agent-neutral path to steps 2–3; `README.md` names it at step 3 and
  documents `skin_state`. A test pins that the doc names the same profile and fields the handoff
  does — narrow on purpose, since prose is otherwise free to move.
- **Re-vendor decision: `ledger_doctor.py` only, into all 5 cases.** Settled from evidence, not
  assumption. Not required for correctness — every case passed `demo` + `doctor` at rc=0 on its own
  older kernel, and the kit's new doctor accepts all 5 case configs unchanged (the `skin_state`-less
  path is explicitly supported, and no case declares the field). Done anyway because 27 of 28
  vendored tools were already byte-identical and the cases exist to show one kernel running five
  subjects unchanged: 27/28 tells that story worse than 28/28, and the gap only widens. Behaviour
  after re-vendoring is unchanged — all 5 cases still `demo` + `doctor` at rc=0.
- **Not vendored:** `config_edit.py` / `init_plan.py` / `init_apply.py` — no case ships a
  `ledger_cli.py` and no vendored tool imports them, so they would be dead code. `audit_pack.py`
  stays untracked local work.
- **`tests/test_vendor_parity.py`** makes the parity mechanical rather than remembered: every
  vendored tool byte-identical to the kit's, no case-only tool, no missing kernel tool (`CLI_ONLY`
  records the four legitimate absences). The drift this milestone swept had accumulated silently
  once already — 3 mutations, each caught.

**The kit's own product-rule test caught this milestone**:
`test_usage_does_not_advertise_unimplemented_workflow_verbs` asserted `ledger init` was absent from
the help, and failed the moment it was added — the pin working exactly as intended. Updated to assert
`init` IS advertised while `add`/`review`/`publish` are not.

**A mutation walked past a test that looked right:** `rules_prompted_even_when_given` asserted no
`Rule 1` prompt, but a run already holding one rule from `--rule` asks for **Rule 2** — the assertion
was too specific and the mutation passed all 23. Now asserts no rule prompt at all. A second test's
input mock answered `"y"` to everything, which made a re-prompting mutation loop forever instead of
failing; a test that hangs under mutation cannot report, so the mock is bounded.

### E1 - evaluator experience pass

Begin after C6 and complete before the next public release. A cold reader should understand why
Ledger matters from `LEDGER_MAP.md` and one generated pack without first learning the repository's
implementation. Preserve the evaluator commands and evidence boundaries while improving their
explanatory and visual quality.

#### `LEDGER_MAP.md`

- Present the researcher workflow before the internal machinery.
- Use progressive disclosure rather than giving every node equal visual weight.
- Make the guarantee / judgement / data boundary immediately legible.
- Verify every displayed component and edge against the repository.
- Keep development history in `PROGRESS_LOG.md`, not in the map.
- Provide a useful fallback when Mermaid rendering is unavailable.

#### Generated pack and dashboard

- Make the first screen answer what Ledger protects, what it cannot prove, what this project
  contains, what was checked, the corpus-dependent verification ceiling and what still needs human
  judgement.
- Prioritise findings over machinery. Route each finding to its quotation, inference and judgement
  record where those artefacts exist.
- Make empty states informative; remove dead or decorative panels.
- Keep the output offline, navigable, responsive and readable in both themes, with accessible
  contrast and keyboard operation.
- Show real disputes, double-count risks, provenance and verification. Do not substitute decorative
  metrics or promotional claims for evidence.

#### Worked cases

- State the distinct lesson each case demonstrates.
- Recommend one compact first case for a new evaluator.
- Ensure the cases demonstrate gates and judgement surfaces rather than merely returning green.

#### Cold-reader acceptance test

After five minutes with the map and one generated pack, a reader should be able to answer:

1. What does Ledger mechanically guarantee?
2. What remains a human judgement?
3. How does a prose citation reach a source quotation?
4. What did this case actually reveal?
5. What should the researcher do next?

Verify that generated HTML opens offline, internal links resolve, no panel is accidentally empty,
both themes remain readable and the strongest claims on the page are supported by the displayed
project evidence. C7 and M4.3 may refine the status and judgement portions later; E1 establishes the
coherent evaluator baseline now.

#### Delivery order

E1 runs in four steps, honesty before presentation, so no visual work rests on a claim the page
cannot support:

- **E1a - verification honesty.** DONE. The pack asserted `Guaranteed - re-proves byte-for-byte
  against the source on disk` while shipping no corpus, so no reader could re-prove anything, and
  stated no ceiling. `verification_state` (`judge_dashboard.py`, read by both surfaces) separates
  the two axes: whether a proof was RECORDED for these ledgers, and whether the artefact carries
  the bytes to REPEAT it. `Guaranteed` is reachable only through the reader's axis, so the status
  cannot outrun the evidence. Both surfaces state the ceiling once.
- **E1b - findings and next action.** DONE for `covid_origins`. Cold-reader Q4/Q5. Each case states
  its lesson and one evidence-specific next action (trace the load-bearing disputed inference from
  prose to quotation to judgement record), not navigation. A finding must be derived from existing
  verified claims and judgement records through the `AGENTS.md` proposal-and-approval loop - never
  written to fill a panel. Built on the existing 13 gates: `check_assessment.resolve_rec_refs` is the
  one resolver for `[rec: id]` markers in gated prose, and `evidence_trace` renders only from what it
  resolved, so an address the gates reject cannot reach the page. A finding is human-authored and
  never generated; `finding_lead` reads the lead for both surfaces (prose after the title, before the
  first `## `) rather than searching for a heading, which would impose the template each case exists
  to avoid. No finding renders the honest empty state, never filler.
- **E1c - workflow-first map.** Researcher workflow before machinery; progressive disclosure; a
  fallback where Mermaid does not render.
- **E1d - cold-reader verification.** DONE for the pack as an artefact; the comprehension pass
  remains. `tests/test_pack_offline.py` opens a bundle outside the repo and resolves every link from
  the page it is written on, forbids a remote load or a builder path, requires the evidence readable
  without scripts, and reads WCAG AA out of the shipped stylesheet rather than a copy of the palette.

Four of five cases still carry no `content/finding.md` citing sealed records, so they render the
honest empty state and ship no trace. Each remaining finding goes through the proposal-and-approval
loop on its own, and must show a *different* reason Ledger is useful - a lesson is never inferred to
satisfy the renderer.

### C7 - compact status

Begin after Phase 2 supplies structured status. Move posture drift tests from rendered prose to
structured data. Default status fits on one screen; `--verbose` shows every posture.

## 8. Phase 2 - shared internal architecture

### M2.1 - introduce `tools/ledger_core`

Use `tools/ledger_core/` deliberately to retain zero-install execution. Suggested modules:

```text
project.py
config.py
diagnostics.py
capabilities.py
claims.py
provenance.py
graph.py
assessments.py
renderers.py
```

Dependency direction is `flat tools -> ledger_core`. Existing flat modules remain compatibility
facades.

### Structured diagnostics

```python
@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    path: Path | None = None
    line: int | None = None
    ref: str | None = None
    remediation: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

class Outcome(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    ERROR = "error"
    UNAVAILABLE = "unavailable"

@dataclass(frozen=True)
class GateResult:
    gate: str
    diagnostics: tuple[Diagnostic, ...]
    outcome: Outcome
```

Inactive gates produce no result. `UNAVAILABLE` carries a stable cause code and the aggregate
decides whether it blocks.

Provide `legacy_text`, concise text and stable JSON renderers. Pin diagnostic codes and outcomes,
not every word of new concise prose.

### Configuration and project model

Move parsing and effective resolution into `ledger_core.config`. Once an authoritative `profile:`
exists, resolve `explicit override -> declared profile default -> kernel default`. Inferred profiles
never affect resolution.

`ledger_core.project` owns root discovery, paths, project state, corpus presence, ledger inventory,
kernel identity and configuration location.

### Capability handshake

Each kernel exposes protocol version, kernel version and capabilities. Integration policy:

- compatible kernel: in-process;
- different kernel with JSON: subprocess JSON;
- older kernel: legacy subprocess text.

### Conversion milestones

- M2.2: convert three pattern gates: manifest, coverage and synthesis.
- M2.3: convert remaining gates in small batches; convert only the check path of quote verification,
  leaving `--stamp` untouched.
- M2.4: move `ledger check` to structured `GateResult` aggregation.
- M2.5: consolidate logging, root discovery, posture readers, path bootstraps and `--project` support.

## 9. C8 - guarded `ledger publish`

Depends on M2.4. Publication uses an in-memory submission configuration, never mutates project
config, blocks on failures or errors, creates no output on failure and cleans partial output.

Only after successful checks does it build a pack. The pack records the effective profile and
whether source bytes were re-proved or committed records merely attested.

An explicit `--allow-weaker-profile` escape hatch may exist only if the resulting pack prominently
records the weaker validation. Until C8 exists, `ledger pack` remains the honest command.

## 10. Phase 3 - evidence intake with `ledger add`

Depends on M2.1. On-disk artefacts are authoritative; `.ledger/intake/<key>.json` is a resumability
and provenance aid.

The memo records original input, candidates, selected identity, locator, retrieval time, acquisition
command/result and derived state. Title search requires confirmation; DOI, URL and local file may
resolve directly. Local sources are copied into the ignored corpus by default, with explicit symlink
or reference-in-place alternatives.

Derive stages from artefacts: acquired, extracted, claim workspace created, claims present,
verified, stamped and registered.

Claim selection remains human-controlled. Ledger may enumerate units and create templates but never
silently promotes model-selected passages into `verified_claims/`. Future untrusted drafts belong in
`.ledger/drafts/claims/`.

Commands:

```text
ledger add <DOI|URL|FILE|TITLE>
ledger add --resume <key>
ledger add --claims <key>
```

Reuse the existing acquisition script and load intake dependencies lazily.

Milestones:

- M3.1: detection, keying, memo and derived state;
- M3.2: acquisition and extraction with injectable fetchers;
- M3.3: registration, claim workspace and claim listing;
- M3.4: resume, verification, stamping and offline smoke test.

## 11. Phase 4 - judgement queue with `ledger review`

The queue is a computed view, not a new source of truth. Task IDs are deterministic.

Rank by severity and scope:

1. project-wide selection gap;
2. disputed load-bearing inference;
3. ordinary disputed inference;
4. unassessed load-bearing edge;
5. unassessed ordinary edge;
6. stale semantic review.

Explain what each item affects and why it is prioritised. Collapse related findings about one
subject into one task with ordered sub-actions.

Commands:

```text
ledger review
ledger review next
ledger review draft <task-id>
ledger review seal <draft-id>
```

Drafts live in `.ledger/drafts/assessments/`, outside enforcement. Sealing rejects placeholders,
validates references, computes the seal, moves the record atomically, runs the assessment gate and
removes the draft only after success.

Milestones:

- M4.1: queue, ranking, identifiers and rendering;
- M4.2: draft/edit/seal lifecycle;
- M4.3: status and dashboard integration.

## 12. Phase 5 - repository consolidation

Keep one fully standalone case as the portability fixture. Convert four cases to content-only
projects using the root kernel. Generate audit packs for all and test compatibility between the
standalone and root kernels.

Each case receives `KERNEL.md` recording kernel version, interchange version, profile, creation
date, compatibility range and whether raw source bytes were present during the latest verification.

Before removing duplicates, build a hash manifest, reconcile drift, run compatibility tests and
record expected exits/findings from live execution.

Review `tools/audit_pack.py` and its test as user-owned work before deciding whether to commit them.

Treat documentation deduplication separately. Preserve unique historical evidence and consolidate
durable conclusions into a canonical trust-model document.

Package `ledger_core` from `tools/ledger_core` without weakening zero-install operation. Target
release: `0.2.0`.

Milestones:

- M5.0: reconcile audit-pack work;
- M5.1: parity and compatibility harness;
- M5.2: case compatibility in CI;
- M5.3: de-vendor four cases;
- M5.4: packaging, packs, documentation and release.

**M5.3 must revise `tests/test_vendor_parity.py`.** It is **transitional**, and byte parity is the
honest expectation only while all five cases vendor a full kernel. Once four are content-only and
one remains the standalone portability fixture, the contract changes shape: byte parity applies to
the fixture alone, and the other four need the opposite check — that they carry *no* kernel to drift.
Left as-is it would fail the moment de-vendoring starts, and reading that failure as "re-vendor them"
would undo M5.3.

## 13. Dependency graph

```text
Step 0: tracked roadmap
  |
  +-- C1: ledger check
       |
       +-- C2: tiered help and inspect
            |
            +-- C3: researcher documentation
                 |
                 +-- C4: config effective

C5: configuration mutation
  |
  +-- C6: safe init
       |
       +-- E1: evaluator experience baseline

M2.1: ledger_core foundation
  |
  +-- M2.2: pattern gates
  |    |
  |    +-- M2.3: remaining gates
  |         |
  |         +-- M2.4: structured aggregate check
  |         |    |
  |         |    +-- C8: guarded publish
  |         |
  |         +-- M5.1: compatibility harness
  |
  +-- C7: compact structured status
  |
  +-- Phase 3: evidence intake
  |
  +-- Phase 4: judgement queue

M2.4 + M5.1
  |
  +-- M5.3: case de-vendoring
       |
       +-- M5.4: package and release
```

E1 lands after C6 and before the next public release. C7 and M4.3 later enrich its status and
judgement views without postponing the baseline evaluator pass.

M5.0 and documentation consolidation may proceed independently after reviewing overlapping
user-owned work.

## 14. Test programme

### `ledger check`

Test gate/pre-commit parity, demo isolation, legacy demo compatibility, kernel-default resolution,
absence of inferred profile defaults, explicit `--no-corpus`, no-ledger behaviour, advisory corpus
absence in pristine projects, blocking corpus absence in strict projects, unchanged demo semantics,
exit normalisation, warning parsing, inactive-gate hiding, a single ceiling statement, non-project
errors and exactly one existing next action.

### Configuration and init

Test defaults, profile comparison, deterministic ties, duplicate rejection, malformed config,
colons, missing newlines, dry runs, idempotence, unrelated-line preservation, rollback, refusal to
overwrite configured projects, skin confirmation and idempotent directory creation.

### Structured diagnostics

Test stable codes, outcome-to-exit mapping, unavailable cause codes, explicit aggregate policies,
absence of results for inactive gates, text/JSON semantic equivalence and legacy text compatibility.

### Intake

Test DOI/URL/file/title recognition, search confirmation, local storage choices, disk-derived state,
idempotent resume, missing-dependency remediation, network-free unit tests and the Sandve fixture.

### Review

Test deterministic task IDs, ranking, collapsing, drafts outside enforcement, placeholder rejection,
atomic sealing, draft retention on failure and valid records on success.

### Publication and compatibility

Test in-memory submission requirements, unchanged project config, no output on failure, partial
cleanup, profile/ceiling recording, marked weak-profile exports, legacy exit codes, content-only
cases, foreign-kernel fallback and protocol compatibility.

## 15. Verification per milestone

After every implementation commit:

```bash
python3 -m pytest -q
python3 tools/ledger_doctor.py
python3 ledger_cli.py demo cases/covid_origins_ledger
python3 ledger_cli.py dashboard cases/covid_origins_ledger --out /tmp/ledger-dashboard.html
python3 ledger_cli.py pack cases/covid_origins_ledger --out /tmp/ledger-pack
```

For C1 also run:

```bash
python3 ledger_cli.py check
python3 ledger_cli.py check cases/covid_origins_ledger
python3 ledger_cli.py check cases/covid_origins_ledger --verbose
```

Confirm that the pristine root is not incorrectly corpus-unavailable, strict projects without their
corpus do not receive a false healthy exit, citation coverage still runs without source bytes,
inactive gates remain hidden and evaluator demo semantics remain unchanged.

Keep the rewritten README below 900 words.

## 16. Repository process

- Work on `feature/researcher-workflow`.
- Do not develop directly on `main`.
- Preserve unrelated and untracked user changes.
- Use small, independently releasable commits.
- Update this roadmap status and the progress log with each milestone.
- Update repository maps and snapshots with their corresponding shape changes.
- Run the full tests and evaluator canaries before every merge.
- Merge only after explicit approval.

## 17. Immediate execution order

1. Persist this roadmap.
2. Implement C1: `ledger check`.
3. Implement C2: tiered help and `inspect`.
4. Implement C3: researcher documentation.
5. Implement C4: `config effective`.
6. Reassess the release slice.
7. Continue with C5/C6 and Phase 2 according to the dependency graph.
8. Run E1 after C6, before the next public release; carry structured-status and review refinements
   into C7 and M4.3.

This is the full repository redesign delivered incrementally, with `ledger check` as the first
researcher-facing improvement and existing enforcement preserved throughout.
