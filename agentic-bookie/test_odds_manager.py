#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import dotenv

# Add the project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Load environment variables
dotenv.load_dotenv()

# Check for OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("OPENAI_API_KEY not found in environment variables")
    sys.exit(1)

from agents.agentGroup import process_odds_update_request, AgentContext

def test_odds_manager():
    """Test the odds manager agent's ability to update odds for markets"""
    print("🏀 Testing Odds Manager Agent...")
    
    # Create a context
    context = AgentContext(user_request="Update odds for all markets")
    
    # Process a request through the odds manager
    result = process_odds_update_request(context)
    
    # Print the results
    print("\n============= Odds Manager Response =============")
    print(result["response"])
    print(f"Updated odds for {len(result.get('odds_updates', []))} markets")
    
    # Print market details if any were updated
    if result.get('odds_updates'):
        for i, update in enumerate(result['odds_updates']):
            print(f"\nUpdate {i+1}:")
            if 'error' not in update:
                market_address = update.get('market_address', 'Unknown')
                home_odds = update.get('home_odds', 'Unknown')
                away_odds = update.get('away_odds', 'Unknown')
                print(f"Market: {market_address}")
                print(f"New odds: Home {home_odds}, Away {away_odds}")
            else:
                print(f"Error: {update.get('error', 'Unknown error')}")

if __name__ == "__main__":
    test_odds_manager()