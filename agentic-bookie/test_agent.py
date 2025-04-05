#!/usr/bin/env python3
"""
Test script for the NBA betting agent system
"""
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Import the process_request function
from agents.agentGroup import process_request

def main():
    if len(sys.argv) > 1:
        # Use command line argument as request
        request = " ".join(sys.argv[1:])
    else:
        # Default request
        request = "Can you create markets for today's NBA games?"
    
    print(f"Processing request: {request}")
    print("-" * 50)
    
    try:
        result = process_request(request)
        
        print("Agent response:")
        print(result["response"])
        print("-" * 50)
        
        print(f"Markets created: {len(result['created_markets'])}")
        for i, market in enumerate(result['created_markets']):
            print(f"\nMarket {i+1}:")
            if 'market' in market and market['market']:
                address = market['market'].get('address', 'Unknown')
                home_team = market['market'].get('homeTeam', 'Unknown')
                away_team = market['market'].get('awayTeam', 'Unknown')
                print(f"Address: {address}")
                print(f"Teams: {home_team} vs {away_team}")
            else:
                print(f"Error: {market.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"Error running agent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()