@echo off
echo 🐳 Starting Redis with Docker...
echo.

REM Check if Docker is running
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Docker is not running or not installed
    echo Please start Docker Desktop and try again
    pause
    exit /b 1
)

echo ✅ Docker is available
echo.

REM Start Redis using docker-compose
echo 🚀 Starting Redis container...
docker-compose up redis -d

if errorlevel 1 (
    echo ❌ Failed to start Redis with docker-compose
    echo.
    echo 🔄 Trying standalone Redis container...
    docker run --name redis-devsecops -p 6379:6379 -d redis:7-alpine
    if errorlevel 1 (
        echo ❌ Failed to start standalone Redis container
        pause
        exit /b 1
    )
    echo ✅ Standalone Redis container started
) else (
    echo ✅ Redis started with docker-compose
)

echo.
echo 🔍 Testing Redis connection...
timeout /t 3 /nobreak >nul

REM Test Redis connection
docker exec -it withops-redis redis-cli ping >nul 2>&1
if errorlevel 1 (
    REM Try standalone container
    docker exec -it redis-devsecops redis-cli ping >nul 2>&1
    if errorlevel 1 (
        echo ⚠️ Redis might still be starting up...
        echo Please wait 10 seconds and check your backend logs
    ) else (
        echo ✅ Redis is responding (standalone)
    )
) else (
    echo ✅ Redis is responding (docker-compose)
)

echo.
echo 📋 Redis Status:
docker ps --filter "name=redis" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo.
echo 🎉 Redis setup complete!
echo You can now start your backend and it should connect to Redis
echo.
echo 🔧 Useful commands:
echo   - Stop Redis: docker-compose down
echo   - View logs: docker-compose logs redis
echo   - Redis CLI: docker exec -it withops-redis redis-cli
echo.
pause
