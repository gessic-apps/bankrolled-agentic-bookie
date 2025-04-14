#!/usr/bin/env python3
import json
import sys
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from ..api.client import api_get

# Define data structure for Market objects
class Market(BaseModel):
    oddsApiId: str
    # Adding other optional fields that might be present in API responses
    address: Optional[str] = None
    homeTeam: Optional[str] = None
    awayTeam: Optional[str] = None 
    gameTimestamp: Optional[int] = None
    homeOdds: Optional[int] = None
    awayOdds: Optional[int] = None
    gameStarted: Optional[bool] = None
    gameEnded: Optional[bool] = None
    oddsSet: Optional[bool] = None
    isReadyForBetting: Optional[bool] = None

def get_all_markets() -> List[Dict[str, Any]]:
    """Fetches all existing betting markets from the platform API."""
    try:
        markets_data = api_get("/api/markets")
        
        # Ensure the response is a list and contains required fields
        cleaned_markets = []
        if isinstance(markets_data, list):
            for market in markets_data:
                if isinstance(market, dict) and all(k in market for k in ["address", "oddsApiId", "status"]):
                    # A market is ready for betting if its status is 'Open' OR 'Pending'
                    market["isReadyForBetting"] = (market.get("status") == "Open" or market.get("status") == "Pending")
                    cleaned_markets.append(market)
                else:
                    print(f"Warning: Skipping market entry due to missing required fields (address, oddsApiId, status) or incorrect format: {market}", file=sys.stderr)
        else:
            print(f"Warning: Expected a list from /api/markets, but got {type(markets_data)}", file=sys.stderr)
            return []

        print(f"Successfully fetched {len(cleaned_markets)} existing markets with required fields.")
        return cleaned_markets
    except Exception as e:
        print(f"An unexpected error occurred in get_all_markets: {e}", file=sys.stderr)
        return []

def get_market_details(market_address: str) -> Dict[str, Any]:
    """Fetch details for a specific market by its address"""
    try:
        return api_get(f"/api/market/{market_address}")
    except Exception as e:
        print(f"Error fetching market details for {market_address}: {e}", file=sys.stderr)
        return {}

def check_event_exists(game_id: str, existing_markets: List[Dict[str, Any]]) -> bool:
    """Checks if a betting market already exists for a given Odds API game ID within a provided list."""
    print(f"Checking existence for game_id: {game_id} against {len(existing_markets)} provided markets.")
    
    # Create a set of all oddsApiIds for more efficient lookup
    existing_ids = {market.get("oddsApiId") for market in existing_markets if market.get("oddsApiId")}
    
    # Check if game_id exists in the set
    exists = game_id in existing_ids
    print(f"Market exists for game_id {game_id}: {exists}")
    return exists