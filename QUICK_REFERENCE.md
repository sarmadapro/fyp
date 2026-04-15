# 🚀 Quick Reference Card

## 📦 One-Time Setup

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Add your Groq API key to .env
# Edit .env and set: GROQ_API_KEY=your_key_here

# 3. Install backend dependencies
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..

# 4. Install STT dependencies
cd services/stt
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ../..

# 5. Install TTS dependencies
cd services/tts
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ../..

# 6. Install frontend dependencies
cd frontend
npm install
cd ..
```

## ▶️ Start All Services

**Windows:**
```bash
start_all_services.bat
```

**Linux/Mac:**
```bash
chmod +x start_all_services.sh
./start_all_services.sh
```

**Manual (4 separate terminals):**
```bash
# Terminal 1: Backend
cd backend && source venv/bin/activate && python main.py

# Terminal 2: STT
cd services/stt && source venv/bin/activate && python main.py

# Terminal 3: TTS
cd services/tts && source venv/bin/activate && python main.py

# Terminal 4: Frontend
cd frontend && npm run dev
```

## 🔍 Health Checks

```bash
# Check all services
python test_services.py

# Or manually:
curl http://localhost:8000/health  # Backend
curl http://localhost:8001/health  # STT
curl http://localhost:8002/health  # TTS
# Open http://localhost:5173        # Frontend
```

## 🧪 Verify Setup

```bash
python check_setup.py
```

## 📡 API Endpoints

### Backend (Port 8000)

**Health:**
- `GET /health` - Service health check

**Documents:**
- `GET /document/status` - Get current document info
- `POST /document/upload` - Upload a document (multipart/form-data)
- `DELETE /document/delete` - Delete current document

**Chat:**
- `POST /chat` - Send a text message
  ```json
  {
    "question": "What is this document about?",
    "conversation_id": "optional-uuid"
  }
  ```
- `DELETE /chat/history/{conversation_id}` - Clear conversation history

**Voice:**
- `POST /voice/transcribe` - Transcribe audio to text
- `POST /voice/synthesize?text=Hello` - Convert text to speech
- `POST /voice/chat` - Full voice-to-voice interaction
- `WS /voice/stream` - WebSocket streaming voice chat

### STT Service (Port 8001)

- `GET /health` - Service health check
- `POST /transcribe` - Transcribe audio file

### TTS Service (Port 8002)

- `GET /health` - Service health check
- `POST /synthesize` - Synthesize speech from text
  ```json
  {
    "text": "Hello, world!",
    "voice": "af_sky"
  }
  ```
- `POST /synthesize/stream` - Streaming synthesis

## 🌐 URLs

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **STT Service:** http://localhost:8001
- **TTS Service:** http://localhost:8002

## 📁 Important Files

| File | Purpose |
|------|---------|
| `.env` | Environment configuration (API keys, ports) |
| `START_HERE.md` | Detailed setup guide |
| `PROGRESS.md` | Full project progress tracker |
| `CURRENT_STATUS.md` | Current implementation status |
| `PART2_PLANNING.md` | Next phase planning |

## 🔧 Common Commands

```bash
# Check setup
python check_setup.py

# Test services
python test_services.py

# Start all services (Windows)
start_all_services.bat

# Start all services (Linux/Mac)
./start_all_services.sh

# View backend logs
cd backend && source venv/bin/activate && python main.py

# View API documentation
# Open http://localhost:8000/docs in browser

# Install new Python package
cd backend && source venv/bin/activate && pip install package_name

# Install new npm package
cd frontend && npm install package_name
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "GROQ_API_KEY not found" | Add your API key to `.env` file |
| Port already in use | Kill process on port or change port in `.env` |
| Microphone not working | Grant browser microphone permissions |
| Models downloading slowly | First run downloads ~5GB of models, be patient |
| CORS error | Check `CORS_ORIGINS` in `.env` matches frontend URL |
| Import errors | Activate venv and reinstall: `pip install -r requirements.txt` |

## 📊 Project Structure

```
voice-rag-ai-agent/
├── backend/              # FastAPI backend (Port 8000)
│   ├── app/
│   │   ├── api/         # Route handlers
│   │   ├── core/        # Configuration
│   │   ├── models/      # Pydantic schemas
│   │   └── services/    # Business logic
│   └── main.py          # Entry point
├── services/
│   ├── stt/             # Speech-to-Text (Port 8001)
│   └── tts/             # Text-to-Speech (Port 8002)
├── frontend/            # React + Vite (Port 5173)
│   └── src/
│       ├── api/         # API client
│       ├── pages/       # Page components
│       └── hooks/       # Custom hooks
└── .env                 # Configuration (not in git)
```

## 🎯 Testing Workflow

1. ✅ Start all 4 services
2. ✅ Run `python test_services.py` to verify health
3. ✅ Open http://localhost:5173
4. ✅ Upload a test document (PDF/TXT/DOCX)
5. ✅ Test text chat with questions about the document
6. ✅ Test voice mode by recording a question
7. ✅ Verify audio response plays back

## 🚀 Next Steps

- **Part 1 Complete:** All MVP features working
- **Part 2:** Add multi-tenant SaaS features (see `PART2_PLANNING.md`)
- **Part 3:** Premium UI upgrade
- **Part 4:** Cloud deployment

## 💡 Pro Tips

- First model load takes 5-10 minutes (downloads models)
- Use Chrome/Edge for best voice recording support
- Keep all 4 services running while testing
- Check `/docs` endpoint for interactive API testing
- Use conversation_id to maintain chat context
- WebSocket streaming provides lower latency for voice

## 📚 Documentation

- Full setup: `START_HERE.md`
- Progress tracker: `PROGRESS.md`
- Current status: `CURRENT_STATUS.md`
- Part 2 planning: `PART2_PLANNING.md`
- This reference: `QUICK_REFERENCE.md`

---

**Need help?** Check `START_HERE.md` for detailed instructions.
