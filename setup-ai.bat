@echo off
echo 🚀 DevSecOps AI Setup Helper
echo.

echo 📋 STEP 1: Groq AI API Key Setup
echo.
echo Please follow these steps:
echo 1. Go to https://console.groq.com/
echo 2. Sign up for a free account
echo 3. Navigate to API Keys section
echo 4. Create a new API key
echo 5. Copy the API key (starts with 'gsk_')
echo.

set /p GROQ_API_KEY="Enter your Groq API key: "

if "%GROQ_API_KEY%"=="" (
    echo ❌ No API key provided. Setup cancelled.
    pause
    exit /b 1
)

echo.
echo 🔧 Setting environment variable...
setx GROQ_API_KEY "%GROQ_API_KEY%"

echo.
echo ✅ Groq API key configured!
echo.

echo 📋 STEP 2: Starting Services
echo.

echo 🔄 Starting Backend...
cd backend
start "DevSecOps Backend" cmd /k "python main.py"

echo 🔄 Starting Frontend...
cd ..\frontend
start "DevSecOps Frontend" cmd /k "npm run dev"

echo.
echo 🎉 Setup Complete!
echo.
echo 📍 Services running at:
echo   - Backend:  http://localhost:8000
echo   - Frontend: http://localhost:5174
echo.
echo 🤖 AI Features:
echo   - Navigate to threat modeling canvas
echo   - Select any component to see AI analysis
echo   - Use the chat interface for custom questions
echo.
echo 📱 Collaboration Mode: Local-only (no external connections)
echo.

pause
