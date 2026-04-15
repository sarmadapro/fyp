#!/bin/bash
# Voice-to-Voice RAG AI Agent - Start All Services
# This script starts all 4 services in separate terminal tabs/windows

echo "========================================"
echo "Voice-to-Voice RAG AI Agent"
echo "Starting All Services..."
echo "========================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.example to .env and add your GROQ_API_KEY"
    exit 1
fi

# Detect OS and terminal
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - use Terminal.app
    echo "Starting services in separate Terminal windows..."
    
    osascript -e 'tell application "Terminal" to do script "cd \"'$(pwd)'/backend\" && source venv/bin/activate && python main.py"'
    sleep 1
    osascript -e 'tell application "Terminal" to do script "cd \"'$(pwd)'/services/stt\" && source venv/bin/activate && python main.py"'
    sleep 1
    osascript -e 'tell application "Terminal" to do script "cd \"'$(pwd)'/services/tts\" && source venv/bin/activate && python main.py"'
    sleep 1
    osascript -e 'tell application "Terminal" to do script "cd \"'$(pwd)'/frontend\" && npm run dev"'
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - try gnome-terminal, then xterm as fallback
    if command -v gnome-terminal &> /dev/null; then
        echo "Starting services in separate gnome-terminal tabs..."
        gnome-terminal --tab --title="Backend (8000)" -- bash -c "cd backend && source venv/bin/activate && python main.py; exec bash"
        sleep 1
        gnome-terminal --tab --title="STT (8001)" -- bash -c "cd services/stt && source venv/bin/activate && python main.py; exec bash"
        sleep 1
        gnome-terminal --tab --title="TTS (8002)" -- bash -c "cd services/tts && source venv/bin/activate && python main.py; exec bash"
        sleep 1
        gnome-terminal --tab --title="Frontend (5173)" -- bash -c "cd frontend && npm run dev; exec bash"
    else
        echo "gnome-terminal not found. Starting in background..."
        echo "You can monitor logs in the terminal or check http://localhost:8000/health"
        cd backend && source venv/bin/activate && python main.py &
        cd ../services/stt && source venv/bin/activate && python main.py &
        cd ../services/tts && source venv/bin/activate && python main.py &
        cd ../../frontend && npm run dev &
    fi
else
    echo "Unsupported OS. Please start services manually."
    exit 1
fi

echo ""
echo "========================================"
echo "All services are starting!"
echo "========================================"
echo ""
echo "Wait 10-15 seconds for all services to initialize..."
echo "Then open: http://localhost:5173"
echo ""
echo "To stop all services, close the terminal windows or press Ctrl+C"
echo ""
