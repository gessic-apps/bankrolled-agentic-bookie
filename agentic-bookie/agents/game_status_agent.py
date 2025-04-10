#!/usr/bin/env python3
import sys
import requests
import os
import datetime
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from collections import defaultdict
from pydantic import BaseModel

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
    if duration_seconds <= 0:
        return "Error: Sleep duration must be positive."
    print(f"Sleeping for {duration_seconds} seconds...")
    time.sleep(duration_seconds)
    return f"Slept for {duration_seconds} seconds."

@function_tool
def get_bettable_unsettled_markets() -> List[Dict[str, Any]]:
    """Fetches markets from the API that are ready for betting but not yet settled (game not ended)."""
    if not API_URL:
        print("Error: Cannot get markets, API_URL is not configured.", file=sys.stderr)
        return []

    try:
        url = f"{API_URL}/api/markets"
        response = requests.get(url)
        response.raise_for_status()
        all_markets_data = response.json()

        relevant_markets = []
        if isinstance(all_markets_data, list):
            for market in all_markets_data:
                # Market must be ready for betting AND not yet ended
                if isinstance(market, dict) and \
                   all(k in market for k in ["address", "oddsApiId", "status", "resultSettled", "sportKey"]) and \
                   market.get("status") == "Open" and \
                   market.get("resultSettled") is False:
                    relevant_markets.append({
                        "address": market["address"],
                        "oddsApiId": market["oddsApiId"],
                        "sportKey": market["sportKey"]
                        # Only include necessary fields
                    })
                # Optional: Log skipped markets for debugging if needed
                # else:
                #     print(f"Skipping market: {market.get('address', 'N/A')} - Status: {market.get('status')}, Settled: {market.get('resultSettled')}", file=sys.stderr)

        else:
             print(f"Warning: Expected a list from /api/markets, but got {type(all_markets_data)}", file=sys.stderr)
             return []

        print(f"Found {len(relevant_markets)} markets that are ready for betting and not yet settled.")
        return relevant_markets
    except requests.exceptions.RequestException as e:
        print(f"Error fetching markets: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred in get_bettable_unsettled_markets: {e}", file=sys.stderr)
        return []

# Define a Pydantic model for the market info needed by check_completed_games
class MarketInfo(BaseModel):
    oddsApiId: str
    sportKey: str

