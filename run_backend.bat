@echo off
title Algorise AI - Autonomous B2B Backend Engine
echo ========================================================
echo   ALGORISE AI — AUTONOMOUS B2B BACKEND ENGINE
echo   Meta Graph Webhook • WhatsApp Cloud API • Telegram
echo ========================================================
echo.

cd /d D:\algorise-ai
echo Starting Uvicorn on http://127.0.0.1:8000...
echo Health check: http://127.0.0.1:8000/health
echo Client Portal API: http://127.0.0.1:8000/api/v1/dashboard/1
echo.

python -m uvicorn engine.main:app --host 0.0.0.0 --port 8000 --reload
