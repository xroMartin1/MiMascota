@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start_dev.ps1" %*
if errorlevel 1 (
    echo.
    echo PetCare no pudo iniciarse. Revisa el mensaje anterior.
    pause
)
