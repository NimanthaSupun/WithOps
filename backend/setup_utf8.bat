@echo off
REM Windows batch script to set UTF-8 encoding for Python
REM Run this before starting the backend server on Windows

echo Setting up UTF-8 encoding for Windows...

REM Set UTF-8 code page for console
chcp 65001 > nul

REM Set Python UTF-8 mode
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSFSENCODING=utf-8

echo UTF-8 encoding configured successfully!
echo.
echo You can now run: python main.py
echo.
pause