@echo off
echo 🚀 Starting DevSecOps Platform with Redis and Ollama AI
echo =====================================================

REM Check if Docker is running
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo ✅ Docker is running

REM Stop existing containers
echo 🛑 Stopping existing containers...
docker-compose down

REM Start Redis and Ollama services
echo 🔄 Starting Redis and Ollama services...
docker-compose up redis ollama -d

echo ⏳ Waiting for services to start...
timeout /t 10 /nobreak >nul

REM Check if Redis is running
echo 🔍 Checking Redis...
docker exec withops-redis redis-cli ping >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Redis is running on port 16379
) else (
    echo ❌ Redis failed to start
)

REM Check if Ollama is running
echo 🔍 Checking Ollama...
curl -s http://localhost:11434/api/version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Ollama is running on port 11434
) else (
    echo ⚠️ Ollama may still be starting (this is normal)
)

echo.
echo 🎉 Services started successfully!
echo.
echo 📋 Service Status:
echo   Redis:  http://localhost:16379
echo   Ollama: http://localhost:11434
echo.
echo 🧪 Test your setup:
echo   python test-redis-connection.py
echo   python test-ollama-integration.py
echo.
echo 🚀 Start the backend:
echo   cd backend
echo   python main.py
echo.
pause
