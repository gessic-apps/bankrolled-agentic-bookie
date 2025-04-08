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
API_URL = os.getenv("API_URL", "http://localhost:3000") # Default matching market_creation_agent

if not SPORTS_API_KEY:
    print("Error: SPORTS_API_KEY not found in environment variables.", file=sys.stderr)
if not API_URL:
    print(f"Warning: API_URL not found, defaulting to {API_URL}", file=sys.stderr)

# Import Agent SDK components
from agents import Agent, function_tool

# Import tool functions (assuming they are defined elsewhere, e.g., in agentGroup.py or a tools module)
# Placeholder definitions if not imported:
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
        markets_data = response.json()

        # Ensure the response is a list and contains required fields
        cleaned_markets = []
        if isinstance(markets_data, list):
            for market in markets_data:
                if isinstance(market, dict) and all(k in market for k in ["address", "oddsApiId", "isReadyForBetting"]):
                    # Rename oddsApiId for consistency within this agent if needed, or use directly
                    # market['odds_api_id'] = market.pop('oddsApiId')
                    cleaned_markets.append(market)
                else:
                    print(f"Warning: Skipping market entry due to missing required fields or incorrect format: {market}", file=sys.stderr)
        else:
             print(f"Warning: Expected a list from /api/markets, but got {type(markets_data)}", file=sys.stderr)
             return []

        print(f"Successfully fetched {len(cleaned_markets)} existing markets with required fields.")
        return cleaned_markets
    except requests.exceptions.RequestException as e:
        print(f"Error fetching existing markets: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred in get_existing_markets: {e}", file=sys.stderr)
        return []


