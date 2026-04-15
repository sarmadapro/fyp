# 🏗️ System Architecture

## Overview

The Voice-to-Voice RAG AI Agent is built as a microservices architecture with three main layers:
1. **Frontend Layer** - React SPA for user interaction
2. **Backend Layer** - FastAPI orchestration and RAG pipeline
3. **AI Services Layer** - Specialized microservices for STT and TTS

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Browser                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │           React Frontend (Port 5173)                │    │
│  │                                                      │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │    │
│  │  │  Upload  │  │   Chat   │  │  Voice   │         │    │
│  │  │   Page   │  │   Page   │  │   Page   │         │    │
│  │  └──────────┘  └──────────┘  └──────────┘         │    │
│  │                                                      │    │
│  │  • React Router for navigation                      │    │
│  │  • useAudioRecorder hook for voice                  │    │
│  │  • API client for backend communication             │    │
│  └────────────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTP/WebSocket
                       │ (localhost:8000)
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  FastAPI Backend                             │
│                    (Port 8000)                               │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  API Layer                            │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │  │
│  │  │ Documents  │  │    Chat    │  │   Voice    │     │  │
│  │  │    API     │  │    API     │  │    API     │     │  │
│  │  └────────────┘  └────────────┘  └────────────┘     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │               Service Layer                           │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │  │
│  │  │ Document   │  │    Chat    │  │   Voice    │     │  │
│  │  │  Service   │  │  Service   │  │  Service   │     │  │
│  │  └────────────┘  └────────────┘  └────────────┘     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 RAG Pipeline                          │  │
│  │                                                        │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │  Document Processing                          │   │  │
│  │  │  • PyMuPDF (PDF extraction)                   │   │  │
│  │  │  • python-docx (DOCX extraction)              │   │  │
│  │  │  • RecursiveCharacterTextSplitter (chunking)  │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  │                                                        │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │  Embeddings & Vector Store                    │   │  │
│  │  │  • Sentence-Transformers (all-MiniLM-L6-v2)   │   │  │
│  │  │  • FAISS (similarity search)                  │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  │                                                        │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │  LLM Integration                              │   │  │
│  │  │  • Groq API (Llama 3.3 70B)                   │   │  │
│  │  │  • LangChain orchestration                    │   │  │
│  │  │  • Conversation history tracking              │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Data Storage                             │  │
│  │  • ./data/uploads/ (uploaded documents)              │  │
│  │  • ./data/indices/ (FAISS vector indices)            │  │
│  │  • In-memory conversation history (Part 1)           │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────┬─────────────────────────┬────────────────────┘
               │                         │
               │ HTTP                    │ HTTP
               │ (localhost:8001)        │ (localhost:8002)
               │                         │
               ▼                         ▼
┌──────────────────────┐    ┌──────────────────────┐
│  STT Microservice    │    │  TTS Microservice    │
│    (Port 8001)       │    │    (Port 8002)       │
│                      │    │                      │
│  ┌────────────────┐ │    │  ┌────────────────┐ │
│  │ Faster-Whisper │ │    │  │   Kokoro-82M   │ │
│  │   large-v3     │ │    │  │  Natural Voice │ │
│  └────────────────┘ │    │  └────────────────┘ │
│                      │    │                      │
│  Features:           │    │  Features:           │
│  • VAD filtering     │    │  • Streaming output  │
│  • Multi-format      │    │  • Multiple voices   │
│  • Auto language     │    │  • WAV format        │
│  • Lazy loading      │    │  • Low latency       │
│                      │    │                      │
│  Audio → Text        │    │  Text → Audio        │
└──────────────────────┘    └──────────────────────┘
```

---

## Component Details

### 1. Frontend Layer (React + Vite)

**Technology Stack:**
- React 19.2.4
- Vite 8.0.4
- React Router 7.14.1
- Lucide Icons
- React Hot Toast

**Key Components:**

```
frontend/src/
├── pages/
│   ├── UploadPage.jsx      # Document upload interface
│   ├── ChatPage.jsx        # Text chat interface
│   └── VoicePage.jsx       # Voice interaction interface
├── hooks/
│   └── useAudioRecorder.js # Audio recording logic
├── api/
│   └── client.js           # Backend API client
├── App.jsx                 # Main app with routing
└── main.jsx                # Entry point
```

**Responsibilities:**
- User interface rendering
- Audio recording via MediaRecorder API
- File upload handling
- WebSocket connections (ready for streaming)
- State management
- Error handling and user feedback

---

### 2. Backend Layer (FastAPI)

**Technology Stack:**
- FastAPI 0.115.12
- Uvicorn (ASGI server)
- LangChain 0.3.24
- Sentence-Transformers 4.1.0
- FAISS 1.11.0
- PyMuPDF, python-docx

**Key Components:**

```
backend/
├── main.py                 # FastAPI app entry point
├── app/
│   ├── api/
│   │   ├── documents.py    # Document management endpoints
│   │   ├── chat.py         # Chat endpoints
│   │   └── voice.py        # Voice endpoints
│   ├── services/
│   │   ├── document_service.py  # Document processing logic
│   │   ├── chat_service.py      # RAG chat logic
│   │   └── voice_service.py     # Voice orchestration
│   ├── models/
│   │   └── schemas.py      # Pydantic request/response models
│   └── core/
│       └── config.py       # Configuration management
└── data/
    ├── uploads/            # Uploaded documents
    └── indices/            # FAISS vector indices
