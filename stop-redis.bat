@echo off
echo 🛑 Stopping Redis containers...
echo.

REM Stop docker-compose Redis
echo 🔄 Stopping docker-compose services...
docker-compose down

REM Stop standalone Redis if exists
docker stop redis-devsecops >nul 2>&1
docker rm redis-devsecops >nul 2>&1

echo.
echo 📋 Current Redis containers:
docker ps --filter "name=redis" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo.
echo ✅ Redis containers stopped
pause
