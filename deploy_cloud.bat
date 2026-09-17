@echo off
echo ====================================================
echo Deploying Algorise AI to Cloud (algorise-ai.surge.sh)...
echo ====================================================
powershell -Command "Copy-Item index.html dist/index.html -Force; Copy-Item index.html dist/200.html -Force; Copy-Item realtor_sales_console.html dist/realtor_sales_console.html -Force"
npx surge dist algorise-ai.surge.sh
echo.
echo ====================================================
echo Deployed successfully to https://algorise-ai.surge.sh!
echo ====================================================
pause
