# Contributing to Ledger

Issues and pull requests are welcome.

## What your contribution is licensed under

You keep the copyright in your contribution. By submitting it, you license it under the same
terms as the files it changes, and confirm that you have the right to do so. Code, schemas and
documentation are Apache-2.0, and case content under `cases/` is CC BY 4.0.
[LICENSING.md](LICENSING.md) sets out exactly which files fall under which licence.

Do not add material you have no right to license. Attribute every quotation from a published work
to its source, as the verified-claims files do.

## Checks

Before opening a pull request, run `make test` (after `make venv`) and activate the commit gate
once per clone with `git config core.hooksPath .githooks`. The pre-commit hook runs the same gates
as CI. It also checks that every quotation in a verified-claims file matches its source verbatim,
which CI cannot do because the source papers are not in the repository.
