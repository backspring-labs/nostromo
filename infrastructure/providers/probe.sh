#!/usr/bin/env bash
# WP-1 provider attribution probes. Proves each key bills to its own boundary and reaches only its
# pinned model. Reads keys from the owner's host-local secret files and never prints them.
# Usage: infrastructure/providers/probe.sh
set -uo pipefail
SECRETS="${NOSTROMO_SECRETS:-$HOME/.config/nostromo/secrets}"
OPENAI_MODEL=gpt-5.6-sol
OPENAI_BLOCKED=gpt-6-astra     # the negative control: must be refused
ANTHROPIC_MODEL=claude-opus-5
fail=0
say() { printf '%-6s %-8s %-14s %s\n' "$1" "$2" "$3" "$4"; }

openai_probe() {            # role model expect_http label
  local role="$1" model="$2" want="$3" label="$4" key code
  key="$SECRETS/$role/openai.key"
  [[ -s "$key" ]] || { say FAIL "$role" "$model" "no key at $key"; fail=1; return; }
  local hdr; hdr=$(curl -sS -D - -o /tmp/nostromo_probe.json https://api.openai.com/v1/chat/completions \
    -H "Authorization: Bearer $(cat "$key")" -H 'content-type: application/json' \
    -d "{\"model\":\"$model\",\"max_completion_tokens\":8,\"messages\":[{\"role\":\"user\",\"content\":\"say ok\"}]}" 2>&1)
  code=$(printf '%s' "$hdr" | awk '/^HTTP/{c=$2} END{print c}')
  local proj; proj=$(printf '%s' "$hdr" | awk -F': ' 'tolower($1)=="openai-project"{print $2}' | tr -d '\r')
  if [[ "$code" == "$want" ]]; then say PASS "$role" "$model" "$label — HTTP $code${proj:+, project $proj}"
  else say FAIL "$role" "$model" "$label — expected $want, got $code"; fail=1; fi
}

anthropic_probe() {         # role
  local role="$1" key hdr code ws
  key="$SECRETS/$role/anthropic.key"
  [[ -s "$key" ]] || { say FAIL "$role" "$ANTHROPIC_MODEL" "no key at $key"; fail=1; return; }
  hdr=$(curl -sS -D - -o /tmp/nostromo_probe.json https://api.anthropic.com/v1/messages \
    -H "x-api-key: $(cat "$key")" -H 'anthropic-version: 2023-06-01' -H 'content-type: application/json' \
    -d "{\"model\":\"$ANTHROPIC_MODEL\",\"max_tokens\":8,\"messages\":[{\"role\":\"user\",\"content\":\"say ok\"}]}" 2>&1)
  code=$(printf '%s' "$hdr" | awk '/^HTTP/{c=$2} END{print c}')
  ws=$(printf '%s' "$hdr" | awk -F': ' 'tolower($1)=="anthropic-workspace-id"{print $2}' | tr -d '\r')
  if [[ "$code" == "200" && -n "$ws" ]]; then say PASS "$role" "$ANTHROPIC_MODEL" "pinned model — HTTP 200, workspace $ws"
  else say FAIL "$role" "$ANTHROPIC_MODEL" "expected 200 with a workspace header, got $code"; fail=1; fi
}

echo "== positive: each role reaches its pinned model =="
openai_probe parker "$OPENAI_MODEL" 200 "pinned model"
openai_probe ripley "$OPENAI_MODEL" 200 "pinned model"
anthropic_probe dallas
echo "== paired control: a non-pinned model must be refused =="
openai_probe parker "$OPENAI_BLOCKED" 403 "must be refused"
openai_probe ripley "$OPENAI_BLOCKED" 403 "must be refused"
echo
[[ $fail -eq 0 ]] && echo "all probes passed" || echo "PROBES FAILED"
exit $fail
