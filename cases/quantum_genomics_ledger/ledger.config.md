# Ledger project config — Quantum computing for genomics (out-of-domain demonstration case)
#
# A vendored Ledger CASE: the fourth worked case, deliberately OUTSIDE the three
# provided case topics (COVID origins / LHC black holes / dietary cholesterol). It is
# seeded from the standalone quantum_revolution_ke white-paper project (its verbatim
# quotes + raw corpus) and rebuilt to the current kit grammar so all gates bite.
# Only these per-subject values change; everything else is the reusable kernel.

project_name:        quantum_genomics_ledger
project_root:        <absolute path on disk>
deliverable:         report
source_of_truth:     markdown+quartz
the_reader:          a busy minister AND a sceptical quantum scientist, at once
source_types:        peer-reviewed papers + official government/standards reports (mixed)
unpaywall_email:     <your email for the download service>

# Tracked project mode. pristine = untouched starter kit; configured = a real subject.
# A CONFIGURED project is strict by definition: ledger_doctor hard-fails a configured
# project that has not adopted ALL strict postures below. To run softer, stay pristine.
project_state:       configured

# Prose dirs the citation gate covers.
gated_paths:         content/concept_notes/, content/literature_reviews/, content/inquiry.md, content/finding.md, content/assessments/

# --- strict postures (mandatory once configured) ---
claim_ids:           required
numeric_citations:   block
provenance:          required
structure_layer:     required
assessment_layer:    required

# --- opt-in postures ---
graph_coverage:      off
# Every supports/rebuts edge must carry a [rec: <id>] judgement record (deeper
# judgement layer — the verdict's secondary lever).
edge_assessments:    required
# Every stamped ledger registered in source_register.md; every declared **Position:**
# covered by a source or named under Known gaps (no silent empty side).
selection_audit:     required
# Every included source has a declared discovery/screening route in source_flow.md.
# This is route-in transparency, not proof of representativeness.
source_flow:         required
semantic_health:     warn
semantic_max_age_days: 180
attestation:         off
attestation_signers: .ledger/allowed_signers
# Structural-unit manifests. Off: the corpus is arXiv/journal PDFs that degrade to
# coarse (fully_enumerable:false), so units_layer would only warn — kept off (as eggs).
units_layer:         off
# Significance/superiority/novelty claims in synthesis prose must be anchored or
# hedged (form, not truth). Required here: the no-hype discipline is the whole point
# of a quantum case.
synthesis_claims:    required

skin_rules_file:     content/_ledger/skin_rules.md
writing_skill:       skill-ledger-write
shared_with:         co-authors via git
