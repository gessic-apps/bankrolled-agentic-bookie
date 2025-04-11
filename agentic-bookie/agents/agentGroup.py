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
    # DO NOT CHANGE THIS MODEL FROM THE CURRENT SETTING
    model="gpt-4o-2024-11-20",
)

# ======================= MAIN EXECUTION =======================

if __name__ == "__main__":
    print("=== Testing the Simplified Agentic Bookie System ===")

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
    asyncio.run(test_bookie_system())