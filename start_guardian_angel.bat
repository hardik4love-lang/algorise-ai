@echo off
chcp 65001 > nul
title Guardian Angel™ AI — Scam & Fraud Sentinel (UK & US)
cd /d "%~dp0"

echo ===============================================================================
echo   GUARDIAN ANGEL™ — AI SCAM & FRAUD DEFENSE SENTINEL (UK & US)
echo   Real-time Protection from Bank Impersonation, Delivery Smishing & Vishing
echo   Target Markets: United Kingdom (GBP £) & United States (USD $)
echo ===============================================================================
echo.

echo [1/2] Starting Guardian Angel AI Sentinel Engine on Port 8050...
start "Guardian Angel AI Daemon" cmd /c "title Guardian Angel AI Daemon && python guardian_angel_api.py"

echo [2/2] Opening Guardian Angel AI Defense Console in your browser...
timeout /t 2 /nobreak > nul
start "" "guardian_angel_app.html"

echo.
echo ===============================================================================
echo   GUARDIAN ANGEL IS ONLINE!
echo   - Universal Phone App (PWA): http://127.0.0.1:8050/mobile
echo   - Interactive App Console:   guardian_angel_app.html
echo   - Backend Sentinel API:      http://127.0.0.1:8050/v1/sentinel/triage
echo   - Senior Easy-Read Mode:     WCAG 2.1 AAA Large Fonts & Web Speech Active
echo   - UK & US Scam Detection:    Active (USPS, HMRC, Chase, Evri, Geek Squad)
echo   - Family Angel Co-Pilot:     Active (@Aassqqee_bot Telegram Alerts)
echo ===============================================================================
echo.
pause
