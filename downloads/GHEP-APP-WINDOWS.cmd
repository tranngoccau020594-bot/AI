@echo off
setlocal
set "SEEDANCE_JOIN_OUTPUT=%~dp0Seedance-AI-1.0.160-windows-x64.exe"
if exist "%SEEDANCE_JOIN_OUTPUT%" goto verify
if not exist "%~dp0Seedance-AI.part01" goto missing
if not exist "%~dp0Seedance-AI.part02" goto missing
if not exist "%~dp0Seedance-AI.part03" goto missing
copy /b "%~dp0Seedance-AI.part01"+"%~dp0Seedance-AI.part02"+"%~dp0Seedance-AI.part03" "%SEEDANCE_JOIN_OUTPUT%" >nul
if errorlevel 1 goto failed
:verify
powershell.exe -NoProfile -Command "if ((Get-FileHash -LiteralPath $env:SEEDANCE_JOIN_OUTPUT -Algorithm SHA256).Hash -ne 'c25d582f1fa3c8c03d194681691fd87f90c25e2f3afc984974e26005539c7d92') { Write-Error 'SHA256 mismatch. File is incomplete or changed.'; exit 1 }; Write-Host 'SHA256 OK - Windows app reconstructed successfully.'"
if errorlevel 1 goto failed
echo.
echo Ready: Seedance-AI-1.0.160-windows-x64.exe
echo Runtime has NOT been tested on Windows. Original license is required.
echo Double-click the EXE when you are ready to run it.
pause
exit /b 0
:missing
echo Missing part files. Extract the WHOLE downloaded ZIP before running this tool.
pause
exit /b 1
:failed
echo Failed. Do not run the EXE. Check disk space and download all parts again.
pause
exit /b 1
