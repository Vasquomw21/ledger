#!/bin/bash
# ledger_demo.sh — one-command, read-only walkthrough of a Ledger project.
#
# For a judge: clone, then (no install needed — pure stdlib):
#   ./ledger_demo.sh                       # tour THIS project
#   ./ledger_demo.sh cases/covid_origins_ledger   # tour a vendored configured case
#
# It runs the full commit-time gate set read-only — project health, the dashboard, the
# verbatim-quote check (corpus-gated), the provenance / citation / structure / assessment
# gates, the opt-in coverage / attestation / selection / source-flow / unit / synthesis
# gates, and wiki health — then the Mermaid graph, validity analysis, and faithfulness
# worklist. It changes nothing and is safe to run anywhere.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/ledger_cli.py" demo "$@"
