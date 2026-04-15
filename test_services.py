#!/usr/bin/env python3
"""
Quick test script to verify all services are running and healthy.
Run this after starting all services to ensure everything is connected.
"""

import sys
import requests
from colorama import init, Fore, Style

init(autoreset=True)

SERVICES = {
    "Backend": "http://localhost:8000/health",
    "STT Service": "http://localhost:8001/health",
    "TTS Service": "http://localhost:8002/health",
}


def test_service(name: str, url: str) -> bool:
    """Test if a service is healthy."""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"{Fore.GREEN}✓ {name:15} {Style.BRIGHT}HEALTHY{Style.RESET_ALL} - {data}")
            return True
        else:
            print(f"{Fore.RED}✗ {name:15} {Style.BRIGHT}ERROR{Style.RESET_ALL} - Status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"{Fore.RED}✗ {name:15} {Style.BRIGHT}NOT RUNNING{Style.RESET_ALL} - Cannot connect to {url}")
        return False
    except Exception as e:
        print(f"{Fore.RED}✗ {name:15} {Style.BRIGHT}ERROR{Style.RESET_ALL} - {str(e)}")
        return False


def main():
    print(f"\n{Style.BRIGHT}{'='*60}")
    print(f"  Voice-to-Voice RAG AI Agent - Service Health Check")
    print(f"{'='*60}{Style.RESET_ALL}\n")

    results = {}
    for name, url in SERVICES.items():
        results[name] = test_service(name, url)

    print(f"\n{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
    
    all_healthy = all(results.values())
    if all_healthy:
        print(f"{Fore.GREEN}{Style.BRIGHT}✓ All services are healthy!{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}Next steps:{Style.RESET_ALL}")
        print(f"  1. Open http://localhost:5173 in your browser")
        print(f"  2. Upload a document")
        print(f"  3. Test chat and voice features")
        return 0
    else:
        print(f"{Fore.RED}{Style.BRIGHT}✗ Some services are not running!{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Please start the missing services:{Style.RESET_ALL}")
        for name, healthy in results.items():
            if not healthy:
                print(f"  - {name}")
        print(f"\nSee START_HERE.md for instructions.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
