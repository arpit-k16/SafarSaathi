@echo off
title SafarSaathi
cd /d "%~dp0SafarSaathi_Project"
python run_safarsaathi.py
echo.
echo Server stopped. Press any key to close.
pause >nul
