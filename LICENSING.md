# Licensing

Copyright 2026 Martin Wagah.

Ledger is released under two licences. Material that belongs to someone else is carved out of
both, and those carve-outs take precedence over the two rules that follow.

## The kit: Apache-2.0

Unless a rule below says otherwise, every file in this repository is licensed under the
[Apache License, Version 2.0](LICENSE). That covers the command-line tools, hooks, CI
configuration, tests, JSON schemas, the interchange specification, templates and documentation,
including the copy of the kit vendored inside each case.

## Case content: CC BY 4.0

The written analysis of each worked case is licensed under
[Creative Commons Attribution 4.0 International](LICENSES/CC-BY-4.0.txt):

- `cases/*/content/**`: assessments and their records, findings, crosswalks and the other case
  write-ups;
- `cases/*/literature/verified_claims/**`, except `TEMPLATE.md`, which is part of the kit.

Attribute it as *Martin Wagah, Ledger case studies, https://github.com/Vasquomw21/ledger,
CC BY 4.0*, and say what you changed.

## Not licensed by this project

Neither licence covers the following.

- **Quotations.** Verified-claims files, assessment records, run records and benchmark examples
  reproduce passages from published works, attributed to their authors, so that every claim can
  be checked against its source. Those passages remain the copyright of their authors and
  publishers. Their reuse is governed by each source's own terms and by the copyright law that
  applies to you.
- **Test excerpt.** `tests/smoke/sandve_2013.txt`, and its copy in each case, is an excerpt of
  Sandve et al. (2013), *Ten Simple Rules for Reproducible Computational Research*, PLOS
  Computational Biology, doi:10.1371/journal.pcbi.1003285. © 2013 Sandve et al., distributed
  under the Creative Commons Attribution License.
- **External baseline reports.** `cases/covid_origins_ledger/baseline_research_raw.md` and
  `cases/lhc_safety_ledger/content/baseline_research_raw.md` are the verbatim output of an
  external research agent, kept for comparison with the ledger.
- **The name.** Neither licence grants any right to use the Ledger name (Apache-2.0, section 6).

The source papers are not stored in this repository. The kit fetches them from their
publishers.

## Contributing

A contribution is licensed under the same terms as the files it changes. See
[CONTRIBUTING.md](CONTRIBUTING.md).
