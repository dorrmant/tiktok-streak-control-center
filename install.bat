@echo off
cd /d "%~dp0"
where python >nul 2>nul || (echo Python 3 not found. Install it from python.org and tick "Add to PATH". & pause & exit /b 1)
if not exist .venv\Scripts\python.exe python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -c "from backend import Backend; b=Backend(); print('Bot found:', b.config.get('bot_source') or 'NOT FOUND')"
echo.
echo Install complete. You need Google Chrome installed. Double-click run.bat to start.
pause
