@echo off
title Udhna Cocopeat - Nursery Lead Finder
color 0a
cd /d "%~dp0"
echo ===============================================================================
echo        UDHNA COCOPEAT MFG - NURSERY & B2B AGRI PROSPECTING ENGINE
echo ===============================================================================
echo.
python nursery_lead_scraper.py
echo.
echo Press any key to exit...
pause >nul
