@echo off
REM Build standalone Windows AlgoBridge.exe (zero Python runtime needed on client PC)
pip install pyinstaller >nul 2>&1
pyinstaller --onefile --name AlgoBridge algobridge_agent.py
echo Built dist\AlgoBridge.exe - Place on client Tally desktop and run:
echo AlgoBridge.exe --company-id YOUR_COMPANY_ID --api-key YOUR_ALGORISE_KEY
pause
