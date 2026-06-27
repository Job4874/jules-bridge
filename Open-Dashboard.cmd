@echo off
:: Jules Mission Control — double-click to launch as Administrator
:: Opens the real-time dashboard + bridge + cloud VMs in one shot.
powershell.exe -Command "Start-Process powershell.exe -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File ""C:\Users\abdul\.jules\Launch-Dashboard.ps1""' -Verb RunAs"
