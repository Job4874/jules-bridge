@echo off
REM Opens Jules CLI from this repository root and bypasses broken npm shims.
title Jules CLI - jules-bridge
color 0D
cd /d "%~dp0"

set "JULES_EXE=%USERPROFILE%\.npm-packages\bin\jules.exe"
if exist "%JULES_EXE%" (
    "%JULES_EXE%" %*
    goto :done
)

jules %*

:done
echo.
echo Jules CLI exited.
if "%~1"=="" pause
