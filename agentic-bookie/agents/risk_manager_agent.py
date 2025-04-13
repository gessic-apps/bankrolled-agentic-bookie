#!/usr/bin/env python3
import sys
import requests
import os
import datetime
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:3000") # Default matching other agents

if not API_URL:
    print(f"Warning: API_URL not found, defaulting to {API_URL}", file=sys.stderr)

# Import Agent SDK components
from agents import Agent, function_tool

# Import Monte Carlo simulation tool
from .monte_carlo_sims import analyze_market_risk, bulk_analyze_markets

# Import new market exposure tools
from ..tools.market_exposure_tools import (
    fetch_market_exposure_details,
    set_bet_type_exposure_limit,
    get_market_exposure_by_type
)

# --- Tool Definitions ---

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

# --- Tool Definition from odds_manager_agent ---
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
    """Updates all odds types (moneyline, spread, total) for a specific market to influence betting behavior and manage risk. Expects decimal floats/points, converts to integer format for the API call."""
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
        print(f"Attempting risk-based odds update: POST {url} with payload: {payload}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Successfully updated odds via risk management for market {market_address}. Response: {result}")
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
        error_message = f"HTTP Error updating odds via risk management for market {market_address}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error updating odds via risk management for market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except Exception as e:
         error_message = f"An unexpected error occurred in update_odds_for_market (risk mgmt context): {e}"
         print(error_message, file=sys.stderr)
         return {"status": "error", "message": error_message, "market_address": market_address}

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
    
    result = get_market_exposure_by_type(market_address, API_URL)
    
    print(f"Detailed exposure for market {market_address}: {result}")
    return result

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

# --- Agent Definition ---

risk_manager_agent = Agent(
    name="Risk Manager Agent",
    handoff_description="Specialist agent for managing market risk, including liquidity provision, odds adjustments, and granular exposure limit setting for specific bet types and sides.",
    instructions="""
    You are the Risk Manager Agent. Your primary goals are:
    1. Monitor betting markets to manage overall risk exposure by adding/reducing liquidity and setting exposure limits.
    2. Adjust market odds dynamically to balance betting action and mitigate exposure imbalances on specific outcomes (e.g., H2H, spreads, totals).
    3. Set fine-grained exposure limits on specific bet types and sides within a market if needed.

    Your workflow should be as follows:

    1. Call `get_all_markets` to retrieve information about all current markets, including their status, exposure metrics (`currentExposure`, `maxExposure`), and current odds.

    2. Analyze each market ('Open' status only):
       a. **Initial Assessment:** Quickly assess if a market shows concerning risk patterns:
          i. **Exposure Imbalance:** Check if the distribution of `currentExposure` across different betting outcomes appears heavily skewed (e.g., > 75% of exposure on one outcome).
          ii. **Overall Exposure:** Check the ratio of `currentExposure` to `maxExposure`. High ratios (e.g., > 80%) indicate potential need for more liquidity, odds adjustments, or stricter limits.

       b. **Detailed Exposure Analysis:** For markets with potential risk, use `get_detailed_market_exposure` to see the breakdown of exposure by bet type (moneyline, spread, total) and side (home/away, over/under).

       c. **Monte Carlo Simulation (for high-risk markets):** For markets showing potential risk concerns, use the Monte Carlo simulation tools (`run_monte_carlo_analysis` or `run_monte_carlo_analysis_with_exposure`). This can provide recommendations for odds, liquidity, and potentially bet size limits.

    3. **Risk Mitigation Strategy:** Based on the analysis and simulation results:
       a. **Odds Adjustment:** If significant imbalance exists, use `update_odds_for_market` to adjust odds (either based on Monte Carlo recommendations or your own calculation) to incentivize betting on the less popular side.
       
       b. **Liquidity Management:**
          i. If `currentExposure` is approaching `maxExposure` (e.g., > 80%), or if Monte Carlo suggests needing more capacity, use `add_liquidity_to_market` after checking available funds with `get_liquidity_pool_info`.
          ii. If a market is deemed too risky, has low activity, or needs capital reallocated, consider using `reduce_market_funding` to decrease its `maxExposure` and return funds to the pool. Use this cautiously.
       
       c. **Exposure Limit Management:**
          i. **Global Limit Management:** Use `set_market_exposure_limits` to manage multiple exposure limits in a single call.
          ii. **Granular Bet Type Management:** If specific bet types (e.g., home moneyline, over total) show disproportionate risk, use `set_specific_bet_type_limit` to set limits for individual bet types and sides.
             - Valid bet types: 'moneyline', 'spread', 'total', 'draw'
             - Valid sides: 'home', 'away', 'over', 'under', 'draw' (used with the appropriate bet type)

    4. **When to Use Which Tool:**
       a. **Monte Carlo:** For complex risk assessment, mathematically derived odds/liquidity needs, especially on high-volume or highly imbalanced markets.
       b. **`update_odds_for_market`:** Primary tool for balancing the book by influencing bettor behavior.
       c. **`add_liquidity_to_market`:** Increase capacity for healthy markets or as recommended by simulation.
       d. **`reduce_market_funding`:** Decrease overall risk capacity for a specific market, freeing up capital.
       e. **`set_market_exposure_limits`:** Set multiple exposure limits in a single call (for broad adjustments).
       f. **`set_specific_bet_type_limit`:** Apply surgical risk control on a specific bet type and side (e.g., only limiting exposure on 'total'/'over' bets while leaving 'total'/'under' unchanged).
       g. **`get_detailed_market_exposure`:** Analyze current exposure distribution across different bet types and sides.

    5. **Reporting:** Report a summary of your actions, including:
       a. Markets where odds were adjusted: Address, reason, and new decimal odds.
       b. Markets where liquidity was added/reduced: Address, reason, and amount.
       c. Markets where exposure limits were set: Address, reason, and the specific limits applied (especially note any granular bet type/side limits).
       d. Markets considered but where no action was taken (with reasoning).
       e. Overall assessment of the current risk status.
       f. Give detailed reasoning for your decisions, especially for odds changes, funding reductions, or limit setting. Reference Monte Carlo results if used.

    Note: Prioritize actions based on risk severity. Significant imbalances might require multiple actions (e.g., odds adjustment + setting specific limits). If global liquidity is limited, focus on the highest-risk markets. Use the new granular exposure limit tools judiciously to control specific risks without stifling overall market activity unnecessarily.
    """,
    tools=[
        get_all_markets,
        add_liquidity_to_market,
        get_liquidity_pool_info,
        update_odds_for_market,
        run_monte_carlo_analysis,
        run_monte_carlo_analysis_with_exposure,
        set_market_exposure_limits,
        reduce_market_funding,
        get_detailed_market_exposure,
        set_specific_bet_type_limit
    ],
    # DO NOT CHANGE THIS MODEL FROM THE CURRENT SETTING
    model="gpt-4o-2024-11-20",
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
        result = await Runner.run(risk_manager_agent, prompt)
        print("--- Risk Manager Agent Result ---")
        print(result.final_output)
        print("--------------------------------")

    # Run the test
    asyncio.run(test_risk_management())
    print("Risk Manager Agent defined. Run agentGroup.py to test via Triage.")
