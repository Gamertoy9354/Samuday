@echo off
title Samuday Platform - Local Runner
echo =======================================================================
echo               Samuday Community Super-Platform Local Runner
echo =======================================================================
echo.

:: Check for Docker
echo [1/4] Checking Docker services...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Docker is not installed or not in PATH.
    echo Please make sure Docker Desktop is running if you want local database, redis, and search.
    echo.
) else (
    echo Starting database, cache, and search containers...
    cd samuday-backend
    docker-compose up -d
    cd ..
    echo Docker services are running.
    echo.
)

:: Validate Backend Configuration
echo [2/4] Validating Backend config (.env)...
if not exist "samuday-backend\.env" (
    echo [INFO] Backend .env not found. Creating it from .env.example...
    copy "samuday-backend\.env.example" "samuday-backend\.env"
    echo [WARNING] Please open samuday-backend\.env and add your actual API keys:
    echo - GROQ_API_KEY
    echo - GEMINI_API_KEY
    echo - NVIDIA_API_KEY
    echo.
) else (
    echo Backend .env is present.
    echo.
)

:: Validate Frontend Configuration
echo [3/4] Validating Frontend config (.env)...
if not exist "samuday-frontend\.env" (
    echo [INFO] Frontend .env not found. Creating default configuration...
    echo VITE_GOOGLE_CLIENT_ID=512432791749-cmmd0qi2hr1hrha0vpot4gc143duc1nr.apps.googleusercontent.com> "samuday-frontend\.env"
    echo VITE_API_URL=http://localhost:8000>> "samuday-frontend\.env"
    echo.
) else (
    echo Frontend .env is present.
    echo.
)

:: Start Backend Server
echo [4/4] Starting servers...
echo.
echo Launching Backend server in a new window...
start "Samuday Backend Service" cmd /k "cd samuday-backend && .venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

:: Start Frontend Server
echo Launching Frontend server in a new window...
start "Samuday Frontend Service" cmd /k "cd samuday-frontend && npm run dev"

echo.
echo =======================================================================
echo System starting up!
echo - Frontend URL: http://localhost:5173
echo - Backend API Docs: http://localhost:8000/docs
echo =======================================================================
pause
