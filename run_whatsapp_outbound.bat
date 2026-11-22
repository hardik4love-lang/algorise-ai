@echo off
chcp 65001 > nul
title Algorise AI - Hybrid WhatsApp Outbound & Dispatch Console
echo ===============================================================================
echo   ALGORISE AI — HYBRID OUTBOUND & PERSONAL VISIT DISPATCH LAUNCHER
echo   Direct Care Line: +91 92270 95624 | UPI: 9227095624@upi
echo ===============================================================================
echo.
cd /d "%~dp0"

echo [+] Running WhatsApp Outbound Engine...
python whatsapp_outbound_engine.py

echo.
echo ===============================================================================
echo   Console ready! Open outbound_command_center.html to start sending pitches.
echo ===============================================================================
pause
