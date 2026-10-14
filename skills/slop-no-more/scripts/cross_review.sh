#!/usr/bin/env bash
# Optional: ask a DIFFERENT model family to review a rewrite (idea from ItsssssJack/SlopMonster:
# a model is bad at hearing its own accent). Review only; it never edits the text.
#   scripts/cross_review.sh ORIGINAL REWRITE
# Uses `codex` (GPT) or `gemini` if installed. Otherwise prints the prompt to paste
# into another model family's chat and exits 127.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
[ $# -eq 2 ] && [ -r "$1" ] && [ -r "$2" ] || { echo "usage: cross_review.sh ORIGINAL REWRITE" >&2; exit 64; }
FULL="$(cat "$HERE/../prompts/cross_review.txt")

=== ORIGINAL ===
$(cat "$1")

=== REWRITE ===
$(cat "$2")"
if command -v codex >/dev/null 2>&1; then
  codex exec --skip-git-repo-check --sandbox read-only "$FULL"
elif command -v gemini >/dev/null 2>&1; then
  gemini -p "$FULL"
else
  echo "cross_review: no codex or gemini CLI found. Paste the text below into a non-Claude model's chat:" >&2
  printf '%s\n' "$FULL"
  exit 127
fi
