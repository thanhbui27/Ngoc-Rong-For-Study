@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\part-editor\run.ps1"
echo.
echo Part Studio da dung. Nhan phim bat ky de dong cua so.
pause >nul
