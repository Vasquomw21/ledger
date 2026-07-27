# Extending Ledger

Three things a Ledger user or contributor extends: a **new subject** (the common case — write a
skin over the copied kernel), the **interchange taxonomy** (a new edge type or assessment kind), and
the **enforcement layer** (a new gate/posture). This page covers all three, plus the kernel/skin
seam they sit on. It assumes no Claude Code — every step is a file edit any agent or human can make.

## The kernel/skin seam

The **kernel** is the machinery copied verbatim into every project: the intake pipeline, the gates
in `tools/`, the travelling citation hook, the pre-commit and CI wiring. The **skin** is the thin
per-subject layer you author. `ledger_doctor` enforces the seam mechanically — a project is
`pristine` (untouched kit), `configured` (skin filled, all strict postures adopted), or `broken`
(a declared state its files contradict). Every vendored case under `cases/` carries a full duplicated
kernel; a `diff` across two of them shows what is kernel (identical) and what is skin (differs).

What is kernel, and the evidence it is domain-neutral (file-level diff across two real projects):

| Kernel artefact | Function | Evidence of neutrality |
|---|---|---|
| `literature/fetch_paper.sh` | retry-ladder source downloader with identity validation | byte-identical across two subjects |
| `literature/check.sh` | pre-download register lookup | 1-line diff (a path in an error string) |
| `literature/build_register.py` | source register from disk + ledgers | 2-hunk diff, both path-portability refactors |
| `literature/extract_text.py` | greppable text from PDF/HTML | self-locating; zero domain terms |
| `literature/verify_quotes.py` | mechanical verbatim-quote verifier | self-locating; zero domain terms |
| `.claude/hooks/verify-citations.sh` | block prose citing an undownloaded/unquoted source | resolves `literature/` relative to its own location, so it travels to any clone |
| `tools/*` gates | the enforcement layer (coverage, provenance, structure, assessment, …) | self-locating (`parents[1]`); posture-driven, no subject terms |
| schema-file templates | the three-file split, as blank templates | structure invariant, content is skin |

The skin is what you write per subject: a domain-principle pack, the source-of-truth format, the
named reader (for the Mara readability test), and the config. A single writing discipline
(`AGENTS.md`, or `skill-ledger-write` in Claude Code) holds the universal rules and *loads* the
per-project skin, so a universal fix benefits every subject.

## 1. Stand up a new subject (by hand)

`skill-ledger-bootstrap` automates this in Claude Code. `ledger init` does steps 2 and 3 with no
agent at all — it previews, asks, then makes one atomic write per file, and refuses rather than
creating anything it could not un-make. It leaves `project_state` to you, so the strictness you end
up with is always something you declared. The fully manual path below is four steps, and is what
both of them write.

1. **Copy the kit** to a new folder and `git init`. Activate the commit gate once:
   `git config core.hooksPath .githooks`.
2. **Fill `ledger.config.md`** — the only per-subject *config* file. Set `project_name`, `project_root`,
   `deliverable`, `source_of_truth`, `the_reader` (names the Mara reader), `source_types`,
   `unpaywall_email`, and `gated_paths` (the prose dirs the citation gate covers). Flip
   `project_state: configured` — which makes the project **strict by definition**: `ledger_doctor`
   then requires `claim_ids: required`, `numeric_citations: block`, `provenance: required`,
   `structure_layer: required`, `assessment_layer: required`. **Set those five in the same edit**
   (paste a block from `python3 ledger_cli.py profiles strict-local`, or `submission`) — otherwise
   `ledger_doctor` reports `broken` at step 4. To run softer, stay `pristine`.
3. **Write the skin** — `content/_ledger/skin_rules.md` (subject-specific writing rules) and the
   gated content dirs (`content/concept_notes/`, `content/literature_reviews/`). Rules given to
   `ledger init --rule` land here and the project reads as `drafted` (gates lenient) until you
   sharpen them and set `skin_state: confirmed`; a skin of filler would be worse than one that
   admits it is empty.
