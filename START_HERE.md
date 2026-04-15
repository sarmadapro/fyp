# 🚀 Voice-to-Voice RAG AI Agent — Quick Start Guide

## 📋 Prerequisites

- Python 3.10+ installed
- Node.js 18+ installed
- Groq API key (get one free at https://console.groq.com)

---

## 🔧 Setup Instructions

### 1. Configure Environment Variables

Copy the example environment file and add your Groq API key:

```bash
cp .env.example .env
```

Then edit `.env` and add your `GROQ_API_KEY`:
```
GROQ_API_KEY=your_actual_groq_api_key_here
```

### 2. Install Backend Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

### 3. Install STT Service Dependencies

```bash
cd services/stt
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ../..
```

### 4. Install TTS Service Dependencies

```bash
cd services/tts
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ../..
```

### 5. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

---

## 🎬 Running the Application

You need to run **4 services** in separate terminal windows:

### Terminal 1: Backend (Port 8000)
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python main.py
```

### Terminal 2: STT Service (Port 8001)
```bash
cd services/stt
source venv/bin/activate  # On Windows: venv\Scripts\activate
python main.py
```

### Terminal 3: TTS Service (Port 8002)
```bash
cd services/tts
source venv/bin/activate  # On Windows: venv\Scripts\activate
python main.py
```

### Terminal 4: Frontend (Port 5173)
```bash
cd frontend
npm run dev
```

---

## 🧪 Testing the Application

1. **Open your browser** to http://localhost:5173

2. **Upload a Document**
   - Click "Upload" in the navigation
   - Drag and drop a PDF, TXT, or DOCX file
   - Wait for processing to complete

3. **Test Text Chat**
   - Click "Chat" in the navigation
   - Type a question about your document
   - Verify you get a relevant answer

4. **Test Voice Chat**
   - Click "Voice" in the navigation
   - Click the microphone button to start recording
   - Ask a question about your document
   - Click again to stop recording
   - Wait for the AI to respond with voice

---

## 🔍 Health Check

Verify all services are running:

- Backend: http://localhost:8000/health
- STT Service: http://localhost:8001/health
- TTS Service: http://localhost:8002/health
- Frontend: http://localhost:5173

---

## 🐛 Troubleshooting

### "GROQ_API_KEY not found" error
- Make sure you copied `.env.example` to `.env`
- Add your actual Groq API key to the `.env` file

### STT/TTS service fails to start
- First run may take time to download models
- Check that you have enough disk space (~5GB for models)
- On Windows, TTS uses `espeakng-loader` which downloads espeak-ng automatically

### Frontend can't connect to backend
- Verify all 3 backend services are running (ports 8000, 8001, 8002)
- Check CORS settings in `.env` match your frontend URL

### Voice recording doesn't work
- Grant microphone permissions in your browser
- Use HTTPS or localhost (required for microphone access)
- Try a different browser (Chrome/Edge recommended)

---

## 📊 What's Next?

Now that Part 1 (MVP) is complete, you can:

1. **Test the system thoroughly** with different documents and questions
2. **Move to Part 2** to add multi-tenant SaaS features (database, auth, client portal)
3. **Move to Part 3** to upgrade the UI with premium design
4. **Move to Part 4** to deploy to production

See `PROGRESS.md` for the complete roadmap.

---

## 🎯 Current Architecture

```
┌─────────────────┐
│  React Frontend │  (Port 5173)
│   (Vite + UI)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI Backend│  (Port 8000)
│  (RAG + Groq)   │
└────┬────────┬───┘
     │        │
     ▼        ▼
┌─────────┐ ┌─────────┐
│   STT   │ │   TTS   │
│ Service │ │ Service │
│ (8001)  │ │ (8002)  │
└─────────┘ └─────────┘
```

Happy building! 🎉
