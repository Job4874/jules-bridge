@echo off
set "GNUPGHOME=/c/Users/abdul/jules-bridge/.gnupg-local"
if exist "C:\Program Files\Git\usr\bin\gpg.exe" (
  "C:\Program Files\Git\usr\bin\gpg.exe" %*
) else (
  gpg %*
)