4. **Prove the loop** on one real source — fetch, extract, write the ledger, stamp, then cite.
   Substitute `KEY` (a short source id) and `PMCID` (or use `--doi` / `--title`):

   ```bash
   # a. fetch the primary source into literature/ (PMCID → PMC body HTML)
   literature/fetch_paper.sh --out literature/KEY.html --pmcid PMCID
   # b. build the greppable text layer so quotes can be mechanically verified
   python3 literature/extract_text.py KEY
   # c. read + grep the text, then hand-write literature/verified_claims/KEY.md — the
   #    > "…" quotes with section/page refs (copy TEMPLATE.md; set its `file:` frontmatter
   #    to literature/KEY.html so --stamp can locate the source)
   # d. bind the provenance stamp: source/extract/body sha256 + verbatim verdict
   python3 literature/verify_quotes.py --stamp
   ```

   `python3 ledger_cli.py doctor` should now report `configured`.

`python3 ledger_cli.py profiles` prints copy-paste posture blocks
(`pristine`/`strict-local`/`submission`) so you needn't set the ~13 flags by hand.

## 2. Extend the interchange taxonomy

The taxonomy is deliberately small (see `spec/INTERCHANGE.md` §3–§4). Adding to it is a coordinated
edit across code + published schema, and `tests/test_interchange.py` fails until they agree.

**A new edge type** (e.g. `qualifies`):
1. Add the label to `EDGE_LABELS` in `tools/claim_graph.py` — the edge regex derives from it, so
   parsing is automatic.
2. Add it to the `edges[].type` enum in `spec/schemas/graph.schema.json` and the
   `spec/INTERCHANGE.md` §3 edge table. (The assessment-record schema has no edge-type field —
   an edge is assessed by a `kind: edge` record keyed on target+grounding, so nothing changes there.)
3. Give it semantics only where needed. The assessed `supports`/`rebuts` subset is defined ONCE as
   `check_assessment.ASSESSED_EDGE_TYPES` and imported by `build_graph`, `analyze_graph`,
   `judge_dashboard`, and `faithfulness_probe`; contradiction is hardcoded in `check_structure.py`.
   (`analyze_graph.SUPPORT_TYPES` is a SEPARATE set — the `supports`/`depends-on` dependency spine —
   not the assessed subset.) A label-only type resolves and renders without
   touching these; a type with argument force does not.

**A new assessment kind** (e.g. `precision`):
1. Add it to the `ASSESS_KINDS` frozenset in `tools/assess_record.py` — it propagates to the CLI
   `--kind` choices and to `check_assessment`'s membership check.
2. Add it to the assessment-record schema enum and `spec/INTERCHANGE.md` §4.
3. Add a validation branch only if the kind needs one (e.g. `rhetorical`/`faithfulness` require a
   quote-pinned span; `faithfulness` must contest a record on the same subject).

**A new source type** is the frictionless case: one row in the `spec/EXTRACTION.md` table plus the
deterministic slug rule — no code, no schema enum, no gate. It is advisory.

## 3. Add a gate/posture

Every posture flows through the canonical registry `tools/postures.py`, and three tests fail if a
consumer falls behind: `tests/test_postures.py` (the operator dashboard, the judge-pack checklist,
the config template), `tests/test_ledger_cli.py` (the named profiles), and
`tests/test_gate_parity.py` (pre-commit vs CI run the same gate).

To add a posture `foo_layer`:
1. Add `("foo_layer", "Foo layer", "required")` to `POSTURES` in `tools/postures.py`.
2. Declare `foo_layer:` in `ledger.config.md` (the template and your project), and add the key to
   each named profile in `ledger_cli.py`.
3. Write `tools/check_foo.py` with a `foo_mode(config)` reader returning `off`/`warn`/`required`
   (copy an existing gate — they share `parse_config` and the off→skip / warn→report / required→fail
   contract; an empty layer must always pass).
4. Add the reader to the `readers` map in `tools/ledger_status.py`.
5. Add a gate block to `.githooks/pre-commit` **and** a matching step to `.github/workflows/ci.yml`
   (both must run it — a corpus-dependent gate is the only allowed local-only exception).

Run `pytest -q`; the three guard tests above name any consumer you left behind.
