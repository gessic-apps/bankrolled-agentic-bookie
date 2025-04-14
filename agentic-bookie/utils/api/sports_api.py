#!/usr/bin/env python3
import requests
import sys
import datetime
from typing import List, Dict, Any, Optional

# Try to import dotenv, but handle when it's not available
try:
    from dotenv import load_dotenv
    # Load environment variables from .env file
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv package not installed, skipping .env file loading.", file=sys.stderr)

from ..config import SPORTS_API_KEY
def fetch_odds_api(
    sport_key: str,
    regions: str = "us",
    markets: str = "h2h,spreads,totals",
    odds_format: str = "decimal",
    date_format: str = "iso",
    commence_time_from: Optional[str] = None,
    commence_time_to: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Generic function to fetch data from The Odds API with various parameters"""
    if not SPORTS_API_KEY:
        print("Error: Cannot fetch from The Odds API, SPORTS_API_KEY is missing.", file=sys.stderr)
        return []

    try:
        params = {
            "apiKey": SPORTS_API_KEY,
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format,
            "dateFormat": date_format,
        }
        
        # Add optional time filters if provided
        if commence_time_from:
            params["commenceTimeFrom"] = commence_time_from
        if commence_time_to:
            params["commenceTimeTo"] = commence_time_to
            
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from The Odds API for {sport_key}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred fetching data for {sport_key}: {e}", file=sys.stderr)
        return []