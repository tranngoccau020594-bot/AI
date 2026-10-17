@echo off
setlocal
set "STUDIO_ZIP=%~dp0Independent-Studio-0.2.0-windows-x64.zip"
if exist "%STUDIO_ZIP%" goto verify
if not exist "%~dp0Independent-Studio.zip.part01" goto missing
if not exist "%~dp0Independent-Studio.zip.part02" goto missing
if not exist "%~dp0Independent-Studio.zip.part03" goto missing
if not exist "%~dp0Independent-Studio.zip.part04" goto missing
copy /b "%~dp0Independent-Studio.zip.part01"+"%~dp0Independent-Studio.zip.part02"+"%~dp0Independent-Studio.zip.part03"+"%~dp0Independent-Studio.zip.part04" "%STUDIO_ZIP%" >nul
if errorlevel 1 goto failed
:verify
powershell.exe -NoProfile -Command "if ((Get-FileHash -LiteralPath $env:STUDIO_ZIP -Algorithm SHA256).Hash -ne '020762c658f96c2ba93ff6d5a58677ff4981a74c9c835ada5f8612c6bc75c35a') { Write-Error 'SHA256 mismatch'; exit 1 }; Write-Host 'SHA256 OK'"
if errorlevel 1 goto failed
echo Extract ALL files from Independent-Studio-0.2.0-windows-x64.zip.
echo Then open Independent Studio.exe, or OPEN-WITH-OPENAI.cmd to enter your own key.
echo Windows execution has not been tested by the build environment.
pause
exit /b 0
:missing
echo Missing ZIP part files. Extract the whole GitHub download first.
pause
exit /b 1
:failed
echo Failed. Do not use the incomplete ZIP. Check space and download all parts again.
pause
exit /b 1
