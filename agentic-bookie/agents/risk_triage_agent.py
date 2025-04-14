#!/usr/bin/env python3
import sys
from typing import List, Dict, Any, Optional, Union

# Import Agent SDK components
from agents import Agent, function_tool, handoff

# Import risk handler agents
from .high_risk_handler_agent import high_risk_handler_agent  
from .risk_manager_agent import risk_manager_agent  # Use existing agent for batch updates

# Import utility modules
from utils.config import SUPPORTED_SPORT_KEYS
from utils.markets.market_data import get_all_markets
from utils.risk_management.exposure import get_detailed_market_exposure, get_market_exposure_by_type
from utils.sports.games_data import fetch_games_with_odds

@function_tool
def get_all_markets_with_exposure() -> List[Dict[str, Any]]:
    """Fetches all existing betting markets from the smart contract API with exposure data."""
    markets = get_all_markets()
    
    # Process exposure values to ensure they're floats for easier comparison
    for market in markets:
        try:
            # Convert exposure values to float for easier comparison if they exist
            if "maxExposure" in market:
                market["maxExposure"] = float(market["maxExposure"])
            else:
                market["maxExposure"] = 2000.0  # Default value
                
            if "currentExposure" in market:
                market["currentExposure"] = float(market["currentExposure"])
            else:
                market["currentExposure"] = 0.0  # Default value
        except (ValueError, TypeError):
            print(f"Warning: Could not convert exposure values to float for market {market.get('address')}", file=sys.stderr)
            # Use default values if conversion fails
            market["maxExposure"] = 2000.0
            market["currentExposure"] = 0.0
    
    print(f"Successfully fetched {len(markets)} existing markets with exposure data.")
    return markets

