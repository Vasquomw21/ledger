# Ledger — the evaluator's path

*Auditing Ledger rather than using it? This is the whole tour. To use it instead, start from the
[README](README.md).*

Ledger is a research toolkit for people and AI working together. It keeps a growing knowledge base
tied to its evidence: every citation in gated, authored prose must point to a quotation checked
against the original source, while the claims, their connections, and human judgements remain
visible and reviewable.

Ledger does not establish that the sources are complete, the reasoning is sound, or the conclusion
is true. When the source files are unavailable, it attests the committed proof rather than
re-checking the bytes.

The verification spine is plain Python enforced at three independent points, so the guarantee holds
under any agent — Claude Code, Codex, or a human hand-editing. A citation that points to a quotation
not verified against its source cannot pass the gate.

> *Citation fabrication* is caught mechanically — a quotation that is not verified verbatim
> cannot enter gated, authored prose through a citation. (Which prose that covers is a
> declaration, `gated_paths`: material you archive rather than assert, such as a captured model
> transcript, stays ungated on purpose — see [`cases/README.md`](cases/README.md). And that every
> claim carries a citation at all is a human discipline above the mechanical gate — the gate secures
> each citation, not that one exists.)
> *Faithful interpretation* is likewise not a mechanical guarantee: a real
> quote can be read tendentiously or out of context. That stays a matter of judgement — Ledger
> **assists** it (`ledger faithfulness` walks every inference and a reviewer argues whether the
> grounding quote warrants it; a genuine gap is filed as a sealed `faithfulness` **dispute** record)
> and **surfaces** it (assessments, Known gaps, `ledger inspect analysis`), but does not claim to prove it.
> The boundary is the table in §4.

---

## 1. Run the tour

```bash
# Zero installs — the demo tools are pure Python stdlib (needs only python3 ≥3.10):
python3 ledger_cli.py demo cases/covid_origins_ledger   # tour a worked case, read-only
python3 ledger_cli.py demo                               # tour THIS repo (the empty kit)
```

`make demo DIR=cases/covid_origins_ledger` wraps the same command; **bare `make demo` tours this empty starter kit** (the root ships no content), so pass `DIR=cases/…` to exercise the gates. To run the **test
suite** or **ingest new papers**, install the pip extras once (`pip install -r requirements.txt`,
or `make venv`); only those tiers need third-party libraries. conda (`make conda-env`) is an
optional route to the full intake/publish toolchain (node/gh/jq) — not needed to evaluate the kit.

For a navigable, zero-install review **bundle**, generate a judge pack:

```bash
python3 ledger_cli.py pack cases/covid_origins_ledger --out /tmp/covid_judge_pack
# then open /tmp/covid_judge_pack/index.html in any browser
```

The bundle carries no raw corpus, so it opens stating its own verification ceiling: the committed
records are **attested** there, not re-proved from source bytes. It reads `Guaranteed` only for what
you can check from the folder in your hands (§4 is the same boundary, per surface).

`index.html` is organised **Inputs → Processes → Outputs** (the Ingestion → Structure →
Assessment stack): a guaranteed-vs-judged trust table, a flow infographic with the human-in-the-loop
band, a **table of ingested documents** that links to a rendered page per ledger (provenance, stamps,
verbatim claims, and edges cross-linked to the documents they cite), the **five-layer integrity
stack** (each failure mode and how strongly Ledger catches it) beside the enforced-gates checklist, a
**Collaboration** section that maps every human touchpoint (write a verified quote, contest a quote's
use, declare gaps, draw an edge, assess, curate) to the exact command that performs it — plus the live
"awaiting judgement" queue and a presentation-vs-production note — and the interactive
argument graph. It opens offline in any browser, light or dark (a theme toggle sits in the nav) — no
install, no server, no CDN (markdown is rendered
by an in-kit dependency-free converter). It is derived output for judges and collaborators; the source
of truth remains the Ledger project. (`ledger dashboard <case>` emits the same interactive graph as a
single emailable HTML file.)

