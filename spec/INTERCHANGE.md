# Ledger interchange format — v0.1

**Status:** versioned, tool-independent. This document + the JSON Schemas in `schemas/` are the
published contract for Ledger's compounding artefacts, so a *non-Ledger* tool can **emit** or
**consume** them and have its pieces interoperate with a Ledger project. Nothing here depends on
Ledger's Python: the formats are plain Markdown conventions and plain JSON. The *process* that
produces a claim ledger from a raw text base — near-deterministically and across corpus types — is
the companion spec `EXTRACTION.md`.

The artefacts:

| Artefact | Where | Schema | What it is |
|---|---|---|---|
| **Claim ledger** | `literature/verified_claims/<key>.md` | (Markdown grammar, §1–§2 below) | one source's verbatim quotes, each with a stable claim id; the atom |
| **Claim-graph edge** | in-band lines in a ledger | (grammar, §3) | a typed, grounded claim-to-claim relationship |
| **Assessment record** | `content/assessments/_records/<id>.assess.json` | `schemas/assessment_record.schema.json` | a sealed, quote-grounded judgement |
| **Run-record** | `literature/verified_claims/_runs/<key>.run.json` | `schemas/run_record.schema.json` | an auditable verification attestation |
| **Graph export** | `content/graph.json` (derived) | `schemas/graph.schema.json` | the single interrogable view of the argument |

Versioning: this is `v0.1`. The schema `$id`s carry `/v0.1/`. A breaking change bumps the minor
version; additive fields do not. `assess_version` / `verifier_version` inside records track the
record-writer's schema independently.

---

## 1. Claim address — `key:slug`

Every claim has a **global address** `<ledger_key>:<slug>`:

- `ledger_key` is the ledger's filename stem (`andersen_2020` for `andersen_2020.md`).
- `slug` is the claim's stable `**ID:**` value, or its ordinal `cN` (1-based, by header order).
- A **bare** `slug` (no `key:`) means "this ledger" — it resolves within the ledger it is written in.

Addresses are lower-cased for matching. Resolution succeeds only when the ledger file is present
**and** the slug names a real claim in it; a renamed ledger dangles rather than silently
re-resolving (exact-stem matching).

## 2. Claim ledger (Markdown)

A ledger is a Markdown file whose claims are `## Claim` blocks. The minimum a consumer must parse:

```markdown
## Claim 1: short summary

> "the verbatim quote, exactly as in the source"

**ID:** some-stable-slug
**Location:** Section 3.2
```

- The `> "…"` blockquote carries the **verbatim** quote (the text between the first and last
  double-quote on the quote line(s)). This is what the verbatim gate checks against the source.
- `**ID:**` gives the stable slug. A claim with no `**ID:**` is addressable only by ordinal `cN`.
- Frontmatter carries the provenance stamp (source/extract/body sha256, verdict, locator) — see the
  run-record schema for the same fields in JSON.

## 3. Claim-graph edge grammar

An edge is a single in-band line authored **under the grounding claim**, of the form:

```
**<Label>:** <target-address> (grounded by #<grounding-slug>) [rec: <record-id>]
```

- **`<Label>`** is one of the eight edge types (canonical lower-case in JSON):

  | Label | type | meaning |
  |---|---|---|
  | `Supports` | `supports` | inference: the grounding claim supports the target |
  | `Rebuts` | `rebuts` | inference: the grounding claim rebuts the target |
  | `Depends-on` | `depends-on` | the target is a premise of the grounding claim |
  | `Refines` | `refines` | similar but not identical; a sharpening |
  | `Qualifies` | `qualifies` | a bounded caveat (e.g. a subgroup result) |
  | `Restates` | `restates` | same proposition, an INDEPENDENT statement |
  | `Duplicate-of` | `duplicate-of` | same source re-logged → collapses to one node |
  | `Supersedes` | `supersedes` | the grounding claim overtakes the target over time |

  The taxonomy is small: bloat is a generalisability risk and a gaming surface.
- **`<target-address>`** is a `key:slug` (or bare slug) address (§1).
- **`(grounded by #<grounding-slug>)`** names the claim in *this* ledger whose quote asserts the
  relationship — the edge's source endpoint. A missing grounding clause is surfaced (`null`), not
  dropped, so a gate can flag it.
- **`[rec: <record-id>]`** (optional) links the edge to an assessment record judging it apt.

The edge source endpoint in the graph export is `<from_ledger>:<grounding-slug>`.

## 4. Assessment record (JSON) — `schemas/assessment_record.schema.json`

A sealed judgement about a claim. Key invariants a consumer should honour:

- `record_sha256` is the sha256 over **all other fields**, serialised as canonical JSON (sorted
  keys, UTF-8, no `record_sha256` key). It is the self-seal: recompute it to detect a hand-edit.
