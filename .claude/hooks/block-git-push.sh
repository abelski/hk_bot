#!/usr/bin/env bash
# PreToolUse hook (Bash matcher): only the user may push. Claude must never do it.
# Commits are fine — this repo's convention is "commit freely, push only with explicit consent".
set -euo pipefail

input="$(cat)"
command="$(jq -r '.tool_input.command // empty' <<<"$input")"

# ponytail: substring/regex heuristic, not a real shell parser — catches the commands an
# agent would actually type (git push ..., git -C dir push ...), not a determined bypass
# (string concatenation, an obfuscated binary name). Upgrade to shlex-based argv parsing if
# that's ever seen in practice.
if grep -qE '\bgit\b[^;&|]*[[:space:]]push([[:space:]]|$)' <<<"$command"; then
  cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Only the user may run git push — this repo blocks the agent from doing it. Ask the user to push themselves."}}
JSON
  exit 0
fi

exit 0
