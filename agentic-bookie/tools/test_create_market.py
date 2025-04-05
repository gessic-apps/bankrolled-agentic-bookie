#!/usr/bin/env python3
import sys
import json
import time
from createMarket import create_market

def main():
    # Default test values
    home_team = "Lakers"
    away_team = "Warriors"
    # Set game timestamp to 24 hours from now
    game_timestamp = int(time.time()) + 86400
    # home_odds = 2000  # 2.000 odds
    # away_odds = 1800  # 1.800 odds
    
    # Override with command line arguments if provided
    if len(sys.argv) > 1:
        home_team = sys.argv[1]
    if len(sys.argv) > 2:
        away_team = sys.argv[2]
    if len(sys.argv) > 3:
        game_timestamp = int(sys.argv[3])
    if len(sys.argv) > 4:
        home_odds = int(sys.argv[4])
    if len(sys.argv) > 5:
        away_odds = int(sys.argv[5])
    
    print(f"Creating market: {home_team} vs {away_team}")
    print(f"Game timestamp: {game_timestamp}")
    # print(f"Home odds: {home_odds/1000:.3f}, Away odds: {away_odds/1000:.3f}")
    
    # Call the create_market function
    # result = create_market(home_team, away_team, game_timestamp, home_odds, away_odds)
    result = create_market(home_team, away_team, game_timestamp)
    
    # Print the result
    print("\nAPI Response:")
    print(json.dumps(result, indent=2))
    
    # Check if market was created successfully
    if result.get("success"):
        print("\nMarket created successfully!")
        print(f"Market address: {result['market']['address']}")
    else:
        print("\nFailed to create market.")
        print(f"Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()