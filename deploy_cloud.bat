@echo off
echo ====================================================
echo Deploying Algorise AI to Cloud (algorise-ai.surge.sh)...
echo ====================================================
powershell -Command "Copy-Item index.html dist/index.html -Force; Copy-Item index.html dist/200.html -Force; Copy-Item cocopeat.html dist/cocopeat.html -Force; New-Item -ItemType Directory -Force -Path dist/cocopeat; Copy-Item cocopeat.html dist/cocopeat/index.html -Force; Copy-Item realtor_sales_console.html dist/realtor_sales_console.html -Force; Copy-Item creator_studio.html dist/creator_studio.html -Force"
call C:\Users\om\AppData\Local\npm-cache\_npx\23158936acd5c32d\node_modules\.bin\surge.cmd dist algorise-ai.surge.sh
call C:\Users\om\AppData\Local\npm-cache\_npx\23158936acd5c32d\node_modules\.bin\surge.cmd dist algorise.surge.sh
echo.
echo ====================================================
echo Deployed successfully to:
echo   - https://algorise-ai.surge.sh (Primary)
echo   - https://algorise.surge.sh    (Short Fast Alias)
echo   - https://algorise-ai.surge.sh/cocopeat.html
echo ====================================================
