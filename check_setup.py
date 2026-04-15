#!/usr/bin/env python3
"""
Setup verification script for Voice-to-Voice RAG AI Agent.
Checks if all dependencies and configurations are in place before running.
"""

import os
import sys
from pathlib import Path


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{Colors.END}\n")


def check_item(name, condition, fix_hint=None):
    """Check a single item and print result."""
    if condition:
        print(f"{Colors.GREEN}✓ {name}{Colors.END}")
        return True
    else:
        print(f"{Colors.RED}✗ {name}{Colors.END}")
        if fix_hint:
            print(f"  {Colors.YELLOW}→ {fix_hint}{Colors.END}")
        return False


def check_python_version():
    """Check if Python version is 3.10+"""
    version = sys.version_info
    return version.major == 3 and version.minor >= 10


def check_file_exists(filepath):
    """Check if a file exists."""
    return Path(filepath).exists()


def check_directory_exists(dirpath):
    """Check if a directory exists."""
    return Path(dirpath).is_dir()


def check_env_variable(var_name):
    """Check if an environment variable is set."""
    value = os.getenv(var_name)
    return value is not None and value.strip() != ""


def main():
    print_header("Voice-to-Voice RAG AI Agent - Setup Verification")
    
    all_checks = []
    
    # Python version
    print(f"{Colors.BOLD}Python Environment:{Colors.END}")
    all_checks.append(check_item(
        "Python 3.10+",
        check_python_version(),
        "Install Python 3.10 or higher"
    ))
    
    # Project structure
    print(f"\n{Colors.BOLD}Project Structure:{Colors.END}")
    all_checks.append(check_item(
        "Backend directory",
        check_directory_exists("backend"),
        "Project structure is incomplete"
    ))
    all_checks.append(check_item(
        "Frontend directory",
        check_directory_exists("frontend"),
        "Project structure is incomplete"
    ))
    all_checks.append(check_item(
        "STT service directory",
        check_directory_exists("services/stt"),
        "Project structure is incomplete"
    ))
    all_checks.append(check_item(
        "TTS service directory",
        check_directory_exists("services/tts"),
        "Project structure is incomplete"
    ))
    
    # Configuration files
    print(f"\n{Colors.BOLD}Configuration:{Colors.END}")
    all_checks.append(check_item(
        ".env file exists",
        check_file_exists(".env"),
        "Copy .env.example to .env and add your GROQ_API_KEY"
    ))
    
    # Check .env content if it exists
    if check_file_exists(".env"):
        with open(".env", "r") as f:
            env_content = f.read()
            has_groq_key = "GROQ_API_KEY=" in env_content and "your_actual_groq_api_key" not in env_content
            all_checks.append(check_item(
                "GROQ_API_KEY configured",
                has_groq_key,
                "Add your Groq API key to .env file (get one at https://console.groq.com)"
            ))
    
    # Virtual environments
    print(f"\n{Colors.BOLD}Virtual Environments:{Colors.END}")
    all_checks.append(check_item(
        "Backend venv",
        check_directory_exists("backend/venv"),
        "Run: cd backend && python -m venv venv && venv/Scripts/activate && pip install -r requirements.txt"
    ))
    all_checks.append(check_item(
        "STT venv",
        check_directory_exists("services/stt/venv"),
        "Run: cd services/stt && python -m venv venv && venv/Scripts/activate && pip install -r requirements.txt"
    ))
    all_checks.append(check_item(
        "TTS venv",
        check_directory_exists("services/tts/venv"),
        "Run: cd services/tts && python -m venv venv && venv/Scripts/activate && pip install -r requirements.txt"
    ))
    
    # Node modules
    print(f"\n{Colors.BOLD}Frontend Dependencies:{Colors.END}")
    all_checks.append(check_item(
        "Node modules installed",
        check_directory_exists("frontend/node_modules"),
        "Run: cd frontend && npm install"
    ))
    
    # Data directories
    print(f"\n{Colors.BOLD}Data Directories:{Colors.END}")
    all_checks.append(check_item(
        "Upload directory",
        check_directory_exists("backend/data/uploads"),
        "Will be created automatically on first run"
    ))
    all_checks.append(check_item(
        "Index directory",
        check_directory_exists("backend/data/indices"),
        "Will be created automatically on first run"
    ))
    
    # Summary
    print_header("Summary")
    
    passed = sum(all_checks)
    total = len(all_checks)
    
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ All checks passed! ({passed}/{total}){Colors.END}")
        print(f"\n{Colors.BLUE}You're ready to start the application!{Colors.END}")
        print(f"\nNext steps:")
        print(f"  1. Run: {Colors.BOLD}start_all_services.bat{Colors.END} (Windows) or {Colors.BOLD}./start_all_services.sh{Colors.END} (Linux/Mac)")
        print(f"  2. Wait 10-15 seconds for services to start")
        print(f"  3. Open http://localhost:5173 in your browser")
        print(f"  4. Upload a document and start chatting!")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ {total - passed} check(s) failed ({passed}/{total} passed){Colors.END}")
        print(f"\n{Colors.YELLOW}Please fix the issues above before starting the application.{Colors.END}")
        print(f"\nFor detailed setup instructions, see: {Colors.BOLD}START_HERE.md{Colors.END}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Setup check cancelled.{Colors.END}")
        sys.exit(1)
