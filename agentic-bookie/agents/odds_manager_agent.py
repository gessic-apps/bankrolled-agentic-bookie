#!/usr/bin/env python3
import json
from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict

from agents import Agent, function_tool
from utils.config import SUPPORTED_SPORT_KEYS
from utils.sports.games_data import fetch_games_with_odds
from utils.markets.market_data import get_all_markets
from utils.markets.odds_management import (
    update_odds_for_market,
    update_odds_for_multiple_markets,
    check_market_odds,
    OddsData
)
from utils.markets.odds_operations import fetch_and_update_all_markets

# Function tool for agent to use
@function_tool
def get_existing_markets() -> List[Dict[str, Any]]:
    """Fetches all existing betting markets from the smart contract API."""
    return get_all_markets()

@function_tool
def update_market_odds(
    market_address: str,
    home_odds: float,
    away_odds: float,
    draw_odds: Optional[float],
    home_spread_points: float,
    home_spread_odds: float,
    away_spread_odds: float,
    total_points: float,
    over_odds: float,
    under_odds: float
) -> Dict[str, Any]:
    """Updates all odds types (moneyline including draw, spread, total) for a specific market."""
    return update_odds_for_market(
        market_address=market_address,
        home_odds=home_odds,
        away_odds=away_odds,
        draw_odds=draw_odds,
        home_spread_points=home_spread_points,
        home_spread_odds=home_spread_odds,
        away_spread_odds=away_spread_odds,
        total_points=total_points,
        over_odds=over_odds,
        under_odds=under_odds
    )

@function_tool
def update_multiple_markets_odds(markets_data: List[OddsData]) -> Dict[str, Any]:
    """Updates odds for multiple markets at once."""
    return update_odds_for_multiple_markets(markets_data)

@function_tool
def fetch_odds(sport_keys: List[str]) -> List[Dict[str, Any]]:
    """Fetches today's games for the specified sports with latest odds from The Odds API."""
    return fetch_games_with_odds(sport_keys)

@function_tool
def check_odds(market_address: str) -> Dict[str, Any]:
    """Checks if a specific betting market (identified by its address) already has odds set."""
    return check_market_odds(market_address)

@function_tool
def fetch_and_update_odds() -> Dict[str, Any]:
    """Fetches games with odds, gets existing markets, and updates all market odds in a single operation."""
    return fetch_and_update_all_markets()

#Add a function that lets the agent read the most recent actions from the file.
@function_tool
def read_actions_from_file():
    """
    Reads the most recent actions from the file.
    """
    with open("/Users/osman/bankrolled-agent-bookie/agentic-bookie/agents/risk_manager_context.json", "r") as f:
        return f.read()

# Define the Odds Manager Agent
odds_manager_agent = Agent(
    name="Odds Manager Agent",
    handoff_description="Specialist agent for managing and updating odds (including draw odds for soccer) for NBA & Soccer betting markets",
    instructions="""
    You are the Odds Manager Agent. Your goal is to set (but not update) odds (moneyline including draw, spreads, totals) for markets across supported sports (NBA & Soccer).
    
    IMPORTANT: You are not allowed to update any existing markets. You are only allowed to set new odds. Use `check_odds` if you need to verify if a market already has odds before attempting to set them.
    
    **Primary Workflow:**
    1. Call `fetch_and_update_odds()` which will:
       - Fetch games with latest odds from The Odds API for all supported sports.
       - Get existing markets from your platform's API.
       - Match markets with their corresponding odds.
       - Return a comprehensive summary of the update process.
    
    2. Report back the summary of results, including:
       - How many markets had odds data available.
       - How many existing markets were found.
       - How many markets were matched and updated successfully.
       - Any errors that occurred.
    
    **Alternative Workflow (for specific cases or verification):**
    - Use `fetch_odds` to get just odds data for specific sports.
    - Use `get_existing_markets` to get just market data.
    - Use `check_odds(market_address=<address>)` to see if a specific market already has odds set.
    - Use `update_market_odds` for single market updates (use carefully according to the 'set new odds only' rule).
    - Use `update_multiple_markets_odds` for batch updates (use carefully according to the 'set new odds only' rule).
    
    For normal operation, prefer the combined `fetch_and_update_odds` function. Adhere strictly to the rule of only setting new odds, not updating existing ones. If using update functions, ideally verify first with `check_odds`.
    """,
    tools=[
        get_existing_markets,
        update_market_odds,
        update_multiple_markets_odds,
        fetch_odds,
        fetch_and_update_odds,
        check_odds
    ],
    # DO NOT CHANGE THIS MODEL FROM THE CURRENT SETTING
    model="gpt-4o-mini-2024-07-18",
)

# Example of how this agent might be run (usually done by a Runner via Triage)
if __name__ == '__main__':
    # This part is just for testing the agent directly if needed
    from agents import Runner
    import asyncio

    async def test_odds_management():
        # Option 1: Test the combined function
        prompt = f"Set or update odds for all markets in supported sports: {', '.join(SUPPORTED_SPORT_KEYS)}."
        print(f"--- Running Odds Manager Agent with prompt: '{prompt}' ---")
        result = await Runner.run(odds_manager_agent, prompt)
        print("--- Odds Manager Agent Result ---")
        print(result.final_output)

        # Define the output file path
        output_file_path = "/Users/osman/bankrolled-agent-bookie/smart-contracts/odds_manager_output.json"
        
        # Prepare the data to be written
        output_data = {"finalOutput": result.final_output}
        
        # Write the data to the JSON file
        try:
            with open(output_file_path, 'w') as f:
                json.dump(output_data, f, indent=4)
            print(f"Successfully wrote agent output to {output_file_path}")
        except Exception as e:
            print(f"Error writing agent output to {output_file_path}: {e}")

        print("---------------------------------")

    # Run the test
    asyncio.run(test_odds_management())
    print("Odds Manager Agent defined. Run agentGroup.py to test via Triage.")