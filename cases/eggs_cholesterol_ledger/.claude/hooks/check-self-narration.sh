#!/bin/bash
# No-self-narration gate (PreToolUse on Write|Edit). Two scopes:
#  - PROSE docs (DEMO.md / README.md / docs/ / content/ .md): the protesting-honesty /
#    self-description tic — state the thing, never write a sentence that describes or
#    praises the document. Matched here, by phrase.
#  - SCRIPTS (*.py / *.sh): delegated to dev/check_comments.py, which parses comments and
#    docstrings rather than raw text and is the same checker pytest and pre-commit run. This
#    hook binds Claude only; the checker is what binds everyone.
# The prose watchlist is tight by design (no legitimate use in scope), so a match is the tic,
# not a false positive. Quote ledgers and source quotes are out of scope (a source may use
# these words). See memory feedback-write-directly-no-self-narration.
# Exit 2 = block; exit 0 = allow.
set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
[ -z "$FILE_PATH" ] && exit 0

CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty')
[ -z "$CONTENT" ] && exit 0

CHECKER="${CLAUDE_PROJECT_DIR:-.}/dev/check_comments.py"

# Self-narration / protesting-honesty phrases for prose. "self-contained" alone is allowed
# (it describes the dashboard/bundle legitimately); only the doc-describing forms are caught.
PROSE_TIC='stated honestly|read this honestly|honesty is itself|honesty is the contribution|honesty about it is|the honest line|the honest claim|the honesty boundary|honest bound|honest limits|claimed as such|stated, not hidden|named, not hidden|with no overreach|named here rather than hidden|rather than asserted|we name the trade|saying so is the point|must not be oversold|everything a judge needs|gets the whole system|not just the verification guarantee|what sets ledger apart|leaves nothing to trust|nothing is posted without|the strongest guarantee|cannot silently drift|it raises the cost and traceability of forgery|the demonstration that the workflow is not overfit|watch the gates actually bite|the central finding falls straight out|stitch[^.]{0,15}documents together|(page|document|section|doc) is self-contained|self-contained (judge|page|document)|explicit debt, not silence'

case "$FILE_PATH" in
  # A watchlist and its fixtures necessarily contain the tokens they define, so a gate that
  # policed them could never be edited. Out of scope by construction.
  */.claude/hooks/*) exit 0 ;;
  */dev/check_comments.py|*/tests/test_comment_discipline.py) exit 0 ;;

  */DEMO.md|*/README.md|*/docs/*.md|*/content/*.md)
    HIT=$(printf '%s' "$CONTENT" | grep -inE "$PROSE_TIC" || true)
    if [ -n "$HIT" ]; then
      echo "BLOCKED (self-narration): this edit describes or praises the document instead of stating the thing. Offending line(s):" >&2
      printf '%s\n' "$HIT" | head -5 >&2
      exit 2
    fi
    ;;

  *.py|*.sh)
    [ -f "$CHECKER" ] || exit 0
    LANG_FLAG=""
    case "$FILE_PATH" in *.py) LANG_FLAG="--python" ;; esac
    if ! HIT=$(printf '%s' "$CONTENT" | python3 "$CHECKER" --stdin $LANG_FLAG 2>/dev/null); then
      echo "BLOCKED (comment discipline): a comment or docstring here names a plan item instead of stating a contract. A plan reference is false as soon as the plan moves, and is not the reader's to act on. State the constraint that stays true, or delete the comment — if removing it does not make the code harder to use safely, it was not carrying one. Offending line(s):" >&2
      printf '%s\n' "$HIT" | head -5 >&2
      exit 2
    fi
    ;;
  *) exit 0 ;;
esac
exit 0
