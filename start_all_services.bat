@echo off
REM Voice-to-Voice RAG AI Agent - Start All Services
REM This script starts all 4 services in separate windows

echo ========================================
echo Voice-to-Voice RAG AI Agent
echo Starting All Services...
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and add your GROQ_API_KEY
    pause
    exit /b 1
)

echo Starting Backend Service (Port 8000)...
start "Backend - Port 8000" cmd /k "cd backend && venv\Scripts\activate && python main.py"
timeout /t 2 /nobreak >nul

echo Starting STT Service (Port 8001)...
start "STT Service - Port 8001" cmd /k "cd services\stt && venv\Scripts\activate && python main.py"
timeout /t 2 /nobreak >nul

echo Starting TTS Service (Port 8002)...
start "TTS Service - Port 8002" cmd /k "cd services\tts && venv\Scripts\activate && python main.py"
timeout /t 2 /nobreak >nul

echo Starting Frontend (Port 5173)...
start "Frontend - Port 5173" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo All services are starting!
echo ========================================
echo.
echo Wait 10-15 seconds for all services to initialize...
echo Then open: http://localhost:5173
echo.
echo To stop all services, close all the terminal windows.
echo.
pause
