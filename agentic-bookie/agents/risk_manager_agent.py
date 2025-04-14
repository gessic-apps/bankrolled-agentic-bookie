#!/usr/bin/env python3
import sys
import os
from typing import List, Dict, Any, Optional
# Don't use TypedDict here to avoid conflicts with function_tool

# Try to import dotenv, but handle when it's not available
try:
    from dotenv import load_dotenv
    # Load environment variables from .env file
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv package not installed, skipping .env file loading.", file=sys.stderr)

from agents import Agent, function_tool, AsyncOpenAI, OpenAIChatCompletionsModel

# Import utilities from our refactored structure
from utils.monte_carlo import analyze_market_risk, bulk_analyze_markets
from utils.risk_management import (
    add_liquidity_to_market,
    get_liquidity_pool_info,
    reduce_market_funding,
    get_detailed_market_exposure,
    set_specific_bet_type_limit,
    set_market_exposure_limits
)
from utils.markets.market_data import get_all_markets
from utils.markets.odds_management import (
    update_odds_for_market,
    update_odds_for_multiple_markets,
    check_market_odds
)
from utils.sports.games_data import fetch_games_with_odds
from utils.predictions import (
    get_bankrolled_predictions,
    find_predictions_for_market,
    analyze_user_prediction_accuracy
)
from utils.config import SUPPORTED_SPORT_KEYS


@function_tool
def get_markets() -> List[Dict[str, Any]]:
    """Fetches all existing betting markets from the smart contract API."""
    return get_all_markets()

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

# --- Set Market Exposure Limits ---
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

# --- Reduce Market Funding ---
@function_tool
def decrease_market_funding(
    market_address: str,
    amount: int
) -> Dict[str, Any]:
    """Reduces the total funding (and thus max exposure) allocated to a specific market from the central liquidity pool."""
    return reduce_market_funding(market_address, amount)

# --- Granular Exposure Management Tools ---
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
def check_odds(market_address: str) -> Dict[str, Any]:
    """Checks if a specific betting market (identified by its address) already has odds set."""
    return check_market_odds(market_address)

@function_tool
def update_multiple_markets_odds(
    markets_data: str
) -> Dict[str, Any]:
    """Updates odds for multiple markets at once. Takes a JSON string of market data.
    
    The JSON string should contain a list of market objects with the following structure:
    [
        {
            "market_address": "0x1234...",
            "home_odds": 1.5,
            "away_odds": 2.5,
            "draw_odds": 3.1,
            "home_spread_points": -1.5,
            "home_spread_odds": 1.9,
            "away_spread_odds": 1.9,
            "total_points": 220.5,
            "over_odds": 1.9,
            "under_odds": 1.9
        },
        ...
    ]
    """
    import json
    
    # Parse the JSON string
    try:
        markets_list = json.loads(markets_data)
    except json.JSONDecodeError:
        return {"status": "error", "message": "Invalid JSON string provided"}
    
    # Validate and convert fields to the right types
    typed_markets_data = []
    for market in markets_list:
        if not isinstance(market, dict):
            continue
            
        # Get the required market_address
        market_address = market.get("market_address")
        if not market_address or not isinstance(market_address, str):
            continue
            
        # Create a properly typed market dictionary
        typed_market = {
            "market_address": market_address,
            "home_odds": float(market.get("home_odds", 0.0)),
            "away_odds": float(market.get("away_odds", 0.0)),
            "draw_odds": float(market.get("draw_odds", 0.0)),
            "home_spread_points": float(market.get("home_spread_points", 0.0)),
            "home_spread_odds": float(market.get("home_spread_odds", 0.0)),
            "away_spread_odds": float(market.get("away_spread_odds", 0.0)),
            "total_points": float(market.get("total_points", 0.0)),
            "over_odds": float(market.get("over_odds", 0.0)),
            "under_odds": float(market.get("under_odds", 0.0))
        }
        typed_markets_data.append(typed_market)
    
    # If no valid markets were found, return an error
    if not typed_markets_data:
        return {"status": "error", "message": "No valid market data found in the input"}
    
    # Update the odds for the markets
    return update_odds_for_multiple_markets(typed_markets_data)

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
    if not sport_keys:
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
    games_with_odds = fetch_games_with_odds(SUPPORTED_SPORT_KEYS)
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
    update_results = update_multiple_markets_odds(markets_for_update)
    
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
    handoff_description="Specialist agent for updating odds after the market and initial odds are set. market risk, including liquidity provision, odds adjustments, and granular exposure limit setting for specific bet types and sides.",
    instructions="""
        # Batch Risk Manager Instructions
        Overview:
        You are the risk manager for a decntralized sports betting platform. Your job is to manage liquidity and risk in order to maximize profit, and minimize insolvency risk.
        You have full autonomy to make decisions, using all the tools provided to you You do not need to ask for clarification or which market to do first, you have the freedom to proceed as you see fit.
        The levers you have to do your job are:
        • Understanding how much liquidity is in the market, and how much is allocated to each market.
        • Understanding the exposure limits for each market, and the bet types and sides within each market.
        • Understanding the odds for each market, and the bet types and sides within each market.
        • Understanding the betting trends for each market, and the bet types and sides within each market.
        • Understanding the sharp users for each market, and the bet types and sides within each market.
        • Understanding the market sentiment for each market, and the bet types and sides within each market.
        • Ability to run monte carlo simulations to obtain recommandetaion  (you always prefer to run the simulations)
        • Ability to set exposure limits for each bet type and side within a market.
        • Ability to add liquidity to a market.
        • Ability to decrease liquidity from a market.
        • Ability to check the current exposure limits for each market.
        • Ability to change the current odds for any market to make one side more attractive, or to make the market more balanced.

       
    """,
    tools=[
        get_markets,
        add_market_liquidity,
        get_pool_info,
        # update_market_odds,
        # update_multiple_markets_odds,
        check_odds,
        # fetch_latest_odds,
        # fetch_and_update_markets,
        # run_monte_carlo_analysis,
        run_monte_carlo_analysis_with_exposure,
        set_exposure_limits,
        # decrease_market_funding,
        # get_market_exposure,
        # set_bet_type_limit,
        # get_prediction_data,
        # get_market_predictions
    ],
    # DO NOT CHANGE THIS MODEL FROM THE CURRENT SETTING
    model="o3-mini-2025-01-31",
)

# Example of how this agent might be run
if __name__ == '__main__':
    # This part is just for testing the agent directly if needed
    from agents import Runner
    import asyncio
    import json

    async def test_risk_management():
        # Input prompt to trigger the agent's logic
        prompt = "Review the current markets - decide whether to update the odds and/or exposure limits for each bet type or the entire market based on betting activity."
        print(f"--- Running Risk Manager Agent with prompt: '{prompt}' ---")
        result = await Runner.run(risk_manager_agent, prompt, max_turns=20)
        print("--- Risk Manager Agent Result ---")
        print(result.final_output)
        print("--------------------------------")

    # Run the test
    # loop through this next line 3 times
    for i in range(3):
        asyncio.run(test_risk_management())
    print("Risk Manager Agent defined. Run agentGroup.py to test via Triage.")