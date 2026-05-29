@echo off
setlocal
set "APP_DIR=%~dp0"
set "PYTHONPATH=%APP_DIR%src"

where python >nul 2>nul
if not errorlevel 1 (
  python -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    python -m redaction_assistant.cli %*
    exit /b
  )
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    py -3 -m redaction_assistant.cli %*
    exit /b
  )
)

set "LO_PYTHON=D:\Program Files\PantumUtilities\lib\LibreOffice\program\python.exe"
if exist "%LO_PYTHON%" (
  "%LO_PYTHON%" -m redaction_assistant.cli %*
  exit /b
)

echo Cannot find Python. Please install Python 3.10+ or run with a configured Python environment.
exit /b 1
