@echo off
:: Jules Mission Control — double-click to launch as Administrator
:: Opens the real-time dashboard + bridge + cloud VMs in one shot.
powershell.exe -Command "Start-Process powershell.exe -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File ""%~dp0Launch-Dashboard.ps1""' -Verb RunAs"
