@echo off
chcp 65001 >nul
where py >nul 2>nul
if errorlevel 1 (
    echo Python 3 is required for the wizard.
    echo Install it from https://www.python.org/downloads/ ^(keep "py launcher" checked^), then run this again.
    echo.
    pause
    exit /b 1
)
py "%~dp0tools\famswap_wizard.py"
echo.
pause
