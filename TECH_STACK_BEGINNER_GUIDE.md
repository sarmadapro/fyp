# VoiceRAG Technology Stack - Beginner's Detailed Guide

A comprehensive explanation of every technology used in the project, what it does, and how it works together.

---

## Table of Contents

1. [Backend Framework - FastAPI](#1-backend-framework---fastapi)
2. [Database - PostgreSQL & SQLAlchemy](#2-database---postgresql--sqlalchemy)
3. [Authentication - JWT & bcrypt](#3-authentication---jwt--bcrypt)
4. [RAG Foundation - Embeddings](#4-rag-foundation---embeddings)
5. [Vector Search - FAISS](#5-vector-search---faiss)
6. [Re-ranking - BGE](#6-re-ranking---bge)
7. [Large Language Models - LLM Stack](#7-large-language-models---llm-stack)
8. [Speech-to-Text - Whisper](#8-speech-to-text---whisper)
9. [Text-to-Speech - Kokoro & Edge-TTS](#9-text-to-speech---kokoro--edge-tts)
10. [Frontend - React & Vite](#10-frontend---react--vite)
11. [Containerization - Docker & Compose](#11-containerization---docker--compose)
12. [How They Work Together](#12-how-they-work-together)

---

## 1. Backend Framework - FastAPI

### What is FastAPI?

**FastAPI** is a modern Python web framework used to build REST APIs (web services that handle requests/responses over HTTP).

### Why Does It Exist?

Before FastAPI:
- Older frameworks like Flask or Django were slow at handling many simultaneous requests
- Building APIs required writing a lot of boilerplate code
- Type-checking and automatic documentation were difficult

FastAPI solves these problems with:
- **Async/Await support** - Handle thousands of requests simultaneously without blocking
- **Automatic validation** - Check if incoming data is correct
- **Auto-generated documentation** - Swagger UI appears automatically at `/docs`
- **Type hints** - Python code that's easier to understand and debug

### How Does It Work?

```
Client sends HTTP request
    ↓
FastAPI receives request at a "route" (e.g., POST /chat)
    ↓
Route handler function processes request (async = can handle other requests while waiting)
    ↓
Function returns JSON response
    ↓
Client receives response
```

### Example:
```python
from fastapi import FastAPI

app = FastAPI()

@app.post("/chat")
async def chat(question: str):
    # This function is "async" - FastAPI can handle other requests while this runs
    # If this function takes 5 seconds to respond, FastAPI can handle 100 other requests simultaneously
    answer = "Your response"
    return {"response": answer}
```

### How VoiceRAG Uses FastAPI

**Purpose:** Backend API server that handles all requests from frontend and mobile apps

**Used for:**
1. **Authentication endpoints** (`/auth/login`, `/auth/register`)
   - User logs in → FastAPI validates email/password → Returns JWT token

2. **Chat endpoints** (`/portal/chat`)
   - User asks question → FastAPI searches documents → Returns AI response
   - Uses async to handle multiple users asking questions simultaneously

3. **Voice endpoints** (`/voice/conversation` WebSocket)
   - Real-time voice streaming from client
   - FastAPI receives audio chunks → sends to STT service → searches documents → sends TTS response
   - Async streaming makes this possible without blocking

4. **Document upload** (`/portal/document/upload`)
   - User uploads PDF → FastAPI extracts text → Creates embeddings → Saves to database
   - Async processing prevents the server from freezing during heavy indexing

5. **Admin panel** (`/admin/stats`, `/admin/users`)
   - Returns platform statistics (total users, API calls, etc.)

**Why Async Matters in VoiceRAG:**
- Without async: If one user's voice transcription takes 5 seconds, all other users must wait
- With async: FastAPI handles other users while transcription is happening

---

## 2. Database - PostgreSQL & SQLAlchemy

### What is a Database?

A **database** is organized storage for your application's data (users, documents, conversations, etc.).

Think of it like a spreadsheet, but:
- Millions of rows (not just 1000s)
- Structured (columns have types: number, text, date, etc.)
- Query language (SQL) to find/update data

### PostgreSQL vs SQLite

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| **Use case** | Development, simple apps | Production, multi-user |
| **Capacity** | ~1GB optimal | Terabytes |
| **Concurrent users** | 1-2 | 1000+ |
| **Cost** | Free | Free |
| **Setup** | One file on disk | Separate server |

**VoiceRAG uses:** SQLite for development (easier), PostgreSQL for production (scalable)

### Example Database Schema (Simplified)

```
USERS TABLE (stores customer info)
┌─────────────────────────────────────────┐
│ id  │ email           │ password_hash   │
├─────┼─────────────────┼─────────────────┤
│ 1   │ user@gmail.com  │ bcrypt_hash_... │
│ 2   │ company@biz.com │ bcrypt_hash_... │
└─────────────────────────────────────────┘

DOCUMENTS TABLE (stores uploaded files)
┌──────────────────────────────────────────────┐
│ id  │ user_id │ filename       │ chunk_count │
├─────┼─────────┼────────────────┼─────────────┤
│ 1   │ 1       │ research.pdf   │ 45          │
│ 2   │ 2       │ guide.docx     │ 23          │
└──────────────────────────────────────────────┘

CONVERSATIONS TABLE (stores chat history)
┌──────────────────────────────────────────────┐
│ id  │ user_id │ question      │ response     │
├─────┼─────────┼───────────────┼──────────────┤
│ 1   │ 1       │ What is AI?    │ AI is...     │
│ 2   │ 1       │ Tell me more   │ More details │
└──────────────────────────────────────────────┘
```

### What is SQLAlchemy?

**SQLAlchemy** is a "bridge" between Python code and the database.

**Without SQLAlchemy:**
```python
# Writing raw SQL (error-prone)
result = db.execute("SELECT * FROM users WHERE id = 1")
```

**With SQLAlchemy (ORM):**
```python
# Python objects (type-safe, easier to read)
user = User.query.filter(User.id == 1).first()
print(user.email)  # Can see properties autocomplete in IDE
```

Benefits:
- Write Python code instead of SQL strings
- Automatic error checking
- Works with any database (PostgreSQL, MySQL, SQLite)
- IDE can auto-complete property names

### How VoiceRAG Uses Databases

**Data stored:**

1. **Users/Clients**
   - Email, password (hashed), company name, is_admin flag
   - Purpose: Authentication & multi-tenant isolation

2. **API Keys**
   - Key hash, creation date, last used
   - Purpose: Widget authentication (3rd-party websites)

3. **Documents**
   - Filename, file type, upload date, chunk count, client_id
   - Purpose: Track what documents each user uploaded

4. **Conversations**
   - User question, AI response, timestamp, latency metrics, language
   - Purpose: Chat history & analytics

5. **Refresh Tokens**
   - Token hash, user_id, expiry date
   - Purpose: Keep user logged in for 7 days

**Multi-tenant isolation (crucial):**
```python
# Every database query includes the current user's ID
# So User A's documents are never returned to User B

@app.get("/documents")
async def get_documents(current_user: User):
    # Query: "Get documents WHERE user_id = current_user.id"
    # User B's documents are excluded automatically
    return db.query(Document).filter(Document.user_id == current_user.id)
```

---

## 3. Authentication - JWT & bcrypt

### The Problem: How Does Server Know User is Logged In?

**Scenario:**
1. User logs in with email/password
2. User asks question via frontend
3. Server must know: "Is this actually the logged-in user?"

Without authentication, anyone could pretend to be anyone else.

### How Authentication Works (Traditional)

**Traditional Session-Based (Old way):**
```
1. User logs in
2. Server: "You are user#123" → stores in session (server memory)
3. Server gives user a session_id cookie
4. User sends cookie with every request
5. Server checks: "Does this session_id exist?" → If yes, allow

Problem: Server must store all active sessions (memory/disk)
If you have 1 million users, server is full of session data
```

### JWT (Modern Way) - Used by VoiceRAG

**JWT = JSON Web Token**

Instead of server storing session data, the token itself contains the data.

**How it works:**

```
1. User logs in with email/password
   ↓
2. Server creates a token:
   {
     "user_id": 123,
     "email": "user@gmail.com",
     "exp": 1713610000  (expires in 30 minutes)
   }
   
   Server "signs" this token with a secret key
   (Server: "I created this token, if you receive an unsigned copy, it's fake")
   
   Token becomes: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjN9.signature123"
   ↓
3. Server returns token to client
   Client stores in localStorage (browser's local storage)
   ↓
4. User asks question
   Client sends: Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjN9.signature123
   ↓
5. Server receives token
   Server "decodes" it (checks signature is valid)
   If signature is valid → "This token is legitimate, I created it"
   Extract user_id = 123
   ↓
6. Server knows this is user#123, allows request
```

**JWT Structure (simplified):**
```
eyJhbGciOiJIUzI1NiJ9  .  eyJ1c2VyX2lkIjoxMjN9  .  signature123
   (header)             (data/payload)              (proof of authenticity)
```

**VoiceRAG JWT contains:**
```json
{
  "user_id": 123,
  "email": "company@example.com",
  "exp": 1713610000  // 30 minutes from now
}
```

### bcrypt - Hashing Passwords

**The Problem:**
If you store passwords as plain text in database:
- Hackers steal database → they have all passwords
- Users reuse passwords → hackers can log into their bank accounts

**Solution: Hash passwords**

A "hash" is a one-way encryption:
```
password: "MyPassword123"
hash: "$2b$12$8qI5rFUVUP5..." (always same for same password)

Key point: Cannot reverse hash back to password
```

**How bcrypt works:**

```
1. User registers with password "MyPassword123"
2. bcrypt: "MyPassword123" → "$2b$12$8qI5rFUVUP5..."
3. Store hash in database (password is gone forever)

4. User logs in, enters password "MyPassword123"
5. bcrypt: "MyPassword123" → "$2b$12$8qI5rFUVUP5..."
6. Compare with stored hash
7. Hashes match? → Password is correct!
```

**Even if database is stolen:**
- Hacker sees: "$2b$12$8qI5rFUVUP5..."
- Cannot reverse it back to "MyPassword123"
- bcrypt is intentionally slow (takes ~100ms per check) to prevent brute-force guessing

### How VoiceRAG Uses JWT & bcrypt

**Registration Flow:**
```
1. User enters email + password
2. FastAPI endpoint: POST /auth/register
3. Code:
   hashed_pwd = bcrypt.hash("password123")  // Hashing happens
   db.save(User(email="user@gmail.com", password=hashed_pwd))
   
   token = create_jwt_token(user_id=123)  // JWT created
   return {"access_token": token}

4. Frontend stores token in localStorage
```

**Login Flow:**
```
1. User enters email + password
2. FastAPI endpoint: POST /auth/login
3. Code:
   user = db.query(User).filter(User.email == "user@gmail.com")
   
   if bcrypt.verify("password123", user.password):  // Verify password
       token = create_jwt_token(user_id=user.id)  // Create JWT
       return {"access_token": token}

4. Frontend stores token
```

**Using JWT for Subsequent Requests:**
```
1. User asks question
2. Frontend sends: Authorization: Bearer eyJ...
3. FastAPI extracts token
4. Code:
   current_user = verify_jwt_token(token)  // Decode & verify signature
   # Now current_user = User(id=123, email="...")
   
   # Fetch only this user's documents
   docs = db.query(Document).filter(Document.user_id == current_user.id)
   return {"documents": docs}

5. Multi-tenant isolation: Each user only sees their own data
```

**Refresh Token (Keep User Logged In):**
```
Access token expires in 30 minutes (security)
Refresh token expires in 7 days (convenience)

Flow:
1. User logs in → gets access_token (30min) + refresh_token (7 days)
2. After 25 minutes, access_token is still valid
3. After 31 minutes, access_token is expired
4. Frontend uses refresh_token to get new access_token
5. User doesn't need to log in again

Location:
- access_token: localStorage (JavaScript can access)
- refresh_token: HTTP-only cookie (JavaScript cannot access - safer!)
```

---

## 4. RAG Foundation - Embeddings

### What is RAG?

**RAG = Retrieval-Augmented Generation**

**Traditional LLM Problem:**
```
You: "What was the GDP of my company in 2023?"
LLM: "I don't know. I'm trained on data until 2023, but not your company."

You: "What does Chapter 5 of my research paper say?"
LLM: "I don't have access to your files."
```

**Solution: RAG**
```
1. User uploads documents → System reads & indexes them
2. User asks question
3. System finds relevant parts of documents
4. System gives those parts to LLM: "Here are relevant documents. Answer based on this."
5. LLM generates answer from your documents (not from training data)

Result: AI knows about YOUR documents
```

### What are Embeddings?

**Embeddings** = Converting text into numbers (vectors).

**Why?**
- Computers are good at comparing numbers, bad at comparing text
- "What does this question have in common with that document?"
- Need numbers to answer that

### Example: Converting Text to Embeddings

```
Word: "apple"
Embedding: [0.2, -0.5, 0.8, 0.1, -0.3, ...]  (384 numbers)

Word: "orange"
Embedding: [0.21, -0.48, 0.82, 0.09, -0.31, ...]  (384 numbers, similar to "apple")

Word: "car"
Embedding: [0.9, 0.1, -0.7, 0.2, 0.5, ...]  (384 numbers, different from "apple")
```

**Why similar?**
- "apple" and "orange" are both fruits → embeddings are similar
- "apple" and "car" are different → embeddings are different

### The Embedding Model

VoiceRAG uses: **Sentence-Transformers (all-MiniLM-L6-v2)**

```
Input: "What are the benefits of exercise?"
    ↓
Model processes text (neural network)
    ↓
Output: [0.12, -0.34, 0.56, ..., 0.89]  (384 numbers)
```

**Pre-trained model = Model that already learned from millions of text examples**
- You don't train it (takes months)
- You just use it
- It's good at understanding text similarity

### How Embeddings Work in RAG

```
DOCUMENT INDEXING (One-time, during upload):

User uploads PDF with text:
"Apple is a fruit. It's red or green."
"Orange is also a fruit."
"Car is a vehicle."

Split into chunks (smaller pieces):
Chunk 1: "Apple is a fruit. It's red or green."
Chunk 2: "Orange is also a fruit."
Chunk 3: "Car is a vehicle."

Convert each chunk to embedding:
Chunk 1 → [0.2, -0.5, 0.8, ...]
Chunk 2 → [0.21, -0.48, 0.82, ...]
Chunk 3 → [0.9, 0.1, -0.7, ...]

Store embeddings + original text
```

```
SEARCH (When user asks question):

User question: "What are fruits?"
    ↓
Convert to embedding: [0.19, -0.49, 0.81, ...]
    ↓
Compare with stored chunks:
    Chunk 1 embedding: [0.2, -0.5, 0.8, ...]    similarity: 0.99 ✓ (very similar)
    Chunk 2 embedding: [0.21, -0.48, 0.82, ...] similarity: 0.98 ✓ (very similar)
    Chunk 3 embedding: [0.9, 0.1, -0.7, ...]    similarity: 0.1 ✗ (not similar)
    ↓
Return Chunk 1 and Chunk 2 to LLM
    ↓
LLM reads: "Apple is a fruit... Orange is also a fruit..."
LLM generates: "Apples and oranges are fruits."
```

### Similarity Measurement

How do you compare two embedding vectors?

**Cosine Similarity:**
```
Chunk 1 embedding: [0.2, -0.5, 0.8]
Question embedding: [0.19, -0.49, 0.81]

Formula: Dot product / (magnitude A * magnitude B)
Result: 0.99 (means 99% similar)
```

Think of it like angles:
- Same direction (parallel) = 1.0 = 100% similar
- Opposite direction = -1.0 = completely opposite
- Perpendicular = 0.0 = unrelated

### How VoiceRAG Uses Embeddings

**On Document Upload:**
```python
def upload_document(pdf_file):
    # 1. Extract text from PDF
    text = extract_text(pdf_file)
    
    # 2. Split into chunks (1000 characters each)
    chunks = split_text(text, chunk_size=1000)
    
    # 3. Convert each chunk to embedding
    embeddings = []
    for chunk in chunks:
        embedding = model.encode(chunk)  # [384 numbers]
        embeddings.append(embedding)
    
    # 4. Store embeddings + text in database
    save_to_database(embeddings, chunks)
    
    return "Document indexed and ready for search"
```

**On Chat Question:**
```python
def answer_question(question: str):
    # 1. Convert question to embedding
    question_embedding = model.encode(question)  # [384 numbers]
    
    # 2. Find similar chunks (FAISS search - explained next)
    similar_chunks = faiss.search(question_embedding, top_k=40)
    
    # 3. Re-rank to get top 5 (explained later)
    top_5_chunks = rerank(similar_chunks)
    
    # 4. Give to LLM
    context = "\n\n".join(top_5_chunks)
    prompt = f"Based on:\n{context}\n\nAnswer: {question}"
    response = llm.generate(prompt)
    
    return response
```

---

## 5. Vector Search - FAISS

### The Problem: Finding Similar Documents is Slow

**Without FAISS:**
```
User asks question
User's question embedding: [0.2, -0.5, 0.8, ...]

Compare with ALL stored chunks:
Chunk 1: compute similarity (0.001 seconds)
Chunk 2: compute similarity (0.001 seconds)
Chunk 3: compute similarity (0.001 seconds)
...
Chunk 100,000: compute similarity (0.001 seconds)

Total: 100 seconds for 100,000 chunks!
User waits 100 seconds. Bad experience.
```

### FAISS Solution

**FAISS = Facebook AI Similarity Search**

Instead of comparing with all chunks, use indexing:
- Like a book's index (find "apples" → page 45, not read every page)
- Organize embeddings intelligently
- Find similar ones in milliseconds

### How FAISS Works

**Simple Version (not actual algorithm):**

Imagine all embeddings as points in 3D space:

```
    Chunk 1
    /
   /
  /_________ Chunk 2
 /
/
Question (search point)

Find chunks closest to question point = find similar chunks
```

FAISS builds a structure (tree-like) to organize points:
- "These chunks are near each other in space"
- When searching, prune impossible branches
- Only check nearby points

### How VoiceRAG Uses FAISS

**Setup (one-time):**
```python
import faiss
import numpy as np

# 1. Prepare all embeddings
all_embeddings = [
    [0.2, -0.5, 0.8, ...],  # Chunk 1 embedding
    [0.21, -0.48, 0.82, ...],  # Chunk 2 embedding
    ...
    [0.9, 0.1, -0.7, ...],  # Chunk 100,000 embedding
]

# 2. Create index
index = faiss.IndexFlatL2(384)  # 384 = embedding dimension
index.add(np.array(all_embeddings).astype('float32'))

# 3. Save for later
faiss.write_index(index, "faiss_index.bin")
```

**Search (during chat):**
```python
# 1. Load index
index = faiss.read_index("faiss_index.bin")

# 2. Get question embedding
question = "What is AI?"
question_embedding = model.encode(question)  # [384 numbers]

# 3. Search for top 40 similar chunks
distances, indices = index.search(
    np.array([question_embedding]).astype('float32'),
    k=40  # Return top 40
)

# indices = [5, 23, 12, 44, ...]  (indices of top 40 chunks)
# distances = [0.1, 0.15, 0.18, ...]  (how different they are)

# 4. Retrieve actual text
top_40_chunks = [all_chunks[i] for i in indices[0]]

return top_40_chunks  # Pass to reranker next
```

**Per-Client Isolation:**
```python
# Each user (client) has separate FAISS index
# User A's index at: data/clients/user_A/faiss_index.bin
# User B's index at: data/clients/user_B/faiss_index.bin

# When User A asks question:
index_A = faiss.read_index(f"data/clients/{user_A_id}/faiss_index.bin")
results_A = index_A.search(question_embedding, k=40)
# Only searches User A's documents, not User B's
```

### Why 40 Chunks? Why not Stop Here?

FAISS finds the 40 closest embeddings, but:
- Embedding similarity ≠ actual relevance
- A chunk might be similar numerically but not actually answer the question
- Need a second filter: **Re-ranking** (next section)

---

## 6. Re-ranking - BGE

### The Problem: Embedding Similarity Isn't Enough

**Example:**

User question: "How much does your product cost?"

FAISS returns 40 similar chunks:
```
Chunk 1: "Our product costs $100/month"
         (Relevant! ✓)

Chunk 2: "We value transparency in pricing discussions"
         (Mentioned "price" but not actually the price ✗)

Chunk 3: "Cost-benefit analysis shows ROI of 3x"
         (Has "cost" but it's about ROI, not pricing ✗)

Chunk 4: "We don't have a free trial anymore"
         (About pricing but not relevant ✗)
```

Embedding similarity found all of these because they mention similar words.
But only Chunk 1 actually answers the question.

### BGE - Bi-Encoder for Ranking

**BGE = BAAI General Embedding**

Instead of just comparing vectors, BGE asks: "Does this really answer the question?"

```
BGE receives:
- Question: "How much does your product cost?"
- Chunk 1: "Our product costs $100/month"

BGE thinks:
"Does this chunk answer the question? 
 Yes! It gives the price."

Score: 0.95 (very relevant)
```

```
BGE receives:
- Question: "How much does your product cost?"
- Chunk 2: "We value transparency in pricing discussions"

BGE thinks:
"Does this chunk answer the question?
 No, it just mentions pricing."

Score: 0.2 (not relevant)
```

### How BGE Works

BGE is another neural network (pre-trained, like embeddings):

```
Input: (question, chunk) pair
    ↓
Neural network processes both
    ↓
Output: Score 0-1 (how well chunk answers question)
```

**Key difference from embeddings:**
- Embedding: "How similar are these texts?" (word-level)
- BGE: "Does this answer this?" (semantic understanding)

### How VoiceRAG Uses BGE

**Flow:**
```
1. FAISS returns top 40 chunks

2. For each of 40 chunks:
   score = bge_model.score(question, chunk)
   
   Example:
   Chunk 1 score: 0.95
   Chunk 2 score: 0.2
   Chunk 3 score: 0.3
   ...

3. Sort by score, keep top 5

4. Check if max score < 0.0:
   if max_score < 0.0:
       return "I don't have information about that"
   
   This prevents hallucination!
   
5. Pass top 5 to LLM
```

**Code in VoiceRAG:**
```python
def rank_chunks(question: str, chunks: list):
    # Load BGE model
    from sentence_transformers import CrossEncoder
    reranker = CrossEncoder('mmarco-MiniLMv2-L12-H384-v1')
    
    # Score each chunk
    scores = reranker.predict([[question, chunk] for chunk in chunks])
    
    # Sort by score
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    
    # Keep top 5
    top_5 = [chunk for chunk, score in ranked[:5]]
    
    # Check if any chunk is actually relevant
    if ranked[0][1] < 0.0:  # Score gate
        return None  # No relevant chunks found
    
    return top_5
```

### Why This Prevents Hallucination

**Without score gate:**
```
Question: "What is your company's secret recipe?"
Chunk 1 (score 0.3): "Our ingredients include flour and water"

BGE says: Not very relevant (0.3)
But LLM still gets it: "Based on this, I'll make something up"
Result: LLM hallucinates
```

**With score gate (VoiceRAG):**
```
Question: "What is your company's secret recipe?"
Chunk 1 (score 0.3): "Our ingredients include flour and water"

BGE says: Not relevant (0.3 < 0.0 threshold)
Return: "I don't have information about that"
Result: No hallucination
```

---

## 7. Large Language Models - LLM Stack

### What is an LLM?

**LLM = Large Language Model** (like ChatGPT)

A neural network trained on billions of text examples to predict the next word:

```
Input: "The capital of France is"
LLM: (thinks about patterns in training data)
Output: "Paris"
```

### Three LLM Options in VoiceRAG

| LLM | Speed | Cost | Location | Best For |
|-----|-------|------|----------|----------|
| **Groq** (llama-3.3-70b) | ⚡ ~800 tokens/sec | Cheap | Cloud API | Primary (fast) |
| **DeepSeek** | 🐌 ~100 tokens/sec | Ultra-cheap | Cloud API | Fallback (cheaper) |
| **Ollama** (local) | 🐢 ~5-20 tokens/sec | Free | Your computer | Fallback (offline) |

### Groq (Primary Choice)

**What is Groq?**

A cloud service that runs Llama LLM very fast.

**Why fast?**
- Custom hardware (LPU = Language Processing Unit, not GPU)
- Optimized for text generation
- 800 tokens/second (ChatGPT is ~100 tokens/second)

**Cost:**
- ~$0.0007 per 1000 tokens
- Compared to ChatGPT: ~$0.005 per 1000 tokens
- Groq is 7x cheaper and 8x faster!

### Ollama (Local Fallback)

**What is Ollama?**

Running an LLM on your own computer (offline, free).

**Tradeoff:**
- Slow (5-20 tokens/second on CPU)
- But free and works without internet
- Good fallback if Groq is down or rate-limited

```
Regular flow:
User asks → Try Groq (fast) → Success

Fallback flow (if Groq fails):
User asks → Groq fails → Try DeepSeek → Try Ollama (local)
Result: No user-facing outage
```

### How VoiceRAG Uses LLMs

**LLM Generation:**

```python
def generate_response(context: str, question: str):
    # 1. Create prompt with instructions + context + question
    prompt = f"""
    You are a helpful assistant. 
    Based on the following documents, answer the question.
    
    Documents:
    {context}
    
    Question: {question}
    
    Answer:
    """
    
    # 2. Try Groq first (fastest, cheapest)
    try:
        response = groq_client.generate(prompt, max_tokens=500)
        return response
    except RateLimitError:
        # Groq is rate-limited
        pass
    
    # 3. Try DeepSeek (fallback)
    try:
        response = deepseek_client.generate(prompt, max_tokens=500)
        return response
    except Exception:
        # DeepSeek is down
        pass
    
    # 4. Try Ollama (local, always works if installed)
    response = ollama_client.generate(prompt, max_tokens=500)
    return response
```

**Grounding Prompt (Prevent Hallucination):**

```
Standard prompt:
"What is AI?"
LLM: "AI is... [makes up stuff if not in training data]"

Grounding prompt (VoiceRAG):
"Based on the provided documents, answer: What is AI?
If the answer is not in the documents, say 'Not found in documents'"

LLM: "The documents say AI is... [only uses provided context]"
```

### Streaming Response

**Traditional:**
```
User: "Tell me about AI"
LLM generates full response: (takes 5 seconds)
LLM: "AI is..."
User sees nothing for 5 seconds, then full response appears

Bad user experience
```

**Streaming (VoiceRAG):**
```
User: "Tell me about AI"
LLM starts generating
After 0.5 seconds: "AI"
After 1 second: "AI is"
After 1.5 seconds: "AI is artificial"
...
After 5 seconds: full response

User sees words appearing in real-time
Better experience
```

---

## 8. Speech-to-Text - Whisper

### What is Speech-to-Text (STT)?

Converting spoken audio into text.

```
User speaks: "What is artificial intelligence?"
    ↓
Whisper model processes audio
    ↓
Output text: "What is artificial intelligence?"
```

### Whisper Model

**Whisper** = OpenAI's speech recognition model

Trained on 680,000 hours of multilingual audio:
- Understands 99 languages
- Handles background noise well
- Detects language automatically

### How Whisper Works

```
Input: Audio file (WAV, MP3, etc.)
    ↓
Pre-processing: Convert to 16kHz mono audio
    ↓
Encoder: Neural network listens to audio, creates representation
    ↓
Decoder: Generates text from representation
    ↓
Output: "What is artificial intelligence?"
```

### Faster-Whisper

VoiceRAG uses **Faster-Whisper** (optimized version of Whisper):

- Same accuracy as Whisper
- 4x faster
- 6x smaller model
- CUDA acceleration (uses GPU)

**Speed:**
- 10 seconds of audio → 400ms processing (with GPU)
- Without GPU (CPU): ~2-5 seconds

### How VoiceRAG Uses Whisper

**Architecture:**

```
Frontend (browser)
    ↓ Audio chunks via WebSocket
Backend (FastAPI)
    ↓ Send to STT service
STT Service (Faster-Whisper, port 8001)
    ↓ Convert to text
Backend (receives text)
    ↓ Send to RAG pipeline
```

**Flow:**

```python
# STT Service (services/stt/main.py)
from faster_whisper import WhisperModel

model = WhisperModel("large-v3", device="cuda", compute_type="int8")

@app.post("/transcribe")
async def transcribe(audio_file):
    # 1. Receive audio from backend
    # 2. Run through Whisper
    segments, info = model.transcribe(audio_file)
    # segments[0].text = "What is AI?"
    
    # 3. Return text + detected language
    return {
        "text": segments[0].text,
        "language": info.language,
        "confidence": segments[0].confidence
    }

# Backend receives text, sends to RAG
```

**Voice Activity Detection (VAD):**

Problem: User speaks, then pauses for breath, then speaks again.
- Do we transcribe after each word? No, too many interruptions.
- Do we wait until user finishes? How to know when they're finished?

Solution: **Silero VAD** (detects speech vs silence)

```
Audio stream:
[speech] [silence 1 sec] [speech] [silence 3 secs]
    ↓
Silero VAD:
"User is speaking" → "User paused (1 sec, not finished)" → "User speaking again" → "Long silence (3 secs, finished!)"
    ↓
After 3-second silence, send audio to Whisper for transcription
```

**In VoiceRAG:**
```python
# Frontend (useVoiceConversation.js)
import Vad from '@ricky0123/vad-web'

vad = new Vad()

# Listen to microphone
while microphone_is_on:
    audio_chunk = microphone.get_chunk()
    
    is_speech = vad.process(audio_chunk)  # On-device VAD
    
    if is_speech:
        # Send to backend
        websocket.send(audio_chunk)
    elif silence_duration > 500ms:
        # User finished speaking
        websocket.send("END_OF_SPEECH")
        # Backend transcribes accumulated audio
```

---

## 9. Text-to-Speech - Kokoro & Edge-TTS

### What is Text-to-Speech (TTS)?

Converting text into spoken audio.

```
Input text: "Hello, how are you?"
    ↓
TTS model synthesizes audio
    ↓
Output: Audio file of someone saying the sentence
```

### Two TTS Options

| TTS | Speed | Language Support | Cost | Quality |
|-----|-------|-----------------|------|---------|
| **Kokoro** | 100ms/sentence | English only | Free (local) | Excellent |
| **Edge-TTS** | 500ms/sentence | 17+ languages | Free (Microsoft) | Good |

### Kokoro

**Kokoro-82M** = Small language model optimized for speech synthesis

```
Input: "What is AI?"
    ↓
Neural network: "How to pronounce this? What intonation?"
    ↓
Output: Audio waveform (high quality, natural sounding)
```

**Advantages:**
- 100ms per sentence (very fast)
- Works locally (no API calls)
- Works offline
- Excellent English quality

**Disadvantage:**
- English only

### Edge-TTS

**Edge-TTS** = Microsoft's cloud TTS service

Supports: English, Spanish, French, German, Chinese, Arabic, Urdu, and 11+ more

```
Input: "Salam, aapko kaise hain?" (Urdu text)
    ↓
Microsoft cloud API
    ↓
Output: Urdu speaker pronouncing the sentence
```

### How VoiceRAG Uses TTS

**Architecture:**

```
Backend (FastAPI) with LLM response
    ↓ "AI is... [long paragraph]"
1. Split into sentences (natural boundaries)
    ↓ ["AI is...", "It can...", "Examples include..."]
2. Send each sentence to TTS in parallel
    ↓
TTS Service (port 8002) or Edge-TTS API
    ↓ Generates audio for each sentence
3. Stream audio back to frontend via WebSocket
    ↓ base64-encoded WAV data
Frontend
    ↓ Plays audio to user
```

**Code:**

```python
# Backend (app/services/voice_service.py)
def generate_response_audio(text: str, language: str):
    # 1. Split into sentences
    sentences = split_sentences(text)
    
    # 2. Generate audio for each
    for sentence in sentences:
        if language == "en":
            # Use Kokoro (fast, local)
            audio = kokoro_tts(sentence)
        else:
            # Use Edge-TTS (multilingual)
            audio = edge_tts(sentence, language)
        
        # 3. Convert to base64 WAV
        audio_base64 = base64.encode(audio)
        
        # 4. Send via WebSocket to frontend
        websocket.send(audio_base64)

# Frontend (useVoiceConversation.js)
websocket.on_message((audio_base64) => {
    # 1. Decode from base64
    audio_bytes = atob(audio_base64)
    
    # 2. Create audio blob
    audio_blob = new Blob([audio_bytes], {type: 'audio/wav'})
    
    # 3. Play immediately
    audio.src = URL.createObjectURL(audio_blob)
    audio.play()
})
```

**Sentence Splitting:**

Why split by sentence?

```
Without splitting:
LLM generates: "AI is... This means... For example..." (5 sentences, 30 seconds)
User waits 30 seconds
Audio plays: All 30 seconds at once
Bad UX (long latency)

With splitting:
LLM generates: "AI is..."
Send to TTS immediately
100ms later: Audio plays (user hears response quickly)
LLM generates: "This means..."
Audio plays (user continues hearing)
Good UX (progressive response)
```

---

## 10. Frontend - React & Vite

### What is React?

**React** = JavaScript library for building interactive user interfaces.

**Problem without React:**
```html
<button id="myButton">Click me</button>

<script>
  let count = 0;
  document.getElementById("myButton").onclick = () => {
    count++;
    document.getElementById("myButton").innerHTML = `Clicked ${count} times`;
  }
</script>
```

Complex, hard to maintain, error-prone.

**With React:**
```jsx
function Counter() {
  const [count, setCount] = useState(0);
  
  return (
    <button onClick={() => setCount(count + 1)}>
      Clicked {count} times
    </button>
  );
}
```

Simpler, more maintainable.

### Core Concepts

**Components:**
```jsx
// Reusable UI piece
function ChatBox() {
  return (
    <div>
      <input placeholder="Type here" />
      <button>Send</button>
    </div>
  );
}
```

**State (data that changes):**
```jsx
function ChatPage() {
  const [messages, setMessages] = useState([]);
  
  const addMessage = (msg) => {
    setMessages([...messages, msg]);  // Update state
    // React automatically re-renders with new messages
  }
  
  return (
    <div>
      {messages.map(msg => <p>{msg}</p>)}
      <button onClick={() => addMessage("Hi")}>Send</button>
    </div>
  );
}
```

**Hooks:**
```jsx
useEffect(() => {
  // Run when component loads
  fetch_current_user();
}, [])  // Empty array = run once on load

useEffect(() => {
  // Run when 'userId' changes
  fetch_user_documents(userId);
}, [userId])  // Re-run if userId changes
```

### Vite

**Vite** = Fast development server + bundler for React

**Problem with old bundlers:**
```
Make change to code
Old bundler (Webpack): Wait 30 seconds
See change in browser
Bad developer experience
```

**Vite:**
```
Make change to code
Vite: Instant reload (<100ms)
See change in browser
Great developer experience
```

### How VoiceRAG Uses React

**Page Structure:**

```
App.jsx (main router)
  ├── LandingPage (public homepage)
  ├── AuthPage (login/register)
  ├── Portal (after login)
  │   ├── UploadPage (drag-drop documents)
  │   ├── ChatPage (text questions)
  │   ├── VoicePage (voice interaction)
  │   ├── APIKeysPage (widget keys)
  │   └── AnalyticsPage (usage stats)
  └── AdminApp (admin portal)
```

**Key Components:**

1. **useVoiceConversation Hook:**
   ```jsx
   // Hook = Reusable logic
   function VoicePage() {
     const {
       isRecording,
       transcript,
       response,
       startRecording,
       stopRecording
     } = useVoiceConversation();
     
     return (
       <div>
         <button onClick={startRecording}>🎤 Start</button>
         {transcript && <p>You: {transcript}</p>}
         {response && <p>AI: {response}</p>}
       </div>
     );
   }
   ```

2. **WebSocket for Voice:**
   ```jsx
   useEffect(() => {
     // Connect to WebSocket when component loads
     const ws = new WebSocket('ws://localhost:8000/voice/conversation');
     
     ws.onmessage = (event) => {
       // Receive audio from backend
       const audioData = event.data;
       playAudio(audioData);
     }
     
     return () => ws.close();  // Cleanup
   }, []);
   ```

3. **Document Upload:**
   ```jsx
   function UploadPage() {
     const handleDrop = (files) => {
       files.forEach(file => {
         // POST to backend with FormData
         fetch('/api/documents/upload', {
           method: 'POST',
           body: formData,  // Contains file
           headers: {
             'Authorization': `Bearer ${token}`  // JWT token
           }
         });
       });
     }
     
     return <Dropzone onDrop={handleDrop} />;
   }
   ```

---

## 11. Containerization - Docker & Compose

### The Problem: "Works on My Computer"

```
Developer A: "My code works perfectly"
Developer B: "It doesn't work on my machine"

Why?
- Different Python version
- Different Node version
- Missing environment variables
- Different OS (Windows vs Linux)
```

### Docker Solution

**Docker** = Package your entire application (code + dependencies + OS) into a container.

Think of it like a shipping container:
```
Your app + Python 3.11 + FastAPI + PostgreSQL client
Sealed in a container

Anywhere the container runs (Windows/Mac/Linux/Cloud), works identically
```

### Dockerfile Example

```dockerfile
# Start from Python 3.11 image
FROM python:3.11

# Set working directory
WORKDIR /app

# Copy code
COPY . /app

# Install dependencies
RUN pip install -r requirements.txt

# Run app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

This creates a package:
```
Inside container:
- Linux OS
- Python 3.11
- FastAPI
- All Python packages from requirements.txt
- Your code

Result: Same behavior everywhere
```

### Docker Compose

**Docker Compose** = Run multiple containers together.

VoiceRAG needs 5 services:
```
postgres (database, port 5432)
backend (FastAPI, port 8000)
stt (Whisper, port 8001)
tts (Kokoro, port 8002)
frontend (React, port 80)
```

**Without Compose:**
```bash
# Start postgres container
docker run -p 5432:5432 postgres

# In another terminal, start backend
docker run -p 8000:8000 my-backend

# In another terminal, start STT
docker run -p 8001:8001 my-stt

# In another terminal, start TTS
docker run -p 8002:8002 my-tts

# In another terminal, start frontend
docker run -p 80:80 my-frontend

# Nightmare: manage 5 terminals
```

**With Compose:**
```bash
docker-compose up

# All 5 services start together
# Auto-restarts if one crashes
# Single command to stop all
```

### How VoiceRAG Uses Docker Compose

**docker-compose.yml:**

```yaml
version: '3.9'

services:
  # Database
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: voicerag
      POSTGRES_USER: voicerag
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # Backend
  backend:
    build: ./backend  # Build from Dockerfile
    ports:
      - "8000:8000"
    depends_on:
      - postgres  # Wait for postgres to start first
    environment:
      DATABASE_URL: postgresql://voicerag:password@postgres:5432/voicerag
      GROQ_API_KEY: ${GROQ_API_KEY}
    volumes:
      - backend_data:/app/data

  # STT Service
  stt:
    build: ./services/stt
    ports:
      - "8001:8001"
    environment:
      DEVICE: cuda  # Use GPU if available
    volumes:
      - stt_models:/root/.cache

  # TTS Service
  tts:
    build: ./services/tts
    ports:
      - "8002:8002"
    volumes:
      - tts_models:/root/.cache

  # Frontend
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
  backend_data:
  stt_models:
  tts_models:
```

**How it works:**
```
docker-compose up

1. Start postgres (wait for healthy)
2. Start backend (can now connect to postgres)
3. Start stt (independent, start immediately)
4. Start tts (independent, start immediately)
5. Start frontend (can now call backend)

All services run simultaneously
All logs stream to one terminal
Press Ctrl+C to stop everything
```

---

## 12. How They Work Together

### Complete Flow: User Uploads Document

```
1. USER uploads PDF via drag-and-drop (Frontend - React)
   ↓ React sends multipart file to backend
   
2. BACKEND receives file (FastAPI)
   ↓ Route: POST /portal/document/upload
   
3. DOCUMENT_SERVICE extracts text
   ↓ PyMuPDF reads PDF
   ↓ Extracts: "Chapter 1 talks about..."
   
4. CHUNKING splits text into pieces
   ↓ LangChain: Split into 1000-char chunks
   ↓ Creates parent/child hierarchy
   
5. EMBEDDINGS converts to numbers
   ↓ Sentence-Transformers model
   ↓ Each chunk → [0.2, -0.5, 0.8, ..., 384 numbers]
   
6. FAISS indexes embeddings
   ↓ Creates FAISS index
   ↓ Saves to: data/clients/{user_id}/faiss_index.bin
   
7. DATABASE stores metadata
   ↓ SQLAlchemy saves to PostgreSQL
   ↓ Document name, chunk count, upload date
   
8. FRONTEND receives success
   ↓ React shows: "Document indexed, X chunks found"

Total time: ~2-5 seconds
```

### Complete Flow: User Asks Text Question

```
1. USER types "What is AI?" (Frontend)
   ↓ React sends to backend
   
2. BACKEND receives question (FastAPI)
   ↓ Route: POST /portal/chat
   ↓ Extract JWT token, verify user
   
3. EMBEDDINGS converts question to numbers
   ↓ Same model used for documents
   ↓ Question → [0.19, -0.49, 0.81, ...]
   
4. FAISS searches
   ↓ Load user's index from disk
   ↓ Search for top 40 similar chunks
   ↓ Return indices: [5, 23, 12, ...]
   
5. RE-RANKING scores results
   ↓ BGE model receives (question, each chunk)
   ↓ Scores: [0.95, 0.2, 0.3, ...]
   ↓ Sort by score, keep top 5
   
6. SCORE GATE checks relevance
   ↓ if max_score < 0.0:
   ↓   return "I don't have that information"
   
7. PARENT SWAP gets full context
   ↓ Top 5 chunks might be children
   ↓ Replace with their parent (full sections)
   ↓ Gives LLM more complete context
   
8. LLM generates response (Groq)
   ↓ Prompt: "Based on: [context]. Answer: [question]"
   ↓ Groq returns: "AI is artificial intelligence..."
   ↓ Streams token-by-token to frontend
   
9. ANALYTICS records trace
   ↓ Save: question, response, language, latency (retrieval 5ms + rerank 15ms + LLM 200ms)
   
10. DATABASE saves conversation
    ↓ SQLAlchemy saves Q&A pair
    ↓ Next follow-up uses history
    
11. FRONTEND displays response
    ↓ React renders streaming text
    ↓ Shows sources

Total time: ~250ms (retrieval + rerank + LLM generation)
```

### Complete Flow: User Asks Via Voice

```
1. USER taps microphone (Frontend - React + WebSocket)
   ↓ Audio streaming via WebSocket
   ↓ Silero VAD detects speech segments
   
2. VAD detects end of speech (500ms silence)
   ↓ Send accumulated audio to backend
   
3. BACKEND receives audio (FastAPI WebSocket)
   ↓ Route: WS /voice/conversation
   ↓ Extract JWT from WebSocket auth
   
4. SEND TO STT SERVICE
   ↓ HTTP POST to localhost:8001
   ↓ Faster-Whisper processes audio
   ↓ Returns: "What is AI?"
   ↓ Latency: ~400ms for 10s audio
   
5. FOLLOW SAME RAG PIPELINE
   ↓ Embed question
   ↓ FAISS search + BGE rerank
   ↓ LLM generates: "AI is artificial intelligence..."
   
6. SENTENCE SPLITTING splits response
   ↓ "AI is..." → Sentence 1
   ↓ "It can..." → Sentence 2
   
7. SEND TO TTS SERVICE
   ↓ HTTP POST sentence to localhost:8002
   ↓ Kokoro (if English) or Edge-TTS (other languages)
   ↓ Returns: audio WAV file
   ↓ Latency: ~100ms per sentence
   
8. STREAM AUDIO BACK
   ↓ Convert WAV to base64
   ↓ Send via WebSocket to frontend
   
9. FRONTEND plays audio
   ↓ Decode base64 → WAV bytes
   ↓ Create Blob → Audio element
   ↓ Play immediately (no waiting for full response)
   
10. SAVE CONVERSATION
    ↓ Database: speech input, text response, latency breakdown
    
11. USER can interrupt (barge-in)
    ↓ If user speaks while audio is playing
    ↓ Stop audio playback
    ↓ Start recording new question

Total time: STT (400ms) + Retrieval (5ms) + Rerank (15ms) + LLM (200ms) + TTS (100ms) = ~720ms
End-to-end: User speaks → Hears response in ~720ms
```

---

## Summary: The Orchestration

```
┌─────────────────────────────────────────────────────────────┐
│                     VOICERAG ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Frontend (React + Vite)                                     │
│  - UI components (pages, hooks)                              │
│  - WebSocket for real-time voice                             │
│  - JWT token management                                      │
│  ↓                                                            │
│  FastAPI Backend                                             │
│  - REST/WebSocket endpoints                                  │
│  - JWT authentication                                        │
│  - Multi-tenant isolation                                    │
│  ↓                                                            │
│  RAG Pipeline                                                │
│  - Embeddings (Sentence-Transformers)                        │
│  - Vector Search (FAISS)                                     │
│  - Reranking (BGE)                                           │
│  ↓                                                            │
│  LLM Decision (Groq → DeepSeek → Ollama)                    │
│  - Grounded response generation                              │
│  - Streaming output                                          │
│  ↓                                                            │
│  Microservices                                               │
│  - STT (Faster-Whisper)                                      │
│  - TTS (Kokoro/Edge-TTS)                                     │
│  ↓                                                            │
│  Data Layer                                                  │
│  - PostgreSQL (user data, conversations)                     │
│  - FAISS indices (per-client)                                │
│  - Redis (conversation cache)                                │
│  ↓                                                            │
│  Docker Compose (orchestration)                              │
│  - All services containerized                                │
│  - Health checks, restarts, networking                       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Next Steps: Learning More

1. **FastAPI**: Read "Building APIs with FastAPI" guide
2. **RAG**: Understand embeddings first, then vector search, then reranking
3. **LLMs**: Try ChatGPT API to understand how prompts work
4. **React**: Build a simple counter/todo app
5. **Docker**: Containerize a simple Python app
6. **Full Stack**: Build a simple chat app (frontend + backend + database)

Each piece makes sense on its own. Put them together, and you have VoiceRAG.
