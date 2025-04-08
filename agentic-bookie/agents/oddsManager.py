#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, TypedDict
from dataclasses import dataclass
import requests  # Add requests import
from dotenv import load_dotenv # Add dotenv import

# Add the project root to path to find the tools
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import the tools
from tools.createMarket import get_all_markets, update_market_odds
from tools.events.fetchEvents import fetch_nba_games_today, GameEvent

# Import OpenAI Agent SDK
# Note: Make sure to install with: pip install "openai[agents]"
from openai import OpenAI
from agents import Agent, Runner, function_tool, RunConfig
from agents.run import RunContextWrapper

# Import the AgentContext class, avoiding circular imports
from agents.agentGroup import AgentContext

# Load environment variables from .env file
load_dotenv(dotenv_path=project_root.parent / '.env')

class OddsData(TypedDict):
    """Type definition for odds data"""
    home_odds: int  # Integer with 3 decimal precision (e.g. 1941 for 1.941)
    away_odds: int  # Integer with 3 decimal precision (e.g. 1051 for 1.051)

@function_tool
def fetch_existing_markets() -> List[Dict[str, Any]]:
    """
    Fetches all existing betting markets from the API
    
    Returns:
        List of market objects with details including market address, teams, odds, and status
    """
    markets = get_all_markets()
    return markets

@function_tool
def update_odds_for_market(market_address: str, home_odds: int, away_odds: int) -> Dict[str, Any]:
    """
    Updates the odds for an existing market
    
    Args:
        market_address: The blockchain address of the market
        home_odds: Home team odds as integer with 3 decimal precision (e.g., 1941 for 1.941)
        away_odds: Away team odds as integer with 3 decimal precision (e.g., 1051 for 1.051)
    
    Note:
        Odds must be at least 1.000, represented as 1000 in the contract.
        Examples: 1.941 is stored as 1941, 10.51 is stored as 10510
    
    Returns:
        API response with update details
    """
    result = update_market_odds(market_address, home_odds, away_odds)
    return result

