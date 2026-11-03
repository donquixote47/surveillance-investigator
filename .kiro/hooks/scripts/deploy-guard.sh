#!/usr/bin/env bash
# PreToolUse hook on execute_bash: ask for confirmation before commands that create or change
# billable AWS resources. Fails open (exit 0, no decision) on anything it does not recognise.
set -u
input=$(cat)

# Pull the command string out of tool_input if possible; fall back to the raw payload.
cmd=$(printf '%s' "$input" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    ti=d.get("tool_input") or {}
    print(ti.get("command") or ti.get("cmd") or json.dumps(ti))
except Exception:
    print(sys.stdin.read())
' 2>/dev/null || printf '%s' "$input")

pattern='(agentcore[[:space:]]+(deploy|launch|create|up)|cdk[[:space:]]+deploy|sam[[:space:]]+deploy|terraform[[:space:]]+apply|aws[[:space:]]+bedrock-agentcore-control[[:space:]]+(create|update)-|aws[[:space:]]+cloudformation[[:space:]]+(create-stack|update-stack|deploy)|aws[[:space:]]+bedrock-agentcore[[:space:]]+invoke-agent-runtime|aws[[:space:]]+(lambda|dynamodb|cognito-idp|s3api)[[:space:]]+create-)'

if printf '%s' "$cmd" | grep -Eiq "$pattern"; then
  short=$(printf '%s' "$cmd" | head -c 160 | tr '\n' ' ')
  reason="Creates or changes billable AWS resources (project rule: near-zero AWS cost, eu-west-2 only, tag Project=agentcore-surveillance-investigator). Command: ${short}"
  esc=$(printf '%s' "$reason" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '"%s"' "$reason")
  printf '{"hookSpecificOutput":{"permissionDecision":"ask","permissionDecisionReason":%s}}\n' "$esc"
fi
exit 0
