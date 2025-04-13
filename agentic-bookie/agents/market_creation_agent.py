#!/usr/bin/env python3
import sys
import requests
import os
import datetime
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pydantic import BaseModel

# Add the project root to path if needed (adjust based on actual structure)
# project_root = Path(__file__).resolve().parent.parent
# if str(project_root) not in sys.path:
#     sys.path.append(str(project_root))

# Load environment variables from .env file
load_dotenv()
SPORTS_API_KEY = os.getenv("SPORTS_API_KEY")
API_URL = os.getenv("API_URL", "http://localhost:3000") # Default if not set

if not SPORTS_API_KEY:
    print("Error: SPORTS_API_KEY not found in environment variables.", file=sys.stderr)
    # Consider raising an exception or exiting if the key is essential
if not API_URL:
    print("Warning: API_URL not found, defaulting to http://localhost:3000", file=sys.stderr)

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

# Import Agent SDK components
from agents import Agent, function_tool

# Import tool functions (assuming they are defined elsewhere, e.g., in agentGroup.py or a tools module)
# If tools are in agentGroup.py, they need to be importable or moved.
# For now, we define placeholders or assume they are globally available where this agent is used.
# from .agentGroup import get_nba_games, create_betting_market, get_existing_markets

# Define the list of target sports
SUPPORTED_SPORT_KEYS = [
    "basketball_nba",
    "soccer_epl", # English Premier League
    "soccer_france_ligue_one",
    "soccer_italy_serie_a",
    "soccer_germany_bundesliga",
    "soccer_spain_la_liga",
    "soccer_uefa_champs_league",
    "soccer_uefa_europa_league"
]

# Placeholder definitions if not imported:
@function_tool
def fetch_upcoming_games(sport_keys: List[str]) -> List[str]:
    """Fetches upcoming games (today and tomorrow) for the specified sports from The Odds API."""
    if not SPORTS_API_KEY:
        print("Error: Cannot fetch games, SPORTS_API_KEY is missing.", file=sys.stderr)
        return []
    if not sport_keys:
        print("Warning: No sport_keys provided to fetch_upcoming_games.", file=sys.stderr)
        return []

    all_games = []
    processed_game_ids = set()

    # Define the sport and region
    regions = "us" # Adjust if necessary for soccer leagues, though 'us' often covers major international sports
    markets = "h2h" # Head-to-head market is sufficient to get game details
    odds_format = "decimal"
    date_format = "iso"

    # Calculate time filtering range to include both today and tomorrow
    today_utc = datetime.datetime.now(datetime.timezone.utc).date()
    # Start from current time to get today's games
    start_of_period_utc = datetime.datetime.now(datetime.timezone.utc)
    # End at the end of tomorrow
    tomorrow_utc = today_utc + datetime.timedelta(days=1)
    end_of_period_utc = datetime.datetime.combine(tomorrow_utc, datetime.time(23, 59, 59), tzinfo=datetime.timezone.utc)

    # Format using strftime to ensure YYYY-MM-DDTHH:MM:SSZ format
    commence_time_from = start_of_period_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    commence_time_to = end_of_period_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

    for sport_key in sport_keys:
        print(f"Fetching games for sport: {sport_key}...")
        try:
            response = requests.get(
                f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds",
                params={
                    "apiKey": SPORTS_API_KEY,
                    "regions": regions,
                    "markets": markets,
                    "oddsFormat": odds_format,
                    "dateFormat": date_format,
                    "commenceTimeFrom": commence_time_from,
                    "commenceTimeTo": commence_time_to,
                }
            )
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            games_data = response.json()

            # Extract relevant game details
            games_count = 0
            for game in games_data:
                game_id = game.get("id")
                if not game_id or game_id in processed_game_ids:
                    continue # Skip if ID missing or game already added from another sport query (unlikely but possible)

                # Convert ISO commence_time to Unix timestamp (integer seconds)
                commence_dt = datetime.datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
                commence_timestamp = int(commence_dt.timestamp())

                game_info = {
                    "id": game_id, # Odds API specific game ID
                    "sport_key": sport_key, # Add sport key for context
                    "home_team": game["home_team"],
                    "away_team": game["away_team"],
                    "commence_time": game["commence_time"], # Keep ISO for reference
                    "game_timestamp": commence_timestamp, # Add Unix timestamp
                }
                all_games.append(json.dumps(game_info))
                processed_game_ids.add(game_id)
                games_count += 1
            print(f"Successfully fetched {games_count} games for {sport_key}.")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching games for {sport_key} from The Odds API: {e}", file=sys.stderr)
            # Continue to next sport key if one fails
        except Exception as e:
            print(f"An unexpected error occurred fetching games for {sport_key}: {e}", file=sys.stderr)
            # Continue to next sport key

    print(f"Total unique games fetched across all sports: {len(all_games)}")
    return all_games

