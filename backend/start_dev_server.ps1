# PowerShell script to start DevSecOps backend with vulnerability prediction
Write-Host "🚀 Starting DevSecOps Backend with Vulnerability Prediction" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green

# Change to backend directory
Set-Location "D:\project\dev-testing\DevSecOps\backend"

Write-Host "✅ Activating virtual environment..." -ForegroundColor Yellow
& "D:\project\dev-testing\DevSecOps\.venv\Scripts\Activate.ps1"

Write-Host "✅ Starting server on port 8000..." -ForegroundColor Yellow
Write-Host "📖 API Documentation will be available at: http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "🔧 Vulnerability Prediction endpoints: http://127.0.0.1:8000/docs#/vulnerability-prediction" -ForegroundColor Cyan
Write-Host ""

# Start the server with fixed logging configuration
python start_server_fixed.py