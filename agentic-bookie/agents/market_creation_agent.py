#!/usr/bin/env python3
import json
from typing import List, Dict, Any, Optional

from agents import Agent, function_tool
from utils.config import SUPPORTED_SPORT_KEYS
from utils.sports.games_data import fetch_upcoming_games
from utils.markets.market_data import get_all_markets, check_event_exists
from utils.markets.market_creation import create_betting_market, batch_process_markets
from dotenv import load_dotenv

load_dotenv()
# Function tool for agent to use
@function_tool
def get_markets() -> List[str]:
    """Fetches all existing betting markets from the smart contract API."""
    markets = get_all_markets()
    # Convert market objects to JSON strings for compatibility with the agent
    return [json.dumps(market) for market in markets]

@function_tool
def check_market_exists(game_id: str, existing_markets: List[str]) -> bool:
    """Checks if a betting market already exists for a given Odds API game ID within a provided list."""
    # Parse JSON strings into dictionaries
    market_dicts = []
    for market_str in existing_markets:
        try:
            market_dicts.append(json.loads(market_str))
        except Exception:
            continue
    
    return check_event_exists(game_id, market_dicts)

@function_tool
def create_market(
    home_team: str,
    away_team: str,
    game_timestamp: int,
    game_id: str,
    home_odds: Optional[int] = None,
    away_odds: Optional[int] = None
) -> str:
    """Creates a new betting market via the smart contract API."""
    result = create_betting_market(
        home_team=home_team,
        away_team=away_team,
        game_timestamp=game_timestamp,
        game_id=game_id,
        home_odds=home_odds,
        away_odds=away_odds
    )
    return json.dumps(result)

@function_tool
def fetch_games(sport_keys: List[str]) -> List[str]:
    """Fetches upcoming games (today and tomorrow) for the specified sports from The Odds API."""
    games = fetch_upcoming_games(sport_keys)
    # Convert game objects to JSON strings for compatibility with the agent
    return [json.dumps(game) for game in games]

@function_tool
def process_markets(upcoming_games: List[str]) -> str:
    """Process multiple game events at once, checking which ones need markets created and creating them in batch."""
    # Parse JSON strings into dictionaries
    game_dicts = []
    for game_str in upcoming_games:
        try:
            game_dicts.append(json.loads(game_str))
        except Exception:
            continue
    
    result = batch_process_markets(game_dicts)
    return json.dumps(result)

# Define the Market Creation Agent
market_creation_agent = Agent(
    name="Market Creation Agent",
    handoff_description="Specialist agent for creating betting markets for NBA games",
    instructions="""
    You are the Market Creation Agent. Your goal is to create betting markets for upcoming games (today and tomorrow) across supported sports (NBA and major Soccer leagues) that do not already exist.
    
    Follow these steps:
    1. Call `fetch_games` with the list of supported sport keys to find upcoming games for today and tomorrow. Each game is returned as a JSON string.
    2. Call `process_markets` with the list of upcoming games from step 1. This function will:
       a. Fetch existing markets
       b. Check which games need new markets 
       c. Create markets for games that don't already have one
       d. Return a summary of results
    3. Report a summary of the markets created based on the results from step 2. Include:
       - Total number of markets created
       - Total number of markets skipped (already existed)
       - List of market details (game ID, teams) that were created
       - Any errors that occurred
       
    This batch approach is more efficient than processing games one-by-one.
    """,
    # Ensure all necessary tools are available
    tools=[fetch_games, process_markets, get_markets, check_market_exists, create_market],
    # DO NOT CHANGE THIS MODEL FROM THE CURRENT SETTING
    model="gpt-4o-2024-11-20",
)

# Example of how this agent might be run (usually done by a Runner via Triage)
if __name__ == '__main__':
    # This part is just for testing the agent directly if needed
    from agents import Runner
    import asyncio
    
    async def test_market_creation():
        # Input prompt to trigger the agent's logic
        prompt = f"Create markets for upcoming games in supported sports: {', '.join(SUPPORTED_SPORT_KEYS)}."
        print(f"--- Running Market Creation Agent with prompt: '{prompt}' ---")
        result = await Runner.run(market_creation_agent, prompt)
        print("--- Market Creation Agent Result ---")
        print(result.final_output)

        # Define the output file path
        output_file_path = "/Users/osman/bankrolled-agent-bookie/smart-contracts/market_creation_output.json"
        
        # Prepare the data to be written
        output_data = {"finalOutput": result.final_output}
        
        # Write the data to the JSON file
        try:
            with open(output_file_path, 'w') as f:
                json.dump(output_data, f, indent=4)
            print(f"Successfully wrote agent output to {output_file_path}")
        except Exception as e:
            print(f"Error writing agent output to {output_file_path}: {e}")

        print("------------------------------------")
    
    # Run the test
    asyncio.run(test_market_creation())
    print("Market Creation Agent defined. Run agentGroup.py to test via Triage.")