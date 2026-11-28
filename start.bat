@echo off
cd /d "%~dp0"

rem Prefer the Python 3.11 that already has all dependencies installed.
set "PYEXE=C:\Users\wei\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

"%PYEXE%" -c "import fastapi, uvicorn, bcrypt, chromadb" >nul 2>nul
if errorlevel 1 goto envfail

echo Starting AI assistant at http://127.0.0.1:8000
"%PYEXE%" -m uvicorn main:app --reload
if errorlevel 1 pause
exit /b 0

:envfail
echo.
echo [ERROR] Missing dependencies for: %PYEXE%
echo Use this interpreter instead:
echo     C:\Users\wei\AppData\Local\Programs\Python\Python311\python.exe
echo Or install deps for the current one:
echo     python -m pip install -r requirements.txt
echo.
pause
exit /b 1