@function_tool
def get_games_with_odds() -> List[Dict[str, Any]]:
    """
    Fetches today's NBA games with latest odds data from The Odds API
    
    Returns:
        List of NBA games with odds
    """
    games = fetch_nba_games_today()
    
    api_key = os.getenv("SPORTS_API_KEY")
    if not api_key:
        print("Error: SPORTS_API_KEY not found in environment variables.")
        # Fallback to mock data or handle error appropriately
        return [] # Or return games with default/mock odds

    sport_key = "basketball_nba"
    regions = "us"
    markets = "h2h" # Head-to-head (moneyline)
    odds_format = "decimal"
    
    odds_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"

    params = {
        "apiKey": api_key,
        "regions": regions,
        "markets": markets,
        "oddsFormat": odds_format,
    }

    try:
        response = requests.get(odds_url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        odds_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching odds from API: {e}")
        # Fallback or error handling
        return [] # Or return games with default/mock odds
    
    # Process odds data into a dictionary keyed by game ID for easier lookup
    api_odds_dict = {}
    for event in odds_data:
        event_id = event.get("id")
        if not event_id or not event.get("bookmakers"):
            continue

        # Find the first bookmaker with the h2h market
        home_odds = None
        away_odds = None
        
        for bookmaker in event["bookmakers"]:
            for market in bookmaker.get("markets", []):
                if market.get("key") == "h2h":
                    outcomes = market.get("outcomes", [])
                    if len(outcomes) == 2:
                        # Assuming the first outcome is the away team and the second is the home team
                        # based on the example, but this might need adjustment if order varies.
                        # Need to match outcome name with game's home/away team if necessary.
                        
                        # Simple approach: Identify by team name match
                        outcome1_name = outcomes[0].get("name")
                        outcome2_name = outcomes[1].get("name")
                        price1 = outcomes[0].get("price")
                        price2 = outcomes[1].get("price")

                        if outcome1_name == event.get("home_team"):
                             home_odds_decimal = price1
                             away_odds_decimal = price2
                        elif outcome2_name == event.get("home_team"):
                             home_odds_decimal = price2
                             away_odds_decimal = price1
                        else:
                            # Fallback if names don't match exactly (e.g. abbreviations)
                            # This logic might need refinement based on actual API data variability.
                            # For now, assume fixed order if names don't match home_team
                            print(f"Warning: Could not reliably match odds outcomes for event {event_id}. Assuming order.")
                            if event.get("home_team") in outcome2_name: # Crude check
                                home_odds_decimal = price2
                                away_odds_decimal = price1
                            else: # Assume default order
                                away_odds_decimal = price1
                                home_odds_decimal = price2


                        if home_odds_decimal and away_odds_decimal:
                             # Convert decimal odds to integer format (price * 1000)
                             home_odds = int(home_odds_decimal * 1000)
                             away_odds = int(away_odds_decimal * 1000)
                             # Ensure odds are at least 1000 (1.000)
                             home_odds = max(1000, home_odds)
                             away_odds = max(1000, away_odds)
                             break # Found odds for this bookmaker
            if home_odds is not None:
                break # Found odds from a bookmaker

        if home_odds is not None and away_odds is not None:
            api_odds_dict[event_id] = {"home_odds": home_odds, "away_odds": away_odds}
        else:
            print(f"Warning: Could not find h2h odds for event {event_id}")


    # Combine game data with fetched odds
    result = []
    for game in games:
        game_odds_api_id = game.get("odds_api_id")
        fetched_odds = api_odds_dict.get(game_odds_api_id)

        if fetched_odds:
            odds_to_use = fetched_odds
        else:
            # Fallback to default odds if not found for a game
            print(f"Warning: Odds not found for game {game.get('id')} (Odds API ID: {game_odds_api_id}). Using default.")
            odds_to_use = {"home_odds": 2000, "away_odds": 2000} # Default 2.000 odds

        result.append({
            "id": game["id"],
            "odds_api_id": game_odds_api_id,
            "home_team": {
                "name": game["home_team"]["name"],
                "abbreviation": game["home_team"]["abbreviation"]
            },
            "away_team": {
                "name": game["away_team"]["name"],
                "abbreviation": game["away_team"]["abbreviation"]
            },
            "start_time": game["start_time"],
            "status": game["status"],
            "odds": odds_to_use
        })
        
    return result

def save_odds_update_result(context: RunContextWrapper[AgentContext], result: Dict[str, Any]):
    """Helper function to save odds update results to context"""
    if context.context and hasattr(context.context, 'odds_updates'):
        context.context.odds_updates.append(result)
        if "error" not in result:
            print(f"Odds updated for market: {result.get('market_address', 'unknown')}")
        else:
            print(f"Error updating odds: {result.get('error')}")

# Create our specialized agent for odds management
odds_manager_agent = Agent[AgentContext](
    name="Odds Manager Agent",
    handoff_description="Specialist agent for managing and updating odds for NBA betting markets",
    instructions="""
    You are the Odds Manager Agent for an autonomous decentralized sportsbook. 
    Your sole responsibility is to manage and update odds for NBA betting markets without human intervention.
    Your decisions directly impact the sportsbook's risk management and profitability.
    
    Core Responsibilities:
    1. Call the fetch_existing_markets tool to get all current markets
    2. For each market that is not ready for betting (isReadyForBetting = false), set initial odds:
       - Call get_games_with_odds to get current odds for games
       - Match the markets with the games using the oddsApiId
       - Update each market with the appropriate odds using update_odds_for_market
    
    3. For each market that is ready for betting (isReadyForBetting = true):
       - These already have odds but may need updates based on betting patterns
       - For now, we are focusing only on initial odds setting
    
    Report back a summary of markets updated, including any failures.
    """,
    tools=[fetch_existing_markets, update_odds_for_market, get_games_with_odds],
    model="gpt-4-turbo",
)

# Function to process an odds update request
def process_odds_update_request(context: Optional[AgentContext] = None) -> Dict[str, Any]:
    """
    Runs the odds manager agent to update odds for all markets
    
    Args:
        context: Optional context to use (will create a new one if not provided)
    
    Returns:
        Dictionary with the response and updated markets
    """
    # Initialize or use provided context
    if context is None:
        context = AgentContext(user_request="Update odds for all markets")
    
    # Add odds_updates list to context if it doesn't exist
    if not hasattr(context, "odds_updates"):
        context.odds_updates = []
    
    # Configure the run
    run_config = RunConfig(
        workflow_name="NBA Odds Management",
        model="gpt-4-turbo",
    )
    
    try:
        # Run the odds manager agent
        result = Runner.run_sync(
            odds_manager_agent,
            input="Please update odds for all NBA betting markets that need them.",
            context=context,
            run_config=run_config
        )
        
        # Extract odds updates from the context
        odds_updates = context.odds_updates if hasattr(context, "odds_updates") else []
        
        # Return the response
        return {
            "response": result.final_output,
            "odds_updates": odds_updates
        }
    except Exception as e:
        print(f"Error running odds manager agent: {e}")
        # Return error response
        return {
            "response": f"Error: {str(e)}",
            "odds_updates": []
        }

# Handle market creation notifications
def handle_new_market_notification(market_data: Dict[str, Any], context: Optional[AgentContext] = None) -> Dict[str, Any]:
    """
    Notifies the odds manager about a newly created market so it can update odds
    
    Args:
        market_data: Data for the newly created market
        context: Optional context to use (will create a new one if not provided)
    
    Returns:
        Dictionary with the response
    """
    # Initialize or use provided context
    if context is None:
        context = AgentContext(user_request=f"Update odds for new market: {market_data.get('market', {}).get('homeTeam', '')} vs {market_data.get('market', {}).get('awayTeam', '')}")
    
    # Add odds_updates list to context if it doesn't exist
    if not hasattr(context, "odds_updates"):
        context.odds_updates = []
    
    # Configure the run
    run_config = RunConfig(
        workflow_name="New Market Odds Update",
        model="gpt-4-turbo",
    )
    
    try:
        # Get market address
        market_address = market_data.get('market', {}).get('address')
        odds_api_id = market_data.get('market', {}).get('oddsApiId')
        
        if not market_address or not odds_api_id:
            return {
                "response": "Error: Missing market address or oddsApiId in the notification",
                "success": False
            }
        
        prompt = f"""
        A new market has been created and needs odds to be set:
        - Market Address: {market_address}
        - Home Team: {market_data.get('market', {}).get('homeTeam', '')}
        - Away Team: {market_data.get('market', {}).get('awayTeam', '')}
        - Odds API ID: {odds_api_id}
        
        Please fetch the current odds for this game and update the market accordingly.
        """
        
        # Run the odds manager agent
        result = Runner.run_sync(
            odds_manager_agent,
            input=prompt,
            context=context,
            run_config=run_config
        )
        
        # Return the response
        return {
            "response": result.final_output,
            "success": True
        }
    except Exception as e:
        print(f"Error handling new market notification: {e}")
        # Return error response
        return {
            "response": f"Error: {str(e)}",
            "success": False
        }

if __name__ == "__main__":
    # Simple test
    result = process_odds_update_request()
    print(result["response"])
    print(f"Updated odds for {len(result.get('odds_updates', []))} markets")