- `body_sha256` is the sha256 of the **subject** claim's current body; a mismatch means the
  assessed claim was edited after the judgement (stale → re-seal).
- `kind` is one of the schema enum values. `faithfulness` is the adversarial-faithfulness contest:
  its `span` must be a verbatim substring of its grounding quote, and its `disputes` must be
  non-empty (it contests a record on the **same subject** — typically an `edge` aptness record).
  `faithfulness-pass` is the positive paired review: the edge was adversarially read and no
  quote-context dispute was filed; its `reviews` must be non-empty.
- `disputes` makes competing judgements first-class: each entry is a record id assessing the same
  subject. This is how disagreement is recorded rather than resolved.
- `reviews` links a positive review to the edge record it reviewed.

Example: `examples/assessment_record.example.json`.

## 5. Run-record (JSON) — `schemas/run_record.schema.json`

An auditable attestation of one *local* verification. The trust boundary is explicit in the fields:
`source_sha256` is local-only (the corpus is git-ignored, so CI cannot re-hash the source bytes),
while `body_sha256` is recomputable from the committed ledger, so a quote edited after stamping is
caught at the push gate. `record_sha256` self-seals as in §4. This is **auditable, attributable
attestation, not independent proof**.

## 6. Graph export (JSON) — `schemas/graph.schema.json`

`content/graph.json` is the **derived** single view: `nodes`, typed `edges`, `sub_questions`,
`addresses` (claim→sub-question references), `assessments`, and derived `findings`
(`double_count`, `superseded`). It is never hand-edited and is git-ignored — a consumer regenerates
it, or reads a committed copy as a snapshot. Derived `findings` are **heuristics, not proofs**.

Each `double_count` entry is a typed object:

```json
{
  "a": "chen_2021",
  "b": "sun_2021",
  "target": "zhao_2022:harmful-mortality",
  "kind": "exact-cohort-reuse",
  "basis": "both analyse the WHI cohort — not independent evidence",
  "sealed_record": "whi-double-count"
}
```

- **`a`, `b`** — the two correlated supporters, by ledger key (a canonical unordered pair).
- **`target`** — the claim address both support.
- **`kind`** — one of `exact-cohort-reuse` · `overlapping-pools` · `shared-evidence` ·
  `other-declared-dependence`, read from `content/correlation_kinds.md` (below); a pair the file does
  not classify falls back to `other-declared-dependence`. Author-declared, never inferred.
- **`basis`** — the free text of the ledger's own `Correlated-with:` annotation: authored, not
  source-verified (a surface labels it "Declared basis").
- **`sealed_record`** — the id of a `kind: correlated-with` assessment record whose grounding names
  both members of the pair (**sealed**); `null` means the dependence is **declared-only**.

Example: `examples/graph.example.json` (the eggs / dietary-cholesterol case).

### The author-declared correlation-kinds surface — `content/correlation_kinds.md`

A correlation's `kind` is authored epistemic metadata, so it lives in a committed, validated,
author-declared file — never in a stamped ledger body (a `kind:` edit there makes the existing stamp
and bound records stale). Format:

```markdown
---
authored_by: <identity>
last_updated: YYYYMMDD
status: active
---
## <keyA> ↔ <keyB>
- kind: exact-cohort-reuse
```

- **Provenance fields** `authored_by` / `last_updated` / `status` are required.
- **Pair canonicalisation**: `## a ↔ b` names the unordered pair `{a, b}`; `b ↔ a` is the same
  entry, and a duplicate is rejected.
- Each pair must resolve to a real declared `Correlated-with:` edge (no orphans); the kind must be
  allowed; a missing classification defaults to `other-declared-dependence`.
- The file **classifies; it never seals** — it cannot change a pair's sealed-vs-declared status.
  Validated by the assessment gate.

## 7. Conformance

A producer is conformant if its emitted JSON validates against the schemas in `schemas/` and its
ledgers/edges parse under §1–§3. `tests/test_interchange.py` validates the kit's own emitters and
the bundled examples against these schemas with a dependency-free checker, so a drift between the
published contract and the implementation fails the test.

## 8. What the format does NOT carry

The interchange format is about **shape and provenance**, never **truth**. A conformant assessment
record is sealed and grounded; it is not therefore *correct*. A resolvable edge is not therefore
*apt*. A faithfulness dispute is a recorded challenge, not a verdict; a faithfulness-pass record is
a recorded review, not proof. The contract guarantees form and names the judgement it cannot
mechanise (see `../docs/integrity_framework.md`).

The three presentation layers a pack/dashboard stacks (derived summary · recorded judgements ·
authored interpretation) are **derived views over this data, not part of the interchange contract**:
a conformant consumer reads the ledgers, edges, records, `correlation_kinds.md` and `graph.json`
above and renders them however it likes.
