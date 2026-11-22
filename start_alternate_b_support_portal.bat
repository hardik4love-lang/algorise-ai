@echo off
chcp 65001 > nul
title Algorise AI — Alternate B: Web & Telegram-First Support Portal
cd /d "%~dp0"

echo ===============================================================================
echo   ALGORISE AI — ALTERNATE B: WEB & TELEGRAM-FIRST SUPPORT DESK
echo   100%% Zero WhatsApp Automation Footprint (Personal SIM Completely Safe)
echo   Founder Personal Desk: +91 92270 95624 | Merchant UPI: 9227095624@upi
echo   Telegram Bot:          @Aassqqee_bot   | Alerts Chat ID: 8737013099
echo   Remote Support:        ₹250 Flat       | Surat On-Site: ₹500+
echo ===============================================================================
echo.

echo [1/3] Starting Aria 24/7 Production Daemon & Telegram Gateway...
start "AlgoRise Aria & Telegram Daemon" cmd /c "title AlgoRise Aria & Telegram Daemon && python aria_service.py"

echo [2/3] Waiting 2 seconds for server to initialize...
timeout /t 2 /nobreak > nul

echo [3/3] Opening Interactive Web Support Portal in browser...
start "" "http://127.0.0.1:8000/support"

echo.
echo ===============================================================================
echo   ALTERNATE B IS LIVE!
echo   - Local Support Portal:    http://127.0.0.1:8000/support
echo   - Public HTTPS Tunnel:     Run start_cloudflare_tunnel.bat
echo   - Telegram Alerts:         Enabled -> Chat ID 8737013099
echo   - AnyDesk Remote Session:  Flat ₹250 Dynamic UPI QR
echo   - Surat Onsite Doorstep:   ₹500 / ₹750 Advance Deposit
echo ===============================================================================
echo.
echo Press any key to close this launcher window.
pause > nul
