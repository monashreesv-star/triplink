@echo off
title Stop TripLink
echo Stopping TripLink server on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo Terminating process PID %%a...
    taskkill /F /PID %%a >nul 2>&1
)
echo TripLink server stopped.
timeout /t 2 >nul
