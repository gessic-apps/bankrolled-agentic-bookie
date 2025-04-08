#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add the project root to path to find the tools
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Import the actual tool implementation functions
from tools.events.fetchEvents import fetch_nba_games_today, GameEvent # Assuming GameEvent is used by fetch
from tools.createMarket import create_market, get_all_markets, update_market_odds

# Import OpenAI Agent SDK
from agents import Agent, Runner, function_tool, handoff

# Import the specialized agents
from .market_creation_agent import market_creation_agent
from .odds_manager_agent import odds_manager_agent
from .game_status_agent import game_status_agent

# Set up OpenAI API key from environment (optional, SDK might handle this)
# api_key = os.getenv("OPENAI_API_KEY")
# if not api_key:
#     print("OPENAI_API_KEY not found in environment variables.")
#     # Consider exiting or letting the SDK handle the missing key error
#     # sys.exit(1)

# ======================= TOOL FUNCTION WRAPPERS =======================
# These functions wrap the imported implementations for the Agent SDK

@function_tool
def get_nba_games() -> List[Dict[str, Any]]:
    """
    Fetches today's NBA games from the sports API.
    Returns a list of game dictionaries suitable for the agent.
    """
    try:
        games = fetch_nba_games_today()
        # Convert GameEvent objects (if returned) to simple dicts for the agent
        return [
            {
                "id": game.id, # Access attributes directly if GameEvent is a class/dataclass
                "odds_api_id": game.odds_api_id,
                "home_team": {
                    "name": game.home_team.name,
                    "abbreviation": game.home_team.abbreviation
                },
                "away_team": {
                    "name": game.away_team.name,
                    "abbreviation": game.away_team.abbreviation
                },
                # Convert datetime to timestamp if necessary, or pass as string
                "start_time": int(game.start_time.timestamp()) if hasattr(game.start_time, 'timestamp') else str(game.start_time),
                "status": game.status
            }
            for game in games
        ]
    except Exception as e:
        print(f"Error fetching NBA games: {e}")
        # Return an empty list or an error structure if preferred
        return []

@function_tool
def get_existing_markets() -> List[Dict[str, Any]]:
    """
    Fetches all existing betting markets from the API.
    Returns a list of market dictionaries.
    """
    try:
        markets = get_all_markets()
        # Assuming get_all_markets already returns a list of dicts
        # Add error handling if necessary
        return markets
    except Exception as e:
        print(f"Error fetching existing markets: {e}")
        return []

@function_tool
def create_betting_market(
    home_team: str,
    away_team: str,
    game_timestamp: int,
    odds_api_id: str,
    home_odds: Optional[int] = None,
    away_odds: Optional[int] = None
) -> Dict[str, Any]:
    """
    Creates a new betting market via the smart contract API.
    Uses the imported `create_market` function.
    """
    try:
        result = create_market(
            home_team=home_team,
            away_team=away_team,
            game_timestamp=game_timestamp,
            odds_api_id=odds_api_id,
            home_odds=home_odds,
            away_odds=away_odds
        )
        # Add logging or confirmation
        print(f"Tool 'create_betting_market' called for {home_team} vs {away_team}. Result: {result.get('status', 'unknown')}")
        return result
    except Exception as e:
        print(f"Error creating betting market for {home_team} vs {away_team}: {e}")
        return {"error": str(e), "status": "failed"}

@function_tool
def update_odds_for_market(market_address: str, home_odds: int, away_odds: int) -> Dict[str, Any]:
    """
    Updates the odds for an existing market via the API.
    Uses the imported `update_market_odds` function.
    """
    try:
        # Basic validation
        if home_odds < 1000 or away_odds < 1000:
             raise ValueError("Odds must be at least 1.000 (represented as 1000)")

        result = update_market_odds(market_address, home_odds, away_odds)
        print(f"Tool 'update_odds_for_market' called for {market_address}. Result: {result.get('status', 'unknown')}")
        return result
    except Exception as e:
        print(f"Error updating odds for market {market_address}: {e}")
        return {"error": str(e), "status": "failed", "market_address": market_address}

