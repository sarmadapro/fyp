#!/usr/bin/env python3
"""
Comprehensive diagnostic script for Voice-to-Voice RAG AI Agent.
Run this to diagnose any setup or configuration issues.
"""

import os
import sys
from pathlib import Path

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def check_item(name, condition, details=""):
    status = "✓" if condition else "✗"
    print(f"{status} {name}")
    if details:
        print(f"  → {details}")
    return condition

print_section("Voice-to-Voice RAG AI Agent - Diagnostic Report")

all_checks = []

# 1. Python Version
print_section("1. Python Environment")
version = sys.version_info
all_checks.append(check_item(
    "Python Version",
    version.major == 3 and version.minor >= 10,
    f"Current: {version.major}.{version.minor}.{version.micro}"
))

# 2. Project Structure
print_section("2. Project Structure")
all_checks.append(check_item("Backend directory", Path("backend").exists()))
all_checks.append(check_item("Frontend directory", Path("frontend").exists()))
all_checks.append(check_item("STT service", Path("services/stt").exists()))
all_checks.append(check_item("TTS service", Path("services/tts").exists()))

# 3. Environment File
print_section("3. Environment Configuration")
env_exists = Path(".env").exists()
all_checks.append(check_item(".env file", env_exists, f"Location: {Path('.env').resolve()}"))

if env_exists:
    with open(".env", "r") as f:
        env_content = f.read()
        has_groq = "GROQ_API_KEY=" in env_content
        has_real_key = has_groq and "your_actual_groq_api_key" not in env_content and "gsk_" in env_content
        
        all_checks.append(check_item(
            "GROQ_API_KEY in .env",
            has_groq,
            "Found in file" if has_groq else "Not found - add your Groq API key"
        ))
        all_checks.append(check_item(
            "GROQ_API_KEY looks valid",
            has_real_key,
            "Starts with 'gsk_'" if has_real_key else "Looks like placeholder - replace with real key"
        ))

# 4. Virtual Environments
print_section("4. Virtual Environments")
all_checks.append(check_item("Backend venv", Path("backend/venv").exists()))
all_checks.append(check_item("STT venv", Path("services/stt/venv").exists()))
all_checks.append(check_item("TTS venv", Path("services/tts/venv").exists()))

# 5. Dependencies
print_section("5. Backend Dependencies")
try:
    sys.path.insert(0, str(Path("backend").resolve()))
    
    # Test imports
    try:
        import fastapi
        all_checks.append(check_item("FastAPI", True, f"Version: {fastapi.__version__}"))
    except ImportError:
        all_checks.append(check_item("FastAPI", False, "Not installed"))
    
    try:
        import langchain
        all_checks.append(check_item("LangChain", True, f"Version: {langchain.__version__}"))
    except ImportError:
        all_checks.append(check_item("LangChain", False, "Not installed"))
    
    try:
        import langchain_groq
        all_checks.append(check_item("LangChain-Groq", True))
    except ImportError:
        all_checks.append(check_item("LangChain-Groq", False, "Not installed"))
    
    try:
        import sentence_transformers
        all_checks.append(check_item("Sentence-Transformers", True))
    except ImportError:
        all_checks.append(check_item("Sentence-Transformers", False, "Not installed"))
    
    try:
        import faiss
        all_checks.append(check_item("FAISS", True))
    except ImportError:
        all_checks.append(check_item("FAISS", False, "Not installed"))
        
except Exception as e:
    print(f"Error checking dependencies: {e}")

# 6. Data Directories
print_section("6. Data Storage")
all_checks.append(check_item("Upload directory", Path("backend/data/uploads").exists()))
all_checks.append(check_item("Index directory", Path("backend/data/indices").exists()))

# Check if document is indexed
index_files = list(Path("backend/data/indices").glob("*.faiss"))
if index_files:
    all_checks.append(check_item(
        "FAISS index exists",
        True,
        f"Found: {index_files[0].name} ({index_files[0].stat().st_size} bytes)"
    ))
else:
    all_checks.append(check_item("FAISS index exists", False, "No document indexed yet"))

# 7. Test Environment Loading
print_section("7. Environment Variable Loading")
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    groq_key = os.getenv("GROQ_API_KEY")
    all_checks.append(check_item(
        "GROQ_API_KEY in environment",
        bool(groq_key),
        f"{groq_key[:20]}..." if groq_key else "Not loaded"
    ))
    
    # Test importing settings
    from backend.app.core.config import settings
    all_checks.append(check_item(
        "Settings module loads",
        True,
        f"API Key: {settings.GROQ_API_KEY[:20] if settings.GROQ_API_KEY else 'NOT SET'}..."
    ))
    
except Exception as e:
    all_checks.append(check_item("Settings module loads", False, str(e)))

# 8. Test Groq API
print_section("8. Groq API Connection")
try:
    if groq_key:
        from langchain_groq import ChatGroq
        llm = ChatGroq(api_key=groq_key, model="llama-3.3-70b-versatile", temperature=0.3)
        response = llm.invoke("Say 'OK' and nothing else.")
        all_checks.append(check_item(
            "Groq API call",
            True,
            f"Response: {response.content}"
        ))
    else:
        all_checks.append(check_item("Groq API call", False, "API key not available"))
except Exception as e:
    all_checks.append(check_item("Groq API call", False, str(e)))

# Summary
print_section("Summary")
passed = sum(all_checks)
total = len(all_checks)

if passed == total:
    print(f"✓ All checks passed! ({passed}/{total})")
    print("\nYour system is properly configured.")
    print("\nTo start the application:")
    print("  1. Run: start_all_services.bat (Windows) or ./start_all_services.sh (Linux/Mac)")
    print("  2. Open http://localhost:5173 in your browser")
else:
    print(f"✗ {total - passed} check(s) failed ({passed}/{total} passed)")
    print("\nPlease fix the issues above before starting the application.")
    print("\nCommon fixes:")
    print("  - Missing .env: Copy .env.example to .env")
    print("  - Invalid API key: Get one at https://console.groq.com")
    print("  - Missing venv: Run setup commands from START_HERE.md")
    print("  - Missing dependencies: Activate venv and run 'pip install -r requirements.txt'")

print("\n" + "="*60)