```

**Responsibilities:**
- API endpoint handling
- Document text extraction
- Text chunking and embedding
- FAISS index management
- RAG pipeline orchestration
- Conversation history tracking
- Microservice coordination

---

### 3. AI Services Layer

#### STT Service (Faster-Whisper)

**Technology Stack:**
- FastAPI
- Faster-Whisper
- Model: large-v3

**Endpoint:**
- `POST /transcribe` - Convert audio to text

**Features:**
- Voice Activity Detection (VAD)
- Multi-format support (WAV, WebM, MP3, OGG, FLAC)
- Automatic language detection
- Optimized for latency (beam_size=5, int8 compute)

#### TTS Service (Kokoro)

**Technology Stack:**
- FastAPI
- Kokoro TTS
- Model: Kokoro-82M

**Endpoints:**
- `POST /synthesize` - Convert text to audio
- `POST /synthesize/stream` - Streaming synthesis

**Features:**
- Natural voice synthesis
- Multiple voice options
- Streaming support for low latency
- WAV audio output

---

## Data Flow Diagrams

### Document Upload Flow

```
┌──────┐
│ User │
└───┬──┘
    │ 1. Select file (PDF/TXT/DOCX)
    ▼
┌─────────────┐
│  Frontend   │
└──────┬──────┘
       │ 2. POST /document/upload (multipart/form-data)
       ▼
┌─────────────────────┐
│  Backend API        │
│  (documents.py)     │
└──────┬──────────────┘
       │ 3. Save file to ./data/uploads/
       ▼
┌─────────────────────┐
│  Document Service   │
└──────┬──────────────┘
       │ 4. Extract text (PyMuPDF/python-docx)
       │ 5. Split into chunks (RecursiveCharacterTextSplitter)
       │ 6. Generate embeddings (Sentence-Transformers)
       │ 7. Create FAISS index
       │ 8. Save index to ./data/indices/
       ▼
┌─────────────┐
│  Response   │ {"message": "Document uploaded", "filename": "..."}
└─────────────┘
```

### Text Chat Flow

```
┌──────┐
│ User │
└───┬──┘
    │ 1. Type question
    ▼
┌─────────────┐
│  Frontend   │
└──────┬──────┘
       │ 2. POST /chat {"question": "...", "conversation_id": "..."}
       ▼
┌─────────────────────┐
│  Backend API        │
│  (chat.py)          │
└──────┬──────────────┘
       │ 3. Forward to Chat Service
       ▼
┌─────────────────────┐
│  Chat Service       │
└──────┬──────────────┘
       │ 4. Query FAISS for relevant chunks
       ▼
┌─────────────────────┐
│  Document Service   │
│  (similarity_search)│
└──────┬──────────────┘
       │ 5. Return top-k chunks with scores
       ▼
┌─────────────────────┐
│  Chat Service       │
└──────┬──────────────┘
       │ 6. Format context with chunks
       │ 7. Build prompt with conversation history
       │ 8. Call Groq LLM (Llama 3.3 70B)
       ▼
