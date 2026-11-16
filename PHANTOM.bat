@echo off
chcp 65001 >nul
cd /d "%~dp0"

call :findpy
if not defined PY (
    powershell -NoProfile -ExecutionPolicy Bypass -File "app\setup\install-python.ps1" -App PHANTOM -Accent green
    if errorlevel 1 exit /b 1
    call :findpy
)
if not defined PY (
    echo [PHANTOM] Python is still not available. Close this window and start PHANTOM again.
    pause
    exit /b 1
)

%PY% "app\phantom.py"
if errorlevel 1 pause
exit /b

:findpy
rem A working Python 3.8+ is needed. "python" can also be the Microsoft Store
rem placeholder that only opens the Store, so each candidate is actually run.
set "PY="
python -c "import sys; sys.exit(sys.version_info < (3, 8))" >nul 2>nul && (set "PY=python" & goto :eof)
py -3 -c "import sys; sys.exit(sys.version_info < (3, 8))" >nul 2>nul && (set "PY=py -3" & goto :eof)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
goto :eof