@function_tool
def get_market_exposure_details(market_address: str) -> Dict[str, Any]:
    """
    Gets detailed exposure information for a specific market, broken down by bet type and side.
    
    Args:
        market_address (str): The blockchain address of the market
        
    Returns:
        dict: Detailed exposure information organized by bet type and side
    """
    # Use the refactored utility function directly 
    return get_detailed_market_exposure(market_address)

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
        games_with_odds = fetch_games_with_odds(sport_keys)
        
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
def identify_high_risk_markets() -> Dict[str, Any]:
    """
    Analyzes all open markets to identify those with high risk profiles.
    Criteria for high-risk designation:
    1. Exposure imbalance - one bet type/side has much greater exposure than others (>2:1 ratio)
    2. High utilization - market's current exposure exceeds 70% of max exposure
    3. Significant line movement - notable changes in spreads or totals from API
    
    Returns:
        dict: List of high-risk markets with details on risk factors and latest odds data
    """
    # Step 1: Get all markets
    all_markets = get_all_markets_with_exposure()
    open_markets = [m for m in all_markets if m.get("status") == "Open"]
    print(f"Found {len(open_markets)} open markets out of {len(all_markets)} total markets")
    
    if not open_markets:
        return {
            "status": "info",
            "message": "No open markets found to analyze",
            "high_risk_markets": [],
            "regular_markets": []
        }
    
    # Step 2: Fetch latest odds
    latest_odds_result = fetch_latest_odds()
    latest_odds_data = latest_odds_result.get("odds_data", {})
    
    # Step 3: Analyze each market for risk factors
    high_risk_markets = []
    regular_markets = []
    
    for market in open_markets:
        market_address = market.get("address")
        odds_api_id = market.get("oddsApiId")
        risk_factors = []
        risk_details = {}
        
        # Check exposure utilization
        max_exposure = float(market.get("maxExposure", 0))
        current_exposure = float(market.get("currentExposure", 0))
        utilization = 0
        
        if max_exposure > 0:
            utilization = (current_exposure / max_exposure) * 100
            if utilization > 70:
                risk_factors.append("high_exposure_utilization")
                risk_details["utilization_percentage"] = utilization
        
        # Get detailed exposure
        exposure_data = get_market_exposure_details(market_address)
        
        # Check for imbalances
        if "moneyline" in exposure_data:
            ml_data = exposure_data["moneyline"]
            home_exp = ml_data.get("home", 0)
            away_exp = ml_data.get("away", 0)
            draw_exp = ml_data.get("draw", 0)
            
            # Check moneyline imbalance
            if home_exp > 0 and away_exp > 0:
                ratio = max(home_exp, away_exp) / min(home_exp, away_exp)
                if ratio > 2:
                    risk_factors.append("moneyline_imbalance")
                    risk_details["moneyline_ratio"] = ratio
                    risk_details["home_exposure"] = home_exp
                    risk_details["away_exposure"] = away_exp
        
        if "spread" in exposure_data:
            spread_data = exposure_data["spread"]
            home_spread_exp = spread_data.get("home", 0)
            away_spread_exp = spread_data.get("away", 0)
            
            # Check spread imbalance
            if home_spread_exp > 0 and away_spread_exp > 0:
                ratio = max(home_spread_exp, away_spread_exp) / min(home_spread_exp, away_spread_exp)
                if ratio > 2:
                    risk_factors.append("spread_imbalance")
                    risk_details["spread_ratio"] = ratio
                    risk_details["home_spread_exposure"] = home_spread_exp
                    risk_details["away_spread_exposure"] = away_spread_exp
        
        if "total" in exposure_data:
            total_data = exposure_data["total"]
            over_exp = total_data.get("over", 0)
            under_exp = total_data.get("under", 0)
            
            # Check total imbalance
            if over_exp > 0 and under_exp > 0:
                ratio = max(over_exp, under_exp) / min(over_exp, under_exp)
                if ratio > 2:
                    risk_factors.append("total_imbalance")
                    risk_details["total_ratio"] = ratio
                    risk_details["over_exposure"] = over_exp
                    risk_details["under_exposure"] = under_exp
        
        # Check for line movement
        if odds_api_id in latest_odds_data:
            latest_odds = latest_odds_data[odds_api_id]
            current_spread = market.get("homeSpreadPoints", 0)
            latest_spread = latest_odds.get("home_spread_points", 0)
            
            # Check if spread has moved significantly
            if abs(current_spread - latest_spread) >= 1.0:
                risk_factors.append("significant_spread_movement")
                risk_details["current_spread"] = current_spread
                risk_details["latest_spread"] = latest_spread
                risk_details["spread_movement"] = latest_spread - current_spread
            
            current_total = market.get("totalPoints", 0)
            latest_total = latest_odds.get("total_points", 0)
            
            # Check if total has moved significantly
            if abs(current_total - latest_total) >= 2.0:
                risk_factors.append("significant_total_movement")
                risk_details["current_total"] = current_total
                risk_details["latest_total"] = latest_total
                risk_details["total_movement"] = latest_total - current_total
        
        # If any risk factors identified, add to high risk markets
        if risk_factors:
            high_risk_markets.append({
                "market_address": market_address,
                "odds_api_id": odds_api_id,
                "risk_factors": risk_factors,
                "risk_details": risk_details,
                "utilization": utilization,
                "max_exposure": max_exposure,
                "current_exposure": current_exposure,
                "homeTeam": market.get("homeTeam", ""),
                "awayTeam": market.get("awayTeam", ""),
                "latest_odds": latest_odds_data.get(odds_api_id, {})
            })
        else:
            regular_markets.append({
                "market_address": market_address,
                "odds_api_id": odds_api_id,
                "utilization": utilization,
                "homeTeam": market.get("homeTeam", ""),
                "awayTeam": market.get("awayTeam", "")
            })
    
    # Step 4: Return identified markets
    return {
        "status": "success",
        "message": f"Identified {len(high_risk_markets)} high-risk markets out of {len(open_markets)} open markets",
        "high_risk_markets": high_risk_markets,
        "regular_markets": regular_markets
    }