@function_tool
def get_games_with_odds() -> List[Dict[str, Any]]:
    """
    Fetches today's NBA games including the latest odds data.
    (Currently uses mock odds).
    """
    try:
        games = fetch_nba_games_today() # Re-fetch games or use a cached list

        # Mock odds data - replace with actual odds API call later
        mock_odds_data = {
            game.odds_api_id: {
                "home_odds": 1850 + hash(game.odds_api_id) % 300, # Slightly varied mock odds
                "away_odds": 2150 - hash(game.odds_api_id) % 300
            } for game in games
        }

        result_list = []
        for game in games:
             game_data = {
                "id": game.id,
                "odds_api_id": game.odds_api_id,
                "home_team": {
                    "name": game.home_team.name,
                    "abbreviation": game.home_team.abbreviation
                },
                "away_team": {
                    "name": game.away_team.name,
                    "abbreviation": game.away_team.abbreviation
                },
                "start_time": int(game.start_time.timestamp()) if hasattr(game.start_time, 'timestamp') else str(game.start_time),
                "status": game.status,
                # Get mock odds or default if not found
                "odds": mock_odds_data.get(game.odds_api_id, {"home_odds": 2000, "away_odds": 2000})
            }
             result_list.append(game_data)

        print(f"Tool 'get_games_with_odds' called. Found {len(result_list)} games.")
        return result_list
    except Exception as e:
        print(f"Error fetching games with odds: {e}")
        return []


# ======================= AGENT DEFINITIONS =======================

# Define the Triage Agent
# No context type specified, simplifying the agent definition
triage_agent = Agent(
    name="Triage Agent",
    instructions="""
    You are the main dispatcher for a sports betting platform automation system.
    Your role is to understand the user's request and route it to the correct specialized agent.

    1.  If the request is about **creating new betting markets** for NBA games, hand off to the `Market Creation Agent`.
        Keywords: create markets, set up games, new NBA markets, list games for betting.
    2.  If the request is about **setting or updating odds** for existing markets, hand off to the `Odds Manager Agent`.
        Keywords: update odds, set odds, manage odds, check prices.
    3.  If the request is about **checking game start times or updating game statuses**, hand off to the `Game Status Agent`.
        Keywords: game start, check status, monitor games, start betting.
    4.  For any other requests, politely explain that you currently only support market creation, odds management, and game status updates for NBA games via the specialized agents. Do not attempt to fulfill other requests yourself.

    Use the provided handoff tools to transfer the task.
    """,
    # Provide the imported agents to the handoff function
    handoffs=[
        handoff(
            market_creation_agent, # Use the imported agent object
            tool_name_override="transfer_to_market_creation_agent",
            tool_description_override="Transfer task to the agent specializing in creating new NBA betting markets."
        ),
        handoff(
            odds_manager_agent, # Use the imported agent object
            tool_name_override="transfer_to_odds_manager_agent",
            tool_description_override="Transfer task to the agent specializing in setting and updating odds for NBA markets."
        ),
        handoff( # Add handoff for the new agent
            game_status_agent, # Use the imported agent object
            tool_name_override="transfer_to_game_status_agent",
            tool_description_override="Transfer task to the agent specializing in monitoring game start times and updating market status."
        )
    ],
    model="gpt-4-turbo",
    # Note: Tools defined above are not directly used by Triage, but are available
    # if needed, and are used by the agents it hands off to.
    # tools=[get_nba_games, get_existing_markets, create_betting_market, update_odds_for_market, get_games_with_odds]
)

# ======================= MAIN EXECUTION =======================

if __name__ == "__main__":
    print("=== Testing the Simplified Agentic Bookie System ===")

