@echo off
echo ========================================
echo  VocalizeWeb - Starting All Services
echo ========================================
echo.

REM ── Kill anything already on these ports ──────────────────────────
echo Clearing ports 8000 8002 5173 3000...
for %%P in (8000 8002 5173 3000) do (
    for /f "tokens=5" %%i in ('netstat -aon ^| findstr ":%%P " ^| findstr "LISTENING"') do (
        taskkill /PID %%i /F >nul 2>&1
    )
)
timeout /t 1 /nobreak >nul

REM ── Run DB migrations ─────────────────────────────────────────────
echo Running database migrations...
cd backend && venv\Scripts\python.exe migrate_db.py
cd ..
echo.

REM ── Backend — Port 8000 ───────────────────────────────────────────
echo Starting Backend (port 8000)...
start "Backend :8000" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && python main.py"
timeout /t 3 /nobreak >nul

REM ── TTS — Port 8002 ───────────────────────────────────────────────
echo Starting TTS service (port 8002)...
start "TTS :8002" cmd /k "cd /d %~dp0services\tts && venv\Scripts\activate && python main.py"
timeout /t 2 /nobreak >nul

REM ── VocalizeWeb Frontend — Port 5173 ─────────────────────────────
echo Starting VocalizeWeb frontend (port 5173)...
start "Frontend :5173" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 2 /nobreak >nul

REM ── Namal Demo Site — Port 3000 ──────────────────────────────────
echo Starting Namal demo site (port 3000)...
start "Namal :3000" cmd /k "cd /d %~dp0Namal_-frontend && npm start"

echo.
echo ========================================
echo  All 4 services launching in windows:
echo    Backend    -^> http://localhost:8000
echo    TTS        -^> http://localhost:8002
echo    Portal     -^> http://localhost:5173
echo    Namal Demo -^> http://localhost:3000
echo.
echo  STT: OpenAI Whisper API (direct, no microservice)
echo  To stop everything: run stop_all_services.bat
echo ========================================
echo.
pause
