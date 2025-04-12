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

# Define the list of target sports (consistent with market_creation_agent)
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
    draw_odds: Optional[float],
    home_spread_points: float,
    home_spread_odds: float,
    away_spread_odds: float,
    total_points: float,
    over_odds: float,
    under_odds: float
) -> Dict[str, Any]:
    """Updates all odds types (moneyline including draw, spread, total) for a specific market. Expects decimal floats/points, converts to integer format for the API call. Draw odds should be provided for relevant markets (e.g., soccer), otherwise pass 0.0 or None."""
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
            "drawOdds": int(draw_odds * 1000) if draw_odds is not None and draw_odds >= 1.0 else 0,
            "homeSpreadPoints": int(home_spread_points * 10),
            "homeSpreadOdds": int(home_spread_odds * 1000),
            "awaySpreadOdds": int(away_spread_odds * 1000),
            "totalPoints": int(total_points * 10),
            "overOdds": int(over_odds * 1000),
            "underOdds": int(under_odds * 1000)
        }
    except (ValueError, TypeError) as e:
        error_message = f"Error converting odds/points to integer format: {e}. Input: home_odds={home_odds}, away_odds={away_odds}, draw_odds={draw_odds}, home_spread_points={home_spread_points}, home_spread_odds={home_spread_odds}, away_spread_odds={away_spread_odds}, total_points={total_points}, over_odds={over_odds}, under_odds={under_odds}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}

    try:
        url = f"{API_URL}/api/market/{market_address}/update-odds"
        print(f"Attempting to update full odds (inc. draw): POST {url} with payload: {payload}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Successfully updated full odds (inc. draw) for market {market_address}. Response: {result}")
        # Report success with the original decimal odds/points for clarity
        return {
            "status": "success",
            "market_address": market_address,
            "decimal_odds_set": {
                "home": home_odds, "away": away_odds, "draw": draw_odds,
                "home_spread_points": home_spread_points, "home_spread_odds": home_spread_odds, "away_spread_odds": away_spread_odds,
                "total_points": total_points, "over_odds": over_odds, "under_odds": under_odds
            }
        }
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error updating full odds (inc. draw) for market {market_address}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error updating full odds (inc. draw) for market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except Exception as e:
         error_message = f"An unexpected error occurred in update_odds_for_market: {e}"
         print(error_message, file=sys.stderr)
         return {"status": "error", "message": error_message, "market_address": market_address}


