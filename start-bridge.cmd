@echo off
REM start-bridge.cmd -- Starts the Jules Bridge as a fully detached background process.
REM Called by Launch-AutoPilot.ps1 when bridge is not running.

set PYTHONPATH=C:\Users\shpctac1002c\AppData\Roaming\Python\Python312\site-packages
set PYTHONEXE=C:\Users\shpctac1002c\AppData\Local\Programs\Python\Python312\python.exe

REM Load .env into environment
for /f "usebackq tokens=1,* delims==" %%A in ("%~dp0.env") do (
    if not "%%A"=="" if not "%%A:~0,1%"=="#" (
        set "%%A=%%B"
    )
)

REM Start bridge fully detached (not a child of this cmd window)
start /b "" "%PYTHONEXE%" "%~dp0bridge.py"
echo Bridge started.
