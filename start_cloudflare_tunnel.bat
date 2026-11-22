@echo off
title Algorise AI — Cloudflare Public HTTPS Tunnel
cd /d "%~dp0"

echo ================================================================================
echo   ALGORISE AI — CLOUDFLARE PUBLIC HTTPS TUNNEL
echo   Exposing http://127.0.0.1:8000 to the Public Internet
echo   Personal Visit Line: +91 92270 95624 | Merchant UPI: 9227095624@upi
echo ================================================================================
echo.
echo Launching Cloudflare Quick Tunnel...
echo Copy the generated https://*.trycloudflare.com URL into your MacroDroid or Webhook settings.
echo.

cloudflared tunnel --url http://127.0.0.1:8000
pause
