@echo off
setlocal
cd /d "%~dp0"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set TARGET_DATE=%%i
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format HHmmss"') do set RUN_TIME=%%i
set RUN_LABEL=live-stop7-%RUN_TIME%

echo [1/3] Running scrape + build + publish...
python update_products.py run --categories "%~dp0categories.json" --target-date %TARGET_DATE% --run-label %RUN_LABEL% --stop-days 7
if errorlevel 1 (
  echo Workflow failed.
  exit /b 1
)

echo [2/3] Committing site updates...
git add products.json data.js app.js index.html products.html styles.css update_products.py 1688_auto_trial\scraper_channel_cdp.js .gitignore
git commit -m "Update site data %TARGET_DATE% %RUN_LABEL%"
if errorlevel 1 (
  echo No new commit was created. Continuing to push current branch.
)

echo [3/3] Pushing to GitHub...
git push origin main
if errorlevel 1 (
  echo Push failed.
  exit /b 1
)

echo Done.
echo Run folder: outputs\%TARGET_DATE%\%RUN_LABEL%
echo Site: https://selection-site.vercel.app/index.html