# Implementation function
def create_betting_market_impl(
    home_team: str,
    away_team: str,
    game_timestamp: int, # Expecting Unix timestamp
    game_id: str, # Renamed from odds_api_id
    home_odds: Optional[int] = None, # Market Creation Agent shouldn't set odds
    away_odds: Optional[int] = None  # Market Creation Agent shouldn't set odds
) -> str:
    """Creates a new betting market via the smart contract API."""
    if not API_URL:
        print("Error: Cannot create market, API_URL is not configured.", file=sys.stderr)
        return json.dumps({"status": "error", "message": "API_URL not configured"})

    # Double-check market doesn't already exist
    try:
        existing_markets = get_existing_markets_impl()
        # Convert market objects to JSON strings for check_event_exists
        existing_markets_json = [json.dumps(market) for market in existing_markets]
        if check_event_exists_impl(game_id, existing_markets_json):
            print(f"DUPLICATE PREVENTION: Market for game ID {game_id} ({home_team} vs {away_team}) already exists. Skipping creation.")
            return json.dumps({
                "status": "skipped", 
                "message": f"Market for game ID {game_id} already exists",
                "game_id": game_id,
                "home_team": home_team,
                "away_team": away_team
            })
    except Exception as e:
        print(f"Warning: Error during duplicate check: {e}. Will attempt market creation anyway.", file=sys.stderr)

    # The agent instructions say *not* to set odds, so we ignore home_odds/away_odds
    payload = {
        "homeTeam": home_team,
        "awayTeam": away_team,
        "gameTimestamp": game_timestamp, # API expects Unix timestamp directly
        "oddsApiId": game_id, # Use the passed game_id for the internal API's oddsApiId field
        # Do not include homeOdds or awayOdds
    }

    try:
        url = f"{API_URL}/api/market/create"
        print(f"Attempting to create market: POST {url} with payload: {payload}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Successfully created market for {home_team} vs {away_team}. Response: {result}")
        # Assuming the API returns a success status and market details
        return json.dumps({"status": "success", "market": result.get("market", result)}) 
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error creating market for {home_team} vs {away_team}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        return json.dumps({"status": "error", "message": error_message})
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error creating market for {home_team} vs {away_team}: {e}"
        print(error_message, file=sys.stderr)
        return json.dumps({"status": "error", "message": error_message})
    except Exception as e:
         error_message = f"An unexpected error occurred in create_betting_market: {e}"
         print(error_message, file=sys.stderr)
         return json.dumps({"status": "error", "message": error_message})

# Function tool for agent to use
@function_tool
def create_betting_market(
    home_team: str,
    away_team: str,
    game_timestamp: int, # Expecting Unix timestamp
    game_id: str, # Renamed from odds_api_id
    home_odds: Optional[int] = None, # Market Creation Agent shouldn't set odds
    away_odds: Optional[int] = None  # Market Creation Agent shouldn't set odds
) -> str:
    """Creates a new betting market via the smart contract API."""
    return create_betting_market_impl(
        home_team=home_team,
        away_team=away_team,
        game_timestamp=game_timestamp,
        game_id=game_id,
        home_odds=home_odds,
        away_odds=away_odds
    )

