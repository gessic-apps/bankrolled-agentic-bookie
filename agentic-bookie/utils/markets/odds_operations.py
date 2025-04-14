#!/usr/bin/env python3
import sys
from typing import List, Dict, Any
import json
import os

from ..config import SUPPORTED_SPORT_KEYS
from ..sports.games_data import fetch_games_with_odds
from ..markets.market_data import get_all_markets, get_market_details
from ..markets.odds_management import update_odds_for_multiple_markets, update_odds_for_market

#Add a function that lets the agent read the most recent actions from the file.

def read_actions_from_file():
    """
    Reads the most recent actions from the risk manager context file and parses the JSON.
    Returns an empty dictionary if the file doesn't exist, is empty, or contains invalid JSON.
    """
    file_path = "/Users/osman/bankrolled-agent-bookie/agentic-bookie/agents/risk_manager_context.json"
    try:
        with open(file_path, "r") as f:
            content = f.read()
            if not content:
                print(f"Warning: Risk context file is empty: {file_path}")
                return {}
            return json.loads(content)
    except FileNotFoundError:
        print(f"Warning: Risk context file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Warning: Error decoding JSON from risk context file {file_path}: {e}")
        return {}
    except Exception as e:
        print(f"Warning: An unexpected error occurred reading risk context file {file_path}: {e}")
        return {}


def fetch_and_update_all_markets() -> Dict[str, Any]:
    """Fetches games with odds, gets existing markets, and updates all market odds in a single operation."""
    # Step 1: Fetch games with odds for all supported sports
    print("Fetching games with odds for all supported sports...")
    games_with_odds = fetch_games_with_odds(SUPPORTED_SPORT_KEYS)
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
    existing_markets = get_all_markets()
    print(f"Found {len(existing_markets)} existing markets")
    
    if not existing_markets:
        return {
            "status": "error", 
            "message": "No existing markets found from the platform API",
            "total_markets_with_odds": len(odds_api_id_to_odds),
            "total_markets_updated": 0
        }
    
    # Step 3.5: Read risk control actions
    print("Reading risk control actions...")
    risk_actions_result = read_actions_from_file()
    risk_actions = {}
    if isinstance(risk_actions_result, dict) and 'status' not in risk_actions_result:
        risk_actions = risk_actions_result
        print(f"Loaded risk control data for {len(risk_actions)} markets.")
    elif isinstance(risk_actions_result, dict) and 'status' in risk_actions_result:
         print(f"Info/Warning from read_actions_from_file: {risk_actions_result.get('message', 'No message provided')}")
    else:
        print("Warning: Could not read or parse risk control actions file correctly.")

    # Step 4: Match markets with odds and prepare update data, skipping risk-controlled ones
    markets_for_update = []
    markets_skipped_risk_control = 0 # Counter for skipped markets

    for market in existing_markets:
        odds_api_id = market.get("oddsApiId")
        market_address = market.get("address")
        
        if not (odds_api_id and market_address):
            print(f"Warning: Market missing oddsApiId or address: {market}")
            continue
            
        # Check risk control status first
        if market_address in risk_actions and risk_actions[market_address].get('risk_controlled') is True:
            print(f"Skipping market {market_address} due to active risk control.")
            markets_skipped_risk_control += 1
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
    print(f"Preparing to update {len(markets_for_update)} markets with available odds data. Skipped {markets_skipped_risk_control} due to risk control.")
    
    if not markets_for_update:
        return {
            "status": "info",
            "message": f"No markets need odds updates (excluding {markets_skipped_risk_control} risk-controlled markets).",
            "total_markets_with_odds": len(odds_api_id_to_odds),
            "total_existing_markets": len(existing_markets),
            "total_markets_skipped_risk_control": markets_skipped_risk_control,
            "total_markets_updated": 0
        }
    
    # Perform the batch update
    update_results = update_odds_for_multiple_markets(markets_for_update)
    
    # Step 6: Return combined result summary
    return {
        "status": "success",
        "message": f"Attempted update for {len(markets_for_update)} markets (skipped {markets_skipped_risk_control} risk-controlled). Successful: {update_results['successful_updates']}.",
        "total_markets_with_odds": len(odds_api_id_to_odds),
        "total_existing_markets": len(existing_markets),
        "total_markets_skipped_risk_control": markets_skipped_risk_control,
        "total_markets_matched_for_update": len(markets_for_update),
        "total_markets_updated": update_results["successful_updates"],
        "failed_updates": update_results["failed_updates"],
        "detailed_results": update_results["results"]
    }


