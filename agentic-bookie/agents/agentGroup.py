#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# Add the project root to path to find the tools
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Import from shared utilities
from utils.config import SUPPORTED_SPORT_KEYS

# Import OpenAI Agent SDK
from agents import Agent, Runner, function_tool, handoff

# Import the specialized agents
from .market_creation_agent import market_creation_agent
from .odds_manager_agent import odds_manager_agent
from .game_status_agent import game_status_agent
from .risk_triage_agent import risk_triage_agent  # New risk triage agent replaces direct risk_manager use
from .high_risk_handler_agent import high_risk_handler_agent  # For individual high-risk market handling
from .risk_manager_agent import risk_manager_agent  # Still used for batch updates through risk_triage_agent

# Define the Triage Agent
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
        The Odds Manager can now efficiently handle all markets in a single operation using the new fetch_and_update_all_markets function.
    3.  If the request is about **checking game completion or setting final results** for markets in supported sports, hand off to the `Game Result Settlement Agent`.
        Keywords: check status, monitor games, settle results, game finished, final score.
    4.  If the request is about **managing risk and liquidity** for betting markets, hand off to the `Risk Triage Agent`.
        Keywords: risk management, add liquidity, manage exposure, liquidity pool, market liquidity, risk assessment, odds adjustments, bet limits.
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
            tool_description_override="Transfer task to the agent specializing in setting and updating odds for NBA and soccer markets. Now uses a combined function to fetch and update all odds in one operation."
        ),
        handoff( # Add handoff for the new agent
            game_status_agent, # Use the imported agent object
            tool_name_override="transfer_to_game_status_agent",
            tool_description_override="Transfer task to the agent specializing in monitoring game start times and updating market status."
        ),
        handoff( # Add handoff for the risk triage agent
            risk_manager_agent, # Use the imported agent object
            tool_name_override="transfer_to_risk_manager_agent",
            tool_description_override="Transfer task to the agent specializing in triaging market risk, identifying high-risk markets for individual handling, and coordinating batch updates for regular markets."
        )
    ],
    # DO NOT CHANGE THIS MODEL FROM THE CURRENT SETTING
    model="gpt-4o-mini-2024-07-18",
)

# ======================= MAIN EXECUTION =======================

if __name__ == "__main__":
    print("=== Testing the Simplified Agentic Bookie System ===")

    # --- Test Runner ---
    async def test_bookie_system():
        # Ensure environment variables are loaded if testing directly
        from dotenv import load_dotenv # Ensure load_dotenv is imported here too
        load_dotenv()
        print(os.getenv("SPORTS_API_KEY"))
        if not os.getenv("SPORTS_API_KEY"):
             print("Error: Missing SPORTS_API_KEY or API_URL in .env file. Cannot run full test.", file=sys.stderr)
             # Decide if you want to proceed with partial tests or return
             # return

        # Example prompts for each agent
        supported_sports_str = ", ".join(SUPPORTED_SPORT_KEYS)
        market_creation_prompt = f"Create betting markets for today's games in these leagues: {supported_sports_str}."
        odds_management_prompt = f"Set or update odds for all existing markets for these sports: {supported_sports_str}."
        game_status_prompt = f"Check for completed games and settle results for markets in these sports: {supported_sports_str}."
        risk_management_prompt = f"Analyze current markets and adjust odds, liquidity or limits/exposures where needed based on risk assessment."

        # Helper function to write output to JSON
        def write_output_to_json(output_data, filename_base):
            # output_file_path = f"/Users/osman/bankrolled-agent-bookie/smart-contracts/{filename_base}_output.json"
            output_file_path = Path(__file__).resolve().parent.parent.parent / "smart-contracts" / f"{filename_base}_output.json"
            data_to_write = {"finalOutput": output_data}
            try:
                with open(output_file_path, 'w') as f:
                    json.dump(data_to_write, f, indent=4)
                print(f"Successfully wrote agent output to {output_file_path}")
            except Exception as e:
                print(f"Error writing agent output to {output_file_path}: {e}")

        # --- Run Market Creation Agent ---
        print("\n--- Running Market Creation Agent ---")
        triage_result_market = await Runner.run(triage_agent, market_creation_prompt)
        print("Triage Result (Market Creation):", triage_result_market.final_output)
        write_output_to_json(triage_result_market.final_output, "triage_market_creation")

        # --- Run Odds Manager Agent ---
        print("\n--- Running Odds Manager Agent ---")
        triage_result_odds = await Runner.run(triage_agent, odds_management_prompt)
        print("Triage Result (Odds Management):", triage_result_odds.final_output)
        write_output_to_json(triage_result_odds.final_output, "triage_odds_manager")

        # --- Run Game Status Agent ---
        print("\n--- Running Game Status Agent ---")
        triage_result_status = await Runner.run(triage_agent, game_status_prompt)
        print("Triage Result (Game Status):", triage_result_status.final_output)
        write_output_to_json(triage_result_status.final_output, "triage_game_status")

        # --- Run Risk Triage Agent ---
        print("\n--- Running Risk Triage Agent ---")
        triage_result_risk = await Runner.run(triage_agent, risk_management_prompt)
        print("Triage Result (Risk Management):", triage_result_risk.final_output)
        write_output_to_json(triage_result_risk.final_output, "triage_risk_management")

        print("\n--- Test Sequence Complete ---")

    import asyncio
    asyncio.run(test_bookie_system())