@function_tool # Renamed and updated
def fetch_games_with_odds(sport_keys: List[str]) -> List[Dict[str, Any]]:
    """Fetches today's games for the specified sports with latest H2H, Spreads, and Totals odds (decimal float/points) from The Odds API."""
    if not SPORTS_API_KEY:
        print("Error: Cannot fetch games with odds, SPORTS_API_KEY is missing.", file=sys.stderr)
        return []

    if not sport_keys:
        print("Warning: No sport_keys provided to fetch_games_with_odds.", file=sys.stderr)
        return []

    regions = "us"
    markets = "h2h,spreads,totals" # Fetch all required markets
    odds_format = "decimal"
    date_format = "iso"
    all_games_with_full_odds = []
    processed_game_ids = set() # Avoid duplicates if API returns same game under different sports?
    print(f"Fetching games/odds for sport: {sport_keys}...")
    for sport_key in sport_keys:
        print(f"Fetching games/odds for sport: {sport_key}...")
        try:

            # Fetch odds (in decimal format)
            response = requests.get(
                f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds",
                params={
                    "apiKey": SPORTS_API_KEY,
                    "regions": regions,
                    "markets": markets,
                    "oddsFormat": odds_format,
                    "dateFormat": date_format,
                }
            )
            print(f"Response: {response.json()}")
            response.raise_for_status()
            odds_api_data = response.json()
            print(f"Received {len(odds_api_data)} game events from The Odds API.")

            for game in odds_api_data:
                game_id = game.get("id")
                home_team = game.get("home_team")
                away_team = game.get("away_team")
                bookmakers = game.get("bookmakers", [])

                # Check if game_id exists and hasn't been processed
                if not game_id or not home_team or not away_team or game_id in processed_game_ids:
                    print(f"Warning: Skipping game event due to missing ID, home_team, or away_team: {game.get('id', 'N/A')}", file=sys.stderr)
                    continue

                processed_game_ids.add(game_id) # Mark as processed
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

                        # Initialize best_odds structure here for clarity
                        if market_key == "h2h":
                            if "home_odds" not in best_odds["h2h"]: # Initialize if not already
                                best_odds["h2h"] = {"home_odds": None, "away_odds": None, "draw_odds": None} # Add draw_odds field
                        elif market_key == "spreads":
                             if "home_spread_points" not in best_odds["spreads"]:
                                best_odds["spreads"] = {"home_spread_points": None, "home_spread_odds": None, "away_spread_odds": None}
                        elif market_key == "totals":
                             if "total_points" not in best_odds["totals"]:
                                best_odds["totals"] = {"total_points": None, "over_odds": None, "under_odds": None}


                        if market_key == "h2h" and len(outcomes) == 2:
                            # Standard 2-way H2H (e.g., NBA)
                            # draw_odds remains None (default from initialization)
                            for outcome in outcomes:
                                name = outcome.get("name")
                                price = outcome.get("price")
                                if name == home_team and price is not None:
                                    best_odds["h2h"]["home_odds"] = price # Take first found for now
                                elif name == away_team and price is not None:
                                    best_odds["h2h"]["away_odds"] = price # Take first found for now

                        elif market_key == "h2h" and len(outcomes) == 3 and sport_key.startswith("soccer_"):
                            # Soccer H2H - Expect 3 outcomes (Home, Away, Draw)
                            home_found, away_found, draw_found = False, False, False # Add draw_found
                            # print(f"DEBUG: Processing SOCCER H2H market for game {game_id}. Raw outcomes: {outcomes}", file=sys.stderr) # DEBUG LOG
                            for outcome in outcomes:
                                name = outcome.get("name")
                                price = outcome.get("price")
                                if name == home_team and price is not None:
                                    # print(f"DEBUG: Found home odds for {game_id}: {price} ({name})", file=sys.stderr) # DEBUG LOG
                                    best_odds["h2h"]["home_odds"] = price
                                    home_found = True
                                elif name == away_team and price is not None:
                                    # print(f"DEBUG: Found away odds for {game_id}: {price} ({name})", file=sys.stderr) # DEBUG LOG
                                    best_odds["h2h"]["away_odds"] = price
                                    away_found = True
                                elif name == "Draw" and price is not None: # Check for Draw
                                    # print(f"DEBUG: Found draw odds for {game_id}: {price} ({name})", file=sys.stderr) # DEBUG LOG
                                    best_odds["h2h"]["draw_odds"] = price
                                    draw_found = True
                                # Ignore other outcomes

                            if not (home_found and away_found and draw_found): # Check all three
                                # print(f"DEBUG: Missing home, away or draw odds for soccer game {game_id}. Home: {home_found}, Away: {away_found}, Draw: {draw_found}", file=sys.stderr) # DEBUG LOG
                                print(f"Warning: Could not find all H2H odds (home, away, draw) for soccer game {game_id}", file=sys.stderr)
                                best_odds["h2h"]["home_odds"] = None # Invalidate if incomplete
                                best_odds["h2h"]["away_odds"] = None
                                best_odds["h2h"]["draw_odds"] = None
                            else:
                                print(f"DEBUG: Successfully found H2H odds (inc. draw) for soccer game {game_id}.", file=sys.stderr) # DEBUG LOG
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
                # For H2H, we now need all three for soccer, but only two for others
                h2h_valid = False
                if sport_key.startswith("soccer_"):
                     # Soccer needs home, away, and draw
                     h2h_valid = all(v is not None for v in best_odds["h2h"].values())
                else:
                     # Other sports only need home and away (draw_odds will be None)
                     h2h_valid = best_odds["h2h"]["home_odds"] is not None and best_odds["h2h"]["away_odds"] is not None


                spreads_valid = all(v is not None for v in best_odds["spreads"].values())
                totals_valid = all(v is not None for v in best_odds["totals"].values())

                if h2h_valid and spreads_valid and totals_valid:
                    try:
                        # Combine all odds into a single structure, converting to float
                        full_odds_data = {
                            "home_odds": float(best_odds["h2h"]["home_odds"]),
                            "away_odds": float(best_odds["h2h"]["away_odds"]),
                            # Include draw_odds, converting None to 0.0 for non-soccer or if missing (though h2h_valid should prevent missing for soccer)
                            "draw_odds": float(best_odds["h2h"]["draw_odds"]) if best_odds["h2h"]["draw_odds"] is not None else 0.0,
                            "home_spread_points": float(best_odds["spreads"]["home_spread_points"]),
                            "home_spread_odds": float(best_odds["spreads"]["home_spread_odds"]),
                            "away_spread_odds": float(best_odds["spreads"]["away_spread_odds"]),
                            "total_points": float(best_odds["totals"]["total_points"]),
                            "over_odds": float(best_odds["totals"]["over_odds"]),
                            "under_odds": float(best_odds["totals"]["under_odds"]),
                        }

                        # Basic validation (e.g., odds >= 1.0), skip draw_odds if it's 0.0
                        odds_to_validate = [
                            full_odds_data["home_odds"], full_odds_data["away_odds"],
                            full_odds_data["home_spread_odds"], full_odds_data["away_spread_odds"],
                            full_odds_data["over_odds"], full_odds_data["under_odds"]
                        ]
                        if full_odds_data["draw_odds"] > 0:
                             odds_to_validate.append(full_odds_data["draw_odds"])


                        if any(o < 1.0 for o in odds_to_validate):
                             print(f"Warning: Skipping game {game_id} due to invalid decimal odds < 1.0 found.", file=sys.stderr)
                             continue

                        all_games_with_full_odds.append({
                            "odds_api_id": game_id,
                            "sport_key": sport_key, # Include sport key
                            "odds": full_odds_data # Store the combined odds dictionary
                        })
                    except (ValueError, TypeError) as e:
                         print(f"Warning: Could not parse or validate final odds structure for game {game_id}. Error: {e}", file=sys.stderr)
                else:
                    missing = []
                    if not h2h_valid: missing.append("H2H (check home/away/draw as applicable)")
                    if not spreads_valid: missing.append("Spreads")
                    if not totals_valid: missing.append("Totals")
                    print(f"Warning: Could not find complete odds ({', '.join(missing)}) for game {game_id} ({home_team} vs {away_team}) across all bookmakers.", file=sys.stderr)

            print(f"Successfully processed and found complete odds for {len(all_games_with_full_odds)} games for sport {sport_key}.")
            # >>> INCORRECT RETURN LOCATION <<< - This causes exit after first sport
            # return all_games_with_full_odds 

        except requests.exceptions.RequestException as e:
            print(f"Error fetching games/odds for {sport_key} from The Odds API: {e}", file=sys.stderr)
            # Continue to next sport key
        except Exception as e:
            print(f"An unexpected error occurred fetching games/odds for {sport_key}: {e}", file=sys.stderr)
            # Continue to next sport key

    print(f"Total unique games with complete odds found across all sports: {len(all_games_with_full_odds)}")
    return all_games_with_full_odds


