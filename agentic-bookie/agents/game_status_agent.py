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


# --- Agent Definition ---

game_status_agent = Agent(
    name="Game Status Agent",
    handoff_description="Specialist agent for monitoring game start times and updating market status.",
    instructions="""
    You are the Game Status Agent. Your primary goal is to monitor NBA games associated with betting markets and signal when they have started.
    Your workflow should be as follows:
    1. Call `get_markets_to_check` to find markets that are not yet ready for betting (`isReadyForBetting` is false). These markets will have an `address` and an `oddsApiId`.
    2. If the list of markets to check is empty, your job is done for now. Report that no markets need checking and finish.
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
    9. After checking all markets from step 1, report a summary of the markets whose status you updated (list their addresses). If no games had started yet, state that.
    10. Call `sleep_tool` with the `duration_seconds` parameter set to 60 (e.g., `sleep_tool(duration_seconds=60)`) to wait for about 1 minute before repeating the process.
    11. Go back to step 1 to check for newly created markets or games that might have started since the last check. Continue this loop.
    """,
    tools=[
        get_markets_to_check,
        get_games_with_start_times,
        start_game_on_chain,
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