# --- New function to update a single market ---

def prepare_single_market_update_payload(market_address: str) -> Dict[str, Any]:
    """Fetches latest odds and prepares the data payload for updating a single specified market.
    Returns the payload dictionary on success, or an error dictionary.
    """
    print(f"Preparing update payload for single market: {market_address}")

    # Step 1: Get market details to find its oddsApiId
    print(f"Fetching details for market: {market_address}")
    market_details = get_market_details(market_address)
    
    if not market_details or market_details.get("status") == "error":
        message = f"Error fetching details for market {market_address}: {market_details.get('message', 'Unknown error')}"
        print(message)
        # Return an error structure consistent with previous return types
        return {"status": "error", "message": message, "market_address": market_address}
    
    odds_api_id = market_details.get("oddsApiId")
    if not odds_api_id:
        message = f"Market {market_address} is missing oddsApiId."
        print(message)
        return {"status": "error", "message": message, "market_address": market_address}
        
    print(f"Market {market_address} corresponds to oddsApiId: {odds_api_id}")

    # Step 2: Fetch the latest odds data for relevant sports
    print("Fetching latest games with odds...")
    games_with_odds = fetch_games_with_odds(SUPPORTED_SPORT_KEYS)
    
    if not games_with_odds:
        message = "No games with odds found from The Odds API."
        print(message)
        return {"status": "error", "message": message, "market_address": market_address}

    # Find the specific odds data for our market
    odds_data = None
    for game in games_with_odds:
        if game.get("odds_api_id") == odds_api_id:
            odds_data = game.get("odds")
            break
            
    if not odds_data:
        message = f"No current odds data found for oddsApiId: {odds_api_id} (Market: {market_address})."
        print(message)
        # Use 'nodata' status or similar to distinguish from other errors
        return {"status": "nodata", "message": message, "market_address": market_address}

    # Step 3: Prepare the data payload
    market_update_payload = {
        # Include status and message in the success case for consistency
        "status": "success",
        "message": f"Successfully prepared update payload for market {market_address}.",
        "market_address": market_address,
        "home_odds": odds_data.get("home_odds"),
        "away_odds": odds_data.get("away_odds"),
        "draw_odds": odds_data.get("draw_odds"), # Pass along if present
        "home_spread_points": odds_data.get("home_spread_points"),
        "home_spread_odds": odds_data.get("home_spread_odds"),
        "away_spread_odds": odds_data.get("away_spread_odds"),
        "total_points": odds_data.get("total_points"),
        "over_odds": odds_data.get("over_odds"),
        "under_odds": odds_data.get("under_odds")
    }

    # Check if all essential odds fields are present (draw_odds is optional)
    required_keys = {k for k in market_update_payload if k not in ["status", "message", "market_address", "draw_odds"]}
    if not all(market_update_payload.get(k) is not None for k in required_keys):
        missing_keys = [k for k in required_keys if market_update_payload.get(k) is None]
        message = f"Incomplete odds data found for oddsApiId {odds_api_id}. Missing: {missing_keys}. Cannot prepare payload for market {market_address}."
        print(f"Warning: {message}")
        return {"status": "incomplete_data", "message": message, "market_address": market_address}

    print(f"Payload prepared for market {market_address}")
    # Step 4: Return the prepared payload
    return market_update_payload


# Example usage (if run as a script)
# ... (keep existing example usage for fetch_and_update_all_markets)

# Updated example for the renamed function:
if __name__ == "__main__":
    # Example for fetch_and_update_all_markets (optional)
    # all_results = fetch_and_update_all_markets()
    # print("\n--- All Markets Update Results ---")
    # print(json.dumps(all_results, indent=2))

    # Example for prepare_single_market_update_payload
    target_market = "0xadAAD64F6f200C1CBBF719A3b457608aC17fC147" # Replace with a real address
    print(f"\n--- Preparing Payload for Single Market: {target_market} ---")
    payload_result = prepare_single_market_update_payload(target_market)
    print("\n--- Single Market Payload Result ---")
    print(json.dumps(payload_result, indent=2))
    
    # You would then call update_odds_for_market separately if status is 'success'
    # if payload_result.get("status") == "success":
    #     print("\n--- Calling update_odds_for_market with payload ---")
    #     # Remove status/message before passing to update function if needed
    #     update_payload = {k: v for k, v in payload_result.items() if k not in ["status", "message"]}
    #     # update_result = update_odds_for_market(**update_payload)
    #     # print(json.dumps(update_result, indent=2))
    # else:
    #     print("\nPayload preparation failed, skipping market update.")