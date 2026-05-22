# Test Sports RAG API - PowerShell version
# Run: .\test_api.ps1

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Testing Sports RAG API" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$baseUrl = "http://localhost:8000"

# Test 1: Health check
Write-Host "[1] Health Check..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/health" -Method GET
    $json = $response.Content | ConvertFrom-Json
    Write-Host "✓ Status: $($json.status)" -ForegroundColor Green
    Write-Host "  Uptime: $($json.uptime_s)s" -ForegroundColor Gray
} catch {
    Write-Host "✗ Error: $_" -ForegroundColor Red
    Write-Host "  Make sure API is running: uvicorn src.api.main:app --reload" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n[2] Query Test..." -ForegroundColor Yellow
try {
    $body = @{
        question = "Who won the 2022 World Cup?"
        sport_filter = "football"
        top_k = 5
    } | ConvertTo-Json

    $response = Invoke-WebRequest -Uri "$baseUrl/query" `
        -Method POST `
        -Headers @{"Content-Type"="application/json"} `
        -Body $body

    $json = $response.Content | ConvertFrom-Json
    
    Write-Host "✓ Query succeeded!" -ForegroundColor Green
    Write-Host "  Question: $($json.question)" -ForegroundColor Gray
    Write-Host "  Answer: $($json.answer)" -ForegroundColor Cyan
    Write-Host "  Latency: $($json.latency_ms.total_ms)ms" -ForegroundColor Gray
    Write-Host "  Sources: $($json.sources.Count) chunks retrieved" -ForegroundColor Gray

} catch {
    Write-Host "✗ Error: $_" -ForegroundColor Red
    Write-Host "Response:" -ForegroundColor Yellow
    Write-Host $_.Exception.Response.Content -ForegroundColor Gray
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Test Complete!" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
