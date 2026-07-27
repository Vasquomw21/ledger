#!/bin/bash
# Pre-download register lookup. Call this BEFORE you curl or wget a paper —
# if the paper is already on disk, reuse the canonical filename it reports;
# do not re-download.
#
# Usage:
#   literature/check.sh <author_surname> <year>
#
# Exit codes:
#   0 — paper is present and usable. stdout = canonical filename in literature/.
#   1 — paper is not in the register. You may proceed to download.
#   2 — paper is in the register but flagged (landing_page, mismatch,
#       paywalled_manual_needed, unknown). STOP and ask the user to sort it
#       out manually — DO NOT re-download into a new filename.
#
# Example:
#   $ literature/check.sh Neafsey 2015
#   neafsey_2015.html
#   $ echo $?
#   0

set -euo pipefail

if [ $# -ne 2 ]; then
  echo "Usage: $(basename "$0") <author_surname> <year>" >&2
  exit 3
fi

AUTHOR=$(echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E "s/['’]//g")
YEAR="$2"

# Resolve paths relative to THIS script's own location so the pipeline is
# portable across projects/clones — no hardcoded project path. The register
# and the build_register.py that regenerates it both live beside this script.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REGISTER="$SCRIPT_DIR/REGISTER.tsv"

if [ ! -f "$REGISTER" ]; then
  echo "[ERROR] register not found at $REGISTER" >&2
  echo "[ERROR] run: python3 $SCRIPT_DIR/build_register.py" >&2
  exit 3
fi

# Fields: 1=key 2=filename 3=ext 4=title 5=doi 6=journal 7=year 8=first_author 9=status
# Match keys that start with <author>_<year> (optionally followed by a/b suffix).
MATCHES=$(awk -F'\t' -v a="$AUTHOR" -v y="$YEAR" \
  'NR>1 && $1 ~ ("^" a "_" y "[a-z]?$") {print}' "$REGISTER")

if [ -z "$MATCHES" ]; then
  exit 1
fi

# Prefer status=verified, then downloaded, then anything else.
# Within the same status, prefer HTML over PDF (cheaper context: text vs rendered pages).
BEST=$(echo "$MATCHES" | awk -F'\t' '
  { status=$9; ext=$3
    status_rank = (status=="verified")?0 : (status=="downloaded")?1 : 9
    ext_rank    = (ext=="html")?0 : (ext=="pdf")?1 : 9
    print status_rank "\t" ext_rank "\t" $0 }' | sort -n -k1,1 -k2,2 | head -1 | cut -f3-)

STATUS=$(echo "$BEST" | awk -F'\t' '{print $9}')
KEY=$(echo "$BEST" | awk -F'\t' '{print $1}')
EXT=$(echo "$BEST" | awk -F'\t' '{print $3}')

case "$STATUS" in
  verified|downloaded)
    echo "${KEY}.${EXT}"
    exit 0
    ;;
  landing_page|mismatch|paywalled_manual_needed|unknown)
    echo "[STOP] paper $AUTHOR $YEAR is registered with status=${STATUS}. Do not re-download. Ask the user to triage literature/${KEY}.* manually." >&2
    exit 2
    ;;
  *)
    # duplicate_of:X, etc. — resolve to canonical
    echo "${KEY}.${EXT}"
    exit 0
    ;;
esac
