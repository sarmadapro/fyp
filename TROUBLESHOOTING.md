# 🔧 Troubleshooting Guide

## Common Issues and Solutions

### Issue 1: "GROQ_API_KEY not set" Error

**Symptoms:**
```
groq.GroqError: The api_key client option must be set either by passing api_key to the client or by setting the GROQ_API_KEY environment variable
```

**Cause:** The backend is not loading the `.env` file correctly, or you're not running it with the virtual environment activated.

**Solutions:**

#### Solution A: Use the Startup Script (Recommended)
```bash
# Windows
start_backend.bat

# Or use the all-in-one script
start_all_services.bat
```

#### Solution B: Manual Start with Correct Steps
```bash
# 1. Make sure you're in the project root
cd C:\Users\USER\Desktop\sarmad

# 2. Activate the backend virtual environment
cd backend
venv\Scripts\activate

# 3. Verify the API key is loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv('../.env'); print('API Key:', os.getenv('GROQ_API_KEY')[:20] if os.getenv('GROQ_API_KEY') else 'NOT FOUND')"

# 4. Start the backend
python main.py
```

#### Solution C: Verify .env File
```bash
# Check if .env exists in project root
dir .env

# Check if it contains your API key
type .env | findstr GROQ_API_KEY

# If not, copy from example and add your key
copy .env.example .env
# Then edit .env and add your real Groq API key
```

#### Solution D: Test Environment Loading
```bash
cd backend
venv\Scripts\activate
python test_env.py
```

This will show you exactly where the issue is.

---

### Issue 2: Document Uploads But Chat Fails

**Symptoms:**
- Document uploads successfully
- FAISS index is created
- Chat returns 500 error

**Diagnosis:**
```bash
# Check if FAISS index was created
dir backend\data\indices\

# You should see:
# - index.faiss (vector index)
# - index.pkl (metadata)
# - doc_meta.txt (document info)
```

**Solution:**
This is usually the same as Issue 1 - the Groq API key isn't loading. Follow Solution A or B above.

---

### Issue 3: "Module not found" Errors

**Symptoms:**
```
ModuleNotFoundError: No module named 'langchain_groq'
ModuleNotFoundError: No module named 'faiss'
```

**Cause:** Running Python without activating the virtual environment.

**Solution:**
```bash
# Always activate venv before running
cd backend
venv\Scripts\activate
python main.py
```

**Verify packages are installed:**
```bash
cd backend
venv\Scripts\activate
pip list | findstr "langchain groq faiss"
```

You should see:
- faiss-cpu
- groq
- langchain
- langchain-groq
- langchain-community
- langchain-core

If missing, reinstall:
```bash
pip install -r requirements.txt
```

---

### Issue 4: Port Already in Use

**Symptoms:**
```
OSError: [WinError 10048] Only one usage of each socket address is normally permitted
```

**Solution:**
```bash
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F

# Or change the port in .env
# Edit .env and set:
BACKEND_PORT=8001
```

---

### Issue 5: CORS Errors in Browser

**Symptoms:**
```
Access to fetch at 'http://localhost:8000/chat' from origin 'http://localhost:5173' has been blocked by CORS policy
```

