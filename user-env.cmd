@echo off
REM user-env.cmd -- Portable environment setup. No hardcoded user paths.
REM Uses %~dp0 (directory containing this script) for all paths.
setlocal

set "JULES_REPO=%~dp0"
set "PYTHONIOENCODING=utf-8"
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "JULES_EXE="
REM Jules CLI: override by setting JULES_EXE in your system environment or .env
REM Example: set "JULES_EXE=C:\Users\YourName\.npm-packages\bin\jules.exe"
