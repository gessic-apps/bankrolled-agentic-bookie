#!/usr/bin/env python3
import datetime
import json
import sys
from typing import List, Dict, Any, Optional

# Try to import dotenv, but handle when it's not available
try:
    from dotenv import load_dotenv
    # Load environment variables from .env file
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv package not installed, skipping .env file loading.", file=sys.stderr)

from ..api.sports_api import fetch_odds_api
from ..config import is_soccer_sport
def fetch_upcoming_games(sport_keys: List[str]) -> List[Dict[str, Any]]:
    """Fetches upcoming games (today and tomorrow) for the specified sports from The Odds API."""
    all_games = []
    processed_game_ids = set()

    # Define API request parameters
    regions = "us"
    markets = "h2h"  # Head-to-head market is sufficient to get game details
    odds_format = "decimal"
    date_format = "iso"

    # Calculate time filtering range to include both today and tomorrow
    today_utc = datetime.datetime.now(datetime.timezone.utc).date()
    print(today_utc)
    # Start from one hour before current time to get today's games
    start_of_period_utc = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=4)
    print(start_of_period_utc)
    # End at the end of tomorrow
    tomorrow_utc = today_utc + datetime.timedelta(days=1)
    end_of_period_utc = datetime.datetime.combine(tomorrow_utc, datetime.time(23, 59, 59), tzinfo=datetime.timezone.utc)

    # Format using strftime to ensure YYYY-MM-DDTHH:MM:SSZ format
    commence_time_from = start_of_period_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    commence_time_to = end_of_period_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

    for sport_key in sport_keys:
        print(f"Fetching games for sport: {sport_key}...")
        try:
            games_data = fetch_odds_api(
                sport_key=sport_key,
                markets=markets,
                commence_time_from=commence_time_from,
                commence_time_to=commence_time_to
            )

            # Extract relevant game details
            games_count = 0
            for game in games_data:
                game_id = game.get("id")
                if not game_id or game_id in processed_game_ids:
                    continue  # Skip if ID missing or game already added

                # Convert ISO commence_time to Unix timestamp (integer seconds)
                commence_dt = datetime.datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
                commence_timestamp = int(commence_dt.timestamp())

                game_info = {
                    "id": game_id,
                    "sport_key": sport_key,
                    "home_team": game["home_team"],
                    "away_team": game["away_team"],
                    "commence_time": game["commence_time"],
                    "game_timestamp": commence_timestamp,
                }
                all_games.append(game_info)
                processed_game_ids.add(game_id)
                games_count += 1
            print(f"Successfully fetched {games_count} games for {sport_key}.")

        except Exception as e:
            print(f"An unexpected error occurred fetching games for {sport_key}: {e}", file=sys.stderr)
            # Continue to next sport key

    print(f"Total unique games fetched across all sports: {len(all_games)}")
    return all_games

