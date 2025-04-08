#!/usr/bin/env python3
import sys
import requests
import os
import datetime
import time
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
API_URL = os.getenv("API_URL", "http://localhost:3000") # Default if not set

if not SPORTS_API_KEY:
    print("Error: SPORTS_API_KEY not found in environment variables.", file=sys.stderr)
    # Consider raising an exception or exiting if the key is essential
if not API_URL:
    print("Warning: API_URL not found, defaulting to http://localhost:3000", file=sys.stderr)


# Import Agent SDK components
from agents import Agent, function_tool

# Import tool functions (assuming they are defined elsewhere, e.g., in agentGroup.py or a tools module)
# If tools are in agentGroup.py, they need to be importable or moved.
# For now, we define placeholders or assume they are globally available where this agent is used.
# from .agentGroup import get_nba_games, create_betting_market, get_existing_markets
# Placeholder definitions if not imported:
@function_tool
def get_nba_games() -> List[Dict[str, Any]]:
    """Fetches today's NBA games from The Odds API."""
    if not SPORTS_API_KEY:
        print("Error: Cannot fetch NBA games, SPORTS_API_KEY is missing.", file=sys.stderr)
        return []

    # Define the sport and region
    sport = "basketball_nba"
    regions = "us"
    markets = "h2h" # Head-to-head market is sufficient to get game details
    odds_format = "decimal"
    date_format = "iso"

    # Calculate 'today' in UTC for commenceTime filtering
    today_utc = datetime.datetime.now(datetime.timezone.utc).date()
    start_of_day_utc = datetime.datetime.combine(today_utc, datetime.time.min, tzinfo=datetime.timezone.utc)
    # Explicitly set end time to avoid microseconds from time.max
    end_of_day_utc = datetime.datetime.combine(today_utc, datetime.time(23, 59, 59), tzinfo=datetime.timezone.utc)

    # Format using strftime to ensure YYYY-MM-DDTHH:MM:SSZ format
    commence_time_from = start_of_day_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    commence_time_to = end_of_day_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

    try:
        response = requests.get(
            f"https://api.the-odds-api.com/v4/sports/{sport}/odds",
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
        games = []
        for game in games_data:
             # Convert ISO commence_time to Unix timestamp (integer seconds)
            commence_dt = datetime.datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            commence_timestamp = int(commence_dt.timestamp())
            games.append({
                "id": game["id"], # Odds API specific game ID
                "home_team": game["home_team"],
                "away_team": game["away_team"],
                "commence_time": game["commence_time"], # Keep ISO for reference?
                "game_timestamp": commence_timestamp, # Add Unix timestamp
            })
        print(f"Successfully fetched {len(games)} NBA games for today.")
        return games

    except requests.exceptions.RequestException as e:
        print(f"Error fetching NBA games from The Odds API: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred in get_nba_games: {e}", file=sys.stderr)
        return []


@function_tool
def create_betting_market(
    home_team: str,
    away_team: str,
    game_timestamp: int, # Expecting Unix timestamp
    odds_api_id: str,
    home_odds: Optional[int] = None, # Market Creation Agent shouldn't set odds
    away_odds: Optional[int] = None  # Market Creation Agent shouldn't set odds
) -> Dict[str, Any]:
    """Creates a new betting market via the smart contract API."""
    if not API_URL:
        print("Error: Cannot create market, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}

    # The agent instructions say *not* to set odds, so we ignore home_odds/away_odds
    payload = {
        "homeTeam": home_team,
        "awayTeam": away_team,
        "gameTimestamp": game_timestamp, # API expects Unix timestamp directly
        "oddsApiId": odds_api_id,
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
        return {"status": "success", "market": result.get("market", result)} # Adapt based on actual API response structure
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error creating market for {home_team} vs {away_team}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message}
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error creating market for {home_team} vs {away_team}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message}
    except Exception as e:
         error_message = f"An unexpected error occurred in create_betting_market: {e}"
         print(error_message, file=sys.stderr)
         return {"status": "error", "message": error_message}


@function_tool
def get_existing_markets() -> List[Dict[str, Any]]:
    """Fetches all existing betting markets from the smart contract API."""
    if not API_URL:
        print("Error: Cannot get existing markets, API_URL is not configured.", file=sys.stderr)
        return []

    try:
        url = f"{API_URL}/api/markets"
        response = requests.get(url)
        response.raise_for_status()
        markets = response.json()
        # The API response seems to be a list directly
        # We need to ensure each market dict has an 'odds_api_id' field for comparison
        # Let's assume the API returns 'oddsApiId' field in each market object.
        # If not, we might need to adjust the comparison logic in the agent.
        cleaned_markets = []
        if isinstance(markets, list):
             for market in markets:
                 if isinstance(market, dict) and "oddsApiId" in market:
                     # Rename oddsApiId to odds_api_id for consistency if needed, or just use it directly
                     market['odds_api_id'] = market.pop('oddsApiId') # Example renaming
                     cleaned_markets.append(market)
                 else:
                      print(f"Warning: Skipping market entry due to missing 'oddsApiId' or incorrect format: {market}", file=sys.stderr)
        else:
             print(f"Warning: Expected a list from /api/markets, but got {type(markets)}", file=sys.stderr)
             return []

        print(f"Successfully fetched {len(cleaned_markets)} existing markets with oddsApiId.")
        return cleaned_markets # Assuming the response is the list of markets
    except requests.exceptions.RequestException as e:
        print(f"Error fetching existing markets: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred in get_existing_markets: {e}", file=sys.stderr)
        return []

# Define the Market Creation Agent
market_creation_agent = Agent(
    name="Market Creation Agent",
    # handoff_description is used if this agent itself is part of a handoff list in another agent
    handoff_description="Specialist agent for creating betting markets for NBA games",
    instructions="""
    You are the Market Creation Agent. Your goal is to create betting markets for NBA games.
    1. Call `get_existing_markets` to find markets already created. These markets should contain an `odds_api_id`.
    2. Call `get_nba_games` to find today's NBA games. Each game should contain an `id` field which is the Odds API game ID.
    
    4. For each game  use the `create_betting_market` tool. Pass the `home_team`, `away_team`, `game_timestamp` (Unix timestamp), and the game `id` (as `odds_api_id` parameter) to the tool.
    
    6. Do NOT set initial odds (`home_odds`, `away_odds`) when calling `create_betting_market`; the Odds Manager Agent handles that.
    7. Report a summary of the markets you created (or attempted to create) and any errors encountered. If no new markets needed creation, state that clearly.
    """,
    tools=[get_nba_games, create_betting_market, get_existing_markets],
    model="gpt-4o-2024-11-20",
    # No context type needed if we remove the custom context logic
)

# Example of how this agent might be run (usually done by a Runner via Triage)
if __name__ == '__main__':
    # This part is just for testing the agent directly if needed
    from agents import Runner
    import asyncio

    async def test_market_creation():
        # Input prompt to trigger the agent's logic
        prompt = "Create markets for today's NBA games."
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
    # asyncio.run(test_market_creation())
    print("Market Creation Agent defined. Run agentGroup.py to test via Triage.") # Updated message 