@function_tool
def check_completed_games(markets_to_check: List[MarketInfo]) -> List[Dict[str, Any]]:
    """
    Checks if games with the given IDs are completed by querying the scores endpoint.
    Returns only information for games that are actually completed.

    Args:
        markets_to_check: List of dictionaries, each containing 'oddsApiId' and 'sportKey'.

    Returns:
        List of dictionaries containing information about completed games:
        [
            {
                "odds_api_id": str,
                "completed": bool, # Will always be true in the filtered list
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
        print("Error: Cannot fetch game scores, SPORTS_API_KEY is missing.", file=sys.stderr)
        return []

    if not markets_to_check:
        print("Warning: No markets provided to check_completed_games.", file=sys.stderr)
        return []

    # Group markets by sport_key
    games_by_sport: Dict[str, List[str]] = defaultdict(list)
    for market_info in markets_to_check:
        # Use attribute access now
        sport_key = market_info.sportKey
        odds_api_id = market_info.oddsApiId
        if sport_key and odds_api_id:
            games_by_sport[sport_key].append(odds_api_id)
        else:
            print(f"Warning: Skipping market in check_completed_games due to missing sportKey or oddsApiId: {market_info}", file=sys.stderr)

    all_completed_games_info = []
    processed_ids = set()
    date_format = "iso"
    # Get games from the last 3 days (max allowed) to ensure we capture recently completed games
    days_from = 3
    total_checked_count = len(markets_to_check) # Use the original list size for reporting
    
    # Iterate through each sport and fetch scores
    for sport_key, game_ids_for_sport in games_by_sport.items():
        if not game_ids_for_sport:
            continue

        unique_game_ids_for_sport = list(set(game_ids_for_sport)) # Remove duplicates for this sport

        try:
            # Use comma-separated game IDs to filter for specific games
            event_ids_param = ",".join(unique_game_ids_for_sport)

            # Fetch game data from scores endpoint
            print(f"Checking completion status for {len(unique_game_ids_for_sport)} games in sport {sport_key}...")
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

            completed_games_info = []

            for game in api_data:
                game_id = game.get("id")
                # Check against the unique IDs *for this sport* and globally processed IDs
                if not game_id or game_id not in unique_game_ids_for_sport or game_id in processed_ids:
                    continue # Skip if ID is missing, not requested for this sport, or already processed

                completed = game.get("completed", False)

                # Only process games that are marked as completed
                if completed:
                    processed_ids.add(game_id) # Avoid duplicates if API returns multiple entries
                    game_info = {
                        "odds_api_id": game_id,
                        "completed": True,
                        "home_team": game.get("home_team"),
                        "away_team": game.get("away_team"),
                        "home_score": None,
                        "away_score": None,
                        "last_update": game.get("last_update")
                    }

                    # Add scores if available and valid
                    scores = game.get("scores")
                    home_score_found = False
                    away_score_found = False
                    if scores and isinstance(scores, list):
                        for team_score in scores:
                            team_name = team_score.get("name")
                            score = team_score.get("score") # Score is returned as string

                            if score is None: continue # Skip if score is null

                            if team_name == game_info["home_team"]:
                                game_info["home_score"] = score
                                home_score_found = True
                            elif team_name == game_info["away_team"]:
                                game_info["away_score"] = score
                                away_score_found = True

                    # Only add if scores are validly found for both teams
                    if home_score_found and away_score_found:
                        completed_games_info.append(game_info)
                    else:
                        print(f"Warning: Game {game_id} marked completed but missing valid scores for both teams. Skipping result setting.", file=sys.stderr)

            all_completed_games_info.extend(completed_games_info)
            print(f"Found {len(completed_games_info)} completed games with scores for sport {sport_key}.")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching game completion status for sport {sport_key}: {e}", file=sys.stderr)
            # Continue to next sport key
        except Exception as e:
            print(f"An unexpected error occurred checking completed games for sport {sport_key}: {e}", file=sys.stderr)
            # Continue to next sport key

    print(f"Found {len(all_completed_games_info)} completed games with scores across all sports out of {total_checked_count} markets checked.")
    return all_completed_games_info

@function_tool
def set_game_result(market_address: str, home_score: str, away_score: str) -> Dict[str, Any]:
    """
    Sets the game status to STARTED and then sets the final result for a game
    by calling the game-status API endpoint twice sequentially.

    Args:
        market_address: The address of the market contract to update.
        home_score: The final score of the home team (as a string).
        away_score: The final score of the away team (as a string).

    Returns:
        Dictionary with status information from the API calls.
    """
    if not API_URL:
        print("Error: Cannot set game result, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}

    # Validate scores can be converted to integers before any API calls
    try:
        home_score_int = int(home_score)
        away_score_int = int(away_score)
    except (ValueError, TypeError) as e:
        error_message = f"Invalid score format for market {market_address}. Home: '{home_score}', Away: '{away_score}'. Error: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}

    base_url = f"{API_URL}/api/market/{market_address}/game-status"

    # 1. Call to Start the Game
    start_payload = {"action": "start"}
    start_status = "pending"
    start_message = ""
    start_http_status = None
    try:
        print(f"Attempting to start game: POST {base_url} for market {market_address} with payload: {start_payload}")
        start_response = requests.post(base_url, json=start_payload)
        start_response.raise_for_status() # Raises HTTPError for 4xx/5xx
        start_result = start_response.json()
        print(f"Successfully started game (or it was already started) for market {market_address}. Response: {start_result}")
        start_status = "success"
        start_message = start_result
    except requests.exceptions.HTTPError as e:
        # It's possible the game is already started, which might cause an error here.
        # We'll log it but proceed to try setting the result anyway, as the pre-condition might now be met.
        # The backend handles the specific contract logic.
        start_status = "warning" # Treat as warning, might be okay if already started
        start_message = f"HTTP Error starting game for market {market_address}: {e.response.status_code} - {e.response.text}"
        start_http_status = e.response.status_code
        print(f"Warning: {start_message}", file=sys.stderr)
        # Allow proceeding even if start fails, as it might be due to being already started.
        # The set-result call will fail later if the status is truly incorrect.
    except requests.exceptions.RequestException as e:
        start_status = "error"
        start_message = f"Request Error starting game for market {market_address}: {e}"
        print(start_message, file=sys.stderr)
        # If starting fails due to network/request issues, don't proceed.
        return {"status": "error", "step": "start_game", "message": start_message, "market_address": market_address}
    except Exception as e:
        start_status = "error"
        start_message = f"An unexpected error occurred during game start for market {market_address}: {e}"
        print(start_message, file=sys.stderr)
        # If starting fails unexpectedly, don't proceed.
        return {"status": "error", "step": "start_game", "message": str(e), "market_address": market_address}

    # 2. Call to Set the Result (only if starting didn't have a fatal error)
    set_result_payload = {
        "action": "set-result",
        "homeScore": home_score_int,
        "awayScore": away_score_int
    }
    set_result_status = "pending"
    set_result_message = ""
    set_result_http_status = None

    try:
        print(f"Attempting to set game result: POST {base_url} for market {market_address} with payload: {set_result_payload}")
        set_result_response = requests.post(base_url, json=set_result_payload)
        set_result_response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        set_result_result = set_result_response.json()
        print(f"Successfully set game result for market {market_address}. Response: {set_result_result}")
        set_result_status = "success"
        set_result_message = set_result_result
        # Final status is success only if set_result succeeds
        final_status = "success"
        final_message = {"start_game_result": start_message, "set_result_result": set_result_message}

    except requests.exceptions.HTTPError as e:
        set_result_status = "error"
        set_result_message = f"HTTP Error setting game result for market {market_address}: {e.response.status_code} - {e.response.text}"
        set_result_http_status = e.response.status_code
        print(set_result_message, file=sys.stderr)
        final_status = "error" # If setting result fails, the overall operation failed
        final_message = set_result_message

    except requests.exceptions.RequestException as e:
        set_result_status = "error"
        set_result_message = f"Request Error setting game result for market {market_address}: {e}"
        print(set_result_message, file=sys.stderr)
        final_status = "error"
        final_message = set_result_message

    except Exception as e:
        set_result_status = "error"
        set_result_message = f"An unexpected error occurred in set_game_result for market {market_address}: {e}"
        print(set_result_message, file=sys.stderr)
        final_status = "error"
        final_message = str(e)

    return {
        "status": final_status, # Overall status reflects whether the result was set
        "market_address": market_address,
        "start_game_status": start_status,
        "start_game_http_status": start_http_status,
        "set_result_status": set_result_status,
        "set_result_http_status": set_result_http_status,
        "message": final_message # Contains details from both steps or the final error
    }

# --- Agent Definition ---

game_status_agent = Agent(
    name="Game Result Settlement Agent",
    handoff_description="Specialist agent for checking game completion and setting final results on settled markets.",
    instructions="""
    You are the Game Result Settlement Agent. Your primary goal is to identify completed games (NBA & Soccer) associated with active betting markets and update the market contract with the final scores.

    Your workflow should be as follows:

    1. Call `get_bettable_unsettled_markets` to find markets whose `status` is "Open" and `resultSettled` is false. These markets will have an `address`, `oddsApiId`, and `sportKey`.
    2. If the list of markets is empty, no work needs to be done currently. Proceed to step 6 (sleep).
    3. Prepare a list of dictionaries, where each dictionary contains the `oddsApiId` and `sportKey` for each market found in step 1.
    4. Call `check_completed_games` with the list prepared in step 3 to get data for completed games with valid scores across all relevant sports.
    5. Iterate through the list of completed games returned by `check_completed_games`. For each completed game:
        a. Find the corresponding market(s) from the list obtained in step 1 using the `odds_api_id`. (Note: Multiple markets might exist for the same game ID if created separately, handle each).
        b. Extract the `home_score` and `away_score` from the completed game data.
        c. For each corresponding market address found in step 5a, call `set_game_result` with the market's `address`, `home_score`, and `away_score`. **If the call to `set_game_result` indicates an error for a specific market (e.g., returns a status other than 'success'), log the error details including the market address and the reason for failure, but continue processing the next completed game or market. Do not stop the entire process due to a single market failure.**
    6. Report a summary of the markets for which you attempted to set the result (mentioning success or failure for each attempt, based on the outcome of step 5c). If no markets were processed or no games were found completed, state that.
    7. Call `sleep_tool` with `duration_seconds` set to 60 to wait for 1 minute.
    8. Go back to step 1 to repeat the cycle.
    """,
    tools=[
        get_bettable_unsettled_markets,
        check_completed_games,
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

    async def test_game_result_settlement():
        # Input prompt to trigger the agent's logic loop implicitly
        prompt = "Check for completed games (NBA & Soccer) corresponding to active markets and set their results. Repeat periodically."
        print(f"--- Running Game Result Settlement Agent with prompt: '{prompt}' ---")
        # Ensure environment variables are loaded if running directly
        if not SPORTS_API_KEY or not API_URL:
             print("Error: Missing SPORTS_API_KEY or API_URL in .env file. Cannot run test.", file=sys.stderr)
             return

        # Running it once will perform one cycle.
        result = await Runner.run(game_status_agent, prompt) # Removed max_i if not defined
        print("--- Game Result Settlement Agent Result (One Cycle) ---")
        print(result.final_output)
        print("------------------------------------------------------")

    # To run the test: 
    asyncio.run(test_game_result_settlement())
    # Remember that this only runs *one* cycle. The agent's instructions describe a continuous loop.
    print("Game Result Settlement Agent defined. Run agentGroup.py or similar orchestrator to manage its lifecycle.") 