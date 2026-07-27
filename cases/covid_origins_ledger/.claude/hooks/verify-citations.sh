#!/bin/bash
# Quote-first citation gate for a Ledger project (ships in the starter kit).
# PreToolUse hook on Write|Edit. Self-contained and path-portable: it resolves
# this repo's literature/ relative to its own location, so it travels with the
# repo to any clone (the co-author does not need the author's global hooks).
#
# Layers:
#   1  Paper-on-disk / register   — a cited (Author et al. YYYY) must have a file
#                                    literature/<author>*<year>* OR a usable row in
#                                    literature/REGISTER.tsv.
#   2  Verified-claims ledger      — and a literature/verified_claims/<author>*<year>*.md.
#      Layers 1/2 are delegated to tools/check_citations.py — the same checker
#      that pre-commit and CI run, so the gate cannot drift between agents.
#   3  Content guard               — writes to literature/ or verified_claims/ are
#                                    rejected if they look like a stub / landing page
#                                    / bypass (min 500 non-whitespace chars).
#
# Gated paths come from gated_paths: in ledger.config.md (default:
# content/concept_notes/, content/literature_reviews/). At bootstrap, append the
# per-subject deliverable dir to that config key (e.g. content/white_paper/).
# Exit 2 = block. Exit 0 = allow.
#
# BYPASS FORBIDDEN: when blocked, download + read + quote-log the paper. Never create a
# stub to placate the hook; never reword a citation to dodge the regex. Paywalled paper →
# STOP and ask the user to download it manually.

set -euo pipefail

# Repo root = two levels up from .claude/hooks/.
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HOOK_DIR/../.." && pwd)"

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
[ -z "$FILE_PATH" ] && exit 0

# ---- Layer 3: content guard on literature/ + verified_claims/ writes ----
if echo "$FILE_PATH" | grep -qE '/literature/(verified_claims/)?[^/]+$'; then
  if ! echo "$FILE_PATH" | grep -qE 'verified_claims/TEMPLATE\.md$|/REGISTER\.tsv$|/REGISTER_review\.md$|/OVERRIDES\.tsv$|/(check|fetch_paper)\.sh$|/(build_register|extract_text|verify_quotes)\.py$'; then
    CONTENT_CHECK=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty')
    if [ -n "$CONTENT_CHECK" ]; then
      if echo "$CONTENT_CHECK" | grep -qiE 'placeholder to satisfy|satisfy the (citation verification |verification |citation )?hook|so the hook (passes|accepts)|stub to (pass|satisfy)|bypass the hook|to unblock the hook|to route around|to pass the hook'; then
        echo "BLOCKED (Layer 3 — bypass pattern): this literature/ file reads as a stub created to satisfy the hook. Download and quote-log the real paper, or remove the citation. Do not reword to dodge this check." >&2
        exit 2
      fi
      if echo "$CONTENT_CHECK" | grep -qiE 'just a moment\.\.\.|enable javascript and cookies to continue|access to this article is restricted|you do not have access|subscribe to (read|view)|purchase (this )?article|sign in to continue|please log in|institutional login|request access|cf-challenge|cloudflare'; then
        echo "BLOCKED (Layer 3 — landing page / access-blocked content): this looks like a Cloudflare/paywall/login page, not the paper. Ask the user to download it manually, or remove the citation." >&2
        exit 2
      fi
      # 500 = write-time floor: a real paper or verified-claims record is well
      # past this at author time. Higher than CI's 200-char fresh-clone floor,
      # which must tolerate terse committed ledgers with the corpus absent.
      # Measure the RESULTING FILE, not the edit fragment: an Edit supplies only
      # .new_string (a fragment), but the file already exists on disk and an edit
      # to a real ledger never makes it a stub. Size-check the on-disk file so a
      # small in-band edit (a new marker line) does not false-positive; a Write
      # (.content present, or a brand-new path) is still measured on its content.
      SIZE_SRC=$(echo "$INPUT" | jq -r '.tool_input.content // empty')
      if [ -z "$SIZE_SRC" ] && [ -f "$FILE_PATH" ]; then SIZE_SRC=$(cat "$FILE_PATH"); fi
      [ -z "$SIZE_SRC" ] && SIZE_SRC="$CONTENT_CHECK"
      NONWS_LEN=$(echo "$SIZE_SRC" | tr -d '[:space:]' | wc -c | tr -d ' ')
      if [ "$NONWS_LEN" -lt 500 ]; then
        echo "BLOCKED (Layer 3 — file too small to be a real paper / verified-claims record): ${NONWS_LEN} non-whitespace chars (min 500). If the paper is paywalled, STOP and ask the user to download it manually." >&2
        exit 2
      fi
    fi
  fi
fi

# ---- Structure + assessment courtesy (advisory, never blocks) ----
# On a ledger / inquiry.md / assessments edit, surface any EXISTING claim-graph or
# judgement-record problem as a nudge. Non-blocking by design: at PreToolUse the
# pending edit is not on disk yet, so this validates the current committed state;
# the blocking enforcement is at commit + CI, where the edit is present. Both run
# in 'optional' so they only warn.
case "$FILE_PATH" in
  */literature/verified_claims/*.md|*/content/inquiry.md|*/content/assessments/*)
    python3 "$REPO_ROOT/tools/check_structure.py" --structure optional >&2 || true
    python3 "$REPO_ROOT/tools/check_assessment.py" --assessment optional >&2 || true
    ;;
esac
# On a source-register edit, surface any EXISTING selection-audit problem (advisory).
case "$FILE_PATH" in
  */content/source_register.md)
    python3 "$REPO_ROOT/tools/check_selection.py" --selection warn >&2 || true
    ;;
esac

# ---- Layers 1/2: delegate to the shared checker (path gating lives there) ----
# The content is not on disk yet at PreToolUse time, so it goes in via stdin;
# any non-zero from the checker blocks (fail-closed). printf, not echo, so the
# content arrives unmangled.
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty')
[ -z "$CONTENT" ] && exit 0
printf '%s' "$CONTENT" | python3 "$REPO_ROOT/tools/check_citations.py" --stdin --path "$FILE_PATH" || exit 2
exit 0
