#!/usr/bin/env python3
"""
Test script to verify environment variables are loading correctly.
Run this from the backend directory to debug .env loading issues.
"""

import os
import sys
from pathlib import Path

print("=" * 60)
print("Environment Variable Test")
print("=" * 60)

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

print(f"\n1. Current working directory: {os.getcwd()}")
print(f"2. Script location: {Path(__file__).resolve()}")

# Test manual .env loading
print("\n3. Testing manual .env loading...")
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
print(f"   Looking for .env at: {env_path}")
print(f"   .env exists: {env_path.exists()}")

if env_path.exists():
    load_dotenv(env_path)
    print("   ✓ .env loaded")
else:
    print("   ✗ .env not found!")

# Check if GROQ_API_KEY is in environment
print("\n4. Checking GROQ_API_KEY in environment...")
groq_key = os.getenv("GROQ_API_KEY")
if groq_key:
    print(f"   ✓ GROQ_API_KEY found: {groq_key[:20]}...")
else:
    print("   ✗ GROQ_API_KEY not found in environment!")

# Test importing settings
print("\n5. Testing settings import...")
try:
    from app.core.config import settings
    print("   ✓ Settings imported successfully")
    print(f"   GROQ_API_KEY from settings: {settings.GROQ_API_KEY[:20] if settings.GROQ_API_KEY else 'NOT SET'}...")
    print(f"   LLM Model: {settings.LLM_MODEL}")
    print(f"   Embedding Model: {settings.EMBEDDING_MODEL}")
except Exception as e:
    print(f"   ✗ Failed to import settings: {e}")

# Test creating Groq client
print("\n6. Testing Groq client creation...")
try:
    from langchain_groq import ChatGroq
    
    if groq_key:
        llm = ChatGroq(
            api_key=groq_key,
            model="llama-3.3-70b-versatile",
            temperature=0.3,
        )
        print("   ✓ Groq client created successfully")
        
        # Test a simple call
        print("\n7. Testing Groq API call...")
        response = llm.invoke("Say 'Hello, World!' and nothing else.")
        print(f"   ✓ API call successful: {response.content}")
    else:
        print("   ✗ Cannot create client - GROQ_API_KEY not set")
except Exception as e:
    print(f"   ✗ Failed to create Groq client: {e}")

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)
