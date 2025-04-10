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
                # 1. Check for the fields actually provided by the API: address, oddsApiId, and status
                if isinstance(market, dict) and all(k in market for k in ["address", "oddsApiId", "status"]):
                    # 2. Derive isReadyForBetting based on the status
                    # A market is ready for betting if its status is 'Open'
                    market["isReadyForBetting"] = (market.get("status") == "Open")
                    
                    # Rename oddsApiId for consistency within this agent if needed, or use directly
                    # market['odds_api_id'] = market.pop('oddsApiId') # Keep original name for now
                    cleaned_markets.append(market)
                else:
                    # Updated warning message
                    print(f"Warning: Skipping market entry due to missing required fields (address, oddsApiId, status) or incorrect format: {market}", file=sys.stderr)
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
def update_odds_for_market(
    market_address: str,
    home_odds: float,
    away_odds: float,
    home_spread_points: float,
    home_spread_odds: float,
    away_spread_odds: float,
    total_points: float,
    over_odds: float,
    under_odds: float
) -> Dict[str, Any]:
    """Updates all odds types (moneyline, spread, total) for a specific market. Expects decimal floats/points, converts to integer format for the API call."""
    if not API_URL:
        print("Error: Cannot update odds, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}

    # Convert decimal floats/points to integer format
    # Odds: decimal * 1000
    # Points: decimal * 10 (for spreads and totals line)
    try:
        payload = {
            "homeOdds": int(home_odds * 1000),
            "awayOdds": int(away_odds * 1000),
            "homeSpreadPoints": int(home_spread_points * 10),
            "homeSpreadOdds": int(home_spread_odds * 1000),
            "awaySpreadOdds": int(away_spread_odds * 1000),
            "totalPoints": int(total_points * 10),
            "overOdds": int(over_odds * 1000),
            "underOdds": int(under_odds * 1000)
        }
    except (ValueError, TypeError) as e:
        error_message = f"Error converting odds/points to integer format: {e}. Input: home_odds={home_odds}, away_odds={away_odds}, home_spread_points={home_spread_points}, home_spread_odds={home_spread_odds}, away_spread_odds={away_spread_odds}, total_points={total_points}, over_odds={over_odds}, under_odds={under_odds}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}

    try:
        url = f"{API_URL}/api/market/{market_address}/update-odds"
        print(f"Attempting to update full odds: POST {url} with payload: {payload}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Successfully updated full odds for market {market_address}. Response: {result}")
        # Report success with the original decimal odds/points for clarity
        return {
            "status": "success",
            "market_address": market_address,
            "decimal_odds_set": {
                "home": home_odds, "away": away_odds,
                "home_spread_points": home_spread_points, "home_spread_odds": home_spread_odds, "away_spread_odds": away_spread_odds,
                "total_points": total_points, "over_odds": over_odds, "under_odds": under_odds
            }
        }
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error updating full odds for market {market_address}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error updating full odds for market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except Exception as e:
         error_message = f"An unexpected error occurred in update_odds_for_market: {e}"
         print(error_message, file=sys.stderr)
         return {"status": "error", "message": error_message, "market_address": market_address}


@function_tool
def get_games_with_odds() -> List[Dict[str, Any]]:
    """Fetches today's NBA games with latest H2H, Spreads, and Totals odds (decimal float/points) from The Odds API."""
    if not SPORTS_API_KEY:
        print("Error: Cannot fetch games with odds, SPORTS_API_KEY is missing.", file=sys.stderr)
        return []

    sport = "basketball_nba"
    regions = "us"
    markets = "h2h,spreads,totals" # Fetch all required markets
    odds_format = "decimal"
    date_format = "iso"

    try:
        print(f"Fetching odds from The Odds API for markets: {markets}")
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
        odds_api_data = response.json()
        print(f"Received {len(odds_api_data)} game events from The Odds API.")

        games_with_full_odds = []
        for game in odds_api_data:
            game_id = game.get("id")
            home_team = game.get("home_team")
            away_team = game.get("away_team")
            bookmakers = game.get("bookmakers", [])

            if not game_id or not home_team or not away_team:
                print(f"Warning: Skipping game event due to missing ID, home_team, or away_team: {game.get('id', 'N/A')}", file=sys.stderr)
                continue

            # Use a dictionary to store the best odds found across bookmakers for each market type
            best_odds = {
                "h2h": {"home_odds": None, "away_odds": None},
                "spreads": {"home_spread_points": None, "home_spread_odds": None, "away_spread_odds": None},
                "totals": {"total_points": None, "over_odds": None, "under_odds": None}
            }

            for bookmaker in bookmakers:
                for market in bookmaker.get("markets", []):
                    market_key = market.get("key")
                    outcomes = market.get("outcomes", [])

                    if market_key == "h2h" and len(outcomes) == 2:
                        for outcome in outcomes:
                            name = outcome.get("name")
                            price = outcome.get("price")
                            if name == home_team and price is not None:
                                best_odds["h2h"]["home_odds"] = price # Take first found for now
                            elif name == away_team and price is not None:
                                best_odds["h2h"]["away_odds"] = price # Take first found for now

                    elif market_key == "spreads" and len(outcomes) == 2:
                        # Assuming first outcome is away, second is home (common pattern, might need verification)
                        # Or better: identify by name if possible, fallback to index
                        try:
                            outcome1 = outcomes[0]
                            outcome2 = outcomes[1]
                            # Identify home/away based on name if possible
                            if outcome1.get("name") == home_team:
                                home_outcome = outcome1
                                away_outcome = outcome2
                            elif outcome2.get("name") == home_team:
                                home_outcome = outcome2
                                away_outcome = outcome1
                            # Fallback if names don't match teams (e.g., generic "Team 1")
                            # This part is tricky and depends on API consistency
                            else:
                                # Assuming away is first, home is second if names mismatch
                                away_outcome = outcome1
                                home_outcome = outcome2

                            # Home spread is usually negative if favorite, positive if underdog
                            # The 'point' is the line itself
                            home_point = home_outcome.get("point")
                            home_price = home_outcome.get("price")
                            # Away spread usually opposite sign of home spread
                            away_point = away_outcome.get("point")
                            away_price = away_outcome.get("price")

                            # Store the home team's spread point and both prices
                            if home_point is not None and home_price is not None and away_price is not None:
                                best_odds["spreads"]["home_spread_points"] = home_point
                                best_odds["spreads"]["home_spread_odds"] = home_price
                                best_odds["spreads"]["away_spread_odds"] = away_price

                        except (IndexError, AttributeError, KeyError):
                             print(f"Warning: Could not parse spreads market for game {game_id}, bookmaker {bookmaker.get('key')}", file=sys.stderr)


                    elif market_key == "totals" and len(outcomes) == 2:
                        # Assuming first outcome is Over, second is Under
                        try:
                            over_outcome = next((o for o in outcomes if o.get("name") == "Over"), None)
                            under_outcome = next((o for o in outcomes if o.get("name") == "Under"), None)

                            if over_outcome and under_outcome:
                                total_point = over_outcome.get("point") # Line should be same for Over/Under
                                over_price = over_outcome.get("price")
                                under_price = under_outcome.get("price")

                                if total_point is not None and over_price is not None and under_price is not None:
                                    best_odds["totals"]["total_points"] = total_point
                                    best_odds["totals"]["over_odds"] = over_price
                                    best_odds["totals"]["under_odds"] = under_price
                        except (AttributeError, KeyError):
                            print(f"Warning: Could not parse totals market for game {game_id}, bookmaker {bookmaker.get('key')}", file=sys.stderr)

            # Check if we found all necessary odds components
            h2h_valid = all(v is not None for v in best_odds["h2h"].values())
            spreads_valid = all(v is not None for v in best_odds["spreads"].values())
            totals_valid = all(v is not None for v in best_odds["totals"].values())

            if h2h_valid and spreads_valid and totals_valid:
                try:
                    # Combine all odds into a single structure, converting to float
                    full_odds_data = {
                        "home_odds": float(best_odds["h2h"]["home_odds"]),
                        "away_odds": float(best_odds["h2h"]["away_odds"]),
                        "home_spread_points": float(best_odds["spreads"]["home_spread_points"]),
                        "home_spread_odds": float(best_odds["spreads"]["home_spread_odds"]),
                        "away_spread_odds": float(best_odds["spreads"]["away_spread_odds"]),
                        "total_points": float(best_odds["totals"]["total_points"]),
                        "over_odds": float(best_odds["totals"]["over_odds"]),
                        "under_odds": float(best_odds["totals"]["under_odds"]),
                    }

                    # Basic validation (e.g., odds >= 1.0)
                    if any(o < 1.0 for o in [full_odds_data["home_odds"], full_odds_data["away_odds"],
                                             full_odds_data["home_spread_odds"], full_odds_data["away_spread_odds"],
                                             full_odds_data["over_odds"], full_odds_data["under_odds"]]):
                         print(f"Warning: Skipping game {game_id} due to invalid decimal odds < 1.0 found.", file=sys.stderr)
                         continue

                    games_with_full_odds.append({
                        "odds_api_id": game_id,
                        "odds": full_odds_data # Store the combined odds dictionary
                    })
                except (ValueError, TypeError) as e:
                     print(f"Warning: Could not parse or validate final odds structure for game {game_id}. Error: {e}", file=sys.stderr)
            else:
                missing = []
                if not h2h_valid: missing.append("H2H")
                if not spreads_valid: missing.append("Spreads")
                if not totals_valid: missing.append("Totals")
                print(f"Warning: Could not find complete odds ({', '.join(missing)}) for game {game_id} ({home_team} vs {away_team}) across all bookmakers.", file=sys.stderr)

        print(f"Successfully processed and found complete odds for {len(games_with_full_odds)} games.")
        return games_with_full_odds

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
    2. Call `get_games_with_odds`. This tool fetches the latest head-to-head (H2H), spreads, and totals odds in *decimal* format (floats >= 1.0) from the Odds API. Each result contains `odds_api_id` and an `odds` dictionary with `home_odds`, `away_odds`, `home_spread_points`, `home_spread_odds`, `away_spread_odds`, `total_points`, `over_odds`, and `under_odds` as floats.
    3. For each market identified in step 2, find the corresponding game data from step 3 by matching the market's `oddsApiId` with the game's `odds_api_id`.
    4. If a match is found with valid decimal `home_odds` and `away_odds`, call `update_odds_for_market` using the market's `address` and these *decimal float* odds. The tool will handle converting them to the required integer format (decimal * 1000) before calling the API.
    5. Report back a summary of the markets you updated (providing market address and the *decimal* odds set) or attempted to update (including any errors). If no markets needed initial odds, state that. If you've updated the odds, state the before and after values. in readable decimal format.
    """,
    tools=[get_existing_markets, update_odds_for_market, get_games_with_odds],
    # DO NOT CHANGE THIS MODEL FROM THE CURRENT SETTING
    model="gpt-4o-2024-11-20",
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