@echo off
title TripLink for TBO
cd /d "%~dp0"
echo ==============================================================
echo        🚀 Starting TripLink Native Desktop App for TBO
echo ==============================================================

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python launch_app.py
    exit /b
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py launch_app.py
    exit /b
)

echo [ERROR] Python was not found in your PATH.
echo Please ensure Python is installed and added to PATH.
pause
