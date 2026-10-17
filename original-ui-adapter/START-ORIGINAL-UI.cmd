@echo off
setlocal
cd /d "%~dp0.."
echo After the server starts, open http://127.0.0.1:8770 in your browser.
echo The home page is a status screen. Original diagnostics remain at /original.
python original-ui-adapter\server.py --data-dir "%LOCALAPPDATA%\IndependentStudio\original-ui-probe" --port 8770
pause
