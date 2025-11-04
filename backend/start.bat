@echo off
REM DevSecOps Backend Startup Script with UTF-8 Support

echo Starting DevSecOps Backend Server...
echo.

REM Set UTF-8 encoding
echo Configuring UTF-8 encoding...
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSFSENCODING=utf-8

REM Start the server
echo Starting FastAPI server...
echo.
python main.py

pause