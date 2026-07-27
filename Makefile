# Makefile — entry points for a judge. Adds no gate.
#   make demo       read-only tour — ZERO installs; bare = the EMPTY kit, pass DIR=cases/covid_origins_ledger for a worked case
#   make venv       one-time: .venv + pip-install test + intake deps
#   make test       run the suite (needs pytest — `make venv` first)
#   make conda-env  OPTIONAL full toolchain (node/gh/jq/curl) via conda
# pip/zero-install is primary; conda only for the intake/publish binaries.
# PY = project venv if present, else system python3.

DIR ?=
PY  := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)

.PHONY: demo venv test conda-env

demo:
	$(PY) ledger_cli.py demo $(DIR)

venv:
	python3 -m venv .venv && .venv/bin/pip install -e ".[intake,test]"

test:
	$(PY) -m pytest -q

conda-env:
	conda env create -f environment.yml || conda env update -f environment.yml
