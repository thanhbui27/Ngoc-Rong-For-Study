@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\run.ps1"
echo.
echo Part Studio da dung. Nhan phim bat ky de dong cua so.
pause >nul