# Implementation function
def get_existing_markets_impl() -> List[Dict[str, Any]]:
    """Fetches all existing betting markets from the smart contract API."""
    if not API_URL:
        print("Error: Cannot get existing markets, API_URL is not configured.", file=sys.stderr)
        return []

    try:
        url = f"{API_URL}/api/markets"
        print(f"Fetching existing markets from: {url}")
        response = requests.get(url)
        response.raise_for_status()
        markets = response.json()
        
        # Return market objects directly as dictionaries
        cleaned_markets = []
        if isinstance(markets, list):
            for market in markets:
                if isinstance(market, dict) and "oddsApiId" in market:
                    # Create a simplified market object with just the essential fields
                    market_data = {
                        "oddsApiId": market["oddsApiId"],
                        # Include other fields if they exist
                        "address": market.get("address"),
                        "homeTeam": market.get("homeTeam"),
                        "awayTeam": market.get("awayTeam"),
                        "gameTimestamp": market.get("gameTimestamp")
                    }
                    cleaned_markets.append(market_data)
                else:
                    print(f"Warning: Skipping market entry due to missing 'oddsApiId': {market}", file=sys.stderr)
        else:
            print(f"Warning: Expected a list from /api/markets, but got {type(markets)}", file=sys.stderr)
            return []

        print(f"Successfully fetched {len(cleaned_markets)} existing markets with oddsApiId.")
        # Print the IDs for debugging
        try:
            oddsApiIds = [m.get('oddsApiId') for m in cleaned_markets]
            print(f"Existing market IDs: {oddsApiIds}")
        except Exception as e:
            print(f"Error parsing market IDs: {e}", file=sys.stderr)
            
        return cleaned_markets
    except requests.exceptions.RequestException as e:
        print(f"Error fetching existing markets: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred in get_existing_markets: {e}", file=sys.stderr)
        return []

# Function tool for agent to use
@function_tool
def get_existing_markets() -> List[str]:
    """Fetches all existing betting markets from the smart contract API."""
    markets = get_existing_markets_impl()
    # Convert market objects to JSON strings for compatibility with the agent
    return [json.dumps(market) for market in markets]

# Implementation function
def check_event_exists_impl(game_id: str, existing_markets: List[str]) -> bool:
    """Checks if a betting market already exists for a given Odds API game ID within a provided list.

    Args:
        game_id: The unique identifier (id) of the game from The Odds API.
        existing_markets: A list of existing market JSON strings.

    Returns:
        True if a market exists for this game_id in the list, False otherwise.
    """
    print(f"Checking existence for game_id: {game_id} against {len(existing_markets)} provided markets.")

    if not isinstance(existing_markets, list):
        print("Error: check_event_exists received invalid existing_markets data (not a list).", file=sys.stderr)
        return False

    # Create a set of all oddsApiIds for more efficient lookup
    existing_ids = set()
    
    for market_str in existing_markets:
        try:
            # Parse the JSON string into a dict
            if isinstance(market_str, str):
                market_data = json.loads(market_str)
                if "oddsApiId" in market_data:
                    existing_ids.add(market_data["oddsApiId"])
            elif isinstance(market_str, dict) and "oddsApiId" in market_str:
                # Backward compatibility
                existing_ids.add(market_str["oddsApiId"])
            else:
                print(f"Warning: Market data item has unexpected format", file=sys.stderr)
        except Exception as e:
            print(f"Error processing market data item: {e}", file=sys.stderr)
            continue

    # Print the set of existing IDs for debugging
    print(f"Existing oddsApiIds: {existing_ids}")
    
    # Check if game_id exists in the set
    exists = game_id in existing_ids
    print(f"Market exists for game_id {game_id}: {exists}")
    return exists

# Function tool for agent to use
@function_tool
def check_event_exists(game_id: str, existing_markets: List[str]) -> bool:
    """Checks if a betting market already exists for a given Odds API game ID within a provided list.

    Args:
        game_id: The unique identifier (id) of the game from The Odds API.
        existing_markets: A list of existing market JSON strings.

    Returns:
        True if a market exists for this game_id in the list, False otherwise.
    """
    return check_event_exists_impl(game_id, existing_markets)

