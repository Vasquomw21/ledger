---
paper: "<Author> et al. (<YEAR>)"
title: "<full paper title>"
doi: "<DOI>"
pmcid: "<PMC ID, if any>"
url: "<source URL the file was fetched from>"
source_version: "<published | preprint>"
file: "literature/<author>_<year>.html"
retrieved: "<YYYYMMDD the source was fetched>"
verified_by: "<agent or person who verified the quotes>"
# The six below are written by `verify_quotes.py --stamp` — do not hand-edit.
# They bind the ledger to the exact source/extract bytes AND its own quoted text
# (body_sha256) it was verified against, so a later quote edit is caught in CI.
source_sha256: "<set by --stamp>"
extract_sha256: "<set by --stamp>"
body_sha256: "<set by --stamp>"
verifier_version: "<set by --stamp>"
verified_verdict: "<pass | fail — set by --stamp>"
verified_date: "<YYYYMMDD — set by --stamp>"
---

# Verified Claims — <Author> et al. (<YEAR>)

Each claim below was extracted by reading the downloaded paper file with the Read
tool, grepping for the specific content, and reading the surrounding context to
confirm the attribution is faithful.

**Rules:**
- Every entry must contain a DIRECT QUOTE from the paper (in blockquote).
- The quote must be locatable by grepping the downloaded file.
- "Location" = the heading/section (HTML) or page number (PDF) where the quote appears.
- Never paraphrase from memory — if you cannot find the quote, do not write the entry.
- Primary sources only — the source that made the claim, not a secondary write-up of it. What
  counts as primary depends on the project's declared `source_types` (papers, official reports, a
  recorded debate, …; see `spec/EXTRACTION.md`); for a paper project that is peer-reviewed
  literature, not a news article about it.
- If a paper is paywalled/inaccessible: STOP, ask the user to download it manually, never
  create a stub to satisfy the citation hook.

## Claim 1: <one-line summary of what your note/review will attribute to this paper>

> "exact quote from the paper supporting this claim"

**ID:** <stable-slug>
**Locus:** <unit-locus>
**Location:** Section X / Page Y / Results paragraph Z
**Grep command used:** `Grep pattern="<pattern>" path="literature/<file>"`

<!-- Prose references a specific claim as `(Author YEAR #<stable-slug>)`. PREFER a
stable **ID:** slug (as above) over the bare ordinal: ordinals (#c1, #c2, … in
`## Claim N` order) silently re-point if you insert or reorder claims, whereas an
**ID:** slug stays bound to its claim. Both resolve; the gate honours
`claim_ids:` in ledger.config.md. -->

<!-- OPTIONAL — **Locus:** (coordinate addressing, the units_layer gate). When the
source has a committed unit manifest (literature/units/<key>.units.json, emitted by
tools/enumerate_units.py), set **Locus:** to the manifest locus of the unit this
claim was lifted from, and make **ID:** equal that locus — so the address is
mechanical, not a chosen name. Under units_layer: required, tools/check_units.py
then attests the quote is a verbatim span WITHIN that unit. Omit **Locus:** for a
claim whose quote spans two units (left honestly off the grid). See
spec/EXTRACTION.md §Coordinate addressing; **Location:** stays free-text. -->


<!-- OPTIONAL — claim-graph edges (structure layer). Under a claim, you may record
a typed relationship to another claim, anywhere in the corpus, addressed as
<ledger_key>:<slug> (a bare <slug> means a claim in THIS ledger):

  **Rebuts:** segreto_2021:fcs-implies-engineering (grounded by #fcs-not-expected)

Edge types: supports · rebuts · depends-on · refines · qualifies · restates ·
duplicate-of · supersedes. The `(grounded by #<slug>)` clause is MANDATORY and must
name a claim IN THIS ledger — the verbatim quote where the relationship is asserted
(so an edge is grounded the way a claim is). check_structure.py checks both
endpoints resolve; it does NOT (and cannot) check the quote truly rebuts/supports —
that is the assessment layer's attested judgement, not a mechanical proof. A
supports/rebuts edge may also carry a trailing `[rec: <id>]` linking it to a
judgement record; under `edge_assessments: required` the edge must be covered by a
matching `kind: edge` record (via that `[rec:]` or a standalone one) — a non-trivial
inference should be judged, not just asserted.
A claim may also opt into the inquiry's question tree with `**Addresses:** <qid>`
(a sub-question id declared in content/inquiry.md). -->

<!-- OPTIONAL — assessment markers (assessment layer). A judgement ABOUT a claim is
recorded both as an in-band marker (for navigation) AND as an attested record in
content/assessments/_records/<id>.assess.json, written by tools/assess_record.py
(sealed + grounded + bound to the subject claim's body, exactly like a verification
run-record). The marker references its record with `[rec: <id>]`:

  **Assess-rhetorical:** "irrefutably show" — overstates the evidence (grounded by #fcs) [rec: fcs-rhetoric]
  **Correlated-with:** segreto_2021:rarity (grounded by #fcs) [shared rarity premise]
  **Crux-of:** fcs-engineering (grounded by #fcs) [if-resolved: settles Q1]
  **Status:** settled | performed-settling   (performed-settling MUST name an open **Crux-of:**)

check_assessment.py attests each record is sealed (record_sha256), its grounding
resolves, its body_sha256 still matches the subject claim, and a rhetorical span is
a substring of its grounding quote; it surfaces a derived DOUBLE-COUNT warning when
two correlated sources both support one claim. It does NOT prove a judgement is
correct — it makes it attributable and re-judgeable. A reviewer's COMPETING
judgement is first-class: write a second record whose frontmatter carries
`disputes: [<other-record-id>]` (it must contest a record on the SAME claim).
Calibration is a separate note
at content/assessments/<id>.md (frontmatter: inside_view, out_of_model_discount,
adversarial_discount, calibrated_confidence; the gate checks calibrated ≤ inside_view). -->

---

## Claim 2: ...

> "exact quote"

**Location:** ...
**Grep command used:** ...
