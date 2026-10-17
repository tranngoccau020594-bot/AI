@echo off
setlocal
cd /d "%~dp0.."
echo After the server starts, open http://127.0.0.1:8770 in your browser.
echo This probe renders the original activation screen; it is not a working studio integration.
python original-ui-adapter\server.py --data-dir "%LOCALAPPDATA%\IndependentStudio\original-ui-probe" --port 8770
pause
