@echo off
echo 🚀 Starting DevSecOps Backend with Vulnerability Prediction
echo ============================================================

REM Change to backend directory
cd /d "D:\project\dev-testing\DevSecOps\backend"

REM Activate virtual environment and start server
echo ✅ Activating virtual environment...
call "D:\project\dev-testing\DevSecOps\.venv\Scripts\activate.bat"

echo ✅ Starting server on port 8000...
echo 📖 API Documentation will be available at: http://127.0.0.1:8000/docs
echo 🔧 Vulnerability Prediction endpoints: http://127.0.0.1:8000/docs#/vulnerability-prediction
echo.

uvicorn main:app --reload --port 8000 --host 127.0.0.1

pause