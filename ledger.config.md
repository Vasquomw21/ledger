# Ledger project config
#
# Filled by skill-ledger-bootstrap at setup. These are the only values that
# change per subject — everything else is the reusable kernel.

project_name:        <e.g. water_policy_ke>
project_root:        <absolute path on disk>
deliverable:         <thesis chapter | policy white paper | report | book companion | ...>
source_of_truth:     <markdown+quartz | docx+python>
the_reader:          <the bored reader, e.g. "a busy minister AND a sceptical scientist">
source_types:        <peer-reviewed papers | legislation & gov reports | books | web | mixed>
unpaywall_email:     <your email for the download service>
# Tracked project mode. pristine = the untouched starter kit (placeholders, empty
# skin, lax postures — and that is fine); configured = a real bootstrapped subject.
# skill-ledger-bootstrap flips this to 'configured' AND sets the five strict
# postures below (claim_ids: required, numeric_citations: block, provenance:
# required, structure_layer: required, assessment_layer: required). ledger_doctor
# cross-checks the declared mode against what the project
# actually looks like (filled fields + written skin): a declared mode that
# contradicts the derivation is 'broken'. Absent → defer to the derivation.
project_state:       pristine
# Prose directories the citation gate covers (comma-separated). Bootstrap
# appends the per-subject deliverable dir here (e.g. content/white_paper/).
gated_paths:         content/concept_notes/, content/literature_reviews/
# Claim-ref posture. A cite may point at a specific quoted claim — (Author YEAR #c1).
# off = ignore refs · optional = validate a ref when present · required = every cite
# must carry a resolvable ref. A ref that names a non-existent claim always fails.
# The kit ships 'optional'; skill-ledger-bootstrap sets 'required' for a real
# project — it forces every cite to name its quoted claim, closing "right paper,
# wrong claim". A CONFIGURED project is strict by definition: ledger_doctor (every
# gate, not just --require-configured) hard-fails a configured project whose
# claim_ids is not 'required'. To run softer, the project must stay pristine.
claim_ids:           optional
# Numeric/superscript citation markers ([42], method.⁵⁴) can't be resolved to a
# ledger without a references map. ignore = silent · warn = report, don't block
# (default) · block = fail the gate on them. Set 'block' if your project is
# strictly author–date and wants numeric styles rejected everywhere.
numeric_citations:   warn
# Provenance binding: each ledger frontmatter records the source+extract sha256 it
# was verified against (verify_quotes.py --stamp). off · warn (default — report a
# missing/stale stamp) · required (block). pre-commit rebinds; CI attests shape.
# The kit ships 'warn'; skill-ledger-bootstrap sets 'required'.
provenance:          warn
# Structure layer (the verified-claim graph). off = skip · optional = validate the
# edges that exist but only warn (default) · required = block on an unresolved or
# ungrounded edge, a contradictory pair, or a bad sub-question id. No posture ever
# forces edges to exist, so an empty graph passes everywhere. The kit ships
# 'optional'; skill-ledger-bootstrap sets 'required'.
structure_layer:     optional
# Assessment layer (quote-grounded, attested judgements). off · optional (warn) ·
# required (block on a malformed/unsealed/stale judgement record). Kit 'optional';
# bootstrap 'required'.
assessment_layer:    optional
# Claim-coverage policy (guards "mechanically green but never modelled"). off
# (default — opt-in) · warn · required. When on, a claim cited WITH a #ref but
# carrying no role in the argument graph (no edge, no **Addresses:**, no assessment)
# is reported/blocked. Pairs with claim_ids: required; an empty graph still passes.
graph_coverage:      off
# Edge-assessment policy. off (default — opt-in) · warn · required. When required, every
# supports/rebuts edge must be covered by a matching `kind: edge` record (target+grounding),
# named by an in-band `[rec: <id>]` or matching a standalone record — a non-trivial
# inference should be judged, not merely asserted. A reviewer's
# competing judgement is first-class: a record may carry `disputes: [<id>...]` to
# contest another record on the same claim (validated by check_assessment).
edge_assessments:    off
# Selection-audit policy (Layer 2 — completeness). off (default — opt-in) · warn ·
# required. When on, the corpus must be registered in content/source_register.md:
# every stamped ledger carries a **Source:** entry with a discovery trail and
# rationale, and every declared **Position:** is covered by a source or named under
# Known gaps — NO SILENT EMPTY SIDE. HONEST LIMIT: this proves the declared position
# set has no empty side, not that it is COMPLETE (missing-viewpoint detection is
# judgement, surfaced via Known gaps + semantic_health). An empty register passes.
selection_audit:     off
# Source-flow policy (Layer 2 — discovery/screening trail). off (default — opt-in) ·
# warn · required. When on, content/source_flow.md must record at least one search
# strategy, the screening counts, and an included-source entry for every stamped
# ledger; included sources must resolve back to verified_claims/. HONEST LIMIT:
# this proves every included source has a declared route into the corpus, not that
# the route is exhaustive or unbiased.
source_flow:         off
# Semantic-review freshness gate. The mechanical gates can be green while the
# knowledge base is intellectually stale (contradictions, claims a newer source
# overturned, one-sided synthesis). off = no check · warn = nudge if the review in
# content/_ledger/semantic_health.md is missing/stale (default) · required = BLOCK
# a configured commit when it is. semantic_max_age_days sets the staleness window
# (default 180). Opt-in to 'required' deliberately — it forces a fresh LLM/human
# review (skill-ledger-curate) before each commit.
semantic_health:     warn
semantic_max_age_days: 180
# Remote attestation of run-records. off (default — opt-in) · warn · required. When
# required, every committed verification run-record must carry a detached SSH
# signature (tools/sign_records.py) from a key on attestation_signers, verified by
# check_attestation.py (ssh-keygen -Y verify) in CI/clones. HONEST LIMIT: this
# proves WHO attested over the committed bytes, not an independent re-hash of the
# git-ignored source — it closes PR-forged run-records, not local mis-verification.
attestation:         off
attestation_signers: .ledger/allowed_signers
# Unit-manifest (coordinate-system) gate. off (default — opt-in) · warn · required.
# When on, every ledger claim carrying a **Locus:** must resolve to a unit in the
# committed literature/units/<key>.units.json manifest (tools/enumerate_units.py),
# and its quote must be a verbatim span WITHIN that unit (tools/check_units.py) —
# making the claim address mechanical (slug = locus) and the span bounded. Opt-in
# and NOT in the strict set, so a configured project is not forced to adopt it; a
# fully_enumerable=false (coarse PDF) manifest downgrades any required finding to a
# warning. See spec/EXTRACTION.md §Coordinate addressing.
units_layer:         off
# Synthesis-claim gate. off (default — opt-in) · warn · required. When on, the synthesis
# prose (content/baseline_comparison.md, inquiry.md, assessments/*.md) is scanned for a
# tight watchlist of significance/superiority/novelty/certainty/completeness words; any
# such claim that carries NO evidence anchor (a key:slug / [[link]] / `tool` ref) and is
# not hedged is flagged (tools/check_synthesis.py). HONEST LIMIT: this enforces ANCHORING
# (form), NOT truth — an anchored-but-overstated claim still passes; whether an anchored
# claim is warranted is the adversarial-faithfulness ASSIST's job. Opt-in, NOT in the strict
# set.
synthesis_claims:    off
skin_rules_file:     content/_ledger/skin_rules.md
# Whether the subject skin holds rules you stand behind. draft = drafted but not yet
# sharpened (the project derives as 'drafted': set up, gates lenient); confirmed = these
# are THIS subject's rules. Absent → ledger_doctor falls back to guessing from the file's
# shape, which cannot tell your rules from the worked example the kit ships — so a
# project that says which it has is believed over the guess. `ledger init` writes
# 'draft'; only you set 'confirmed'.
skin_state:          <draft | confirmed>
writing_skill:       skill-ledger-write
shared_with:         <solo | co-authors via git>
