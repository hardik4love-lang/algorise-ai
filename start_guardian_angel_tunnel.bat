@echo off
chcp 65001 > nul
title Guardian Angel™ — Public HTTPS Cloudflare Tunnel
cd /d "%~dp0"

echo ===============================================================================
echo   GUARDIAN ANGEL™ — LIVE PUBLIC HTTPS CLOUDFLARE TUNNEL
echo   Exposing http://127.0.0.1:8050 to the Public World (UK & US)
echo   Target Audience: Adult Daughters (Sarah) & Seniors (Margaret)
echo ===============================================================================
echo.
echo Launching Quick Tunnel...
echo Copy the generated https://*.trycloudflare.com URL and send it to clients!
echo.

"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://127.0.0.1:8050
pause
