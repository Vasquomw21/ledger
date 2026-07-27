# Quantum-computing-for-genomics — a Ledger case (out-of-domain)

A worked [Ledger](https://github.com/Vasquomw21/ledger) case on **whether quantum computing
offers a genuine advantage for genomics and biology** — and what its arrival means for the
confidentiality of genomic data. It is the kit's **fourth** worked case and the only one
**outside the three provided case topics** (COVID origins, LHC black holes, dietary cholesterol):
the demonstration that the quote-first discipline and the claim/assessment machinery port to a
subject they were never tuned on.

It is a complete standalone Ledger project — its own kernel (`tools/`, `.githooks/`), config, and
quote-first corpus — seeded from the author's `quantum_revolution_ke` white-paper project (its
verbatim quotes and raw sources) and rebuilt to the current kit grammar so every gate bites.

## What it shows

Run the read-only tour from the kit: `make demo DIR=cases/quantum_genomics_ledger`.

- **Quote-first fidelity.** Every claim traces to a verbatim, on-disk, mechanically-verified quote
  from a primary source (arXiv preprints, peer-reviewed papers, NIST/CISA standards).
- **The machinery finds structure, not just checks citations.** The apparent breadth of "quantum
  machine-learning speedup" results is shown to rest on a single caveated primitive (HHL); the
  dequantisation results rebut the *practical* advantage; the load-bearing crux is whether the
  speedup survives its own input/output assumptions. See `content/finding.md`.
- **Honest boundary.** It does not claim quantum computing is useless for biology — quantum
  chemistry is named as the genuine *plausible* (not yet demonstrated) win, and the cryptographic
  threat to genomic data as real and present. The no-hype ladder (demonstrated / plausible /
  aspirational) is enforced by the synthesis gate.

## Layout

`content/` — `inquiry.md` (the question tree), `graph.json` (the claim graph), `source_register.md`
(the selection audit), `assessments/_records/` (sealed judgements), `finding.md` (the read-out).
`literature/verified_claims/` — the quote ledgers (the raw corpus is git-ignored; a clone re-fetches
via the fetch ladder, and the demo *attests* the committed stamp when the corpus is absent).
