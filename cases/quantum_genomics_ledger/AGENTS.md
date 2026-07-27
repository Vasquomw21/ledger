# AGENTS.md — authoring discipline for this Ledger project

This file is the **agent-neutral schema** for a Ledger project: it turns any capable agent 
into the project's disciplined writer and curator. It is the portable equivalent of
the Claude Code skills `skill-ledger-write` and `skill-ledger-curate`: the same discipline, with no
tool dependency. Codex reads this file natively; other agents can be pointed at it; a person can
follow it by hand.

> Running **Claude Code** with the Ledger skills installed? Use them instead
> (`/skill-ledger-write`, `/skill-ledger-curate`) — same discipline, better ergonomics. This file
> is for everyone else.

## Read first (every session)

1. **`ledger.config.md`** (repo root) — `the_reader` (who the bored reader test targets), `source_of_truth`
   (where prose is edited), `skin_rules_file`, and `source_types` (what counts as a primary source).
2. **The skin** named by `skin_rules_file` (default `content/_ledger/skin_rules.md`) — the
   subject-specific rules. They are project gates, audited alongside the universal set below.

If `ledger.config.md` is absent: reader = "an expert in the field, reading tired"; source-of-truth
= `content/`; no skin. Flag the absence so the user can add config.

## The invariant — never violated

1. **Quote-first.** No claim reaches prose without a verbatim, on-disk quote from a primary source,
   recorded in `literature/verified_claims/<author>_<year>.md`. Enforcement is mechanical, not
   trust-based, via one shared checker so it cannot drift between agents. What runs where differs by
   what each point can see: a write-time hook (Claude Code) and `.githooks/pre-commit` and CI all run
   `tools/check_citations.py` — every cited paper has a committed ledger (the *coverage* guarantee,
   which holds on any path); `.githooks/pre-commit` additionally runs `literature/verify_quotes.py`
   to prove each ledger quote is *verbatim* in its source (the verbatim guarantee — local only, as it
   needs the git-ignored corpus; CI cannot run it). A paywalled or inaccessible source → STOP and ask
   the user to fetch it; never write a stub to get past the check.
2. **Human-in-the-loop.** Propose a paragraph-level diff, wait for explicit approval, then apply.
   Never auto-advance to the next section; never edit without showing the diff first.

## The bored reader test — top priority (G0)

Every paragraph must pass before a section is done. The reader is whoever `the_reader` names.

> Can that reader read this paragraph cleanly on first pass — grasping the point without
> backtracking, without holding more in working memory than the claim requires, and without doing
> interpretive work the author should have done?

Five fail-conditions (any one fires → fail):
- **R1** — ≥3 unfamiliar terms / IDs / numbers piled up before the main claim lands.
- **R2** — a paragraph that begins a new beat doesn't open by stating what it will show.
- **R3** — "this in turn / having established…" connective tissue forcing re-derivation.
- **R4** — two unrelated ideas welded into one paragraph.
- **R5** — a finding paragraph that opens with the caveat before the finding.

No section is applied with an unresolved R1–R5 flag. The bored reader test supersedes every other rule on
conflict.

## Universal principles

| Code | Headline |
|---|---|
| **R1–R5** | The bored reader test — top priority (G0) |
| A.1 | One paragraph = one idea; the first sentence states what it proves |
| A.3 | Finding-first: claim in plain words, then the numbers/detail |
| A.4 | Argument paragraphs: point → evidence → implication |
| A.5 | Cross-reference budget: one pointer per claim, at the end of the clause; no dead links |
| A.11 | Null / negative findings are named as findings, not buried |
| A.13 | Heterogeneous results are stratified, or the spread is named — no misleading pooled ranges |
| A.15 | Lucidity over loquacity — every sentence earns its place |
| E.15 | Headers carry the finding, not the topic label |
| B.5 | No argument-signposting (`importantly`, `notably`, `it is worth noting`) |
| B.6 | No self-certifying claims (`rigorous`, `the correct approach`) |
| B.7 | No meta-commentary on corrections |
| B.8 | No manufactured literature / knowledge gaps |
| B.9 | Hedge when interpretation outruns evidence (`may`, `suggests`, `is consistent with`) |
| B.10 | Enumerate alternatives before picking one |
| C.9 | Mechanism-first / observation-first, never apparatus-first |
| D.10 | Every numerical claim traces to a source (figure/table/citation/accession), never a file path |
| D.13 | Every citation has a `verified_claims/<author>_<year>.md` ledger |
| D.21 | First-mention: each named approach carries its citation + a one-line mechanism summary |
| D.22 | Define every non-standard term on first use, or replace it with a plain word |
| F.16 | British English; direct sentences |
| F.19 | No emojis |
| F.20 | Abbreviations defined at first use + collected in a glossary |
| F.21 | Readable prose where content allows; vary cadence |
| F.22 | Respect the agreed section length; reduction is first-class |
| **S.*** | Project skin rules — loaded from `skin_rules_file`, audited as gates (GS) |

Voice is set by the project (sole-author first person, a defined collective "we", or impersonal) —
named in `ledger.config.md` or the skin; never an undefined "we". In Markdown projects,
cross-references are `[[wikilinks]]`; dead links are forbidden (verify the target exists first).

## Writing loop — one section per invocation

1. **Locate** — read the named section from the source-of-truth; report its heading + paragraph count.
2. **Context** — read `ledger.config.md`, the skin, the section's sibling review (if any), and every
   `verified_claims/<author>_<year>.md` for papers it cites. Adopt the review's framing; do not
   re-derive. Flag any stale claim (number/source drift) to fix in this same pass.