@function_tool
def update_odds_for_market(market_address: str, home_odds: float, away_odds: float) -> Dict[str, Any]:
    """Updates the odds for a specific market. Expects decimal floats, converts to integer * 1000 for API call."""
    if not API_URL:
        print("Error: Cannot update odds, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}

    # Convert decimal floats to integer format (decimal * 1000)
    try:
        home_odds_int = int(home_odds * 1000)
        away_odds_int = int(away_odds * 1000)
    except (ValueError, TypeError) as e:
        error_message = f"Error converting decimal odds ({home_odds}, {away_odds}) to integer format: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}

    # Payload sends the converted integer values
    payload = {
        "homeOdds": home_odds_int,
        "awayOdds": away_odds_int
    }

    try:
        url = f"{API_URL}/api/market/{market_address}/update-odds"
        print(f"Attempting to update odds: POST {url} with payload: {payload} (converted from {home_odds}, {away_odds})")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Successfully updated odds for market {market_address}. Response: {result}")
        # Report success with the original decimal odds for clarity
        return {"status": "success", "market_address": market_address, "decimal_odds_set": {"home": home_odds, "away": away_odds}}
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error updating odds for market {market_address}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error updating odds for market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except Exception as e:
         error_message = f"An unexpected error occurred in update_odds_for_market: {e}"
         print(error_message, file=sys.stderr)
         return {"status": "error", "message": error_message, "market_address": market_address}


@function_tool
def get_games_with_odds() -> List[Dict[str, Any]]:
    """Fetches today's NBA games with latest H2H odds (decimal float) from The Odds API."""
    if not SPORTS_API_KEY:
        print("Error: Cannot fetch games with odds, SPORTS_API_KEY is missing.", file=sys.stderr)
        return []

    sport = "basketball_nba"
    regions = "us"
    markets = "h2h" # Head-to-head / Moneyline
    odds_format = "decimal"
    date_format = "iso"

    try:
        # Fetch odds (in decimal format)
        response = requests.get(
            f"https://api.the-odds-api.com/v4/sports/{sport}/odds",
            params={
                "apiKey": SPORTS_API_KEY,
                "regions": regions,
                "markets": markets,
                "oddsFormat": odds_format,
                "dateFormat": date_format,
            }
        )
        response.raise_for_status()
        odds_data = response.json()

        games_with_decimal_odds = []
        for game in odds_data:
            game_id = game.get("id")
            home_team = game.get("home_team")
            away_team = game.get("away_team")
            bookmakers = game.get("bookmakers", [])

            if not game_id or not home_team or not away_team or not bookmakers:
                print(f"Warning: Skipping game due to missing essential info: {game.get('id', 'N/A')}", file=sys.stderr)
                continue

            # Find first bookmaker with H2H odds (decimal)
            home_price = None
            away_price = None
            for bookmaker in bookmakers:
                h2h_market = next((m for m in bookmaker.get("markets", []) if m.get("key") == "h2h"), None)
                if h2h_market:
                    outcomes = h2h_market.get("outcomes", [])
                    if len(outcomes) == 2:
                        for outcome in outcomes:
                            name = outcome.get("name")
                            price = outcome.get("price") # This is decimal (float)
                            if name == home_team:
                                home_price = price
                            elif name == away_team:
                                away_price = price
                        if home_price is not None and away_price is not None:
                            break
            
            # Add decimal odds if found
            if home_price is not None and away_price is not None:
                try:
                    home_odds_float = float(home_price)
                    away_odds_float = float(away_price)
                    
                    # Ensure odds are valid decimals (>= 1.0)
                    if home_odds_float < 1.0 or away_odds_float < 1.0:
                        print(f"Warning: Skipping game {game_id} due to invalid decimal odds < 1.0: home={home_odds_float}, away={away_odds_float}", file=sys.stderr)
                        continue

                    games_with_decimal_odds.append({
                        "odds_api_id": game_id,
                        "odds": {"home_odds": home_odds_float, "away_odds": away_odds_float}
                    })
                except (ValueError, TypeError) as e:
                     print(f"Warning: Could not parse decimal odds for game {game_id}: home={home_price}, away={away_price}. Error: {e}", file=sys.stderr)
            else:
                print(f"Warning: No valid H2H decimal odds found for game {game_id} ({home_team} vs {away_team})", file=sys.stderr)

        print(f"Successfully fetched decimal odds for {len(games_with_decimal_odds)} games.")
        return games_with_decimal_odds

    except requests.exceptions.RequestException as e:
        print(f"Error fetching games with odds from The Odds API: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred in get_games_with_odds: {e}", file=sys.stderr)
        return []


# Define the Odds Manager Agent
odds_manager_agent = Agent(
    name="Odds Manager Agent",
    handoff_description="Specialist agent for managing and updating odds for NBA betting markets",
    instructions="""
    You are the Odds Manager Agent. Your goal is to set initial odds for NBA betting markets that are not yet ready for betting. For markets that are already ready for betting, update the odds to the latest available odds.
    1. Call `get_existing_markets` to get all current markets. Each market should have `address`, `oddsApiId`, and `isReadyForBetting` fields.
    2. Call `get_games_with_odds`. This tool fetches the latest head-to-head (H2H) odds in *decimal* format (floats >= 1.0) from the Odds API. Each result contains `odds_api_id` and an `odds` dictionary with `home_odds` and `away_odds` as floats.
    3. For each market identified in step 2, find the corresponding game data from step 3 by matching the market's `oddsApiId` with the game's `odds_api_id`.
    4. If a match is found with valid decimal `home_odds` and `away_odds`, call `update_odds_for_market` using the market's `address` and these *decimal float* odds. The tool will handle converting them to the required integer format (decimal * 1000) before calling the API.
    5. Report back a summary of the markets you updated (providing market address and the *decimal* odds set) or attempted to update (including any errors). If no markets needed initial odds, state that. If you've updated the odds, state the before and after values. in readable decimal format.
    """,
    tools=[get_existing_markets, update_odds_for_market, get_games_with_odds],
    model="gpt-4-turbo",
    # No context type needed
)

# Example of how this agent might be run (usually done by a Runner via Triage)
if __name__ == '__main__':
    # This part is just for testing the agent directly if needed
    from agents import Runner
    import asyncio

    async def test_odds_management():
        # Input prompt to trigger the agent's logic
        prompt = "Set initial odds for any markets that need them.If the event already has odds, and is ready for betting, update the odds to the latest available odds."
        print(f"--- Running Odds Manager Agent with prompt: '{prompt}' ---")
        # Ensure environment variables are loaded if running directly
        if not SPORTS_API_KEY or not API_URL:
             print("Error: Missing SPORTS_API_KEY or API_URL in .env file. Cannot run test.", file=sys.stderr)
             return
        result = await Runner.run(odds_manager_agent, prompt)
        print("--- Odds Manager Agent Result ---")
        print(result.final_output)
        print("---------------------------------")

    # Note: Running requires tool implementations or proper imports
    # asyncio.run(test_odds_management())
    print("Odds Manager Agent defined. Run agentGroup.py to test via Triage.") 