`ledger_demo.sh` runs the **full commit-time gate set** read-only, in dependency order — project
health, the operator dashboard, the verbatim-quote check (byte re-proof is corpus-gated; when the
corpus is absent the committed stamp is attested, not re-hashed), provenance stamps, citation
coverage, the claim-graph structure and assessment gates, the opt-in claim-coverage / attestation /
**selection** / **source-flow** / unit / synthesis gates, and wiki health — then the read-only
views: the Mermaid argument graph, the validity analysis, and the **adversarial-faithfulness
worklist**. The tour's exit code is the worst of every gate it runs; nothing is written.

## 2. The five worked cases — one command each

The cases are **vendored under [`cases/`](cases/)** — each a complete, standalone Ledger
project (its own kernel, config, ledgers, graph, assessments), copied in so the whole demonstration
is **one clone, offline**. Each stands up the same kernel on a deliberately different *kind* of
question; every node in each traces to a stamped verbatim quote. The `quantum_genomics_ledger` case is on a subject **entirely outside the three provided case topics** (COVID origins, LHC black holes, dietary cholesterol).

| Run this | Case | Kind of question | Inspect first |
|---|---|---|---|
| `make demo DIR=cases/covid_origins_ledger` | FCS engineering? **and** does the early evidence locate origin at the market? | a **contested**, multi-source debate (5 sources, 2 sub-questions) | the **double-count finding** (Worobey + Pekar both support "no lab scenario" but share the early-case data → correlated, flagged); the **faithfulness dispute** challenging the market-epicenter inference as ascertainment bias |
| `make demo DIR=cases/lhc_safety_ledger` | Could LHC collisions make a dangerous black hole? | a **closed technical** case | the `depends-on`/`supports` spine resting on the crux astrophysical bound; the official review marked `performed-settling` |
| `make demo DIR=cases/eggs_cholesterol_ledger` | Do eggs / dietary cholesterol raise CVD risk? | **messy, confounded — 16 sources at corpus scale** | **`content/finding.md`**: applied framing-agnostically, the machinery maps each study to its cohort and flags **three same-cohort double-counts on both sides** (WHI, six-US-cohort, and the null pair), surfacing that confidence in this literature tracks whether a meta-analysis de-duplicates overlapping cohorts. It makes the overlap *auditable*; it does **not** overturn the answer |
| `make demo DIR=cases/quantum_genomics_ledger` | Is there a real quantum-computing advantage for genomics — and what does it mean for genomic-data security? | **out-of-domain** generalisability proof (outside the three provided topics); 17 sources | **`content/finding.md`**: the popular QML "exponential speedup" case turns on **one contested primitive (HHL)**; the **double-count** flags Tang + Chia (same dequantisation *method* → correlated, not independent) on the *skeptical* side while the independent Cerezo supporting the same claim is **not** flagged; a sealed **faithfulness dispute** on the scope of Tang's result. It does **not** claim quantum computing is useless: chemistry is a real *projected* advantage and the crypto threat is real |
| `make demo DIR=cases/covid_debate_ledger` | The recorded Rootclaim COVID-origins debate (lab-leak vs zoonosis + two judges) | **reproducibility / method** — one ledger per voice across source-types (the EXTRACTION.md demonstrator) | the one-ledger-per-voice structure + cross-voice edges; re-run **`ledger repro`** to measure extraction convergence (two blind runs agree on the sub-questions, diverge on span/slug naming) |

(Without `make`: `./ledger_demo.sh cases/covid_origins_ledger`.) The raw corpus is git-ignored and
not shipped, so the verbatim step **attests** each ledger's committed stamp here (the same check
CI runs on a fresh clone — see the trust boundary in §4); rebuild a case's corpus with its
`literature/fetch_paper.sh` to re-prove quotes byte-for-byte. See [`cases/README.md`](cases/README.md).

## 3. What to inspect first

In any case under `cases/`, follow this order — it walks the three layers — Ingestion, Structure, Assessment — bottom-up:

1. **Ingestion / fidelity** — `literature/verified_claims/*.md`: the quote ledgers. Each `## Claim`
   carries the verbatim `> "…"` quote, a stable `**ID:**` slug, and a provenance stamp.
2. **Selection (Layer 2)** — `content/source_register.md`: the declared positions and the
   `## Known gaps`. The audit proves no declared position is silently empty.
3. **Source flow (Layer 2)** — `content/source_flow.md`: the searches, screening counts, and
   included-source route into the corpus. The audit proves every included ledger has a declared
   path in, not that the path is complete.
