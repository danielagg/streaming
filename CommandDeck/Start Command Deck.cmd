@echo off
setlocal

py -3.13 -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo Command Deck needs Python 3.13 with Tkinter.
    echo.
    echo Install Python from https://www.python.org/downloads/windows/
    echo and then run this launcher again.
    echo.
    pause
    exit /b 1
)

start "" pyw -3.13 "%~dp0CommandDeck.pyw"
exit /b 0
