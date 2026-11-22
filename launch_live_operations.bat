@echo off
chcp 65001 > nul
title Algorise AI - Live Hybrid Operations Cockpit
echo ===============================================================================
echo   ALGORISE AI — LIVE HYBRID OPERATIONS & AUTOHEAL COCKPIT
echo   Founder Personal Care Line: +91 92270 95624
echo   Merchant UPI ID:            9227095624@upi
echo   Remote Support:             ₹250 Flat
echo   On-Site Personal Visit:     ₹500 Base + Distance Scaling
echo ===============================================================================
echo.

cd /d "%~dp0"

echo [1/3] Ingesting & Syncing Surat Commercial Accounts into SQLite DB...
python surat_lead_feeder.py

echo.
echo [2/3] Generating WhatsApp Outbound Dispatch Queue & Dynamic UPI QRs...
python whatsapp_outbound_engine.py

echo.
echo [3/3] Starting 24/7 Aria Production Daemon Watchdog...
start "Algorise Aria 24/7 Daemon Watchdog" cmd /c "start_aria_daemon.bat"

echo.
echo ===============================================================================
echo   OPERATIONAL COCKPIT IS LIVE!
echo   - Local API & Health Check:   http://127.0.0.1:8000/health
echo   - Interactive Dispatch UI:    outbound_command_center.html
echo   - Public HTTPS Tunnel:        Run start_cloudflare_tunnel.bat
echo   - Lead Dispatch CSV:          leads/
echo   - AutoHeal Diagnostics:       Continuous 20-second non-blocking supervisor active
echo ===============================================================================
echo.
echo Starting Outbound Command Center in your default browser...
start "" "outbound_command_center.html"
echo.
echo You can keep this window open or press any key to close launcher.
pause > nul
