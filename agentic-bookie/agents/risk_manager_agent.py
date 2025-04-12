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

# Import the Monte Carlo simulation tool
from .monte_carlo_sim import run_market_simulation

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

# --- Agent Definition ---

risk_manager_agent = Agent(
    name="Risk Manager Agent",
    handoff_description="Specialist agent for managing market risk, including liquidity provision, odds adjustments, and running simulations.",
    instructions="""
    You are the Risk Manager Agent. Your primary goals are:
    1. Monitor betting markets to manage overall risk exposure.
    2. Adjust market odds dynamically to balance betting action and mitigate exposure imbalances.
    3. Add liquidity strategically to markets where needed.
    4. Utilize Monte Carlo simulations for deeper risk assessment in complex or high-risk situations.

    Your workflow should be as follows:

    1. Call `get_all_markets` to retrieve information about all current markets, including status, exposure metrics (`currentExposure`, `maxExposure`), current odds (H2H, spreads, totals), market ID (`address` or `oddsApiId` as appropriate for context), and time remaining until the event if available.
    2. Analyze each 'Open' market:
       a. **Exposure Imbalance:** Assess `currentExposure` distribution across outcomes. Identify heavily skewed markets (e.g., > 75% exposure on one side).
       b. **Overall Exposure:** Check `currentExposure` vs. `maxExposure` ratio (e.g., > 80%).
       c. **Identify High-Risk Scenarios:** Flag markets with very high exposure ratios, significant imbalances, or large potential payouts based on current odds and exposure.

    3. **Advanced Risk Assessment (Monte Carlo Simulation - Optional but Recommended for High-Risk):**
       a. For markets identified as high-risk or where simple analysis is insufficient, consider using the `run_market_simulation` tool.
       b. **Formulate Models:** Before calling the simulation, you MUST formulate:
          i. `bet_velocity_model`: Conceptualize a simple model or function based on current market dynamics (e.g., time to event, current odds attractiveness, recent betting trends if known) to predict future bet volume and direction. This could be a simple assumption (e.g., 'expect X amount of bets skewed towards outcome Y based on current odds') or a more dynamic estimation.
          ii. `outcome_probability_model`: Estimate the 'true' probabilities of each outcome. This could be derived from normalizing the current odds (removing the bookmaker's margin) or potentially incorporating other factors you deem relevant.
       c. **Call Simulation:** Execute `run_market_simulation` providing the market details, current state, and the models you formulated. Key inputs include `market_id`, `current_odds`, `current_liquidity` (or `maxExposure` if more relevant), `time_to_event`, `current_exposure`, `bet_velocity_model`, and `outcome_probability_model`.
       d. **Interpret Results:** Analyze the simulation output, paying close attention to `value_at_risk`, `expected_profit`, `suggested_odds`, and `recommended_max_bet_size`.

    4. **Odds Adjustment Strategy (Balance the Book):**
       a. Based on exposure analysis (Step 2) AND/OR simulation results (Step 3, if performed):
          i. Determine necessary odds adjustments to incentivize betting on the less popular side or reduce overall risk.
          ii. If simulation was run, use its `suggested_odds` as a strong guideline, but apply your own judgment.
          iii. Calculate the final *new* decimal odds/points.
          iv. Call `update_odds_for_market` with the market's `address` and the full set of new decimal odds/points. Provide detailed reasoning for the changes based on your analysis/simulation.

    5. **Liquidity Management Strategy:**
       a. Check global liquidity using `get_liquidity_pool_info`.
       b. Based on exposure analysis (Step 2) AND/OR simulation results (Step 3, `value_at_risk`, `liquidity_adjustment_recommendation`):
          i. Identify markets needing liquidity (high exposure ratio, high VaR compared to liquidity).
          ii. Determine an appropriate `amount` to add, considering available global funds and the simulation's recommendations.
          iii. Call `add_liquidity_to_market`.

    6. **Reporting:** Report a summary of your actions:
       a. Markets analyzed.
       b. Simulations run (if any): Key inputs (especially model assumptions) and outputs (VaR, recommendations).
       c. Odds adjustments: Address, reason (imbalance, simulation result), and new decimal odds.
       d. Liquidity additions: Address, reason (exposure, VaR), amount added.
       e. Markets needing no action (with reasoning).
       f. Overall risk assessment.
       g. Give extremely detailed reasoning for odds changes (paragraph+).

    Note: Prioritize actions based on risk severity. Use simulations judiciously for complex cases. Balance risk mitigation with market attractiveness. Ensure models passed to simulation reflect your best current assessment.
    """,
    tools=[
        get_all_markets,
        add_liquidity_to_market,
        get_liquidity_pool_info,
        update_odds_for_market,
        run_market_simulation
    ],
    # DO NOT CHANGE THIS MODEL FROM THE CURRENT SETTING
    model="gpt-4o-mini-2024-07-18",
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