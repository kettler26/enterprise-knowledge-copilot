$ErrorActionPreference = "Stop"

$baseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://127.0.0.1:8000" }
$apiKey = $env:API_KEY
if (-not $apiKey) {
  throw "Set API_KEY environment variable."
}

Write-Host "health..."
$health = Invoke-WebRequest -Uri "$baseUrl/health" -UseBasicParsing
if ($health.Content -notmatch '"status"\s*:\s*"ok"') { throw "health failed" }

Write-Host "ingest..."
$ingest = '{"workspace_id":"default","source":"smoke","content":"Refund within 14 days."}'
Invoke-WebRequest -Uri "$baseUrl/ingest" -Method POST -UseBasicParsing -Headers @{
  "x-api-key" = $apiKey
  "Content-Type" = "application/json"
} -Body $ingest | Out-Null

Write-Host "chat..."
$chat = '{"workspace_id":"default","message":"What is refund policy?"}'
$chatResp = Invoke-WebRequest -Uri "$baseUrl/chat" -Method POST -UseBasicParsing -Headers @{
  "x-api-key" = $apiKey
  "Content-Type" = "application/json"
} -Body $chat
if ($chatResp.Content -notmatch '"answer"') { throw "chat failed" }

Write-Host "capabilities..."
$cap = Invoke-WebRequest -Uri "$baseUrl/capabilities" -UseBasicParsing
if ($cap.Content -notmatch '"jwt_auth"\s*:\s*true') { throw "capabilities failed" }

Write-Host "smoke test passed"
$ErrorActionPreference = "Stop"

$baseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://127.0.0.1:8000" }
$apiKey = $env:API_KEY
if (-not $apiKey) {
  throw "Missing API_KEY environment variable."
}

Write-Host "1) health"
$health = Invoke-WebRequest -Uri "$baseUrl/health" -UseBasicParsing
if ($health.Content -notmatch '"status"\s*:\s*"ok"') {
  throw "Health check failed: $($health.Content)"
}

Write-Host "2) ingest"
$ingestBody = '{"workspace_id":"default","source":"smoke_doc","content":"Refunds are possible within 14 days for annual plans."}'
Invoke-WebRequest -Uri "$baseUrl/ingest" -Method POST -UseBasicParsing -Headers @{
  "x-api-key" = $apiKey
  "Content-Type" = "application/json"
} -Body $ingestBody | Out-Null

Write-Host "3) chat"
$chatBody = '{"workspace_id":"default","message":"Summarize refund rule"}'
$chat = Invoke-WebRequest -Uri "$baseUrl/chat" -Method POST -UseBasicParsing -Headers @{
  "x-api-key" = $apiKey
  "Content-Type" = "application/json"
} -Body $chatBody
if ($chat.Content -notmatch '"answer"') {
  throw "Chat failed: $($chat.Content)"
}

Write-Host "4) capabilities"
$cap = Invoke-WebRequest -Uri "$baseUrl/capabilities" -UseBasicParsing
if ($cap.Content -notmatch '"jwt_auth"\s*:\s*true') {
  throw "Capabilities check failed: $($cap.Content)"
}

Write-Host "Smoke test passed."
