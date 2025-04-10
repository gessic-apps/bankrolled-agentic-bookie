#!/usr/bin/env python3
import sys
import requests
import os
import datetime
import time
from dateutil import parser as date_parser # For parsing ISO 8601 dates
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Add the project root to path if needed (adjust based on actual structure)
# project_root = Path(__file__).resolve().parent.parent
# if str(project_root) not in sys.path:
#     sys.path.append(str(project_root))

# Load environment variables from .env file
load_dotenv()
SPORTS_API_KEY = os.getenv("SPORTS_API_KEY")
API_URL = os.getenv("API_URL", "http://localhost:3000") # Default matching other agents

if not SPORTS_API_KEY:
    print("Error: SPORTS_API_KEY not found in environment variables.", file=sys.stderr)
if not API_URL:
    print(f"Warning: API_URL not found, defaulting to {API_URL}", file=sys.stderr)

# Import Agent SDK components
from agents import Agent, function_tool

# --- Tool Definitions ---

@function_tool
def sleep_tool(duration_seconds: int) -> str:
    """Pauses execution for a specified duration (in seconds)."""
    # Add basic validation
    if duration_seconds <= 0:
        return "Error: Sleep duration must be positive."
    print(f"Sleeping for {duration_seconds} seconds...")
    time.sleep(duration_seconds)
    return f"Slept for {duration_seconds} seconds."

@function_tool
def get_games_with_start_times() -> List[Dict[str, Any]]:
    """Fetches today's NBA games including their start times (ISO 8601 format) from The Odds API."""
    if not SPORTS_API_KEY:
        print("Error: Cannot fetch games, SPORTS_API_KEY is missing.", file=sys.stderr)
        return []

    sport = "basketball_nba"
    regions = "us"
    # Fetch markets necessary for odds (h2h), date format, etc.
    markets = "h2h"
    odds_format = "decimal"
    date_format = "iso"

    try:
        # Fetch game data including commence_time
        response = requests.get(
            f"https://api.the-odds-api.com/v4/sports/{sport}/odds", # Using the odds endpoint which includes commence_time
            params={
                "apiKey": SPORTS_API_KEY,
                "regions": regions,
                "markets": markets, # Need markets to get useful data, even if only using commence_time
                "oddsFormat": odds_format,
                "dateFormat": date_format,
            }
        )
        response.raise_for_status()
        api_data = response.json()

        games_data = []
        for game in api_data:
            game_id = game.get("id")
            start_time_str = game.get("commence_time") # ISO 8601 format string

            if not game_id or not start_time_str:
                print(f"Warning: Skipping game due to missing ID or start time: {game.get('id', 'N/A')}", file=sys.stderr)
                continue

            try:
                # Validate and maybe parse the start time if needed, but returning string is fine
                datetime.datetime.fromisoformat(start_time_str.replace("Z", "+00:00")) # Validate format
                games_data.append({
                    "odds_api_id": game_id,
                    "start_time_iso": start_time_str
                })
            except ValueError:
                 print(f"Warning: Could not parse start time for game {game_id}: {start_time_str}", file=sys.stderr)

        print(f"Successfully fetched start times for {len(games_data)} games from The Odds API.")
        return games_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching games/start times from The Odds API: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred in get_games_with_start_times: {e}", file=sys.stderr)
        return []

@function_tool
def get_markets_to_check() -> List[Dict[str, Any]]:
    """Fetches existing betting markets from the smart contract API and filters for those not yet ready for betting."""
    if not API_URL:
        print("Error: Cannot get markets, API_URL is not configured.", file=sys.stderr)
        return []

    try:
        url = f"{API_URL}/api/markets"
        response = requests.get(url)
        response.raise_for_status()
        all_markets_data = response.json()

        markets_to_check = []
        if isinstance(all_markets_data, list):
            for market in all_markets_data:
                # Check required fields and if the market is NOT ready for betting
                if isinstance(market, dict) and \
                   all(k in market for k in ["address", "oddsApiId", "isReadyForBetting"]) and \
                   market.get("isReadyForBetting") is False:
                    markets_to_check.append({
                        "address": market["address"],
                        "oddsApiId": market["oddsApiId"]
                        # Only include necessary fields
                    })
                elif isinstance(market, dict) and market.get("isReadyForBetting") is True:
                    pass # Skip markets already ready
                else:
                    print(f"Warning: Skipping market entry due to missing fields, incorrect format, or ready status: {market}", file=sys.stderr)
        else:
             print(f"Warning: Expected a list from /api/markets, but got {type(all_markets_data)}", file=sys.stderr)
             return []

        print(f"Found {len(markets_to_check)} markets that are not yet ready for betting.")
        return markets_to_check
    except requests.exceptions.RequestException as e:
        print(f"Error fetching existing markets: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred in get_markets_to_check: {e}", file=sys.stderr)
        return []


