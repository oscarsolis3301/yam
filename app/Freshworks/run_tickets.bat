@echo off
setlocal

:loop
echo Running ticket export script...
python tickets.py

echo Script crashed or exited. Restarting in 30 seconds...
timeout /t 30
goto loop