┌─────────────────────┐
│  Groq API           │
└──────┬──────────────┘
       │ 9. Return generated answer
       ▼
┌─────────────────────┐
│  Chat Service       │
└──────┬──────────────┘
       │ 10. Update conversation history
       │ 11. Return answer
       ▼
┌─────────────┐
│  Frontend   │ Display answer in chat bubble
└─────────────┘
```

### Voice Chat Flow

```
┌──────┐
│ User │
└───┬──┘
    │ 1. Record audio (MediaRecorder API)
    ▼
┌─────────────┐
│  Frontend   │
└──────┬──────┘
       │ 2. POST /voice/chat (audio blob)
       ▼
┌─────────────────────┐
│  Backend API        │
│  (voice.py)         │
└──────┬──────────────┘
       │ 3. Forward to Voice Service
       ▼
┌─────────────────────┐
│  Voice Service      │
└──────┬──────────────┘
       │ 4. POST /transcribe (audio)
       ▼
┌─────────────────────┐
│  STT Service        │
│  (Port 8001)        │
└──────┬──────────────┘
       │ 5. Transcribe audio → text
       ▼
┌─────────────────────┐
│  Voice Service      │
└──────┬──────────────┘
       │ 6. Send text through RAG pipeline
       ▼
┌─────────────────────┐
│  Chat Service       │
│  (same as text chat)│
└──────┬──────────────┘
       │ 7. Return answer text
       ▼
┌─────────────────────┐
│  Voice Service      │
└──────┬──────────────┘
       │ 8. POST /synthesize (text)
       ▼
┌─────────────────────┐
│  TTS Service        │
│  (Port 8002)        │
└──────┬──────────────┘
       │ 9. Synthesize text → audio (WAV)
       ▼
┌─────────────────────┐
│  Voice Service      │
└──────┬──────────────┘
       │ 10. Return {transcription, answer, audio_base64}
       ▼
┌─────────────┐
│  Frontend   │ Display transcription, answer, play audio
└─────────────┘
```

---

## Technology Integration

### RAG Pipeline Details

```
┌─────────────────────────────────────────────────────────┐
│                    RAG Pipeline                          │
│                                                          │
│  1. Document Ingestion                                   │
│     ┌──────────────────────────────────────────┐       │
│     │ Text Extraction                           │       │
│     │ • PyMuPDF for PDF                         │       │
│     │ • python-docx for DOCX                    │       │
│     │ • Direct read for TXT                     │       │
│     └──────────────────────────────────────────┘       │
│                      ↓                                   │
│  2. Text Chunking                                        │
│     ┌──────────────────────────────────────────┐       │
│     │ RecursiveCharacterTextSplitter            │       │
│     │ • chunk_size: 500 characters              │       │
│     │ • chunk_overlap: 50 characters            │       │
│     │ • Preserves semantic boundaries           │       │
│     └──────────────────────────────────────────┘       │
│                      ↓                                   │
│  3. Embedding Generation                                 │
│     ┌──────────────────────────────────────────┐       │
│     │ Sentence-Transformers                     │       │
│     │ • Model: all-MiniLM-L6-v2                 │       │
│     │ • 384-dimensional vectors                 │       │
│     │ • Fast, quality embeddings                │       │
│     └──────────────────────────────────────────┘       │
│                      ↓                                   │
│  4. Vector Storage                                       │
│     ┌──────────────────────────────────────────┐       │
│     │ FAISS Index                               │       │
│     │ • IndexFlatL2 (exact search)              │       │
│     │ • Persisted to disk                       │       │
│     │ • Fast similarity search                  │       │
│     └──────────────────────────────────────────┘       │
│                      ↓                                   │
│  5. Retrieval (Query Time)                               │
│     ┌──────────────────────────────────────────┐       │
│     │ Similarity Search                         │       │
│     │ • Embed user question                     │       │
│     │ • Search FAISS for top-k chunks           │       │
│     │ • Return chunks with scores               │       │
│     └──────────────────────────────────────────┘       │
│                      ↓                                   │
│  6. Context Formatting                                   │
│     ┌──────────────────────────────────────────┐       │
│     │ Prompt Engineering                        │       │
│     │ • Format retrieved chunks                 │       │
│     │ • Add conversation history                │       │
│     │ • Build system prompt                     │       │
│     └──────────────────────────────────────────┘       │
│                      ↓                                   │
│  7. LLM Generation                                       │
│     ┌──────────────────────────────────────────┐       │
│     │ Groq API (Llama 3.3 70B)                  │       │
│     │ • Ultra-fast inference                    │       │
│     │ • Context-aware generation                │       │
│     │ • Temperature: 0.3 (focused)              │       │
│     └──────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

