#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
API_KEY="${API_KEY:-}"

if [[ -z "${API_KEY}" ]]; then
  echo "Set API_KEY first." >&2
  exit 1
fi

echo "health..."
curl -sS "${BASE_URL}/health" | grep -q '"status":"ok"'

echo "ingest..."
curl -sS -X POST "${BASE_URL}/ingest" \
  -H "x-api-key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"workspace_id":"default","source":"smoke","content":"Refund within 14 days."}' >/dev/null

echo "chat..."
curl -sS -X POST "${BASE_URL}/chat" \
  -H "x-api-key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"workspace_id":"default","message":"What is refund policy?"}' | grep -q '"answer"'

echo "capabilities..."
curl -sS "${BASE_URL}/capabilities" | grep -q '"jwt_auth":true'

echo "smoke test passed"
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
API_KEY="${API_KEY:-}"

if [[ -z "${API_KEY}" ]]; then
  echo "Missing API_KEY env var (x-api-key)." >&2
  exit 1
fi

echo "1) health"
curl -sS "${BASE_URL}/health" | tee /dev/stderr | grep -q '"status":"ok"'

echo "2) ingest"
curl -sS -X POST "${BASE_URL}/ingest" \
  -H "x-api-key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"workspace_id":"default","source":"smoke_doc","content":"Refunds are possible within 14 days for annual plans."}' >/dev/null

echo "3) chat"
curl -sS -X POST "${BASE_URL}/chat" \
  -H "x-api-key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"workspace_id":"default","message":"Summarize refund rule"}' | tee /dev/stderr | grep -q '"answer"'

echo "4) capabilities"
curl -sS "${BASE_URL}/capabilities" | tee /dev/stderr | grep -q '"jwt_auth":true'

echo "Smoke test passed."
