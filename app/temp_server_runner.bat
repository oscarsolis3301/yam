@echo off 
setlocal enabledelayedexpansion 
echo [INFO] Starting YAM server process with enhanced session management... 
python server.py --host 0.0.0.0 --port 5000 --mode web --debug --debugger-mode --allow-multiple-sessions 
echo [INFO] Server process started 
pause 