---

## Scalability Considerations

### Current Architecture (Part 1 - MVP)

**Strengths:**
- Simple deployment (4 services)
- No external dependencies (except Groq API)
- Fast local development
- Easy to understand and debug

**Limitations:**
- Single-user (no multi-tenancy)
- In-memory conversation history
- No authentication
- No database
- Local file storage only

### Future Architecture (Part 2+)

**Planned Enhancements:**
- PostgreSQL for data persistence
- JWT authentication
- Multi-tenant data isolation
- Redis for caching and rate limiting
- S3/Cloud storage for documents
- Horizontal scaling with load balancer
- Monitoring and logging (Prometheus, Grafana)

---

## Security Architecture

### Current Security (Part 1)

✅ **Implemented:**
- CORS configuration
- File type validation
- File size limits
- Input sanitization (Pydantic)
- Error handling without exposing internals

⚠️ **Not Yet Implemented (Part 2):**
- Authentication/Authorization
- API rate limiting
- Request signing
- Encryption at rest
- Audit logging

---

## Performance Optimization

### Current Optimizations

1. **Async Operations**
   - FastAPI async endpoints
   - httpx async client for microservices
   - Non-blocking I/O

2. **Model Loading**
   - Lazy loading (on first request)
   - Model caching in memory
   - Reuse across requests

3. **Vector Search**
   - FAISS IndexFlatL2 (exact, fast)
   - Limited top-k results (default: 5)
   - Efficient similarity computation

4. **Audio Processing**
   - Streaming TTS synthesis
   - WebSocket for real-time voice
   - Optimized audio formats

### Performance Targets

- Document upload: < 5 seconds
- Text chat response: < 2 seconds
- Voice transcription: < 3 seconds
- Voice synthesis: < 2 seconds
- End-to-end voice: < 5 seconds

---

## Deployment Architecture (Future)

```
┌─────────────────────────────────────────────────────────┐
│                    Cloud Provider                        │
│                  (AWS/GCP/Azure)                         │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │              Load Balancer                      │    │
│  └──────────────────┬─────────────────────────────┘    │
│                     │                                    │
│         ┌───────────┼───────────┐                       │
│         ▼           ▼           ▼                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │ Backend  │ │ Backend  │ │ Backend  │               │
│  │Instance 1│ │Instance 2│ │Instance 3│               │
│  └──────────┘ └──────────┘ └──────────┘               │
│         │           │           │                       │
│         └───────────┼───────────┘                       │
│                     │                                    │
│         ┌───────────┼───────────┐                       │
│         ▼           ▼           ▼                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │   STT    │ │   TTS    │ │PostgreSQL│               │
│  │ Service  │ │ Service  │ │ Database │               │
│  │  (GPU)   │ │  (GPU)   │ │          │               │
│  └──────────┘ └──────────┘ └──────────┘               │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │              Object Storage (S3)                │    │
│  │  • Documents                                    │    │
│  │  • FAISS indices                                │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │              Monitoring                         │    │
│  │  • Prometheus (metrics)                         │    │
│  │  • Grafana (dashboards)                         │    │
│  │  • CloudWatch/Stackdriver (logs)                │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## Summary

The Voice-to-Voice RAG AI Agent uses a clean, modular architecture that:

✅ Separates concerns (frontend, backend, AI services)  
✅ Enables independent scaling of components  
✅ Provides clear data flow and responsibilities  
✅ Uses modern, proven technologies  
✅ Is ready for production enhancements (Part 2+)

**Current Status:** Part 1 Complete - All components working together seamlessly.