def fetch_games_with_odds(sport_keys: List[str]) -> List[Dict[str, Any]]:
    """Fetches games for the specified sports with latest odds (moneyline, spreads, totals) from The Odds API."""
    all_games_with_full_odds = []
    processed_game_ids = set()  # Avoid duplicates if API returns same game under different sports
    
    for sport_key in sport_keys:
        print(f"Fetching games/odds for sport: {sport_key}...")
        try:
            odds_api_data = fetch_odds_api(
                sport_key=sport_key,
                markets="h2h,spreads,totals"
            )
            
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

                processed_game_ids.add(game_id)  # Mark as processed
                
                # Use a dictionary to store the best odds found across bookmakers for each market type
                best_odds = {
                    "h2h": {"home_odds": None, "away_odds": None},
                    "spreads": {"home_spread_points": None, "home_spread_odds": None, "away_spread_odds": None},
                    "totals": {"total_points": None, "over_odds": None, "under_odds": None}
                }

                # Initialize draw_odds for soccer
                if is_soccer_sport(sport_key):
                    best_odds["h2h"]["draw_odds"] = None

                for bookmaker in bookmakers:
                    for market in bookmaker.get("markets", []):
                        market_key = market.get("key")
                        outcomes = market.get("outcomes", [])

                        if market_key == "h2h":
                            # Handle based on whether it's soccer (3-way) or other sport (2-way)
                            if is_soccer_sport(sport_key) and len(outcomes) == 3:
                                # Soccer: Home, Away, Draw
                                for outcome in outcomes:
                                    name = outcome.get("name")
                                    price = outcome.get("price")
                                    if name == home_team and price is not None:
                                        best_odds["h2h"]["home_odds"] = price
                                    elif name == away_team and price is not None:
                                        best_odds["h2h"]["away_odds"] = price
                                    elif name == "Draw" and price is not None:
                                        best_odds["h2h"]["draw_odds"] = price
                            elif len(outcomes) == 2:
                                # Standard 2-way (e.g., NBA)
                                for outcome in outcomes:
                                    name = outcome.get("name")
                                    price = outcome.get("price")
                                    if name == home_team and price is not None:
                                        best_odds["h2h"]["home_odds"] = price
                                    elif name == away_team and price is not None:
                                        best_odds["h2h"]["away_odds"] = price

                        elif market_key == "spreads" and len(outcomes) == 2:
                            try:
                                # Identify home/away based on name
                                home_outcome = next((o for o in outcomes if o.get("name") == home_team), None)
                                away_outcome = next((o for o in outcomes if o.get("name") == away_team), None)
                                
                                # If names don't match directly, try to infer (less reliable)
                                if not home_outcome or not away_outcome:
                                    # Assume first is away, second is home if we can't identify by name
                                    away_outcome = outcomes[0] if not away_outcome else away_outcome
                                    home_outcome = outcomes[1] if not home_outcome else home_outcome
                                
                                home_point = home_outcome.get("point")
                                home_price = home_outcome.get("price")
                                away_price = away_outcome.get("price")
                                
                                if home_point is not None and home_price is not None and away_price is not None:
                                    best_odds["spreads"]["home_spread_points"] = home_point
                                    best_odds["spreads"]["home_spread_odds"] = home_price
                                    best_odds["spreads"]["away_spread_odds"] = away_price
                            except Exception as e:
                                print(f"Warning: Could not parse spreads market for game {game_id}: {e}", file=sys.stderr)

                        elif market_key == "totals" and len(outcomes) == 2:
                            try:
                                over_outcome = next((o for o in outcomes if o.get("name") == "Over"), None)
                                under_outcome = next((o for o in outcomes if o.get("name") == "Under"), None)
                                
                                if over_outcome and under_outcome:
                                    total_point = over_outcome.get("point")
                                    over_price = over_outcome.get("price")
                                    under_price = under_outcome.get("price")
                                    
                                    if total_point is not None and over_price is not None and under_price is not None:
                                        best_odds["totals"]["total_points"] = total_point
                                        best_odds["totals"]["over_odds"] = over_price
                                        best_odds["totals"]["under_odds"] = under_price
                            except Exception as e:
                                print(f"Warning: Could not parse totals market for game {game_id}: {e}", file=sys.stderr)

                # Check if we found all necessary odds components
                h2h_valid = False
                if is_soccer_sport(sport_key):
                    # Soccer needs home, away, and draw
                    h2h_valid = all(v is not None for v in best_odds["h2h"].values())
                else:
                    # Other sports only need home and away
                    h2h_valid = best_odds["h2h"]["home_odds"] is not None and best_odds["h2h"]["away_odds"] is not None
                
                spreads_valid = all(v is not None for v in best_odds["spreads"].values())
                totals_valid = all(v is not None for v in best_odds["totals"].values())
                
                if h2h_valid and spreads_valid and totals_valid:
                    try:
                        # Combine all odds into a single structure
                        full_odds_data = {
                            "home_odds": float(best_odds["h2h"]["home_odds"]),
                            "away_odds": float(best_odds["h2h"]["away_odds"]),
                            # Include draw_odds for soccer, 0.0 for others
                            "draw_odds": float(best_odds["h2h"].get("draw_odds", 0.0)) if best_odds["h2h"].get("draw_odds") is not None else 0.0,
                            "home_spread_points": float(best_odds["spreads"]["home_spread_points"]),
                            "home_spread_odds": float(best_odds["spreads"]["home_spread_odds"]),
                            "away_spread_odds": float(best_odds["spreads"]["away_spread_odds"]),
                            "total_points": float(best_odds["totals"]["total_points"]),
                            "over_odds": float(best_odds["totals"]["over_odds"]),
                            "under_odds": float(best_odds["totals"]["under_odds"]),
                        }
                        
                        # Basic validation (e.g., odds >= 1.0)
                        odds_to_validate = [
                            full_odds_data["home_odds"], full_odds_data["away_odds"],
                            full_odds_data["home_spread_odds"], full_odds_data["away_spread_odds"],
                            full_odds_data["over_odds"], full_odds_data["under_odds"]
                        ]
                        if full_odds_data["draw_odds"] > 0:
                            odds_to_validate.append(full_odds_data["draw_odds"])
                        
                        if any(o < 1.0 for o in odds_to_validate):
                            print(f"Warning: Skipping game {game_id} due to invalid decimal odds < 1.0", file=sys.stderr)
                            continue
                        
                        all_games_with_full_odds.append({
                            "odds_api_id": game_id,
                            "sport_key": sport_key,
                            "odds": full_odds_data
                        })
                    except Exception as e:
                        print(f"Warning: Could not parse or validate odds for game {game_id}: {e}", file=sys.stderr)
                else:
                    missing = []
                    if not h2h_valid: missing.append("H2H")
                    if not spreads_valid: missing.append("Spreads")
                    if not totals_valid: missing.append("Totals")
                    print(f"Warning: Could not find complete odds ({', '.join(missing)}) for game {game_id}", file=sys.stderr)
            
            print(f"Successfully processed odds for {len(all_games_with_full_odds)} games for sport {sport_key}.")
            
        except Exception as e:
            print(f"An unexpected error occurred fetching games/odds for {sport_key}: {e}", file=sys.stderr)
            # Continue to next sport key
    
    print(f"Total unique games with complete odds found across all sports: {len(all_games_with_full_odds)}")
    return all_games_with_full_odds