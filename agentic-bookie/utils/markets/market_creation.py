#!/usr/bin/env python3
import json
import sys
from typing import Dict, Any, List, Optional

from ..api.client import api_post
from .market_data import get_all_markets, check_event_exists

def create_betting_market(
    home_team: str,
    away_team: str,
    game_timestamp: int,
    game_id: str,
    home_odds: Optional[int] = None,
    away_odds: Optional[int] = None
) -> Dict[str, Any]:
    """Creates a new betting market via the platform API."""
    
    # Double-check market doesn't already exist
    try:
        existing_markets = get_all_markets()
        if check_event_exists(game_id, existing_markets):
            print(f"DUPLICATE PREVENTION: Market for game ID {game_id} ({home_team} vs {away_team}) already exists. Skipping creation.")
            return {
                "status": "skipped", 
                "message": f"Market for game ID {game_id} already exists",
                "game_id": game_id,
                "home_team": home_team,
                "away_team": away_team
            }
    except Exception as e:
        print(f"Warning: Error during duplicate check: {e}. Will attempt market creation anyway.", file=sys.stderr)

    # The agent instructions say *not* to set odds, so we ignore home_odds/away_odds
    payload = {
        "homeTeam": home_team,
        "awayTeam": away_team,
        "gameTimestamp": game_timestamp,
        "oddsApiId": game_id,
    }

    try:
        result = api_post("/api/market/create", payload)
        print(f"Successfully created market for {home_team} vs {away_team}. Response: {result}")
        # Assuming the API returns a success status and market details
        return {"status": "success", "market": result.get("market", result)}
    except Exception as e:
        error_message = f"Error creating market for {home_team} vs {away_team}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message}

def batch_process_markets(upcoming_games: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process multiple game events at once, checking which ones need markets created and creating them in batch."""
    try:
        # Step 1: Fetch existing markets once
        existing_markets = get_all_markets()
        
        # Extract existing IDs for efficient lookup
        existing_ids = {market.get("oddsApiId") for market in existing_markets if market.get("oddsApiId")}
            
        print(f"Found {len(existing_ids)} existing markets")
        
        # Step 2: Process all upcoming games
        results = {
            "total_games": len(upcoming_games),
            "existing_markets": len(existing_ids),
            "markets_created": 0,
            "markets_skipped": 0,
            "errors": 0,
            "created": [],
            "skipped": [],
            "failed": []
        }
        
        for game in upcoming_games:
            try:
                game_id = game.get("id")
                home_team = game.get("home_team")
                away_team = game.get("away_team")
                game_timestamp = game.get("game_timestamp")
                
                # Check if this game already has a market
                if game_id in existing_ids:
                    print(f"DUPLICATE PREVENTION: Market for game ID {game_id} ({home_team} vs {away_team}) already exists. Skipping creation.")
                    results["markets_skipped"] += 1
                    results["skipped"].append({
                        "game_id": game_id,
                        "home_team": home_team,
                        "away_team": away_team
                    })
                    continue
                
                # Create market since it doesn't exist
                result = create_betting_market(
                    home_team=home_team,
                    away_team=away_team,
                    game_timestamp=game_timestamp,
                    game_id=game_id
                )
                
                if result.get("status") == "success":
                    results["markets_created"] += 1
                    results["created"].append({
                        "game_id": game_id,
                        "home_team": home_team,
                        "away_team": away_team,
                        "address": result.get("market", {}).get("address", "unknown")
                    })
                    
                    # Add to existing IDs to prevent duplicate creation in the same batch
                    existing_ids.add(game_id)
                else:
                    results["errors"] += 1
                    results["failed"].append({
                        "game_id": game_id,
                        "home_team": home_team,
                        "away_team": away_team,
                        "error": result.get("message", "Unknown error")
                    })
                
            except Exception as e:
                error_message = f"An unexpected error occurred processing game {game.get('id', 'unknown')}: {e}"
                print(error_message, file=sys.stderr)
                results["errors"] += 1
                results["failed"].append({
                    "game_id": game.get("id", "unknown"),
                    "error": str(e)
                })
                
        return results
        
    except Exception as e:
        error_message = f"An unexpected error occurred in batch_process_markets: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message}