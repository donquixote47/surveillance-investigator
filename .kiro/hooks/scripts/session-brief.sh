#!/usr/bin/env bash
# SessionStart hook: print a short brief so every session starts with current state.
# stdout is added to the agent's context. Keep it bounded.
set -u
cd "$(dirname "$0")/../../.." || exit 0
echo "=== SESSION BRIEF: agentcore-surveillance-investigator ($(date '+%Y-%m-%d %H:%M')) ==="
echo
if [ -f docs/en/STATUS.md ]; then
  echo "--- docs/en/STATUS.md ---"
  cat docs/en/STATUS.md
  echo
fi
echo "--- Last 3 decisions (docs/en/decision-log.md) ---"
if [ -f docs/en/decision-log.md ]; then
  grep -E '^## ' docs/en/decision-log.md | tail -n 3
fi
echo
echo "--- Files changed in the last 7 days (excluding docs and .kiro) ---"
find . -type f -mtime -7 \
  -not -path './.kiro/*' -not -path './docs/*' -not -path './.venv/*' \
  -not -path './node_modules/*' -not -path './cdk.out/*' -not -path './data/*' \
  -not -name '.DS_Store' -not -name 'README.md' -not -name '.gitignore' \
  | sed 's|^\./||' | sort | head -n 30
echo
echo "--- Toolchain ---"
printf 'uv: %s | python(uv): %s | node: %s | agentcore CLI: %s | aws CLI: %s | cdk: %s\n' \
  "$(command -v uv >/dev/null && uv --version 2>/dev/null | head -n1 || echo missing)" \
  "$( [ -f .python-version ] && cat .python-version || echo 'not pinned' )" \
  "$(command -v node >/dev/null && node --version || echo missing)" \
  "$(command -v agentcore >/dev/null && echo present || echo missing)" \
  "$(command -v aws >/dev/null && echo present || echo missing)" \
  "$(command -v cdk >/dev/null && cdk --version 2>/dev/null | head -n1 || echo missing)"
echo
echo "Reminders: region eu-west-2; zero third-party cost; stop Runtime and Code Interpreter sessions after runs; docs are bilingual (docs/en canonical, docs/el twin); follow .kiro/steering/challenge-and-verify.md: do not agree by default."
exit 0