**Solution:**
Check `CORS_ORIGINS` in `.env`:
```env
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

Make sure your frontend URL is included.

---

### Issue 6: Microphone Not Working

**Symptoms:**
- Voice page loads but recording doesn't start
- Browser doesn't ask for microphone permission

**Solutions:**
1. **Use HTTPS or localhost** - Browsers require secure context for microphone
2. **Grant permissions** - Check browser settings → Site permissions → Microphone
3. **Try different browser** - Chrome and Edge have best support
4. **Check microphone** - Test in Windows Sound settings

---

### Issue 7: STT/TTS Services Not Starting

**Symptoms:**
```
Connection refused to http://localhost:8001
Connection refused to http://localhost:8002
```

**Solution:**
Start the services in separate terminals:

**Terminal 1 - STT:**
```bash
cd services\stt
venv\Scripts\activate
python main.py
```

**Terminal 2 - TTS:**
```bash
cd services\tts
venv\Scripts\activate
python main.py
```

**Or use the all-in-one script:**
```bash
start_all_services.bat
```

---

### Issue 8: First Run is Very Slow

**Symptoms:**
- STT service takes 5-10 minutes to start
- TTS service downloads files on first run

**Cause:** Models are being downloaded on first use (~5GB total)

**Solution:**
- This is normal! Be patient on first run
- Models are cached after first download
- Subsequent starts will be much faster

**Progress indicators:**
- STT: Downloads Faster-Whisper large-v3 model
- TTS: Downloads Kokoro-82M model and espeak-ng

---

### Issue 9: Frontend Can't Connect to Backend

**Symptoms:**
- Frontend loads but API calls fail
- Network errors in browser console

**Diagnosis:**
```bash
# Test backend health
curl http://localhost:8000/health

# Or in browser
http://localhost:8000/health
```

**Solutions:**
1. **Backend not running** - Start it with `start_backend.bat`
2. **Wrong port** - Check `VITE_API_URL` in frontend
3. **Firewall** - Allow Python through Windows Firewall

---

### Issue 10: Chat Returns "No document uploaded"

**Symptoms:**
- Document uploaded successfully
- Chat says "No document has been uploaded yet"

**Diagnosis:**
```bash
# Check if index exists
dir backend\data\indices\index.faiss

# Check document service status
curl http://localhost:8000/document/status
```

**Solution:**
- Re-upload the document
- Check backend logs for errors during upload
- Verify FAISS index was created

---

## Diagnostic Commands

### Quick Health Check
```bash
# Check all services
python test_services.py

# Check setup
python check_setup.py

# Full diagnostic
python diagnose_issue.py
```

### Backend Diagnostics
```bash
cd backend
venv\Scripts\activate
python test_env.py
```

### Check Logs
```bash
# Backend logs are printed to console
# Look for:
# - [CONFIG] messages on startup
# - ERROR messages for failures
# - INFO messages for requests
```

### Verify Environment
```bash
# Check .env is loaded
cd backend
venv\Scripts\activate
python -c "from app.core.config import settings; print('API Key:', settings.GROQ_API_KEY[:20] if settings.GROQ_API_KEY else 'NOT SET')"
```

---

## Getting Help

If you're still stuck:

1. **Run diagnostics:**
   ```bash
   python diagnose_issue.py > diagnostic_report.txt
   ```

2. **Check the logs** - Look for ERROR messages in the backend console

3. **Verify setup:**
   - .env file exists in project root
   - GROQ_API_KEY is set in .env
   - Virtual environments are activated
   - All services are running

4. **Common mistakes:**
   - Running without activating venv
   - .env file in wrong location
   - Using placeholder API key
   - Ports already in use
   - Firewall blocking connections

---

## Prevention

To avoid issues:

1. **Always use startup scripts:**
   ```bash
   start_all_services.bat  # Starts everything
   ```

2. **Always activate venv:**
   ```bash
   cd backend
   venv\Scripts\activate
   ```

3. **Check health before testing:**
   ```bash
   python test_services.py
   ```

4. **Keep logs visible** - Run services in separate terminals to see errors

---

## Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| API key error | Use `start_backend.bat` or activate venv |
| Module not found | Activate venv: `venv\Scripts\activate` |
| Port in use | Kill process or change port in .env |
| CORS error | Add frontend URL to CORS_ORIGINS in .env |
| Microphone not working | Use Chrome/Edge, grant permissions |
| Services not starting | Use `start_all_services.bat` |
| Slow first run | Normal - models downloading (~5GB) |
| Can't connect | Check backend is running on port 8000 |
| No document | Re-upload document |

---

**Still having issues?** Check the logs and run `python diagnose_issue.py` for detailed diagnostics.
