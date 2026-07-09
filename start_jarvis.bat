@echo off
title J.A.R.V.I.S - Local AI Assistant
color 0B

echo.
echo  ==========================================
echo    J.A.R.V.I.S  v2.0  -- Starting up...
echo  ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: Start Ollama in background (ignore if already running)
echo  [*] Starting Ollama server...
start /b "" ollama serve >nul 2>&1
timeout /t 2 /nobreak >nul

:: Launch Jarvis
echo  [*] Launching Jarvis...
echo.
python main.py --no-voice %*

pause