4. **Structure** — the in-band edge lines in the ledgers (`**Supports:** key:slug (grounded by
   #slug)`), then `make demo` step 6 (`ledger graph --mermaid`) for the rendered argument map.
5. **Assessment** — `content/assessments/_records/*.assess.json`: sealed, quote-grounded
   judgement records (rhetorical overreach, crux, calibration, correlated-evidence double-count,
   edge aptness, and `faithfulness` **disputes** — an inference whose grounding quote was
   adversarially challenged).
6. **Judge dashboard** — `ledger dashboard --out /tmp/ledger_dashboard.html`: a static page with
   postures, unassessed supports/rebuts, source-flow gaps, selection gaps, double-counts, and record
   parse errors in one place.
7. **Validity & faithfulness assistance** — `ledger inspect analysis` (load-bearing claims, dependency
   closure, double-counts) and `ledger faithfulness` (every inference + whether its grounding quote
   has survived an adversarial read). No verdict — pointers for *your* judgement.

## 4. Guaranteed vs judged — the trust boundary

The gates are **mechanical about *form*, never about *truth***.

| Property | Local (corpus on disk) | CI / fresh clone (corpus git-ignored) | Class |
|---|---|---|---|
| A cited quote is **verbatim** in its source | **re-proved** (`verify_quotes.py`) | **attested** via committed body-hash + run-record | Guarantee (local); attestation (CI) |
| Every citation has a **committed ledger** | enforced | enforced (`--no-corpus`) | Guarantee (everywhere) |
| The **right paper** was fetched (source identity) | bound (sha256 + locator) | attested (stamp shape) | Guarantee/attestation |
| Every graph **edge resolves** + carries a grounding clause | enforced | enforced | Guarantee (of *form*) |
| Every **assessment record** is sealed + grounded + fresh | enforced | enforced | Guarantee (of *form*) |
| The corpus has **no silent empty position** | enforced | enforced | Guarantee (of *form*) |
| Every included ledger has a **declared discovery/screening route** | enforced | enforced | Guarantee (of *form*) |
| A quote is used **faithfully** (in context) | — | — | Judged + **measured + adversarially assisted** (`ledger faithfulness-eval` → a detection rate; `ledger faithfulness` → dispute records) |
| An edge is **apt** (the inference is warranted) | — | — | Judged (assessment record) |
| A **conclusion follows** from the evidence | — | — | Judged (`ledger inspect analysis` assists) |
| The corpus is **representative / complete** | — | — | Judged (surfaced as Known gaps) |

Provenance is *source binding at commit, body + shape attestation in CI*: CI
cannot re-hash the source bytes (the corpus is git-ignored), but it recomputes the body hash from
the committed ledger, so a quote edited after stamping is still caught at the push gate.

### The three trust layers every pack and dashboard renders

Every exported pack and dashboard stacks the same three layers, in one order, from the same shared
models—so the trust boundary is visible on the page, not only in this table:

1. **What Ledger derived from committed records** — mechanically-derived structure: dependence
   warnings, claim targeting, review coverage. Deterministic and reproducible. **Deterministic does
   not mean epistemically true** — a count is a count, and a correlation's *kind* (exact-cohort-reuse,
   overlapping-pools, shared-evidence, other-declared-dependence) is **author-declared** metadata in
   `content/correlation_kinds.md`, never a machine-established fact.
2. **Recorded judgements** — sealed, attributable assessments. **Sealing proves record integrity,
   freshness and resolvable grounding references—not that the grounding is apt or the judgement
   correct**: a record is verified sealed, body-fresh and linked to resolvable grounding, never
   verified right.
3. **Authored interpretation** — the *optional* `content/finding.md`. Its references are validated,
   but the wording and conclusion are the author's. **A pack remains usable without it**: Layers 1 and
   2 still render, and the evidence trace derives from warnings and records independently of authored
   prose.

## 5. The five integrity layers — why the boundary falls where it does

Knowledge work fails in five distinct ways, stacked foundation→delivery; enforcement strength is
**inversely correlated** with how far up the stack you go (the full framework, with the coverage
matrix, is in [`docs/integrity_framework.md`](docs/integrity_framework.md)):

