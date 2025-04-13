#!/usr/bin/env python3
import sys
import requests
import os
import datetime
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:3000") # Default matching other agents

if not API_URL:
    print(f"Warning: API_URL not found, defaulting to {API_URL}", file=sys.stderr)

# Import Agent SDK components
from agents import Agent, function_tool,  AsyncOpenAI, OpenAIChatCompletionsModel

# Import Monte Carlo simulation tool
from .monte_carlo_sims import analyze_market_risk, bulk_analyze_markets

# Import market exposure tools
from ..tools.market_exposure_tools import (
    fetch_market_exposure_details,
    set_bet_type_exposure_limit,
    get_market_exposure_by_type
)

# Import odds management tools
from ..tools.odds_tools import (
    update_odds_for_market_impl,
    update_odds_for_multiple_markets_impl,
    check_market_odds_impl,
    OddsData,
    BatchUpdateResult
)

# Import the fetch_games_with_odds function from odds_manager_agent
# to get the latest odds from the API
from .odds_manager_agent import fetch_games_with_odds_impl, SUPPORTED_SPORT_KEYS

# Import prediction tools
from ..tools.prediction_tools import (
    get_bankrolled_predictions,
    find_predictions_for_market,
    analyze_user_prediction_accuracy
)

# --- Tool Definitions ---
deepseek_client = AsyncOpenAI(base_url="https://api.deepseek.com", api_key="sk-524207d333a049f5b02cbc0c36bc860f")
@function_tool
def get_all_markets() -> List[Dict[str, Any]]:
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
                # Check for all required fields including exposure fields
                if isinstance(market, dict) and all(k in market for k in ["address", "oddsApiId", "status", "maxExposure", "currentExposure"]):
                    # Convert exposure values to float for easier comparison
                    try:
                        market["maxExposure"] = float(market["maxExposure"])
                        market["currentExposure"] = float(market["currentExposure"])
                    except (ValueError, TypeError):
                        print(f"Warning: Could not convert exposure values to float for market {market.get('address')}", file=sys.stderr)
                        # Use default values if conversion fails
                        market["maxExposure"] = 2000.0
                        market["currentExposure"] = 0.0
                    
                    cleaned_markets.append(market)
                else:
                    print(f"Warning: Skipping market entry due to missing required fields: {market}", file=sys.stderr)
        else:
            print(f"Warning: Expected a list from /api/markets, but got {type(markets_data)}", file=sys.stderr)
            return []

        print(f"Successfully fetched {len(cleaned_markets)} existing markets with exposure data.")
        return cleaned_markets
    except requests.exceptions.RequestException as e:
        print(f"Error fetching existing markets: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred in get_all_markets: {e}", file=sys.stderr)
        return []

