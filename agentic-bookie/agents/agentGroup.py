#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, TypedDict
from dataclasses import dataclass

# Add the project root to path to find the tools
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import the tools
from tools.events.fetchEvents import fetch_nba_games_today, GameEvent
from tools.createMarket import create_market, get_all_markets, update_market_odds

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
    odds_updates: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.created_markets is None:
            self.created_markets = []
        if self.odds_updates is None:
            self.odds_updates = []

class OddsData(TypedDict):
    """Type definition for odds data"""
    home_odds: int  # Integer with 3 decimal precision (e.g. 1941 for 1.941)
    away_odds: int  # Integer with 3 decimal precision (e.g. 1051 for 1.051)

# ======================= MARKET CREATION TOOLS =======================

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
def get_existing_markets() -> List[Dict[str, Any]]:
    """
    Fetches all existing betting markets from the API
    
    Returns:
        List of market objects with details including market address, teams, odds, and status
    """
    markets = get_all_markets()
    return markets

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

# ======================= ODDS MANAGEMENT TOOLS =======================

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
    Fetches today's NBA games with latest odds data
    
    Returns:
        List of NBA games with odds
    """
    # This is a mock function for now - in a real implementation, you would 
    # fetch real odds data from a provider like The Odds API
    games = fetch_nba_games_today()
    
    # Mock odds data - in a real implementation, this would come from the odds API
    mock_odds = {
        game["odds_api_id"]: {
            "home_odds": 1850,  # 1.850
            "away_odds": 2000   # 2.000
        } for game in games
    }
    
    # Convert to dict for easier serialization
    result = [
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
            "status": game["status"],
            "odds": mock_odds.get(game["odds_api_id"], {"home_odds": 2000, "away_odds": 2000})
        }
        for game in games
    ]
    
    return result

# ======================= HELPER FUNCTIONS =======================

def save_market_result(context: RunContextWrapper[AgentContext], result: Dict[str, Any]):
    """Helper function to save market results to context"""
    if context.context and hasattr(context.context, 'created_markets'):
        context.context.created_markets.append(result)
        print(f"Market created: {result.get('market', {}).get('homeTeam', '')} vs {result.get('market', {}).get('awayTeam', '')}")
        
        # Notify the odds manager about the new market
        handle_new_market_notification(result, context.context)

def save_odds_update_result(context: RunContextWrapper[AgentContext], result: Dict[str, Any]):
    """Helper function to save odds update results to context"""
    if context.context and hasattr(context.context, 'odds_updates'):
        context.context.odds_updates.append(result)
        if "error" not in result:
            print(f"Odds updated for market: {result.get('market_address', 'unknown')}")
        else:
            print(f"Error updating odds: {result.get('error')}")

# ======================= AGENT DEFINITIONS =======================

# Create our specialized agent for market creation
market_creation_agent = Agent[AgentContext](
    name="Market Creation Agent",
    handoff_description="Specialist agent for creating betting markets for NBA games",
    instructions="""
    You are the Market Creation Agent for an autonomous decentralized sportsbook. 
    Your sole responsibility is to identify NBA games and create betting markets for them without human intervention.
    Your decisions directly impact the sportsbook's offerings, customer engagement, and profitability.
    
    Core Responsibilities:
    1. First call get_existing_markets to fetch all markets that already exist
    2. Then call get_nba_games to fetch today's NBA games
    3. For each game returned, check if a market already exists by matching the oddsApiId
    4. Only create new markets for games that don't already have markets
    5. Create new markets using the create_betting_market tool
    6. Do not set the odds for the market, this is done by the Odds Manager Agent
    7. Handle any errors gracefully and continue with the next game
    
    Report back a summary of markets created, including any failures.
    """,
    tools=[get_nba_games, create_betting_market, get_existing_markets],
    model="gpt-4-turbo",
)

# Create the odds manager agent
odds_manager_agent = Agent[AgentContext](
    name="Odds Manager Agent",
    handoff_description="Specialist agent for managing and updating odds for NBA betting markets",
    instructions="""
    You are the Odds Manager Agent for an autonomous decentralized sportsbook. 
    Your sole responsibility is to manage and update odds for NBA betting markets without human intervention.
    Your decisions directly impact the sportsbook's risk management and profitability.
    
    Core Responsibilities:
    1. Call the get_existing_markets tool to get all current markets
    2. For each market that is not ready for betting (isReadyForBetting = false), set initial odds:
       - Call get_games_with_odds to get current odds for games
       - Match the markets with the games using the oddsApiId
       - Update each market with the appropriate odds using update_odds_for_market
    
    3. For each market that is ready for betting (isReadyForBetting = true):
       - These already have odds but may need updates based on betting patterns
       - For now, we are focusing only on initial odds setting
    
    Report back a summary of markets updated, including any failures.
    """,
    tools=[get_existing_markets, update_odds_for_market, get_games_with_odds],
    model="gpt-4-turbo",
)

# Create the triage agent that will handle all incoming requests
triage_agent = Agent[AgentContext](
    name="Triage Agent",
    instructions="""
    You are the main agent for a sports betting platform. Your role is to:
    
    1. Understand the user's request related to sports betting and market creation
    2. For requests related to creating markets for NBA games, hand off to the Market Creation Agent
    3. For requests related to updating odds for markets, hand off to the Odds Manager Agent
    4. For other types of requests, politely explain that you currently only support creating markets for NBA games 
       and managing odds
    
    Examples of requests to hand off to Market Creation Agent:
    - "Create betting markets for today's NBA games"
    - "Set up markets for basketball games today"
    - "I need markets for NBA games"
    
    Examples of requests to hand off to Odds Manager Agent:
    - "Update odds for existing markets"
    - "Set the odds for markets that need them"
    - "Check and update all market odds"
    
    Handle the conversation professionally and provide clear explanations.
    """,
    handoffs=[
        handoff(
            market_creation_agent,
            tool_name_override="transfer_to_market_creation_agent",
            tool_description_override="Transfer to the specialized agent for creating betting markets for NBA games"
        ),
        handoff(
            odds_manager_agent,
            tool_name_override="transfer_to_odds_manager_agent",
            tool_description_override="Transfer to the specialized agent for managing and updating odds for betting markets"
        )
    ],
    model="gpt-4-turbo",
)

# ======================= PROCESS FUNCTIONS =======================

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
        odds_updates = context.odds_updates if context.odds_updates else []
        
        # Return the response
        return {
            "response": result.final_output,
            "created_markets": created_markets,
            "odds_updates": odds_updates
        }
    except Exception as e:
        print(f"Error running agent: {e}")
        # Return error response
        return {
            "response": f"Error: {str(e)}",
            "created_markets": [],
            "odds_updates": []
        }

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

# ======================= MONKEYPATCHING =======================

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
        
        # Notify the odds manager about the new market
        try:
            odds_result = handle_new_market_notification(result, ctx.context)
            print(f"Odds manager notified: {odds_result['success']}")
        except Exception as e:
            print(f"Error notifying odds manager: {e}")
    
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

# ======================= MAIN TEST FUNCTION =======================

if __name__ == "__main__":
    # Simple test
    print("=== Testing the Agentic Bookie System ===")
    
    # First, try the market creation flow
    print("\n1. Testing Market Creation:")
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
    
    # Next, try the odds update flow
    print("\n2. Testing Odds Management:")
    request = "Can you update the odds for all markets?"
    result = process_request(request)
    print(result["response"])
    print(f"Updated odds for {len(result['odds_updates'])} markets")
    
    # Print odds update details
    for i, update in enumerate(result.get('odds_updates', [])):
        print(f"\nUpdate {i+1}:")
        if 'error' not in update:
            market_address = update.get('market_address', 'Unknown')
            home_odds = update.get('home_odds', 'Unknown')
            away_odds = update.get('away_odds', 'Unknown')
            print(f"Market: {market_address}")
            print(f"New odds: Home {home_odds}, Away {away_odds}")
        else:
            print(f"Error: {update.get('error', 'Unknown error')}")