3. **Claim ledger** — classify every sentence (numerical / methodological / citation / unsourced).
   For each citation, quote the verbatim CONFIRMED line from the ledger that supports *that specific*
   claim (the file existing is necessary, not sufficient). Any unsourced or outline-only claim → STOP (G4).
4. **Audit** — run the bored reader test (R1–R5) first on every paragraph, then the universal principles and
   every loaded skin rule. Output a flat violation list, no prose.
5. **Propose** — a paragraph-by-paragraph diff: Current (verbatim) / Proposed / Fixes (codes) /
   Sources. Plus, mandatory: per-paragraph bored-reader certification (no FAIL reaches the user),
   per-citation verified-claim quote, per-skin-gate certification, and the word delta. Wait for
   explicit approval. Edit nothing yet.
6. **Apply** — after approval: edit the source-of-truth; update any stale note in the same pass;
   add/refresh the `crosswalk.md` row; append a `content/log.md` entry.
7. **Log** — append a milestone to the project history (and `CURRENT_STATE.md` if the project uses one).
8. **Stop** — return control. Do not propose the next section.

## Curating the knowledge base — one operation per invocation

Bookkeeping (`crosswalk.md`, `content/log.md`, the `literature/` pipeline) is done directly; **all
prose edits to notes go through the writing loop above**, so ingested or saved material meets the
same bar as authored prose. Nothing compounds that has not been verified.

- **Ingest a source.** Acquire (`check.sh` → `fetch_paper.sh` → `extract_text.py`), then **extract
  claims per `spec/EXTRACTION.md`**: pick the source-type row, enumerate the source's own structural
  units, keep those bearing on an `inquiry.md` sub-question, and lift each verbatim span into a `> "…"`
  with a locus-derived `**ID:**`, `**Location:**`, and `**Addresses:**` — one ledger per voice. Verify
  (`build_register.py` → `verify_quotes.py`); a non-verbatim span is dropped, never paraphrased. Two
  runs should converge (`ledger repro`). Locate the notes it bears on
  (grep `crosswalk.md` + `content/`). Propose propagation, citing only verified quotes and flagging
  contradictions explicitly — never silently overwrite. Apply prose via the writing loop. Bookkeep:
  `crosswalk.md` rows, a `content/log.md` ingest entry, and `python3 tools/lint_wiki.py content`.
- **Save a good answer.** File a worthwhile exploration back as a note so it compounds. Confirm every
  claim traces to a `verified_claims/` quote (drop or mark what doesn't — a chat answer is not itself
  a source); write the note via the writing loop; bookkeep.
- **Health-check.** Mechanical first (`python3 tools/lint_wiki.py content` — dead/path-style links,
  orphans, uncatalogued notes), then a semantic pass (contradictions between notes, claims a newer
  source overturned, concepts mentioned but lacking a note, missing cross-references). Report; never
  auto-edit. Each fix is a separate approved pass.
- **Adversarial-faithfulness pass.** `python3 tools/faithfulness_probe.py` lists every
  supports/rebuts edge with its grounding quote. For each, read the quote against the inference and
  argue the *other* side: does the quote actually warrant this support/rebut, or is it read out of
  context / as stronger than the source means (possibility used as proof, a hedge dropped, a
  subgroup result generalised)? Where the use is genuinely unfaithful, file the challenge as a
  first-class record (`assess_record.py --kind faithfulness … --disputes <edge-rec-id> --span
  "<verbatim substring>"`); the probe prints the exact command. This does not *settle* faithful use
  (still judgement) — it makes the challenge sealed, attributable, and re-judgeable. Default to
  filing a dispute when the link is not airtight; report, never auto-apply.

## Hard gates

| Gate | Rule |
|---|---|
| **G0** | The bored reader test — highest priority. No apply with an unresolved R1–R5 flag. Supersedes all else on conflict. |
| **G1** | No proposal without a complete claim ledger (step 3). |
| **G2** | No edit without explicit approval of the diff. |
| **G3** | Two-part citation check: (1) a `verified_claims/<author>_<year>.md` exists; (2) each citation in the proposed prose has a verbatim CONFIRMED quote matching that specific claim. Part (2) is mechanically checkable: write the cite as `(Author YEAR #c1)` — `#c1` is the claim's ordinal in the ledger (or an explicit `**ID:**` alias) — and `check_citations.py` resolves it (Layer 2b). Posture is set by `claim_ids:` in `ledger.config.md` (off / optional / required). |
| **G4** | No claim without a source. Outline / aspiration is not data. |
| **GS** | Skin gates — no apply if a gate-tagged rule in the loaded skin is violated. |

## The pipeline this relies on

`literature/` — `check.sh` (already on disk?) · `fetch_paper.sh` (PMC / DOI / Unpaywall / OpenAlex /
web) · `verified_claims/<key>.md` (the quote ledger) · `build_register.py` (index) ·
`extract_text.py` + `verify_quotes.py` (verbatim proof). `content/` — `concept_notes/`,
`literature_reviews/`, `crosswalk.md` (the index), `content/log.md` (activity log),
`_ledger/skin_rules.md` (the skin). `tools/lint_wiki.py` — mechanical wiki health-check.

## Why this file exists

Ledger's authoring discipline is portable by design: the principles, the loop, and the gates are
agent-neutral, and the verification guarantee is enforced by plain code (`verify_quotes.py`) at
commit and push. This file ships that discipline in the repo, so anyone who clones it — on Codex,
another agent, or by hand — gets the whole system, not just the guarantee. The author additionally
uses the Claude Code skills as a personal frontend; this file does not change or depend on that.
