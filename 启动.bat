@echo off
title Zimu - Smart Subtitle Generator

echo.
echo   ==========================================
echo     Zimu - Video Subtitle Generator
echo   ==========================================
echo.
echo   Starting server...

cd /d "%~dp0"

python -c "import fastapi" 2>nul
if %errorlevel% neq 0 (
    echo   [*] Installing dependencies...
    pip install -r requirements.txt
)

start "Zimu-Server" /MIN python -m uvicorn main:app --host 0.0.0.0 --port 8000

echo   Waiting for server to be ready...
:loop
timeout /t 2 /nobreak >nul
curl -s -o NUL http://localhost:8000 2>nul
if %errorlevel% neq 0 goto loop

start http://localhost:8000

echo.
echo   ==========================================
echo     Browser opened: http://localhost:8000
echo     Close the Zimu-Server window to stop
echo   ==========================================
echo.
pause
