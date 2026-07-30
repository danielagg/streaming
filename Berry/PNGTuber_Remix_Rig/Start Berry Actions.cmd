@echo off
title Berry Animation Controls
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0berry_actions.ps1"
if errorlevel 1 (
    echo.
    echo Berry controls stopped because of the error above.
    pause
)