| Layer | Failure it guards | Strength in Ledger |
|---|---|---|
| **1 Fidelity** | fabricated quote · wrong paper · quote out of context | **Guarantee** (fabrication) · structural (wrong paper) · **Measured + Assisted** (out-of-context — `ledger faithfulness-eval` puts a detection rate on a hand-labelled benchmark; `ledger faithfulness` worklist) |
| **2 Completeness** | selection bias · missing source | structural + assisted; selection audit is a **floor against silent one-sidedness**, not a representativeness proof |
| **3 Coherence** | broken/absent links · contradiction · stale claim | structural (links) + assisted (meaning) |
| **4 Validity** | conclusion doesn't follow · cherry-picking | **judged**, with `ledger inspect analysis` assistance — the frontier |
| **5 Clarity** | opacity · undefined jargon | judged, enforced in the writing loop (the bored-reader test) |

## 6. Posture profiles

A project's strictness is one config block. **Day to day you pick a named profile**, not thirteen
flags. `ledger profiles <name>` prints the block to paste into `ledger.config.md`:

- **pristine** — the untouched starter kit (lax by design; ships green).
- **strict-local** — *configured ⟹ strict*: all five strict postures bite locally.
- **submission** — everything on: the maximal posture for a reviewed, shareable artefact.

The underlying flags (`claim_ids`, `numeric_citations`, `provenance`, `structure_layer`,
`assessment_layer`, `graph_coverage`, `edge_assessments`, `selection_audit`, `source_flow`,
`attestation`, `semantic_health`, `units_layer`, `synthesis_claims`) remain available for fine control — see the appendix in
`ledger.config.md`.

### Human-in-the-loop

The synthesis loop is *propose → approve → apply → stop*; it never auto-advances.
A more hands-free run is possible (drafting ledgers and edges automatically), but it **relaxes the
human-approval posture** — the mechanical gates (verbatim, coverage, structure, sealing) still
hold, while the *judgement* layers (faithful use, aptness, selection) go un-reviewed until a human
returns.

## 7. Glossary (plain language)

- **ledger** — one source's verified-claim file (`verified_claims/<key>.md`): its verbatim quotes,
  each with a stable claim ID and a provenance stamp. The atom everything else is built from.
- **kernel** — the portable machinery copied into every Ledger project (the gates, `tools/`, the
  hook, CI). Identical across subjects.
- **skin** — the subject-specific layer re-authored per project: the writing rules, the intended
  reader, the source formats, the config. (kernel = same everywhere; skin = per subject.)
- **claim graph** — typed claim-to-claim edges (`supports`/`rebuts`/`depends-on`/`qualifies`/…),
  each addressed across sources as `key:slug` and grounded in a specific quote.
- **selection audit (Layer 2)** — the check that every declared position is covered by a source or
  named under `## Known gaps` — proving the declared set has no silent empty side.
- **crosswalk** — the index linking note ↔ review ↔ source ↔ section.
- **bored-reader test (a.k.a. the Mara test)** — the readability gate: would a tired, intelligent
  non-specialist follow this on first pass? Named after a specific reader; supersedes other style
  rules when they conflict.

## 8. Going deeper (tracked)

- [`docs/integrity_framework.md`](docs/integrity_framework.md) — the full five-layer framework +
  coverage matrix (what Ledger guarantees, assists, and leaves to the user).
- [`docs/faithfulness_eval.md`](docs/faithfulness_eval.md) — a *measurable* out-of-context detection
  rate: a class-balanced hand-labelled benchmark, scorer (`ledger faithfulness-eval`), and
  transparent rule baseline (`ledger faithfulness-baseline`), with its boundary (measures a
  *detector*, not a guarantee).
- [`README.md`](README.md) — the starter-kit tour, the provenance/stamp mechanism in full, the
  citation-gate scopes, and how Ledger relates to Karpathy's *LLM Wiki*.
- [`AGENTS.md`](AGENTS.md) — the agent-neutral authoring + curation discipline (any agent, or by
  hand).
- [`spec/INTERCHANGE.md`](spec/INTERCHANGE.md) — the versioned, tool-independent format (claim
  graph, assessment records, run-records, graph export) + JSON Schemas, so another tool can emit or
  consume Ledger artefacts.
- [`docs/extending.md`](docs/extending.md) — how the kit extends: the kernel/skin seam, standing up
  a new subject by hand, and adding an edge type, assessment kind, or gate/posture.
