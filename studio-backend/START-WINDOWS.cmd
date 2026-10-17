@echo off
setlocal
cd /d "%~dp0.."
python studio-backend\server.py --port 8766
pause