# Create implementation function
def batch_process_markets_impl(upcoming_games: List[str]) -> str:
    """Process multiple game events at once, checking which ones need markets created and creating them in batch.
    
    Args:
        upcoming_games: A list of JSON string representations of upcoming games.
        
    Returns:
        A JSON string with summary of processed games and results.
    """
    if not API_URL:
        error_message = "Error: Cannot process markets, API_URL is not configured."
        print(error_message, file=sys.stderr)
        return json.dumps({"status": "error", "message": error_message})
    
    try:
        # Step 1: Fetch existing markets once
        existing_markets = get_existing_markets_impl()
        
        # Extract existing IDs for efficient lookup
        existing_ids = set()
        for market_data in existing_markets:
            if isinstance(market_data, dict) and "oddsApiId" in market_data:
                existing_ids.add(market_data["oddsApiId"])
                
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
        
        for game_str in upcoming_games:
            try:
                game = json.loads(game_str)
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
                payload = {
                    "homeTeam": home_team,
                    "awayTeam": away_team,
                    "gameTimestamp": game_timestamp,
                    "oddsApiId": game_id
                }
                
                url = f"{API_URL}/api/market/create"
                print(f"Attempting to create market: POST {url} with payload: {payload}")
                response = requests.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                print(f"Successfully created market for {home_team} vs {away_team}. Response: {result}")
                
                results["markets_created"] += 1
                results["created"].append({
                    "game_id": game_id,
                    "home_team": home_team,
                    "away_team": away_team,
                    "address": result.get("market", {}).get("address", "unknown")
                })
                
                # Add to existing IDs to prevent duplicate creation in the same batch
                existing_ids.add(game_id)
                
            except requests.exceptions.HTTPError as e:
                error_message = f"HTTP Error creating market for {home_team} vs {away_team}: {e.response.status_code} - {e.response.text}"
                print(error_message, file=sys.stderr)
                results["errors"] += 1
                results["failed"].append({
                    "game_id": game_id,
                    "home_team": home_team,
                    "away_team": away_team,
                    "error": error_message
                })
            except Exception as e:
                error_message = f"An unexpected error occurred processing game {game_id if 'game_id' in locals() else 'unknown'}: {e}"
                print(error_message, file=sys.stderr)
                results["errors"] += 1
                results["failed"].append({
                    "game_id": game_id if 'game_id' in locals() else "unknown",
                    "error": error_message
                })
                
        return json.dumps(results)
        
    except Exception as e:
        error_message = f"An unexpected error occurred in batch_process_markets: {e}"
        print(error_message, file=sys.stderr)
        return json.dumps({"status": "error", "message": error_message})

# Now define the function tool that calls the implementation
@function_tool
def batch_process_markets(upcoming_games: List[str]) -> str:
    """Process multiple game events at once, checking which ones need markets created and creating them in batch.
    
    Args:
        upcoming_games: A list of JSON string representations of upcoming games.
        
    Returns:
        A JSON string with summary of processed games and results.
    """
    return batch_process_markets_impl(upcoming_games)

# Define the Market Creation Agent
market_creation_agent = Agent(
    name="Market Creation Agent",
    # handoff_description is used if this agent itself is part of a handoff list in another agent
    handoff_description="Specialist agent for creating betting markets for NBA games",
    instructions="""
    You are the Market Creation Agent. Your goal is to create betting markets for upcoming games (today and tomorrow) across supported sports (NBA and major Soccer leagues) that do not already exist.
    
    Follow these steps:
    1. Call `fetch_upcoming_games` with the list of supported sport keys to find upcoming games for today and tomorrow. Each game is returned as a JSON string.
    2. Call `batch_process_markets` with the list of upcoming games from step 1. This function will:
       a. Fetch existing markets
       b. Check which games need new markets 
       c. Create markets for games that don't already have one
       d. Return a summary of results
    3. Report a summary of the markets created based on the results from step 2. Include:
       - Total number of markets created
       - Total number of markets skipped (already existed)
       - List of market details (game ID, teams) that were created
       - Any errors that occurred
       
    This batch approach is more efficient than processing games one-by-one.
    """,
    # Ensure all necessary tools are available
    tools=[fetch_upcoming_games, batch_process_markets, get_existing_markets, check_event_exists, create_betting_market],
    # DO NOT CHANGE THIS MODEL FROM THE CURRENT SETTING
    model="gpt-4o-2024-11-20", # Adjusted model based on previous message
    # No context type needed if we remove the custom context logic
)

# Example of how this agent might be run (usually done by a Runner via Triage)
if __name__ == '__main__':
    # This part is just for testing the agent directly if needed
    from agents import Runner
    import asyncio

    async def test_market_creation():
        # Input prompt to trigger the agent's logic
        prompt = f"Create markets for upcoming games in supported sports: {', '.join(SUPPORTED_SPORT_KEYS)}."
        print(f"--- Running Market Creation Agent with prompt: '{prompt}' ---")
        # Ensure environment variables are loaded if running directly
        if not SPORTS_API_KEY or not API_URL:
             print("Error: Missing SPORTS_API_KEY or API_URL in .env file. Cannot run test.", file=sys.stderr)
             return
        result = await Runner.run(market_creation_agent, prompt)
        print("--- Market Creation Agent Result ---")
        print(result.final_output)
        print("------------------------------------")

    # Note: Running requires tool implementations or proper imports
    asyncio.run(test_market_creation())
    print("Market Creation Agent defined. Run agentGroup.py to test via Triage.") # Updated message 