#!/usr/bin/env python3
import sys
import requests
import os
import datetime
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
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

# Define implementation functions that can be called directly
def get_existing_markets_impl() -> List[Dict[str, Any]]:
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
                if isinstance(market, dict) and all(k in market for k in ["address", "oddsApiId", "status"]):
                    # A market is ready for betting if its status is 'Open' OR 'Pending'
                    # Fix: Use logical OR instead of sequential assignment
                    market["isReadyForBetting"] = (market.get("status") == "Open" or market.get("status") == "Pending")
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

# Create function tools for the agent to use
@function_tool
def get_existing_markets() -> List[Dict[str, Any]]:
    """Fetches all existing betting markets from the smart contract API."""
    return get_existing_markets_impl()


def update_odds_for_market_impl(
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
    return update_odds_for_market_impl(
        market_address, home_odds, away_odds, draw_odds, 
        home_spread_points, home_spread_odds, away_spread_odds,
        total_points, over_odds, under_odds
    )


class OddsData(TypedDict, total=False):
    market_address: str
    home_odds: float
    away_odds: float
    draw_odds: Optional[float]
    home_spread_points: float
    home_spread_odds: float
    away_spread_odds: float
    total_points: float
    over_odds: float
    under_odds: float

class BatchUpdateResult(TypedDict):
    status: str
    total_markets: int
    successful_updates: int
    failed_updates: int
    results: List[Dict[str, Any]]

def update_odds_for_multiple_markets_impl(
    markets_data: List[OddsData]
) -> BatchUpdateResult:
    """Updates odds for multiple markets at once."""
    if not API_URL:
        print("Error: Cannot update odds, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}
    
    results = []
    print(f"Updating odds for {len(markets_data)} markets")
    for market_data in markets_data:
        try:
            # Extract market info
            market_address = market_data.get("market_address")
            if not market_address:
                results.append({"status": "error", "message": "Missing market_address in market data"})
                continue
                
            # Extract odds data
            home_odds = market_data.get("home_odds")
            away_odds = market_data.get("away_odds")
            draw_odds = market_data.get("draw_odds")
            home_spread_points = market_data.get("home_spread_points")
            home_spread_odds = market_data.get("home_spread_odds")
            away_spread_odds = market_data.get("away_spread_odds")
            total_points = market_data.get("total_points")
            over_odds = market_data.get("over_odds")
            under_odds = market_data.get("under_odds")
            
            # Validate essential data
            if any(v is None for v in [home_odds, away_odds, home_spread_points, home_spread_odds, 
                                      away_spread_odds, total_points, over_odds, under_odds]):
                results.append({
                    "status": "error", 
                    "message": "Missing required odds data",
                    "market_address": market_address
                })
                continue
                
            # Convert decimal floats/points to integer format
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
                error_message = f"Error converting odds/points to integer format: {e}"
                print(error_message, file=sys.stderr)
                results.append({
                    "status": "error", 
                    "message": error_message,
                    "market_address": market_address
                })
                continue
                
            # Make the API request
            try:
                url = f"{API_URL}/api/market/{market_address}/update-odds"
                print(f"Updating odds for market {market_address}")
                response = requests.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                
                results.append({
                    "status": "success",
                    "market_address": market_address,
                    "decimal_odds_set": {
                        "home": home_odds, "away": away_odds, "draw": draw_odds,
                        "home_spread_points": home_spread_points, 
                        "home_spread_odds": home_spread_odds, 
                        "away_spread_odds": away_spread_odds,
                        "total_points": total_points, 
                        "over_odds": over_odds, 
                        "under_odds": under_odds
                    }
                })
            except requests.exceptions.HTTPError as e:
                error_message = f"HTTP Error updating odds for market {market_address}: {e.response.status_code} - {e.response.text}"
                print(error_message, file=sys.stderr)
                results.append({
                    "status": "error", 
                    "message": error_message,
                    "market_address": market_address
                })
            except requests.exceptions.RequestException as e:
                error_message = f"Request Error updating odds for market {market_address}: {e}"
                print(error_message, file=sys.stderr)
                results.append({
                    "status": "error", 
                    "message": error_message,
                    "market_address": market_address
                })
                
        except Exception as e:
            error_message = f"An unexpected error occurred processing market: {e}"
            print(error_message, file=sys.stderr)
            results.append({
                "status": "error", 
                "message": error_message,
                "market_address": market_data.get("market_address", "unknown")
            })
    
    summary = {
        "status": "completed",
        "total_markets": len(markets_data),
        "successful_updates": sum(1 for r in results if r.get("status") == "success"),
        "failed_updates": sum(1 for r in results if r.get("status") == "error"),
        "results": results
    }
    
    print(f"Completed batch update of {summary['total_markets']} markets: {summary['successful_updates']} successful, {summary['failed_updates']} failed")
    return summary

@function_tool
def update_odds_for_multiple_markets(
    markets_data: List[OddsData]
) -> BatchUpdateResult:
    """Updates odds for multiple markets at once."""
    return update_odds_for_multiple_markets_impl(markets_data)


def fetch_games_with_odds_impl(sport_keys: List[str]) -> List[Dict[str, Any]]:
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
            # print(f"Response: {response.json()}")
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
                            # Always ensure draw_odds is initialized to None by default
                            if "draw_odds" not in best_odds["h2h"]:
                                best_odds["h2h"]["draw_odds"] = None
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
                            home_found, away_found, draw_found = False, False, False
                            for outcome in outcomes:
                                name = outcome.get("name")
                                price = outcome.get("price")
                                if name == home_team and price is not None:
                                    best_odds["h2h"]["home_odds"] = price
                                    home_found = True
                                elif name == away_team and price is not None:
                                    best_odds["h2h"]["away_odds"] = price
                                    away_found = True
                                elif name == "Draw" and price is not None: # Check for Draw
                                    best_odds["h2h"]["draw_odds"] = price
                                    draw_found = True
                                # Ignore other outcomes

                            if not (home_found and away_found and draw_found): # Check all three
                                print(f"Warning: Could not find all H2H odds (home, away, draw) for soccer game {game_id}", file=sys.stderr)
                                best_odds["h2h"]["home_odds"] = None # Invalidate if incomplete
                                best_odds["h2h"]["away_odds"] = None
                                best_odds["h2h"]["draw_odds"] = None
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
                            # Include draw_odds, converting None to 0.0 for non-soccer or if missing
                            "draw_odds": float(best_odds["h2h"].get("draw_odds", 0.0)) if best_odds["h2h"].get("draw_odds") is not None else 0.0,
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

@function_tool
def fetch_games_with_odds(sport_keys: List[str]) -> List[Dict[str, Any]]:
    """Fetches today's games for the specified sports with latest H2H, Spreads, and Totals odds (decimal float/points) from The Odds API."""
    return fetch_games_with_odds_impl(sport_keys)


# Define function without decorator first so it can be called directly
def fetch_and_update_all_markets_impl() -> Dict[str, Any]:
    """Fetches games with odds, gets existing markets, and updates all market odds in a single operation."""
    # Step 1: Fetch games with odds for all supported sports
    print("Fetching games with odds for all supported sports...")
    games_with_odds = fetch_games_with_odds_impl(SUPPORTED_SPORT_KEYS)
    print(f"Found {len(games_with_odds)} games with complete odds data")
    
    if not games_with_odds:
        return {
            "status": "error", 
            "message": "No games with odds found from The Odds API",
            "total_markets_with_odds": 0,
            "total_markets_updated": 0
        }
    
    # Step 2: Create a mapping from odds_api_id to odds data for efficient lookup
    odds_api_id_to_odds = {
        game["odds_api_id"]: game["odds"] 
        for game in games_with_odds
    }
    print(f"Created mapping for {len(odds_api_id_to_odds)} games by odds API ID")
    
    # Step 3: Get existing markets directly from the API
    print("Fetching existing markets from platform API...")
    existing_markets = get_existing_markets_impl()
    print(f"Found {len(existing_markets)} existing markets")
    
    if not existing_markets:
        return {
            "status": "error", 
            "message": "No existing markets found from the platform API",
            "total_markets_with_odds": len(odds_api_id_to_odds),
            "total_markets_updated": 0
        }
    
    # Step 4: Match markets with odds and prepare update data
    markets_for_update = []
    markets_with_existing_odds = 0
    
    for market in existing_markets:
        odds_api_id = market.get("oddsApiId")
        market_address = market.get("address")
        
        if not (odds_api_id and market_address):
            print(f"Warning: Market missing oddsApiId or address: {market}")
            continue
            
        # First check if this market already has odds
        odds_status = check_market_odds_impl(market_address)
        if odds_status.get("has_odds"):
            markets_with_existing_odds += 1
            print(f"Skipping market {market_address} as it already has odds set")
            continue
            
        # Check if we have odds for this market
        if odds_api_id in odds_api_id_to_odds:
            odds_data = odds_api_id_to_odds[odds_api_id]
            
            # Create a market data entry with all required fields
            market_data = {
                "market_address": market_address,
                "home_odds": odds_data.get("home_odds"),
                "away_odds": odds_data.get("away_odds"),
                "draw_odds": odds_data.get("draw_odds"),
                "home_spread_points": odds_data.get("home_spread_points"),
                "home_spread_odds": odds_data.get("home_spread_odds"),
                "away_spread_odds": odds_data.get("away_spread_odds"),
                "total_points": odds_data.get("total_points"),
                "over_odds": odds_data.get("over_odds"),
                "under_odds": odds_data.get("under_odds")
            }
            
            # Ensure all required odds data is present
            if all(v is not None for k, v in market_data.items() if k != "draw_odds"):
                markets_for_update.append(market_data)
            else:
                print(f"Warning: Incomplete odds data for market {market_address} (odds API ID: {odds_api_id})")
    
    # Step 5: Update all markets with available odds data
    print(f"Preparing to update {len(markets_for_update)} markets with available odds data")
    
    if not markets_for_update:
        return {
            "status": "info",
            "message": f"No new markets need odds updates. {markets_with_existing_odds} markets already have odds set.",
            "total_markets_with_odds": len(odds_api_id_to_odds),
            "total_existing_markets": len(existing_markets),
            "total_markets_with_existing_odds": markets_with_existing_odds,
            "total_new_markets_updated": 0
        }
    
    # Perform the batch update
    update_results = update_odds_for_multiple_markets_impl(markets_for_update)
    
    # Step 6: Return combined result summary
    return {
        "status": "success",
        "message": f"Set odds for {update_results['successful_updates']} new markets. Skipped {markets_with_existing_odds} markets that already had odds.",
        "total_markets_with_odds": len(odds_api_id_to_odds),
        "total_existing_markets": len(existing_markets),
        "total_markets_with_existing_odds": markets_with_existing_odds,
        "total_new_markets_matched": len(markets_for_update),
        "total_new_markets_updated": update_results["successful_updates"],
        "failed_updates": update_results["failed_updates"],
        "detailed_results": update_results["results"]
    }

# Create a function tool version that can be used by the agent
@function_tool
def fetch_and_update_all_markets() -> Dict[str, Any]:
    """Fetches games with odds, gets existing markets, and updates all market odds in a single operation."""
    return fetch_and_update_all_markets_impl()

# --- New Tool Implementation ---

def check_market_odds_impl(market_address: str) -> Dict[str, Any]:
    """Checks if a specific market already has odds set via the API."""
    if not API_URL:
        print("Error: Cannot check market odds, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured", "market_address": market_address, "has_odds": None}

    try:
        url = f"{API_URL}/api/market/{market_address}"
        print(f"Checking odds status for market: GET {url}")
        response = requests.get(url)
        response.raise_for_status()
        market_data = response.json()

        # Check if ALL essential odds fields exist and are likely set (e.g., not 0 or null)
        # Check moneyline odds
        has_home_odds = market_data.get("homeOdds") is not None and market_data.get("homeOdds") != 0
        has_away_odds = market_data.get("awayOdds") is not None and market_data.get("awayOdds") != 0
        
        # Check spread odds
        has_home_spread_odds = market_data.get("homeSpreadOdds") is not None and market_data.get("homeSpreadOdds") != 0
        has_away_spread_odds = market_data.get("awaySpreadOdds") is not None and market_data.get("awaySpreadOdds") != 0
        has_home_spread_points = market_data.get("homeSpreadPoints") is not None
        
        # Check total odds
        has_over_odds = market_data.get("overOdds") is not None and market_data.get("overOdds") != 0
        has_under_odds = market_data.get("underOdds") is not None and market_data.get("underOdds") != 0
        has_total_points = market_data.get("totalPoints") is not None
        
        # Only consider odds as set if ALL required odds are present
        # Note: We don't check for drawOdds since that's only relevant for soccer
        has_moneyline = has_home_odds and has_away_odds
        has_spreads = has_home_spread_odds and has_away_spread_odds and has_home_spread_points
        has_totals = has_over_odds and has_under_odds and has_total_points
        
        # A market has complete odds only if all three types are set
        has_odds = has_moneyline and has_spreads and has_totals
        
        print(f"Market {market_address} odds status: {'Set' if has_odds else 'Not Set'}")
        return {
            "status": "success",
            "market_address": market_address,
            "has_odds": has_odds,
            # Optionally return the odds if found
            "odds_data": {
                "homeOdds": market_data.get("homeOdds"),
                "awayOdds": market_data.get("awayOdds"),
                "drawOdds": market_data.get("drawOdds"),
                "homeSpreadPoints": market_data.get("homeSpreadPoints"),
                "homeSpreadOdds": market_data.get("homeSpreadOdds"),
                "awaySpreadOdds": market_data.get("awaySpreadOdds"),
                "totalPoints": market_data.get("totalPoints"),
                "overOdds": market_data.get("overOdds"),
                "underOdds": market_data.get("underOdds")
            } if has_odds else None
        }

    except requests.exceptions.HTTPError as e:
        # Handle cases where the market might not be found (e.g., 404)
        if e.response.status_code == 404:
            error_message = f"Market {market_address} not found."
            print(error_message, file=sys.stderr)
            return {"status": "error", "message": error_message, "market_address": market_address, "has_odds": None}
        else:
            error_message = f"HTTP Error checking odds for market {market_address}: {e.response.status_code} - {e.response.text}"
            print(error_message, file=sys.stderr)
            return {"status": "error", "message": error_message, "market_address": market_address, "has_odds": None}
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error checking odds for market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address, "has_odds": None}
    except Exception as e:
        error_message = f"An unexpected error occurred in check_market_odds_impl: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address, "has_odds": None}

@function_tool
def check_market_odds(market_address: str) -> Dict[str, Any]:
    """Checks if a specific betting market (identified by its address) already has odds set."""
    return check_market_odds_impl(market_address)

# --- End New Tool Implementation ---

# Define the Odds Manager Agent
odds_manager_agent = Agent(
    name="Odds Manager Agent",
    handoff_description="Specialist agent for managing and updating odds (including draw odds for soccer) for NBA & Soccer betting markets",
    instructions="""
    You are the Odds Manager Agent. Your goal is to set (but not update) odds (moneyline including draw, spreads, totals) for markets across supported sports (NBA & Soccer).
    
    IMPORTANT: You are not allowed to update any existing markets. You are only allowed to set new odds. Use `check_market_odds` if you need to verify if a market already has odds before attempting to set them.
    
    **Primary Workflow:**
    1. Call `fetch_and_update_all_markets()` which will:
       - Fetch games with latest odds from The Odds API for all supported sports.
       - Get existing markets from your platform's API.
       - Match markets with their corresponding odds.
       - **Attempt** to update all matched markets in a single batch operation (Note: The underlying implementation updates odds, but your instruction is to *set* new odds, implying you should only target markets without existing odds if possible, though the tool might overwrite).
       - Return a comprehensive summary of the update process.
    
    2. Report back the summary of results, including:
       - How many markets had odds data available.
       - How many existing markets were found.
       - How many markets were matched and updated successfully.
       - Any errors that occurred.
    
    **Alternative Workflow (for specific cases or verification):**
    - Use `fetch_games_with_odds` to get just odds data for specific sports.
    - Use `get_existing_markets` to get just market data.
    - Use `check_market_odds(market_address=<address>)` to see if a specific market already has odds set.
    - Use `update_odds_for_market` for single market updates (use carefully according to the 'set new odds only' rule).
    - Use `update_odds_for_multiple_markets` for batch updates (use carefully according to the 'set new odds only' rule).
    
    For normal operation, prefer the combined `fetch_and_update_all_markets` function. Adhere strictly to the rule of only setting new odds, not updating existing ones. If using update functions, ideally verify first with `check_market_odds`.
    """,
    tools=[
        get_existing_markets,
        update_odds_for_market,
        update_odds_for_multiple_markets,
        fetch_games_with_odds,
        fetch_and_update_all_markets,
        check_market_odds
    ],
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
        # Ensure environment variables are loaded if running directly
        if not SPORTS_API_KEY or not API_URL:
             print("Error: Missing SPORTS_API_KEY or API_URL in .env file. Cannot run test.", file=sys.stderr)
             return
        
        # Option 1: Test the combined function directly
        print("--- Testing fetch_and_update_all_markets function directly ---")
        result = fetch_and_update_all_markets_impl()  # Call the implementation function directly
        print("--- Function Result ---")
        print(result)
        print("---------------------------------")
        
        # Option 2: Test through the agent
        prompt = f"Set or update odds for all markets in supported sports: {', '.join(SUPPORTED_SPORT_KEYS)}."
        print(f"--- Running Odds Manager Agent with prompt: '{prompt}' ---")
        result = await Runner.run(odds_manager_agent, prompt)
        print("--- Odds Manager Agent Result ---")
        print(result.final_output)
        print("---------------------------------")

    # Note: Running requires tool implementations or proper imports
    asyncio.run(test_odds_management())
    print("Odds Manager Agent defined. Run agentGroup.py to test via Triage.") 