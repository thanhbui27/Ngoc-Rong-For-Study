@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 goto run_py
where python >nul 2>nul
if not errorlevel 1 goto run_python
echo Python 3 is required to run Clone Studio.
pause
exit /b 1

:run_py
py -3 ui.py %*
goto done

:run_python
python ui.py %*

:done
if errorlevel 1 (
    echo Clone Studio stopped with an error.
    pause
    exit /b 1
)
exit /b 0
