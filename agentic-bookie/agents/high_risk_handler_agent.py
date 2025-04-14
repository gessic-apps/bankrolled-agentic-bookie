#!/usr/bin/env python3
import sys
import os
from typing import Dict, Any, Optional, List

from agents import Agent, function_tool, AsyncOpenAI, OpenAIChatCompletionsModel

# Import utilities from our refactored structure
from utils.monte_carlo import analyze_market_risk
from utils.risk_management import (
    add_liquidity_to_market,
    get_liquidity_pool_info,
    get_detailed_market_exposure,
    set_specific_bet_type_limit,
    set_market_exposure_limits
)
from utils.markets.odds_management import (
    update_odds_for_market,
    check_market_odds
)
from utils.sports.games_data import fetch_games_with_odds
from utils.config import SUPPORTED_SPORT_KEYS

@function_tool
def add_market_liquidity(market_address: str, amount: int) -> Dict[str, Any]:
    """
    Adds liquidity to a specific market.
    
    Args:
        market_address: The blockchain address of the market
        amount: The amount of liquidity to add (typically in the smallest unit of the token)
        
    Returns:
        dict: API response with liquidity addition details
    """
    return add_liquidity_to_market(market_address, amount)

@function_tool
def get_pool_info() -> Dict[str, Any]:
    """
    Gets information about the global liquidity pool.
    
    Returns:
        dict: Information about the liquidity pool including total liquidity,
              allocated liquidity, and available liquidity
    """
    return get_liquidity_pool_info()

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
def update_market_odds(
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
    return update_odds_for_market(
        market_address=market_address,
        home_odds=home_odds,
        away_odds=away_odds,
        draw_odds=draw_odds if draw_odds is not None else 0.0,
        home_spread_points=home_spread_points,
        home_spread_odds=home_spread_odds,
        away_spread_odds=away_spread_odds,
        total_points=total_points,
        over_odds=over_odds,
        under_odds=under_odds
    )

# --- NEW TOOL: Set Market Exposure Limits ---
@function_tool
def set_exposure_limits(
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
    return set_market_exposure_limits(
        market_address=market_address,
        home_moneyline_limit=home_moneyline_limit,
        away_moneyline_limit=away_moneyline_limit,
        draw_limit=draw_limit,
        home_spread_limit=home_spread_limit,
        away_spread_limit=away_spread_limit,
        over_limit=over_limit,
        under_limit=under_limit
    )

@function_tool
def set_bet_type_limit(
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
    return set_specific_bet_type_limit(
        market_address=market_address,
        bet_type=bet_type,
        side=side,
        limit=limit
    )

@function_tool
def fetch_latest_odds_for_market(odds_api_id: str) -> Dict[str, Any]:
    """
    Fetches the latest odds from the API for a specific market by oddsApiId.
    
    Args:
        odds_api_id: The odds API identifier for the market
        
    Returns:
        dict: The latest odds data for the specific market
    """
    try:
        # Fetch all odds (we'll filter for the specific market)
        games_with_odds = fetch_games_with_odds(SUPPORTED_SPORT_KEYS)
        
        # Find the specific market
        market_odds = None
        for game in games_with_odds:
            if game.get("odds_api_id") == odds_api_id:
                market_odds = game.get("odds", {})
                break
        
        if market_odds:
            return {
                "status": "success",
                "odds_api_id": odds_api_id,
                "odds_data": market_odds
            }
        else:
            return {
                "status": "error",
                "message": f"No odds data found for market with odds_api_id: {odds_api_id}",
                "odds_api_id": odds_api_id
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error fetching latest odds for market: {str(e)}",
            "odds_api_id": odds_api_id
        }

@function_tool
def get_market_exposure(market_address: str) -> Dict[str, Any]:
    """
    Gets detailed exposure information for a specific market, broken down by bet type and side.
    
    Args:
        market_address (str): The blockchain address of the market
        
    Returns:
        dict: Detailed exposure information organized by bet type and side
    """
    return get_detailed_market_exposure(market_address)

@function_tool
def check_odds(market_address: str) -> Dict[str, Any]:
    """Checks if a specific betting market (identified by its address) already has odds set."""
    return check_market_odds(market_address)

# --- Define the High Risk Handler Agent ---
high_risk_handler_agent = Agent(
    name="High Risk Handler Agent",
    handoff_description="Specialist agent for handling individual high-risk markets with detailed analysis and targeted risk management strategies",
    instructions="""
# High Risk Handler Agent Instructions

## Objective
You are the High Risk Handler Agent, a specialist in managing individual high-risk betting markets. Your mission is to analyze markets with significant risk factors, run simulations to quantify the risks, and implement targeted strategies to protect the platform's financial health while maintaining market viability.

## Workflow Overview

### 1. Gather Market Information
- You will receive high-risk market details including:
  - Market address and oddsApiId
  - Current odds and exposure data
  - Specific risk factors that triggered the high-risk designation
  - Latest odds data from the API

### 2. Run Detailed Risk Analysis
- Use Monte Carlo simulation to quantify risks and guide decision-making:
  - For markets with detailed exposure data, use `run_monte_carlo_analysis_with_exposure()`
  - For markets without detailed exposure, use basic `run_monte_carlo_analysis()`
  - Use at least 1000 simulations to ensure statistical validity
  - Pay special attention to Value at Risk (VaR) and Expected Shortfall metrics

### 3. Compare Current Odds with Latest API Odds
- Fetch latest odds using `fetch_latest_odds_for_market(odds_api_id)`
- Identify discrepancies in:
  - Moneyline odds (home/away/draw)
  - Spread points and odds 
  - Total points line and over/under odds

### 4. Implement Risk Mitigation Strategies
For each identified risk factor, apply the appropriate mitigation strategy:

#### a) Update Odds and Lines
- Always update to latest odds from API as baseline
- Then apply risk-based adjustments based on risk severity:
  - Moneyline imbalance:
    - Decrease odds on overexposed side by 5-10%
    - Increase odds on underexposed side by 5-10%
  - Spread imbalance:
    - Adjust spread odds (not points) to balance action
    - In severe cases only, adjust spread points by 0.5-1 point
  - Totals imbalance:
    - Adjust over/under odds to balance action
    - In severe cases only, adjust total points line by 0.5-1 point
  - Call `update_market_odds()` with these adjustments

#### b) Set Bet Size Limits
- For severe imbalances (>3:1 ratio):
  - Use `set_bet_type_limit()` to restrict betting on overexposed sides
  - Calculate limit based on current exposure (typically 50-70% of current)
  - Example: If home moneyline exposure is $10,000 and away is $2,000, set home limit to $5,000-$7,000

#### c) Add Liquidity
- When exposure exceeds 80% of max_exposure:
  - Calculate additional liquidity needed (typically 20-30% buffer)
  - Use `add_market_liquidity()` to increase market capacity
  - Verify with `get_pool_info()` that sufficient global liquidity exists

### 5. Verify Changes
- After implementing changes:
  - Use `check_odds()` to verify odds updates
  - Confirm exposure limits with `get_market_exposure()`
  - Ensure all points (spread, total) are updated, not just odds

### 6. Generate Detailed Report
- Provide a comprehensive report of actions taken:
  - Risk factors identified and quantified via simulation
  - Odds and points adjusted (with before/after values)
  - Bet limits applied and reasoning
  - Liquidity added (if applicable)
  - Verification of changes
  - Estimated risk reduction from actions taken

## Important Considerations

### Soccer Markets
- For soccer markets, ensure draw_odds parameter is included in odds adjustments
- Soccer markets have three outcomes to balance (home, away, draw)

### Line Movement Priority
- When a market shows significant line movement, updating to the latest values is top priority
- For spread and total adjustments, use the latest API values as baseline, then apply risk adjustments

### Balance When Updating Odds
- When decreasing one side's odds, consider increasing the other side proportionally
- Maintain a reasonable margin between sides to ensure platform profitability
- For severe imbalances, bet limits are often more effective than extreme odds adjustments
""",
    tools=[
        add_market_liquidity,
        get_pool_info,
        update_market_odds,
        set_exposure_limits,
        set_bet_type_limit,
        run_monte_carlo_analysis,
        run_monte_carlo_analysis_with_exposure,
        fetch_latest_odds_for_market,
        get_market_exposure,
        check_odds
    ],
    # DO NOT CHANGE THIS MODEL FROM THE CURRENT SETTING
    model="gpt-4o-mini-2024-07-18",
)

# Example of how this agent might be run
if __name__ == '__main__':
    # This part is just for testing the agent directly if needed
    from agents import Runner
    import asyncio
    import json

    async def test_high_risk_handler():
        # Input prompt to trigger the agent's logic
        prompt = """Analyze and manage this high-risk market:
        {
          "market_address": "0x1234567890abcdef1234567890abcdef12345678",
          "odds_api_id": "basketball_nba_123456",
          "risk_factors": ["moneyline_imbalance", "high_exposure_utilization"],
          "risk_details": {
            "utilization_percentage": 75.5,
            "moneyline_ratio": 2.8,
            "home_exposure": 15000,
            "away_exposure": 5400
          },
          "max_exposure": 30000,
          "current_exposure": 20400,
          "homeTeam": "Los Angeles Lakers",
          "awayTeam": "Boston Celtics"
        }"""
        
        print(f"--- Running High Risk Handler Agent with prompt: '{prompt}' ---")
        result = await Runner.run(high_risk_handler_agent, prompt)
        print("--- High Risk Handler Agent Result ---")
        print(result.final_output)
        print("--------------------------------")

    # Run the test
    asyncio.run(test_high_risk_handler())
    print("High Risk Handler Agent defined. Run agentGroup.py to test via Triage.")