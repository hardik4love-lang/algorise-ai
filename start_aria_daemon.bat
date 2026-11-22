@echo off
title Algorise AI — Aria 24/7 Production Watchdog & AutoHeal Supervisor
cd /d "%~dp0"

if not exist "logs" mkdir "logs"

echo ================================================================================
echo   ALGORISE AI — ARIA 24/7 PRODUCTION SUPERVISOR WATCHDOG
echo   Personal Visit Line: +91 92270 95624 | Merchant UPI: 9227095624@upi
echo   Remote Flat Fee: Rs. 250 | Visiting Base Fee: Rs. 500
echo ================================================================================

:WATCHDOG_LOOP
echo [%DATE% %TIME%] Starting Aria Production Service on Port 8000...
echo [%DATE% %TIME%] Starting Aria Production Service on Port 8000... >> logs\watchdog.log

python -m uvicorn aria_service:app --host 127.0.0.1 --port 8000

echo [%DATE% %TIME%] WARNING: aria_service.py terminated unexpectedly!
echo [%DATE% %TIME%] WARNING: aria_service.py terminated unexpectedly! Restarting in 3 seconds... >> logs\watchdog.log
timeout /t 3 /nobreak > nul
goto WATCHDOG_LOOP
