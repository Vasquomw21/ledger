# Ledger project config
#
# Filled by skill-ledger-bootstrap at setup. These are the only values that
# change per subject — everything else is the reusable kernel.

project_name:        eggs_cholesterol_ledger
project_root:        <absolute path on disk>
deliverable:         report
source_of_truth:     markdown+quartz
the_reader:          a health journalist AND a sceptical epidemiologist
source_types:        peer-reviewed papers
unpaywall_email:     <your email for the download service>
# Tracked project mode. pristine = the untouched starter kit (placeholders, empty
# skin, lax postures — and that is fine); configured = a real bootstrapped subject.
# skill-ledger-bootstrap flips this to 'configured' AND sets the three strict
# postures below (claim_ids: required, numeric_citations: block, provenance:
# required). ledger_doctor cross-checks the declared mode against what the project
# actually looks like (filled fields + written skin): a declared mode that
# contradicts the derivation is 'broken'. Absent → defer to the derivation.
project_state:       configured
# Prose directories the citation gate covers (comma-separated). Bootstrap
# appends the per-subject deliverable dir here (e.g. content/white_paper/).
gated_paths:         content/concept_notes/, content/literature_reviews/, content/inquiry.md, content/finding.md
# Cites whose ledger key abbreviates the surname: <as cited> -> <ledger key>. The
# ledger key is canonical (graph edges and sealed records address it); an alias only
# lets the prose name the author accurately instead of clipping it to match the key.
citation_aliases:    drouin-chartier_2020 -> drouin_2020
# Claim-ref posture. A cite may point at a specific quoted claim — (Author YEAR #c1).
# off = ignore refs · optional = validate a ref when present · required = every cite
# must carry a resolvable ref. A ref that names a non-existent claim always fails.
# The kit ships 'optional'; skill-ledger-bootstrap sets 'required' for a real
# project — it forces every cite to name its quoted claim, closing "right paper,
# wrong claim". A CONFIGURED project is strict by definition: ledger_doctor (every
# gate, not just --require-configured) hard-fails a configured project whose
# claim_ids is not 'required'. To run softer, the project must stay pristine.
claim_ids:           required
# Numeric/superscript citation markers ([42], method.⁵⁴) can't be resolved to a
# ledger without a references map. ignore = silent · warn = report, don't block
# (default) · block = fail the gate on them. Set 'block' if your project is
# strictly author–date and wants numeric styles rejected everywhere.
numeric_citations:   block
# Provenance binding: each ledger frontmatter records the source+extract sha256 it
# was verified against (verify_quotes.py --stamp). off · warn (default — report a
# missing/stale stamp) · required (block). pre-commit rebinds; CI attests shape.
# The kit ships 'warn'; skill-ledger-bootstrap sets 'required'.
provenance:          required
# Structure layer (the verified-claim graph). off = skip · optional = validate the
# edges that exist but only warn (default) · required = block on an unresolved or
# ungrounded edge, a contradictory pair, or a bad sub-question id. No posture ever
# forces edges to exist, so an empty graph passes everywhere. The kit ships
# 'optional'; skill-ledger-bootstrap sets 'required'.
structure_layer:     required
# Assessment layer (quote-grounded, attested judgements). off · optional (warn) ·
# required (block on a malformed/unsealed/stale judgement record). Kit 'optional';
# bootstrap 'required'.
assessment_layer:    required
# Claim-coverage policy (guards "mechanically green but never modelled"). off
# (default — opt-in) · warn · required. When on, a claim cited WITH a #ref but
# carrying no role in the argument graph (no edge, no **Addresses:**, no assessment)
# is reported/blocked. Pairs with claim_ids: required; an empty graph still passes.
graph_coverage:      off
# Edge-assessment policy. off (default — opt-in) · warn · required. When on, every
# supports/rebuts edge must carry a `[rec: <id>]` resolving to a judgement record —
# a non-trivial inference should be judged, not merely asserted. A reviewer's
# competing judgement is first-class: a record may carry `disputes: [<id>...]` to
# contest another record on the same claim (validated by check_assessment).
edge_assessments:    required
# Selection-audit policy (Layer 2 — completeness). off (default — opt-in) · warn ·
# required. When on, the corpus must be registered in content/source_register.md:
# every stamped ledger carries a **Source:** entry with a discovery trail and
# rationale, and every declared **Position:** is covered by a source or named under
# Known gaps — NO SILENT EMPTY SIDE. HONEST LIMIT: this proves the declared position
# set has no empty side, not that it is COMPLETE (missing-viewpoint detection is
# judgement, surfaced via Known gaps + semantic_health). An empty register passes.
selection_audit:     required
# Source-flow policy (Layer 2 — discovery/screening trail). The case records the
# route each included source took into the corpus; this is a route-in guarantee,
# not a representativeness proof.
source_flow:         required
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
skin_rules_file:     content/_ledger/skin_rules.md
writing_skill:       skill-ledger-write
shared_with:         <solo | co-authors via git>
