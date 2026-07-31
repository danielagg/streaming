@echo off
setlocal
title Command Deck Launcher
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run-local.ps1"
if errorlevel 1 (
  echo.
  echo Command Deck could not start. See the error above.
  pause
)
endlocal