# --- Define the Risk Triage Agent ---
risk_triage_agent = Agent(
    name="Risk Triage Agent",
    handoff_description="Master agent for risk management that identifies high-risk markets and delegates tasks to specialized agents",
    instructions="""
# Risk Triage Agent Instructions

## Objective
You are the Risk Triage Agent, responsible for analyzing betting markets, identifying high-risk situations, and directing specialized agents to handle them efficiently. Your goal is to ensure the platform's financial stability by properly managing risk across all markets.

## Workflow Overview

### 1. Identify High-Risk Markets
- Start by calling `identify_high_risk_markets()` to scan all open markets and determine which ones require special attention
- This function analyzes markets based on:
  - Exposure imbalances (one side having much more betting action)
  - High utilization (current exposure approaching max exposure)
  - Significant line movements (spreads or totals changing substantially)

### 2. Direct Individual High-Risk Market Handling
- For each high-risk market identified:
  - Hand off to the `High Risk Handler Agent` to analyze and implement targeted risk management strategies
  - The `High Risk Handler Agent` will:
    - Run Monte Carlo simulations
    - Adjust odds to balance action
    - Set specific bet type limits
    - Add liquidity if needed

### 3. Handle Regular Markets in Batch
- After addressing high-risk markets individually:
  - Hand off all regular markets to the `Risk Manager Agent` for batch processing
  - The `Risk Manager Agent` will:
    - Update all markets with latest odds from API
    - Perform basic risk checks
    - Apply standard risk management policies

### 4. Generate Summary Report
- Provide a clear summary of actions taken:
  - Number of high-risk markets identified and individually addressed
  - Number of regular markets batch updated 
  - Total liquidity added
  - Key risk metrics across the platform

## Important Guidelines

### Prioritization
- Always handle high-risk markets FIRST, individually, before batch processing regular markets
- Pay special attention to markets with multiple risk factors
- For markets with significant line movements, ensure immediate odds updates

### Decision-Making Authority
- You have authority to determine which markets are high-risk based on the data
- If a market shows ANY risk factors, prioritize individual handling
- When in doubt about risk level, err on the side of caution by treating as high-risk

### Operational Efficiency
- Balance thoroughness with efficiency
- Process similar high-risk markets in small batches if they share risk factors
- Ensure all markets are updated, regardless of risk level
""",
    tools=[
        get_all_markets_with_exposure,
        get_market_exposure_details,
        fetch_latest_odds,
        identify_high_risk_markets
    ],
    handoffs=[
        handoff(
            high_risk_handler_agent,
            tool_name_override="handle_high_risk_market",
            tool_description_override="Transfer a high-risk market to the specialized agent for detailed analysis and targeted risk management."
        ),
        handoff(
            risk_manager_agent,
            tool_name_override="batch_update_regular_markets",
            tool_description_override="Transfer regular (non-high-risk) markets to the agent for batch updating with latest odds and standard risk checks."
        )
    ],
    # DO NOT CHANGE THIS MODEL FROM THE CURRENT SETTING
    model="gpt-4o-mini-2024-07-18",
)

# Example of how this agent might be run
if __name__ == '__main__':
    # This part is just for testing the agent directly if needed
    from agents import Runner
    import asyncio
    from utils.config import API_URL

    async def test_risk_triage():
        # Input prompt to trigger the agent's logic
        prompt = "Analyze all markets, identify high-risk ones for individual handling, and update the rest in batch."
        print(f"--- Running Risk Triage Agent with prompt: '{prompt}' ---")
        # Ensure environment variables are loaded if running directly
        if not API_URL:
             print("Error: Missing API_URL in .env file. Cannot run test.", file=sys.stderr)
             return
        result = await Runner.run(risk_triage_agent, prompt)
        print("--- Risk Triage Agent Result ---")
        print(result.final_output)
        print("--------------------------------")

    # Run the test
    asyncio.run(test_risk_triage())
    print("Risk Triage Agent defined. Run agentGroup.py to test via Triage.")