#!/usr/bin/env python3
import os
import sys
from pathlib import Path
# Try to import dotenv for .env file loading, but fallback if not available
try:
    from dotenv import load_dotenv
    # Load environment variables from .env file
    # load_dotenv('/Users/osman/bankrolled-agent-bookie/agentic-bookie/.env')
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    # load_dotenv('/home/osman/bankrolled-agent-bookie/agentic-bookie/.env')
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv package not installed, skipping .env file loading.", file=sys.stderr)

# API Configuration
SPORTS_API_KEY =  os.getenv("SPORTS_API_KEY")  # Default to empty string if not found
print(SPORTS_API_KEY)
API_URL = os.getenv("API_URL", "http://localhost:3000")  # Default if not set

# Define the list of target sports
SUPPORTED_SPORT_KEYS = [
    "basketball_nba",
    "soccer_epl",  # English Premier League
    "soccer_france_ligue_one",
    "soccer_italy_serie_a",
    "soccer_germany_bundesliga",
    "soccer_spain_la_liga",
    "soccer_uefa_champs_league",
    "soccer_uefa_europa_league"
]

# Validate configuration and print warnings but don't fail
if not SPORTS_API_KEY:
    print("Warning: SPORTS_API_KEY not found in environment variables. Some functionality may be limited.", file=sys.stderr)

if not API_URL:
    print(f"Warning: API_URL not found, defaulting to {API_URL}", file=sys.stderr)

def is_soccer_sport(sport_key: str) -> bool:
    """Determines if a sport key is for a soccer league"""
    return sport_key.startswith("soccer_")