@function_tool
def start_game_on_chain(market_address: str) -> Dict[str, Any]:
    """Signals that a game corresponding to a market has started by calling the game-status API endpoint."""
    if not API_URL:
        print("Error: Cannot start game, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}

    # The API expects {'action': 'start'} based on server.js
    payload = {"action": "start"} # Corrected payload

    try:
        url = f"{API_URL}/api/market/{market_address}/game-status"
        print(f"Attempting to start game: POST {url} for market {market_address} with payload: {payload}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Successfully signaled game start for market {market_address}. Response: {result}")
        return {"status": "success", "market_address": market_address, "api_response": result}
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error starting game for market {market_address}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error starting game for market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except Exception as e:
         error_message = f"An unexpected error occurred in start_game_on_chain: {e}"
         print(error_message, file=sys.stderr)
         return {"status": "error", "message": error_message, "market_address": market_address}

@function_tool
def check_completed_games(game_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Checks if games with the given IDs are completed by querying the scores endpoint.
    
    Args:
        game_ids: List of game IDs (odds_api_id) to check
        
    Returns:
        List of dictionaries containing information about completed games:
        [
            {
                "odds_api_id": str,
                "completed": bool,
                "home_team": str,
                "away_team": str,
                "home_score": Optional[str],
                "away_score": Optional[str],
                "last_update": Optional[str]
            },
            ...
        ]
    """
    if not SPORTS_API_KEY:
        print("Error: Cannot fetch games, SPORTS_API_KEY is missing.", file=sys.stderr)
        return []
    
    if not game_ids:
        print("Warning: No game IDs provided to check_completed_games.", file=sys.stderr)
        return []
    
    sport = "basketball_nba"
    date_format = "iso"
    # Get games from the last 3 days (max allowed) to ensure we capture recently completed games
    days_from = 3
    
    try:
        # Use comma-separated game IDs to filter for specific games
        event_ids_param = ",".join(game_ids)
        
        # Fetch game data from scores endpoint
        print(f"Fetching completion status for {len(game_ids)} games...")
        response = requests.get(
            f"https://api.the-odds-api.com/v4/sports/{sport}/scores/",
            params={
                "apiKey": SPORTS_API_KEY,
                "dateFormat": date_format,
                "daysFrom": days_from,
                "eventIds": event_ids_param
            }
        )
        response.raise_for_status()
        api_data = response.json()
        
        completed_games = []
        for game in api_data:
            game_id = game.get("id")
            completed = game.get("completed", False)
            
            game_info = {
                "odds_api_id": game_id,
                "completed": completed,
                "home_team": game.get("home_team"),
                "away_team": game.get("away_team"),
                "home_score": None,
                "away_score": None,
                "last_update": game.get("last_update")
            }
            
            # Add scores if available
            scores = game.get("scores")
            if scores and isinstance(scores, list):
                for team_score in scores:
                    team_name = team_score.get("name")
                    score = team_score.get("score")
                    
                    if team_name == game_info["home_team"]:
                        game_info["home_score"] = score
                    elif team_name == game_info["away_team"]:
                        game_info["away_score"] = score
            
            completed_games.append(game_info)
        
        print(f"Successfully fetched completion status for {len(completed_games)} games.")
        return completed_games
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching game completion status: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred in check_completed_games: {e}", file=sys.stderr)
        return []

@function_tool
def set_game_result(market_address: str, home_score: str, away_score: str) -> Dict[str, Any]:
    """
    Sets the final result for a game by calling the game-status API endpoint.
    
    Args:
        market_address: The address of the market to update
        home_score: The final score of the home team
        away_score: The final score of the away team
        
    Returns:
        Dictionary with status information
    """
    if not API_URL:
        print("Error: Cannot set game result, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}
    
    # The API expects {'action': 'set-result', 'homeScore': X, 'awayScore': Y}
    payload = {
        "action": "set-result",
        "homeScore": int(home_score),
        "awayScore": int(away_score)
    }
    
    try:
        url = f"{API_URL}/api/market/{market_address}/game-status"
        print(f"Attempting to set game result: POST {url} for market {market_address} with payload: {payload}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Successfully set game result for market {market_address}. Response: {result}")
        return {"status": "success", "market_address": market_address, "api_response": result}
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error setting game result for market {market_address}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error setting game result for market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except Exception as e:
        error_message = f"An unexpected error occurred in set_game_result: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}

@function_tool
def get_active_markets() -> List[Dict[str, Any]]:
    """Fetches active betting markets from the smart contract API."""
    if not API_URL:
        print("Error: Cannot get markets, API_URL is not configured.", file=sys.stderr)
        return []
    
    try:
        url = f"{API_URL}/api/markets"
        response = requests.get(url)
        response.raise_for_status()
        all_markets_data = response.json()
        
        active_markets = []
        if isinstance(all_markets_data, list):
            for market in all_markets_data:
                # Check if market is ready for betting, started but not completed
                if isinstance(market, dict) and \
                   all(k in market for k in ["address", "oddsApiId"]) and \
                   market.get("gameStarted", False) is True and \
                   market.get("gameEnded", False) is False:
                    active_markets.append({
                        "address": market["address"],
                        "oddsApiId": market["oddsApiId"]
                    })
        else:
            print(f"Warning: Expected a list from /api/markets, but got {type(all_markets_data)}", file=sys.stderr)
            return []
        
        print(f"Found {len(active_markets)} active markets that have started but not ended.")
        return active_markets
    except requests.exceptions.RequestException as e:
        print(f"Error fetching active markets: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred in get_active_markets: {e}", file=sys.stderr)
        return []

# --- Agent Definition ---

game_status_agent = Agent(
    name="Game Status Agent",
    handoff_description="Specialist agent for monitoring game start times and updating market status.",
    instructions="""
    You are the Game Status Agent. Your primary goals are to:
    1. Monitor NBA games associated with betting markets and signal when they have started.
    2. Check if games have completed and update the market accordingly with final scores.
    
    Your workflow should be as follows:
    
    PART A: Checking for games that need to be started
    
    1. Call `get_markets_to_check` to find markets that are not yet ready for betting (`isReadyForBetting` is false). These markets will have an `address` and an `oddsApiId`.
    2. If the list of markets to check is empty, proceed to PART B.
    3. Call `get_games_with_start_times` to fetch the scheduled start times (in ISO 8601 UTC format) for upcoming NBA games using their `odds_api_id`.
    4. Create a mapping from `odds_api_id` to `start_time_iso` from the results of step 3.
    5. Iterate through the markets identified in step 1.
    6. For each market, use its `oddsApiId` to look up the corresponding game's `start_time_iso` from the mapping created in step 4.
    7. If a start time is found for the market's game:
        a. Parse the `start_time_iso` string into a datetime object using dateutil.parser.isoparse.
        b. Get the current UTC time using datetime.datetime.now(datetime.timezone.utc).
        c. Compare the current UTC time with the game's start time.
        d. If the current UTC time is *equal to or later than* the game's start time, it means the game has started. Call `start_game_on_chain` with the market's `address`.
    8. Keep track of which markets you successfully signaled as started.
    
    PART B: Checking for games that have completed
    
    9. Call `get_active_markets` to find markets that have started but not yet ended. These will have an `address` and an `oddsApiId`.
    10. If there are active markets, get the list of odds_api_ids from these markets.
    11. Call `check_completed_games` with the list of odds_api_ids to check if any of these games have completed.
    12. For each completed game from the response:
        a. Find the corresponding market from the active markets list.
        b. Extract the home score and away score from the completed game data.
        c. Call `set_game_result` with the market's address and the final scores.
    13. Keep track of which markets you successfully updated with final scores.
    
    PART C: Reporting and looping
    
    14. After checking all markets, report a summary of the markets whose status you updated (both started and completed). If no status updates were made, state that.
    15. Call `sleep_tool` with the `duration_seconds` parameter set to 60 (e.g., `sleep_tool(duration_seconds=60)`) to wait for about 1 minute before repeating the process.
    16. Go back to step 1 to check for new markets or games with changed status. Continue this loop.
    """,
    tools=[
        get_markets_to_check,
        get_active_markets,
        get_games_with_start_times,
        check_completed_games,
        start_game_on_chain,
        set_game_result,
        sleep_tool
    ],
    # DO NOT CHANGE THIS MODEL FROM THE CURRENT SETTING
    model="gpt-4o-2024-11-20",
    # No context type needed
)

# Example of how this agent might be run (usually done by a Runner via Triage)
if __name__ == '__main__':
    # This part is just for testing the agent directly if needed
    from agents import Runner
    import asyncio

    async def test_game_status_monitoring():
        # Input prompt to trigger the agent's logic loop implicitly
        prompt = "Monitor game start times and update market status accordingly. Repeat the check periodically."
        print(f"--- Running Game Status Agent with prompt: '{prompt}' ---")
        # Ensure environment variables are loaded if running directly
        if not SPORTS_API_KEY:
             print("Error: Missing SPORTS_API_KEY or API_URL in .env file. Cannot run test.", file=sys.stderr)
             return

        # Note: The agent's instructions imply a loop. Running it once will perform one cycle.
        # A real runner/orchestrator might re-invoke the agent periodically or based on events.
        result = await Runner.run(game_status_agent, prompt)
        print("--- Game Status Agent Result (One Cycle) ---")
        print(result.final_output)
        print("-------------------------------------------")

    # To run the test: asyncio.run(test_game_status_monitoring())
    # Remember that this only runs *one* cycle. The agent's instructions describe a continuous loop.
    print("Game Status Agent defined. Run agentGroup.py or similar orchestrator to manage its lifecycle.") 