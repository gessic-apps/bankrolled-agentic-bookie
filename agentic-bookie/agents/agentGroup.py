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

# Import SUPPORTED_SPORT_KEYS from one of the agents
from .market_creation_agent import SUPPORTED_SPORT_KEYS
# Import the specialized agents
from .market_creation_agent import market_creation_agent
from .odds_manager_agent import odds_manager_agent
from .game_status_agent import game_status_agent
from .risk_manager_agent import risk_manager_agent

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
    You are the main dispatcher for a sports betting platform automation system handling NBA and major European Soccer leagues.
    Your role is to understand the user's request and route it to the correct specialized agent.

    Supported Sports: NBA and Soccer (EPL, Ligue 1, Serie A, Bundesliga, La Liga, Champions League).

    1.  If the request is about **creating new betting markets** for supported sports, hand off to the `Market Creation Agent`.
        Keywords: create markets, set up games, new markets, list games for betting, add soccer/NBA games.
    2.  If the request is about **setting or updating odds** for existing markets in supported sports, hand off to the `Odds Manager Agent`.
        Keywords: update odds, set odds, manage odds, check prices, set lines, soccer odds, NBA odds.
    3.  If the request is about **checking game completion or setting final results** for markets in supported sports, hand off to the `Game Result Settlement Agent`.
        Keywords: check status, monitor games, settle results, game finished, final score.
    4.  If the request is about **managing risk and liquidity** for betting markets, hand off to the `Risk Manager Agent`.
        Keywords: risk management, add liquidity, manage exposure, liquidity pool, market liquidity, risk assessment.
    5.  For any other requests, politely explain that you currently only support market creation, odds management, game result settlement, and risk management for NBA and the specified Soccer leagues via the specialized agents. Do not attempt to fulfill other requests yourself.

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
        ),
        handoff( # Add handoff for the risk manager agent
            risk_manager_agent, # Use the imported agent object
            tool_name_override="transfer_to_risk_manager_agent",
            tool_description_override="Transfer task to the agent specializing in managing risk and liquidity for betting markets."
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
        supported_sports_str = ", ".join(SUPPORTED_SPORT_KEYS)
        market_creation_prompt = f"Create betting markets for today's games in these leagues: {supported_sports_str}."
        odds_management_prompt = f"Set or update odds for all existing markets for these sports: {supported_sports_str}."
        game_status_prompt = f"Check for completed games and settle results for markets in these sports: {supported_sports_str}." # Updated prompt
        risk_management_prompt = f"Analyze current markets and add liquidity where needed based on risk assessment."

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

        # --- Run Risk Manager Agent ---
        print("\n--- Running Risk Manager Agent ---")
        triage_result_risk = await Runner.run(triage_agent, risk_management_prompt)
        print("Triage Result (Risk Management):", triage_result_risk.final_output)

        print("\n--- Test Sequence Complete ---")

    import asyncio
    asyncio.run(test_bookie_system())