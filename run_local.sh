#!/bin/bash

echo "======================================================================="
echo "              Samuday Community Super-Platform Local Runner"
echo "======================================================================="
echo

# Check for Docker
echo "[1/4] Checking Docker services..."
if ! command -v docker &> /dev/null; then
    echo "[WARNING] Docker is not installed or not in PATH."
    echo "Please make sure Docker Desktop is running if you want local database, redis, and search."
    echo
else
    echo "Starting database, cache, and search containers..."
    cd samuday-backend
    docker-compose up -d
    cd ..
    echo "Docker services are running."
    echo
fi

# Validate Backend Configuration
echo "[2/4] Validating Backend config (.env)..."
if [ ! -f "samuday-backend/.env" ]; then
    echo "[INFO] Backend .env not found. Creating it from .env.example..."
    cp "samuday-backend/.env.example" "samuday-backend/.env"
    echo "[WARNING] Please open samuday-backend/.env and add your actual API keys:"
    echo " - GROQ_API_KEY"
    echo " - GEMINI_API_KEY"
    echo " - NVIDIA_API_KEY"
    echo
else
    echo "Backend .env is present."
    echo
fi

# Validate Frontend Configuration
echo "[3/4] Validating Frontend config (.env)..."
if [ ! -f "samuday-frontend/.env" ]; then
    echo "[INFO] Frontend .env not found. Creating default configuration..."
    echo "VITE_GOOGLE_CLIENT_ID=512432791749-cmmd0qi2hr1hrha0vpot4gc143duc1nr.apps.googleusercontent.com" > "samuday-frontend/.env"
    echo "VITE_API_URL=http://localhost:8000" >> "samuday-frontend/.env"
    echo
else
    echo "Frontend .env is present."
    echo
fi

# Start Backend Server
echo "[4/4] Starting servers..."
echo
echo "Starting Backend server..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # On Windows running bash (like Git Bash)
    start cmd /k "cd samuday-backend && .venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
else
    # On macOS / Linux
    (cd samuday-backend && source .venv/bin/activate && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
fi

# Start Frontend Server
echo "Starting Frontend server..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    start cmd /k "cd samuday-frontend && npm run dev"
else
    (cd samuday-frontend && npm run dev) &
fi

echo
echo "======================================================================="
echo "System starting up!"
echo " - Frontend URL: http://localhost:5173"
echo " - Backend API Docs: http://localhost:8000/docs"
echo "======================================================================="
echo "Press Enter to exit this runner script."
read
