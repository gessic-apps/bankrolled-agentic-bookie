#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Add the project root to path to find the tools
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import the tools
from tools.events.fetchEvents import fetch_nba_games_today, GameEvent
from tools.createMarket import create_market

# Import OpenAI Agent SDK
# Note: Make sure to install with: pip install "openai[agents]"
from openai import OpenAI
from agents import Agent, Runner, function_tool, handoff, RunConfig
from agents.run import RunContextWrapper

# Set up OpenAI API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("OPENAI_API_KEY not found in environment variables")
    sys.exit(1)

@dataclass
class AgentContext:
    """Context that will be shared between agents"""
    user_request: str
    nba_games: Optional[List[GameEvent]] = None
    created_markets: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.created_markets is None:
            self.created_markets = []

# Define tools for the agents
@function_tool
def get_nba_games() -> List[Dict[str, Any]]:
    """
    Fetches today's NBA games from the sports API.
    
    Returns:
        List of NBA games scheduled for today with details
    """
    games = fetch_nba_games_today()
    # Convert to dict for easier serialization
    return [
        {
            "id": game["id"],
            "odds_api_id": game["odds_api_id"],
            "home_team": {
                "name": game["home_team"]["name"],
                "abbreviation": game["home_team"]["abbreviation"]
            },
            "away_team": {
                "name": game["away_team"]["name"],
                "abbreviation": game["away_team"]["abbreviation"]
            },
            "start_time": game["start_time"],
            "status": game["status"]
        }
        for game in games
    ]

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
    Creates a new betting market for a game by calling the smart contract API
    
    Args:
        home_team: Name of the home team
        away_team: Name of the away team
        game_timestamp: Unix timestamp of the game start time
        odds_api_id: Unique ID from the Odds API for this game
        home_odds: Optional - Home team odds in 3-decimal format (e.g. 2000 = 2.000)
        away_odds: Optional - Away team odds in 3-decimal format (e.g. 1800 = 1.800)
    
    Returns:
        Dictionary with market creation result details
    """
    # Call the existing create_market function
    result = create_market(
        home_team=home_team,
        away_team=away_team,
        game_timestamp=game_timestamp,
        odds_api_id=odds_api_id,
        home_odds=home_odds,
        away_odds=away_odds
    )
    return result

def save_market_result(context: RunContextWrapper[AgentContext], result: Dict[str, Any]):
    """Helper function to save market results to context"""
    if context.context and hasattr(context.context, 'created_markets'):
        context.context.created_markets.append(result)
        print(f"Market created: {result.get('market', {}).get('homeTeam', '')} vs {result.get('market', {}).get('awayTeam', '')}")

# Create our specialized agent for market creation
market_creation_agent = Agent[AgentContext](
    name="Market Creation Agent",
    handoff_description="Specialist agent for creating betting markets for NBA games",
    instructions="""
    You are the Market Creation Agent for an autonomous decentralized sportsbook. 
    Your sole responsibility is to identify NBA games and create betting markets for them without human intervention.
    Your decisions directly impact the sportsbook's offerings, customer engagement, and profitability.
    
    Core Responsibilities:
    1. Call the get_nba_games tool to fetch today's NBA games
    2. For each game returned, create a betting market using the create_betting_market tool
    3. Do not set the odds for the market, this is done later
    4. Handle any errors gracefully and continue with the next game
    
    Report back a summary of markets created, including any failures.
    """,
    tools=[get_nba_games, create_betting_market],
    model="gpt-4-turbo",
)

# Create the triage agent that will handle all incoming requests
triage_agent = Agent[AgentContext](
    name="Triage Agent",
    instructions="""
    You are the main agent for a sports betting platform. Your role is to:
    
    1. Understand the user's request related to sports betting and market creation
    2. For requests related to creating markets for NBA games, hand off to the Market Creation Agent
    3. For other types of requests, politely explain that you currently only support creating markets for NBA games
    
    Examples of requests that should be handed off:
    - "Create betting markets for today's NBA games"
    - "Set up markets for basketball games today"
    - "I need markets for NBA games"
    
    Handle the conversation professionally and provide clear explanations.
    """,
    handoffs=[
        handoff(
            market_creation_agent,
            tool_name_override="transfer_to_market_creation_agent",
            tool_description_override="Transfer to the specialized agent for creating betting markets for NBA games"
        )
    ],
    model="gpt-4-turbo",
)

# Function to create a custom RunConfig with tracking
def create_custom_run_config():
    """Create a custom RunConfig with tracking hooks for created markets"""
    # Implement custom hooks here if needed
    return RunConfig(
        workflow_name="NBA Market Creation",
        model="gpt-4-turbo",
        # Add trace_metadata if needed
    )

def process_request(user_request: str) -> Dict[str, Any]:
    """
    Process a user request through the agent system
    
    Args:
        user_request: The user's request as a string
    
    Returns:
        Dictionary with the response and any created markets
    """
    # Initialize the context
    context = AgentContext(user_request=user_request)
    
    # Configure the run with custom config
    run_config = create_custom_run_config()
    
    try:
        # Run the triage agent
        result = Runner.run_sync(
            triage_agent,
            input=user_request,
            context=context,
            run_config=run_config
        )
        
        # Extract created markets from the context
        created_markets = context.created_markets if context.created_markets else []
        
        # Return the response
        return {
            "response": result.final_output,
            "created_markets": created_markets
        }
    except Exception as e:
        print(f"Error running agent: {e}")
        # Return error response
        return {
            "response": f"Error: {str(e)}",
            "created_markets": []
        }

# Monkeypatch to capture market creation results
def patched_create_betting_market(
    ctx: RunContextWrapper[AgentContext],
    home_team: str, 
    away_team: str, 
    game_timestamp: int,
    odds_api_id: str,
    home_odds: Optional[int] = None, 
    away_odds: Optional[int] = None
) -> Dict[str, Any]:
    """Patched version that tracks markets in context"""
    result = create_market(
        home_team=home_team,
        away_team=away_team,
        game_timestamp=game_timestamp,
        odds_api_id=odds_api_id,
        home_odds=home_odds,
        away_odds=away_odds
    )
    
    # Save to context
    if ctx and ctx.context and hasattr(ctx.context, 'created_markets'):
        ctx.context.created_markets.append(result)
        print(f"Market created: {result.get('market', {}).get('homeTeam', '')} vs {result.get('market', {}).get('awayTeam', '')}")
    
    return result

# Apply the monkey patch for tracking
try:
    # We need to try to monkey patch both possible approaches
    # Some versions need different approaches
    import inspect
    sig = inspect.signature(function_tool)
    if len(sig.parameters) > 0 and 'func' in sig.parameters:
        # Method 1: Replace the function
        create_betting_market = function_tool(patched_create_betting_market)
    else:
        # Method 2: Keep the original function but intercept at runtime
        # This will be handled in the hook if needed
        pass
except Exception as e:
    print(f"Warning: Could not patch function_tool: {e}")

if __name__ == "__main__":
    # Simple test
    request = "Can you create markets for today's NBA games?"
    result = process_request(request)
    print(result["response"])
    print(f"Created {len(result['created_markets'])} markets")
    
    # Print market details
    for i, market in enumerate(result["created_markets"]):
        print(f"\nMarket {i+1}:")
        if 'market' in market and market['market']:
            address = market['market'].get('address', 'Unknown')
            home_team = market['market'].get('homeTeam', 'Unknown')
            away_team = market['market'].get('awayTeam', 'Unknown')
            print(f"Address: {address}")
            print(f"Teams: {home_team} vs {away_team}")
        else:
            print(f"Error: {market.get('error', 'Unknown error')}")