# Define the Odds Manager Agent
odds_manager_agent = Agent(
    name="Odds Manager Agent",
    handoff_description="Specialist agent for managing and updating odds (including draw odds for soccer) for NBA & Soccer betting markets",
    instructions="""
    You are the Odds Manager Agent. Your goal is to set or update odds (moneyline including draw, spreads, totals) for markets across supported sports (NBA & Soccer).
    1. Call `fetch_games_with_odds` with the list of supported sport keys (`SUPPORTED_SPORT_KEYS`). This tool fetches the latest H2H (including draw odds for soccer, which will be 0.0 if not applicable/found), spreads, and totals odds in *decimal* format from The Odds API. Each result contains `odds_api_id`, `sport_key`, and an `odds` dictionary.
    2. Create a mapping from `odds_api_id` to the fetched game/odds data (the entire dictionary including `sport_key` and `odds`) from step 1 for efficient lookup.
    3. Call `get_existing_markets` to get all current markets from your platform's API. Note: These markets might *not* have `sportKey` and could have various statuses (e.g., "Pending", "Open").
    4. Iterate through the existing markets obtained in step 3. For each market, regardless of its `status`:
        a. Use the market's `oddsApiId` to look up the corresponding game/odds data in the mapping created in step 2.
        b. If a match is found in the map and it contains a valid `odds` dictionary:
           i. Extract all the decimal odds/points (home_odds, away_odds, draw_odds, home_spread_points, home_spread_odds, away_spread_odds, total_points, over_odds, under_odds) from the matched `odds` data. Note that `draw_odds` will be 0.0 if not applicable (e.g., for NBA).
           ii. Call `update_odds_for_market` using the market's `address` and *all* these extracted decimal float odds/points, explicitly including `draw_odds`. The tool handles the conversion to the required integer format for the API (sending `drawOdds: 0` if the input `draw_odds` is 0.0 or invalid). The underlying API call will determine if the update is allowed based on the market's current status.
        c. If no match is found in the map for the market's `oddsApiId`, log a warning (the game might not be happening today or odds aren't available yet) and continue to the next market.
    5. Report back a summary of the markets you attempted to update (providing market address and the *decimal* odds set including draw) or could not find odds data for. Include any errors returned by the `update_odds_for_market` tool (e.g., if the API rejected the update due to market status).
    """,
    tools=[get_existing_markets, update_odds_for_market, fetch_games_with_odds],
    # DO NOT CHANGE THIS MODEL FROM THE CURRENT SETTING
    model="gpt-4o-mini-2024-07-18",
    # No context type needed
)

# Example of how this agent might be run (usually done by a Runner via Triage)
if __name__ == '__main__':
    # This part is just for testing the agent directly if needed
    from agents import Runner
    import asyncio

    async def test_odds_management():
        # Input prompt to trigger the agent's logic
        prompt = f"Set or update odds for all markets in supported sports: {', '.join(SUPPORTED_SPORT_KEYS)}."
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
    asyncio.run(test_odds_management())
    print("Odds Manager Agent defined. Run agentGroup.py to test via Triage.") 