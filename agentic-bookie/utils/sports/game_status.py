#!/usr/bin/env python3
import sys
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field
# Load environment variables from .env file
load_dotenv()
SPORTS_API_KEY = os.getenv("SPORTS_API_KEY")
API_URL = os.getenv("API_URL", "http://localhost:3000") # Default matching other agents

# Define a Pydantic model for the market info needed by check_completed_games
# Make sportKey optional
class MarketInfo(BaseModel):
    oddsApiId: str
    sportKey: Optional[str] = None # Make sportKey optional


from ..api.client import api_post, api_get
from ..markets.market_data import get_all_markets

def check_completed_games(markets_to_check: List[MarketInfo]) -> List[Dict[str, Any]]:
    """
    Checks if games associated with the given markets are completed.
    If a market's sportKey is missing, it tries all known soccer sportKeys.
    Returns information only for games that are confirmed completed with scores.

    Args:
        markets_to_check: List of MarketInfo objects, potentially with missing sportKey.

    Returns:
        List of dictionaries containing information about completed games.
        (Structure unchanged from original)
    """
    if not SPORTS_API_KEY:
        print("Error: Cannot fetch game scores, SPORTS_API_KEY is missing.", file=sys.stderr)
        return []

    if not markets_to_check:
        print("Warning: No markets provided to check_completed_games.", file=sys.stderr)
        return []

    # --- Group markets ---
    # Group by known sport_key (specific soccer leagues or other sports)
    games_by_known_sport: Dict[str, List[str]] = defaultdict(list)
    # Collect oddsApiIds for markets with unknown/missing sportKey
    ids_with_unknown_sport: set[str] = set()

    for market_info in markets_to_check:
        sport_key = market_info.sportKey
        odds_api_id = market_info.oddsApiId

        if not odds_api_id:
             print(f"Warning: Skipping market in check_completed_games due to missing oddsApiId: {market_info}", file=sys.stderr)
             continue

        # Check if sportKey is known (either specific soccer or other known types)
        if sport_key and (sport_key in SOCCER_SPORT_KEYS or sport_key in NON_SOCCER_SPORT_KEYS):
            games_by_known_sport[sport_key].append(odds_api_id)
        else:
            # If sportKey is missing or not recognized, add ID to the 'unknown' set
            ids_with_unknown_sport.add(odds_api_id)
            if sport_key:
                 print(f"Info: Market {odds_api_id} has unrecognized sportKey '{sport_key}'. Will attempt soccer checks.", file=sys.stderr)
            else:
                 print(f"Info: Market {odds_api_id} has missing sportKey. Will attempt soccer checks.", file=sys.stderr)


    all_completed_games_info = []
    processed_ids = set() # Track globally processed game IDs to avoid duplicates
    date_format = "iso"
    days_from = 3 # Check games from the last 3 days

    # --- 1. Check games with known sport keys ---
    print(f"Checking {len(games_by_known_sport)} known sport keys... {list(games_by_known_sport.keys())}") # Log only keys for brevity
    for sport_key, game_ids_for_sport in games_by_known_sport.items():
        unique_game_ids_for_sport = list(set(game_ids_for_sport)) # Remove duplicates for this sport batch

        if not unique_game_ids_for_sport:
            continue

        try:
            event_ids_param = ",".join(unique_game_ids_for_sport)
            print(f"Checking {len(unique_game_ids_for_sport)} games with known sportKey: {sport_key}...")
            response = requests.get(
                f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores/",
                params={
                    "apiKey": SPORTS_API_KEY,
                    "dateFormat": date_format,
                    "daysFrom": days_from,
                    "eventIds": event_ids_param
                }
            )
            response.raise_for_status()
            api_data = response.json()

            completed_this_batch = 0
            for game in api_data:
                game_id = game.get("id")
                # Check if ID is valid, was requested for this sport, and not already processed
                if not game_id or game_id not in unique_game_ids_for_sport or game_id in processed_ids:
                    continue

                completed = game.get("completed", False)
                if completed:
                    # Extract and validate game info (same logic as before)
                    game_info = extract_valid_completed_game_info(game)
                    if game_info:
                        all_completed_games_info.append(game_info)
                        processed_ids.add(game_id) # Mark as processed globally
                        completed_this_batch += 1

            print(f"Found {completed_this_batch} completed games with scores for known sportKey {sport_key}.")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching game completion status for known sportKey {sport_key}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"An unexpected error occurred checking completed games for known sportKey {sport_key}: {e}", file=sys.stderr)

    # --- 2. Check games with unknown/unrecognized sport keys (try ALL known keys) ---
    # Combine all known sport keys to iterate through
    all_known_sport_keys = SOCCER_SPORT_KEYS + NON_SOCCER_SPORT_KEYS # <-- Define combined list
    # Filter out IDs that might have already been found via a known sportKey check
    ids_to_check_fallback = list(ids_with_unknown_sport - processed_ids)

    if ids_to_check_fallback:
        print(f"Checking {len(ids_to_check_fallback)} games with unknown/unrecognized sportKey against all {len(all_known_sport_keys)} known leagues...")

        for potential_sport_key in all_known_sport_keys: # <-- Iterate through the combined list
            # Avoid re-checking if the ID was already processed by a previous iteration of this loop
            current_ids_to_check = list(ids_with_unknown_sport - processed_ids)
            if not current_ids_to_check:
                 print("All unknown/unrecognized sportKey games have been processed. Stopping fallback checks.")
                 break # No more IDs left to check

            try:
                event_ids_param_current = ",".join(current_ids_to_check)

                print(f"Attempting fallback check against key: {potential_sport_key} for {len(current_ids_to_check)} IDs...") # <-- Updated print
                response = requests.get(
                    f"https://api.the-odds-api.com/v4/sports/{potential_sport_key}/scores/",
                    params={
                        "apiKey": SPORTS_API_KEY,
                        "dateFormat": date_format,
                        "daysFrom": days_from,
                        "eventIds": event_ids_param_current
                    }
                )
                response.raise_for_status()
                api_data = response.json()

                completed_this_fallback_key = 0
                for game in api_data:
                    game_id = game.get("id")
                    # Check if ID is valid, was in the unknown list, and not already processed
                    if not game_id or game_id not in ids_with_unknown_sport or game_id in processed_ids:
                        continue

                    completed = game.get("completed", False)
                    if completed:
                        game_info = extract_valid_completed_game_info(game)
                        if game_info:
                            # Add the sport key we found it under for potential future use/debugging
                            game_info["found_under_sportKey"] = potential_sport_key # <-- Optional: Add found key
                            all_completed_games_info.append(game_info)
                            processed_ids.add(game_id) # Mark as processed globally
                            completed_this_fallback_key += 1

                if completed_this_fallback_key > 0:
                     print(f"Found {completed_this_fallback_key} completed games with scores checking against fallback key {potential_sport_key}.") # <-- Updated print

            except requests.exceptions.RequestException as e:
                # Don't print error for 404/422 if it's just because the game ID isn't in this sport key
                if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code in [404, 422]:
                     print(f"Info: No results found for pending IDs checking against {potential_sport_key} (HTTP {e.response.status_code}). This is expected if IDs belong to other sports.") # <-- Updated print
                else:
                    print(f"Error fetching game completion status checking against fallback key {potential_sport_key}: {e}", file=sys.stderr) # <-- Updated print
            except Exception as e:
                print(f"An unexpected error occurred checking completed games against fallback key {potential_sport_key}: {e}", file=sys.stderr) # <-- Updated print


    total_checked_count = len(markets_to_check)
    print(f"Completed checks. Found {len(all_completed_games_info)} total completed games with scores across all checks for {total_checked_count} markets provided.")
    return all_completed_games_info