#     # Example 1: Market Creation Request
#     print("--- Test 1: Market Creation Request ---")
#     market_request = "Please set up betting markets for today's NBA action."
#     print(f"User Request: {market_request}")
#     try:
#         # Use Runner.run_sync for simple synchronous execution
#         market_result = Runner.run_sync(
#             triage_agent,
#             input=market_request,
#             # No context needed for this simplified setup
#             # No run_config needed unless specific tracing/model overrides are desired
#         )
#         print("--- Triage Agent Final Output (Market Creation) ---")
#         print(market_result.final_output)
#         print("-" * 50)

#         # You could inspect market_result.new_items for details on tool calls/handoffs
#         # print("
# # --- Run Details (Market Creation) ---")
#         # for item in market_result.new_items:
#         #     print(f"- {item.type}: {item.raw_item}")
#         # print("-" * 50)

#     except Exception as e:
#         print(f"Error during market creation test: {e}")

#     # Example 2: Odds Management Request
#     print("--- Test 2: Odds Management Request ---")
#     odds_request = "Update the odds for all markets that need it."
#     print(f"User Request: {odds_request}")
#     try:
#         odds_result = Runner.run_sync(
#             triage_agent,
#             input=odds_request,
#         )
#         print("--- Triage Agent Final Output (Odds Management) ---")
#         print(odds_result.final_output)
#         print("-" * 50)

#         # print("--- Run Details (Odds Management) ---")
#         # for item in odds_result.new_items:
#         #     print(f"- {item.type}: {item.raw_item}")
#         # print("-" * 50)

#     except Exception as e:
#         print(f"Error during odds management test: {e}")

#     # Example 3: Unrelated Request
#     print("--- Test 3: Unrelated Request ---")
#     other_request = "What's the weather like today?"
#     print(f"User Request: {other_request}")
#     try:
#         other_result = Runner.run_sync(
#             triage_agent,
#             input=other_request,
#         )
#         print("--- Triage Agent Final Output (Unrelated) ---")
#         print(other_result.final_output)
#         print("-" * 50)

#     except Exception as e:
#         print(f"Error during unrelated request test: {e}")

#     print("=== Agent Testing Complete ===")

    # --- Test Runner ---
    async def test_bookie_system():
        # Ensure environment variables are loaded if testing directly
        from dotenv import load_dotenv # Ensure load_dotenv is imported here too
        load_dotenv()
        if not os.getenv("SPORTS_API_KEY"):
             print("Error: Missing SPORTS_API_KEY or API_URL in .env file. Cannot run full test.", file=sys.stderr)
             # Decide if you want to proceed with partial tests or return
             # return

        # Example prompts for each agent
        market_creation_prompt = "Create betting markets for today's NBA games."
        odds_management_prompt = "Set initial odds for any markets that need them and update odds for existing markets."
        game_status_prompt = "Monitor game start times and update market status for games that have started." # Prompt for the new agent

        # --- Run Market Creation Agent ---
        print("\n--- Running Market Creation Agent ---")
        # Use the triage_agent instance defined above
        triage_result_market = await Runner.run(triage_agent, market_creation_prompt)
        print("Triage Result (Market Creation):", triage_result_market.final_output)


        # --- Run Odds Manager Agent ---
        print("\n--- Running Odds Manager Agent ---")
        triage_result_odds = await Runner.run(triage_agent, odds_management_prompt)
        print("Triage Result (Odds Management):", triage_result_odds.final_output)

        # --- Run Game Status Agent ---
        print("\n--- Running Game Status Agent ---")
        triage_result_status = await Runner.run(triage_agent, game_status_prompt)
        print("Triage Result (Game Status):", triage_result_status.final_output)


        print("\n--- Test Sequence Complete ---")


    import asyncio
    # The triage_agent instance is already defined above. We just need to run the test function.
    # Remove the incorrect re-definition line below:
    # available_agents = [market_creation_agent, odds_manager_agent, game_status_agent]
    # triage_agent = TriageAgent(agents=available_agents) # <--- REMOVE THIS LINE

    asyncio.run(test_bookie_system())