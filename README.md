# 🎙️ Voice-to-Voice RAG AI Agent

> A production-ready SaaS platform for deploying voice-enabled AI assistants powered by RAG (Retrieval-Augmented Generation) over custom documents.

[![Status](https://img.shields.io/badge/Status-Part%201%20Complete-success)]()
[![Python](https://img.shields.io/badge/Python-3.10+-blue)]()
[![React](https://img.shields.io/badge/React-19.2-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)]()

---

## ✨ Features

### 🎯 Current (Part 1 - MVP Complete)

- ✅ **Document Upload & Processing** - PDF, TXT, DOCX support with automatic text extraction
- ✅ **RAG-Powered Chat** - Intelligent Q&A using Groq's Llama 3.3 70B with context retrieval
- ✅ **Streaming Responses** - Real-time token-by-token chat responses for better UX
- ✅ **Voice-to-Voice Interaction** - Speak to your documents and get spoken responses
- ✅ **Real-time Transcription** - Faster-Whisper large-v3 for accurate speech recognition
- ✅ **Natural Voice Synthesis** - Kokoro-82M for human-like text-to-speech
- ✅ **Conversation Memory** - Maintains context across multiple exchanges
- ✅ **Modern UI** - Responsive React interface with drag-and-drop uploads
- ✅ **WebSocket Streaming** - Low-latency real-time voice interaction

### 🚀 Coming Soon (Part 2-4)

- 🔜 **Multi-Tenant SaaS** - Client portals, user management, and authentication
- 🔜 **Usage Analytics** - Track queries, voice minutes, and document processing
- 🔜 **API Access** - RESTful API for client integrations
- 🔜 **Premium UI** - Glassmorphism design with animations
- 🔜 **Cloud Deployment** - Docker + CI/CD pipeline for production

---

## 🏗️ Architecture

```
┌─────────────────┐
│ React Frontend  │  (Vite + Modern UI)
└────────┬────────┘
         │ HTTP/WebSocket
         ▼
┌─────────────────┐
│ FastAPI Backend │  (RAG Pipeline + Orchestration)
│  • LangChain    │
│  • FAISS        │
│  • Groq LLM     │
└────┬────────┬───┘
     │        │
     ▼        ▼
┌─────────┐ ┌─────────┐
│   STT   │ │   TTS   │  (AI Microservices)
│ Whisper │ │ Kokoro  │
└─────────┘ └─────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Groq API key ([Get one free](https://console.groq.com))

### 1. Clone & Configure

```bash
git clone <your-repo-url>
cd voice-rag-ai-agent
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2. Install Dependencies

```bash
# Backend
cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && cd ..

# STT Service
cd services/stt && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && cd ../..

# TTS Service
cd services/tts && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && cd ../..

# Frontend
cd frontend && npm install && cd ..
```

### 3. Start All Services

**Windows:**
```bash
start_all_services.bat
```

**Linux/Mac:**
```bash
chmod +x start_all_services.sh
./start_all_services.sh
```

### 4. Open Application

Navigate to **http://localhost:5173** and start chatting with your documents!

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [QUICK_FIX.md](QUICK_FIX.md) | ⚡ **START HERE if you have the GROQ_API_KEY error** |
| [START_HERE.md](START_HERE.md) | 📖 Detailed setup guide for new developers |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | ⚡ Quick command reference and API endpoints |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | 🔧 Comprehensive troubleshooting guide |
| [PROGRESS.md](PROGRESS.md) | 📊 Complete project roadmap and progress tracker |
| [CURRENT_STATUS.md](CURRENT_STATUS.md) | 📋 Current implementation status and architecture |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 🏗️ Detailed system architecture diagrams |
| [PART2_PLANNING.md](PART2_PLANNING.md) | 🗺️ Multi-tenant SaaS implementation plan |
| [FIX_SUMMARY.md](FIX_SUMMARY.md) | 📝 Detailed explanation of the API key fix |

---

## 🧪 Testing

### Verify Setup
```bash
python check_setup.py
```

### Health Check
```bash
python test_services.py
```

### Manual Testing
1. Upload a document (PDF/TXT/DOCX)
2. Ask questions via text chat
3. Try voice mode - speak your question
4. Verify audio response plays back

---

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern async Python web framework
- **LangChain** - RAG pipeline orchestration
- **Groq API** - Ultra-fast LLM inference (Llama 3.3 70B)
- **FAISS** - Vector similarity search
- **Sentence-Transformers** - Text embeddings

### AI Services
- **Faster-Whisper** - Speech-to-text (large-v3 model)
- **Kokoro-82M** - Text-to-speech (natural voice)

### Frontend
- **React 19** - UI library
- **Vite** - Fast build tool
- **React Router** - Navigation
- **Lucide Icons** - Modern icon set

### Document Processing
- **PyMuPDF** - PDF text extraction
- **python-docx** - DOCX processing

---

## 📁 Project Structure

```
voice-rag-ai-agent/
├── backend/                 # FastAPI backend (Port 8000)
│   ├── app/
│   │   ├── api/            # REST endpoints
│   │   ├── core/           # Configuration
│   │   ├── models/         # Pydantic schemas
│   │   └── services/       # Business logic
│   ├── data/               # Uploads & FAISS indices
│   └── main.py             # Entry point
│
├── services/               # AI Microservices
│   ├── stt/               # Speech-to-Text (Port 8001)
│   └── tts/               # Text-to-Speech (Port 8002)
│
├── frontend/              # React frontend (Port 5173)
│   └── src/
│       ├── api/          # API client
│       ├── pages/        # Chat, Voice, Upload pages
│       └── hooks/        # Audio recording hook
│
├── .env                   # Configuration (not in git)
├── .env.example          # Configuration template
└── [Documentation files]
```

---

## 🎯 Roadmap

### ✅ Part 1: Core RAG + Voice Assistant (Complete)
- Document upload and processing
- RAG chat pipeline with Groq LLM
- Voice-to-voice interaction
- React frontend with modern UI

### 🔄 Part 2: SaaS Multi-Tenant Solution (Next)
- PostgreSQL database
- JWT authentication
- Client portals and user management
- Usage analytics and API keys
- Admin dashboard

### 📅 Part 3: Premium UI Upgrade
- Glassmorphism design system
- Animated voice visualizations
- Dark mode theme
- Accessibility improvements

### 📅 Part 4: Cloud Deployment
- Docker containerization
- CI/CD pipeline
- Cloud infrastructure (AWS/GCP/Azure)
- Auto-scaling and monitoring

---

## 🔧 Configuration

### Environment Variables

```env
# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional (defaults provided)
BACKEND_PORT=8000
STT_SERVICE_URL=http://localhost:8001
TTS_SERVICE_URL=http://localhost:8002
LLM_MODEL=llama-3.3-70b-versatile
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

See `.env.example` for all available options.

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "GROQ_API_KEY not found" | Use `start_backend.bat` or activate venv before running |
| Services won't start | Check ports 8000, 8001, 8002, 5173 are available |
| Microphone not working | Grant browser permissions (Chrome/Edge recommended) |
| First run is slow | Models download on first use (~5GB, 5-10 minutes) |
| CORS errors | Verify `CORS_ORIGINS` in `.env` matches frontend URL |
| Module not found | Always activate venv: `cd backend && venv\Scripts\activate` |

**For detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)**

See [START_HERE.md](START_HERE.md) for detailed setup instructions.

---

## 📊 Performance

- **Text Chat Response:** < 2 seconds
- **Voice Transcription:** < 3 seconds (10s audio)
- **Voice Synthesis:** < 2 seconds (first audio)
- **End-to-End Voice:** < 5 seconds total

---

## 🤝 Contributing

This is a learning/portfolio project. Feel free to:
- Report bugs
- Suggest features
- Submit pull requests
- Use as a template for your own projects

---

## 📄 License

MIT License - feel free to use this project for learning or commercial purposes.

---

## 🙏 Acknowledgments

- **Groq** - Ultra-fast LLM inference
- **Meta** - Llama 3.3 model
- **OpenAI** - Whisper model architecture
- **Kokoro TTS** - Natural voice synthesis
- **LangChain** - RAG framework
- **FastAPI** - Modern Python web framework

---

## 📞 Support

- 📖 Check [START_HERE.md](START_HERE.md) for setup help
- ⚡ See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for commands
- 📊 Review [PROGRESS.md](PROGRESS.md) for roadmap
- 🐛 Open an issue for bugs

---

## 🎉 Status

**Part 1 (MVP): ✅ Complete**

All core features are implemented and working:
- ✅ Document upload and RAG pipeline
- ✅ Text chat with conversation memory
- ✅ Voice-to-voice interaction
- ✅ Modern responsive UI
- ✅ WebSocket streaming

**Ready for Part 2:** Multi-tenant SaaS features

---

<div align="center">

**Built with ❤️ using FastAPI, React, and cutting-edge AI**

[Get Started](START_HERE.md) • [Documentation](QUICK_REFERENCE.md) • [Roadmap](PROGRESS.md)

</div>
