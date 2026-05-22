@echo off
REM Test Sports RAG API - Windows Command Prompt compatible

echo.
echo ========================================
echo Testing Sports RAG API
echo ========================================
echo.

REM Make sure API is running at http://localhost:8000
REM Run: uvicorn src.api.main:app --reload

echo [1] Health check...
curl -s http://localhost:8000/health | python -m json.tool
echo.

echo [2] Query test...
curl -s -X POST http://localhost:8000/query ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"Who won the 2022 World Cup?\",\"sport_filter\":\"football\"}" ^
  | python -m json.tool

echo.
echo Done!