def set_game_result(
    market_address: str,
    home_score: int,
    away_score: int,
    status: str = "Completed"
) -> Dict[str, Any]:
    """Sets the final score and status for a market after the game has completed."""
    try:
        payload = {
            "homeScore": home_score,
            "awayScore": away_score,
            "status": status
        }
        print(f"Setting game result for market {market_address} with home score {home_score}, away score {away_score}.")
        endpoint = f"/api/market/{market_address}/settle"
        result = api_post(endpoint, payload)
        print(f"Successfully settled market {market_address} with home score {home_score}, away score {away_score}.")
        return {
            "status": "success",
            "market_address": market_address,
            "home_score": home_score,
            "away_score": away_score,
            "game_status": status
        }
    except Exception as e:
        error_message = f"Error settling market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}

def get_unsettled_markets(status_filter: str = None) -> List[Dict[str, Any]]:
    """Gets unsettled markets with option to filter by status."""
    try:
        markets = get_all_markets()
        
        # Filter markets that are not settled (no final score)
        unsettled_markets = []
        for market in markets:
            # Apply status filter if provided
            if status_filter and market.get("status") != status_filter:
                continue
                
            # Check if market has been settled
            if not market.get("gameEnded", False) and market.get("homeScore") is None and market.get("awayScore") is None:
                unsettled_markets.append(market)
        print(f"Found {len(unsettled_markets)} unsettled markets.")
        return unsettled_markets
    except Exception as e:
        print(f"Error getting unsettled markets: {e}", file=sys.stderr)
        return []