@function_tool
def add_liquidity_to_market(market_address: str, amount: int) -> Dict[str, Any]:
    """
    Adds liquidity to a specific market.
    
    Args:
        market_address: The blockchain address of the market
        amount: The amount of liquidity to add (typically in the smallest unit of the token)
        
    Returns:
        dict: API response with liquidity addition details
    """
    if not API_URL:
        print("Error: Cannot add liquidity, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}
    
    payload = {
        "amount": amount
    }
    
    try:
        url = f"{API_URL}/api/market/{market_address}/add-liquidity"
        print(f"Attempting to add liquidity: POST {url} with payload: {payload}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Successfully added liquidity to market {market_address}. Response: {result}")
        return {
            "status": "success",
            "market_address": market_address,
            "amount_added": amount,
            "result": result
        }
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error adding liquidity to market {market_address}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error adding liquidity to market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except Exception as e:
        error_message = f"An unexpected error occurred in add_liquidity_to_market: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}

@function_tool
def get_liquidity_pool_info() -> Dict[str, Any]:
    """
    Gets information about the global liquidity pool.
    
    Returns:
        dict: Information about the liquidity pool including total liquidity,
              allocated liquidity, and available liquidity
    """
    if not API_URL:
        print("Error: Cannot get liquidity pool info, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}
    
    try:
        url = f"{API_URL}/api/liquidity-pool"
        response = requests.get(url)
        response.raise_for_status()
        result = response.json()
        print(f"Successfully fetched liquidity pool information.")
        return {
            "status": "success",
            "pool_info": result
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching liquidity pool info: {e}", file=sys.stderr)
        return {"status": "error", "message": str(e)}
    except Exception as e:
        print(f"An unexpected error occurred in get_liquidity_pool_info: {e}", file=sys.stderr)
        return {"status": "error", "message": str(e)}

# Monte Carlo simulation tools
@function_tool
def run_monte_carlo_analysis(
    market_address: str,
    oddsApiId: str,
    status: str,
    currentExposure: float,
    maxExposure: float,
    homeOdds: float,
    awayOdds: float,
    homeSpreadPoints: float,
    homeSpreadOdds: float,
    awaySpreadOdds: float,
    totalPoints: float,
    overOdds: float,
    underOdds: float,
    num_simulations: int
) -> str:
    """
    Run Monte Carlo simulation on a market to assess risk and recommend actions.
    
    Args:
        market_address: The blockchain address of the market
        oddsApiId: The odds API identifier for the market
        status: Current market status (e.g., "Open")
        currentExposure: Total current exposure amount
        maxExposure: Maximum allowed exposure
        homeOdds: Current home team odds (moneyline)
        awayOdds: Current away team odds (moneyline)
        homeSpreadPoints: Current home spread points
        homeSpreadOdds: Current home spread odds
        awaySpreadOdds: Current away spread odds
        totalPoints: Current total points line
        overOdds: Current over odds
        underOdds: Current under odds
        num_simulations: Number of simulations to run
        
    Returns:
        JSON string containing risk assessment and recommendations
    """
    # Use a default value for num_simulations if needed
    if num_simulations <= 0:
        num_simulations = 10000
    
    market_data = {
        "address": market_address,
        "oddsApiId": oddsApiId,
        "status": status,
        "currentExposure": currentExposure,
        "maxExposure": maxExposure,
        "homeOdds": homeOdds,
        "awayOdds": awayOdds,
        "homeSpreadPoints": homeSpreadPoints,
        "homeSpreadOdds": homeSpreadOdds,
        "awaySpreadOdds": awaySpreadOdds,
        "totalPoints": totalPoints,
        "overOdds": overOdds,
        "underOdds": underOdds
    }
    
    result = analyze_market_risk(market_data, None, num_simulations)
    
    # Return as string for easier compatibility
    import json
    return json.dumps(result, indent=2)

@function_tool
def run_monte_carlo_analysis_with_exposure(
    market_address: str,
    oddsApiId: str,
    status: str,
    currentExposure: float,
    maxExposure: float,
    homeOdds: float,
    awayOdds: float,
    homeSpreadPoints: float,
    homeSpreadOdds: float,
    awaySpreadOdds: float,
    totalPoints: float,
    overOdds: float,
    underOdds: float,
    exposure_home: float,
    exposure_away: float,
    exposure_over: float,
    exposure_under: float,
    exposure_home_spread: float,
    exposure_away_spread: float,
    num_simulations: int
) -> str:
    """
    Run Monte Carlo simulation with detailed exposure distribution.
    
    Args:
        market_address: The blockchain address of the market
        oddsApiId: The odds API identifier for the market
        status: Current market status (e.g., "Open")
        currentExposure: Total current exposure amount
        maxExposure: Maximum allowed exposure
        homeOdds: Current home team odds (moneyline)
        awayOdds: Current away team odds (moneyline)
        homeSpreadPoints: Current home spread points
        homeSpreadOdds: Current home spread odds
        awaySpreadOdds: Current away spread odds
        totalPoints: Current total points line
        overOdds: Current over odds
        underOdds: Current under odds
        exposure_home: Exposure amount on home team moneyline
        exposure_away: Exposure amount on away team moneyline
        exposure_over: Exposure amount on over total
        exposure_under: Exposure amount on under total
        exposure_home_spread: Exposure amount on home team spread
        exposure_away_spread: Exposure amount on away team spread
        num_simulations: Number of simulations to run
        
    Returns:
        JSON string containing risk assessment and recommendations
    """
    market_data = {
        "address": market_address,
        "oddsApiId": oddsApiId,
        "status": status,
        "currentExposure": currentExposure,
        "maxExposure": maxExposure,
        "homeOdds": homeOdds,
        "awayOdds": awayOdds,
        "homeSpreadPoints": homeSpreadPoints,
        "homeSpreadOdds": homeSpreadOdds,
        "awaySpreadOdds": awaySpreadOdds,
        "totalPoints": totalPoints,
        "overOdds": overOdds,
        "underOdds": underOdds
    }
    
    # Use a default value for num_simulations if needed
    if num_simulations <= 0:
        num_simulations = 10000
    
    exposure_distribution = {
        "home": exposure_home,
        "away": exposure_away,
        "over": exposure_over,
        "under": exposure_under,
        "home_spread": exposure_home_spread,
        "away_spread": exposure_away_spread
    }
    
    result = analyze_market_risk(market_data, exposure_distribution, num_simulations)
    
    # Return as string for easier compatibility
    import json
    return json.dumps(result, indent=2)

# --- Tool Definition for odds management ---
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
    under_odds: float,
    draw_odds: Optional[float] = None
) -> Dict[str, Any]:
    """Updates all odds types (moneyline, spread, total) for a specific market to influence betting behavior and manage risk. Expects decimal floats/points, converts to integer format for the API call. Now supports draw odds for soccer markets."""
    # Set default values for draw_odds if None
    draw_odds_val = draw_odds if draw_odds is not None else 0.0
    
    return update_odds_for_market_impl(
        market_address=market_address,
        home_odds=home_odds,
        away_odds=away_odds, 
        draw_odds=draw_odds_val,
        home_spread_points=home_spread_points,
        home_spread_odds=home_spread_odds,
        away_spread_odds=away_spread_odds,
        total_points=total_points,
        over_odds=over_odds,
        under_odds=under_odds,
        api_url=API_URL
    )

# --- NEW TOOL: Set Market Exposure Limits ---
@function_tool
def set_market_exposure_limits(
    market_address: str,
    home_moneyline_limit: Optional[int] = None,
    away_moneyline_limit: Optional[int] = None,
    draw_limit: Optional[int] = None,
    home_spread_limit: Optional[int] = None,
    away_spread_limit: Optional[int] = None,
    over_limit: Optional[int] = None,
    under_limit: Optional[int] = None
) -> Dict[str, Any]:
    """Sets specific exposure limits for various bet types within a market. Only provided limits will be updated."""
    if not API_URL:
        print("Error: Cannot set exposure limits, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}

    payload = {}
    if home_moneyline_limit is not None: payload["homeMoneylineLimit"] = home_moneyline_limit
    if away_moneyline_limit is not None: payload["awayMoneylineLimit"] = away_moneyline_limit
    if draw_limit is not None: payload["drawLimit"] = draw_limit
    if home_spread_limit is not None: payload["homeSpreadLimit"] = home_spread_limit
    if away_spread_limit is not None: payload["awaySpreadLimit"] = away_spread_limit
    if over_limit is not None: payload["overLimit"] = over_limit
    if under_limit is not None: payload["underLimit"] = under_limit

    if not payload:
        return {"status": "warning", "message": "No limits provided to set.", "market_address": market_address}

    try:
        url = f"{API_URL}/api/market/{market_address}/exposure-limits"
        print(f"Attempting to set exposure limits: POST {url} with payload: {payload}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Successfully set exposure limits for market {market_address}. Response: {result}")
        return {
            "status": "success",
            "market_address": market_address,
            "limits_set": payload,
            "result": result
        }
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error setting exposure limits for market {market_address}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error setting exposure limits for market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except Exception as e:
         error_message = f"An unexpected error occurred in set_market_exposure_limits: {e}"
         print(error_message, file=sys.stderr)
         return {"status": "error", "message": error_message, "market_address": market_address}


# --- NEW TOOL: Reduce Market Funding ---
@function_tool
def reduce_market_funding(
    market_address: str,
    amount: int
) -> Dict[str, Any]:
    """Reduces the total funding (and thus max exposure) allocated to a specific market from the central liquidity pool."""
    if not API_URL:
        print("Error: Cannot reduce market funding, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}

    if amount <= 0:
        return {"status": "warning", "message": "Reduction amount must be positive.", "market_address": market_address}

    payload = {
        "bettingEngineAddress": market_address, # API expects bettingEngineAddress
        "amount": amount
    }

    try:
        url = f"{API_URL}/api/liquidity-pool/reduce-market-funding"
        print(f"Attempting to reduce market funding: POST {url} with payload: {payload}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Successfully reduced funding for market {market_address} by {amount}. Response: {result}")
        return {
            "status": "success",
            "market_address": market_address,
            "amount_reduced": amount,
            "result": result
        }
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error reducing funding for market {market_address}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error reducing funding for market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except Exception as e:
         error_message = f"An unexpected error occurred in reduce_market_funding: {e}"
         print(error_message, file=sys.stderr)
         return {"status": "error", "message": error_message, "market_address": market_address}


# --- New Granular Exposure Management Tools ---

@function_tool
def get_detailed_market_exposure(market_address: str) -> Dict[str, Any]:
    """
    Gets detailed exposure information for a specific market, broken down by bet type and side.
    
    Args:
        market_address (str): The blockchain address of the market
        
    Returns:
        dict: Detailed exposure information organized by bet type and side
    """
    if not API_URL:
        print("Error: Cannot get detailed market exposure, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}
    
    try:
        result = get_market_exposure_by_type(market_address, API_URL)
        
        if "error" in result:
            # Try to get basic market info as a fallback
            try:
                url = f"{API_URL}/api/market/{market_address}"
                print(f"Falling back to basic market data from: {url}")
                response = requests.get(url)
                response.raise_for_status()
                market_data = response.json()
                
                # Create a simplified exposure model from the general market data
                max_exposure = float(market_data.get("maxExposure", 0))
                current_exposure = float(market_data.get("currentExposure", 0))
                
                # Calculate a utilization percentage
                utilization = 0
                if max_exposure > 0:
                    utilization = (current_exposure / max_exposure) * 100
                
                simplified_result = {
                    "global": {
                        "max_exposure": max_exposure,
                        "current_exposure": current_exposure,
                        "utilization_percentage": utilization
                    },
                    "warning": "Detailed exposure breakdown not available - showing global values only",
                    "raw_market_data": market_data
                }
                
                print(f"Created simplified exposure model for market {market_address}: utilization {utilization:.1f}%")
                return simplified_result
            except Exception as e:
                print(f"Error fetching basic market data: {e}", file=sys.stderr)
                return result  # Return the original error
        
        print(f"Detailed exposure for market {market_address} fetched successfully")
        return result
    except Exception as e:
        error_message = f"Unexpected error in get_detailed_market_exposure: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}

@function_tool
def set_specific_bet_type_limit(
    market_address: str,
    bet_type: str,
    side: str,
    limit: int
) -> Dict[str, Any]:
    """
    Sets an exposure limit for a specific bet type and side within a market.
    
    Args:
        market_address (str): The blockchain address of the market
        bet_type (str): The type of bet ('moneyline', 'spread', 'total', 'draw')
        side (str): The side of the bet ('home', 'away', 'over', 'under', 'draw')
        limit (int): The exposure limit to set
        
    Returns:
        dict: Result of the operation
    """
    if not API_URL:
        print("Error: Cannot set bet type limit, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}
    
    print(f"Setting limit for {bet_type}/{side} to {limit} on market {market_address}")
    result = set_bet_type_exposure_limit(market_address, bet_type, side, limit, API_URL)
    
    return result

@function_tool
def check_market_odds(market_address: str) -> Dict[str, Any]:
    """Checks if a specific betting market (identified by its address) already has odds set."""
    return check_market_odds_impl(market_address, API_URL)

@function_tool
def update_odds_for_multiple_markets(
    markets_data: List[OddsData]
) -> BatchUpdateResult:
    """Updates odds for multiple markets at once."""
    return update_odds_for_multiple_markets_impl(markets_data, API_URL)

# --- Bankrolled Prediction Tools ---

@function_tool
def fetch_latest_odds(sport_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Fetches the latest odds from the API for the specified sports.
    
    Args:
        sport_keys: List of sport keys to fetch odds for. If not provided, all supported sports will be used.
        
    Returns:
        dict: A structure containing the latest odds mapped by oddsApiId
    """
    # If no sport keys provided, use all supported sports
    if sport_keys is None:
        sport_keys = SUPPORTED_SPORT_KEYS
    try:
        games_with_odds = fetch_games_with_odds_impl(sport_keys)
        
        # Create a mapping from oddsApiId to odds data for efficient lookup
        odds_api_id_to_odds = {}
        for game in games_with_odds:
            odds_api_id = game.get("odds_api_id")
            odds_data = game.get("odds")
            if odds_api_id and odds_data:
                odds_api_id_to_odds[odds_api_id] = odds_data
        
        return {
            "status": "success",
            "message": f"Successfully fetched odds for {len(odds_api_id_to_odds)} games",
            "odds_data": odds_api_id_to_odds,
            "sport_keys": sport_keys
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error fetching latest odds: {str(e)}",
            "odds_data": {},
            "sport_keys": sport_keys
        }

@function_tool
def fetch_and_update_markets() -> Dict[str, Any]:
    """
    Fetches latest odds from the API and updates all markets that need updating.
    Updates include moneyline, spread points, spread odds and totals.
    Unlike the odds_manager, this function updates ALL markets, even those that already have odds.
    
    Returns:
        dict: Results of the batch update operation with details on which markets were updated
    """
    # Step 1: Fetch games with odds for all supported sports
    print("Fetching games with latest odds for all supported sports...")
    sport_keys = SUPPORTED_SPORT_KEYS
    games_with_odds = fetch_games_with_odds_impl(sport_keys)
    print(f"Found {len(games_with_odds)} games with complete odds data")
    
    if not games_with_odds:
        return {
            "status": "error",
            "message": "No games with odds found from The Odds API",
            "total_markets": 0,
            "markets_updated": 0
        }
    
    # Step 2: Create a mapping from odds_api_id to odds data for efficient lookup
    odds_api_id_to_odds = {
        game["odds_api_id"]: game["odds"] 
        for game in games_with_odds
    }
    print(f"Created mapping for {len(odds_api_id_to_odds)} games by odds API ID")
    
    # Step 3: Get existing markets
    print("Fetching existing markets...")
    existing_markets = get_all_markets()
    open_markets = [m for m in existing_markets if m.get("status") == "Open"]
    print(f"Found {len(open_markets)} open markets out of {len(existing_markets)} total markets")
    
    if not open_markets:
        return {
            "status": "info",
            "message": "No open markets found to update",
            "total_markets": len(existing_markets),
            "open_markets": 0,
            "markets_updated": 0
        }
    
    # Step 4: Match markets with odds and prepare update data
    markets_for_update = []
    markets_without_odds_data = []
    
    for market in open_markets:
        odds_api_id = market.get("oddsApiId")
        market_address = market.get("address")
        
        if not (odds_api_id and market_address):
            print(f"Warning: Market missing oddsApiId or address: {market}")
            continue
        
        # Check if we have latest odds for this market
        if odds_api_id in odds_api_id_to_odds:
            odds_data = odds_api_id_to_odds[odds_api_id]
            
            # Create a market data entry with all required fields
            market_data = {
                "market_address": market_address,
                "home_odds": odds_data.get("home_odds"),
                "away_odds": odds_data.get("away_odds"),
                "draw_odds": odds_data.get("draw_odds", 0.0),
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
                missing_fields = [k for k, v in market_data.items() if v is None and k != "draw_odds"]
                print(f"Missing fields: {missing_fields}")
        else:
            markets_without_odds_data.append({
                "market_address": market_address,
                "odds_api_id": odds_api_id
            })
    
    # Step 5: Update all markets with available odds data
    print(f"Preparing to update {len(markets_for_update)} markets with latest odds data")
    
    if not markets_for_update:
        return {
            "status": "warning",
            "message": "No markets had matching updated odds data from the API",
            "total_markets": len(existing_markets),
            "open_markets": len(open_markets),
            "markets_without_data": len(markets_without_odds_data),
            "markets_updated": 0
        }
    
    # Perform the batch update
    update_results = update_odds_for_multiple_markets(markets_for_update)
    
    # Step 6: Return combined result summary
    return {
        "status": "success",
        "message": f"Updated odds (moneyline, spreads, totals) for {update_results['successful_updates']} markets with latest data",
        "total_markets": len(existing_markets),
        "open_markets": len(open_markets),
        "markets_updated": update_results.get("successful_updates", 0),
        "markets_failed": update_results.get("failed_updates", 0),
        "markets_without_data": len(markets_without_odds_data)
    }

@function_tool
def get_prediction_data() -> Dict[str, Any]:
    """
    Retrieves Bankrolled prediction data from the last two days.
    This includes historical prediction records, user performance metrics, and market sentiment.
    
    Returns:
        dict: A structure containing prediction data and user performance metrics
    """
    return get_bankrolled_predictions()

@function_tool
def get_market_predictions(
    home_team: str,
    away_team: str,
    event_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieves and analyzes predictions for a specific market based on team names and optional date.
    
    Args:
        home_team: The name of the home team
        away_team: The name of the away team
        event_date: Optional ISO date string for the event
        
    Returns:
        dict: Analysis of predictions including sharp users and betting trends
    """
    market_data = {
        "homeTeam": home_team,
        "awayTeam": away_team,
        "eventDate": event_date
    }
    
    # Find matching predictions
    matching_predictions = find_predictions_for_market(market_data)
    
    # Analyze the predictions
    analysis = analyze_user_prediction_accuracy(matching_predictions)
    
    return {
        "market": market_data,
        "matchingPredictions": len(matching_predictions),
        "analysis": analysis,
        "predictions": matching_predictions[:10]  # Return just the first 10 predictions to avoid large responses
    }

# --- Agent Definition ---

risk_manager_agent = Agent(
    name="Risk Manager Agent",
    handoff_description="Specialist agent for managing market risk, including liquidity provision, odds adjustments, and granular exposure limit setting for specific bet types and sides.",
    instructions="""
# Risk Manager Agent Instructions

## Objective
The Risk Manager Agent's primary mission is to maximize sportsbook profit while minimizing insolvency risk. It does this by dynamically adjusting ALL betting-related values (odds, spreads, and totals), managing bet size limits, and optimizing liquidity across betting markets.

## Key Responsibilities
1. COMPREHENSIVE ODDS & LINES UPDATES: You **must** update ALL betting values (not just moneyline odds) for EVERY open market in EVERY run:
   - Update moneyline odds (home, away, draw for soccer)
   - Update spread points and spread odds
   - Update total points line and over/under odds
   - ALWAYS ensure ALL values are current with either risk-adjusted values or latest API values

2. DYNAMIC RISK MANAGEMENT: Actively monitor and respond to betting patterns:
   - Set bet size limits for specific bet types/sides when imbalances occur
   - Adjust odds to discourage betting on overexposed outcomes
   - Add liquidity to markets with high potential liability

## Workflow Overview

### 1. First Priority: Update All Markets with Latest Data
- Start by calling `fetch_and_update_markets()` to update ALL open markets with the latest odds and lines
- This ensures spreads and totals are synchronized with the actual game state
- This function will:
  - Fetch latest odds from the API for all supported sports
  - Update ALL open markets with the latest data (moneyline, spreads, totals)

### 2. Retrieve Market Data for Risk Analysis
- Call `get_all_markets()` to access all markets
- For each market with status = "Open":
  - Note current exposure levels
  - Identify markets needing risk assessment

### 3. Evaluate Market Risk
- For each open market:
  - Get detailed exposure using `get_detailed_market_exposure(market_address)` 
  - Identify exposure imbalances across all bet types:
    - Moneyline: home vs away (vs draw for soccer)
    - Spread: home spread vs away spread
    - Totals: over vs under
  - Calculate ratio between sides for each bet type
  - Flag markets with significant imbalances (>2:1 ratio between sides)

### 4. Run Simulations for Risky Markets
- For markets with significant imbalances or high exposure (>50% of max):
  - Run Monte Carlo simulation with the exposure distribution:
    ```
    run_monte_carlo_analysis_with_exposure(
        market_address, 
        oddsApiId, 
        status, 
        currentExposure, 
        maxExposure,
        homeOdds, 
        awayOdds, 
        homeSpreadPoints, 
        homeSpreadOdds, 
        awaySpreadOdds, 
        totalPoints, 
        overOdds, 
        underOdds,
        exposure_home,
        exposure_away,
        exposure_over,
        exposure_under,
        exposure_home_spread,
        exposure_away_spread,
        num_simulations=1000
    )
    ```
  - Analyze simulation results for potential profit/loss scenarios

### 5. Apply Risk-Based Adjustments
For markets with imbalanced exposure, implement these strategies:

#### a) Odds & Lines Adjustment 
- Apply risk-based adjustments based on exposure imbalances:
  - Low risk (1.5:1 ratio): 2-3% adjustment to odds
  - Moderate risk (2:1 ratio): 5-8% adjustment to odds
  - High risk (3:1+ ratio): 8-10% adjustment to odds
- For moneyline imbalances:
  - Decrease odds on overexposed side (less attractive)
  - Increase odds on underexposed side (more attractive)
- For spread imbalances:
  - Adjust spread odds (not the points) to balance action
  - In extreme cases, consider small adjustments to spread points (0.5-1 point)
- For totals imbalances:
  - Adjust over/under odds to balance action
  - In extreme cases, consider small adjustments to the total points line (0.5-1 point)
- Call `update_odds_for_market(market_address, home_odds, away_odds, home_spread_points, home_spread_odds, away_spread_odds, total_points, over_odds, under_odds, draw_odds)` with adjusted values

#### b) Exposure Limits
- For significant imbalances (especially 2:1 or greater):
  - Set specific bet type limits using `set_specific_bet_type_limit(market_address, bet_type, side, limit)`
  - Examples:
    - If home moneyline has 3x more exposure than away: `set_specific_bet_type_limit(market_address, "moneyline", "home", reduced_limit)`
    - If over total has 2x more exposure than under: `set_specific_bet_type_limit(market_address, "total", "over", reduced_limit)`
  - Calculate limits based on current exposure (typically 50-70% of current exposure)

#### c) Liquidity Management
- When exposure exceeds 80% of max_exposure:
  - Add liquidity using `add_liquidity_to_market(market_address, amount)`
  - Use simulation results to determine needed amount (typically 20-30% buffer)
- For extreme cases (>90% utilization or VaR > 50% of max exposure):
  - Consider reducing market funding with `reduce_market_funding(market_address, amount)`

### 6. Verification
- After making risk-based adjustments:
  - Use `check_market_odds(market_address)` to verify odds were applied correctly
  - Confirm exposure limits with `get_detailed_market_exposure(market_address)`

### 7. Generate Report
- Provide a comprehensive report including:
  - Markets with odds/spreads/totals adjusted (with adjustment percentages and reasons)
  - Markets with exposure limits set (limit values and justification)
  - Liquidity adjustments (added/reduced)
  - Monte Carlo simulation insights
  - Markets updated with current API odds only (no risk adjustment)

## Guidance for Special Cases

### Essential Line Movement Updates
- CRITICAL: Always keep both odds AND lines (spreads and totals) updated with the latest values
- Discrepancies between your lines and actual game circumstances can lead to severe liabilities
- First step in every run should be updating ALL markets with the latest information using `fetch_and_update_markets()`

### Soccer Markets
- For soccer markets, ensure draw_odds parameter is included in odds adjustments
- Monitor all three outcomes (home, away, draw) for imbalances

### Live Game Management
- Pay special attention to in-play markets
- Increase update frequency and risk sensitivity as events approach conclusion
- Consider stricter bet limits during critical game moments (last quarter, final minutes)

### Sharp Betting Detection
- Use `get_market_predictions(home_team, away_team)` to identify trends from sharp bettors
- When sharp bettors show strong preference for one side, consider odds adjustment even without current exposure imbalance
    """,
    tools=[
        get_all_markets,
        add_liquidity_to_market,
        get_liquidity_pool_info,
        update_odds_for_market,
        update_odds_for_multiple_markets,
        check_market_odds,
        fetch_latest_odds,
        fetch_and_update_markets,
        run_monte_carlo_analysis,
        run_monte_carlo_analysis_with_exposure,
        set_market_exposure_limits,
        reduce_market_funding,
        get_detailed_market_exposure,
        set_specific_bet_type_limit,
        get_prediction_data,
        get_market_predictions
    ],
    # DO NOT CHANGE THIS MODEL FROM THE CURRENT SETTING
    model="o3-mini-2025-01-31",
    # No context type needed
)

# Example of how this agent might be run
if __name__ == '__main__':
    # This part is just for testing the agent directly if needed
    from agents import Runner
    import asyncio

    async def test_risk_management():
        # Input prompt to trigger the agent's logic
        prompt = "Analyze current markets and add liquidity where needed based on risk assessment."
        print(f"--- Running Risk Manager Agent with prompt: '{prompt}' ---")
        # Ensure environment variables are loaded if running directly
        if not API_URL:
             print("Error: Missing API_URL in .env file. Cannot run test.", file=sys.stderr)
             return
        result = await Runner.run(risk_manager_agent, prompt, max_turns=20)
        print("--- Risk Manager Agent Result ---")
        print(result.final_output)
        print("--------------------------------")

    # Run the test
    asyncio.run(test_risk_management())
    print("Risk Manager Agent defined. Run agentGroup.py to test via Triage.")
