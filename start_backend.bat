@echo off
REM Start Backend Service with proper virtual environment

echo ========================================
echo Starting Backend Service (Port 8000)
echo ========================================
echo.

REM Check if venv exists
if not exist backend\venv (
    echo ERROR: Virtual environment not found!
    echo Please run: cd backend && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check if .env exists
if not exist .env (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and add your GROQ_API_KEY
    pause
    exit /b 1
)

echo Activating virtual environment...
cd backend
call venv\Scripts\activate.bat

echo.
echo Starting FastAPI backend...
echo.
python main.py

pause
