import requests
import json
from typing import List, Dict, Any, Optional

def create_market(home_team, away_team, game_timestamp, odds_api_id, home_odds=None, away_odds=None):
    """
    Creates a new betting market by calling the smart contract API
    
    Args:
        home_team (str): Name of the home team
        away_team (str): Name of the away team
        game_timestamp (int): Unix timestamp of the game start time
        odds_api_id (str): The ID from the Odds API for this game
        home_odds (int, optional): Home team odds in 3-decimal format (e.g. 2000 = 2.000)
        away_odds (int, optional): Away team odds in 3-decimal format (e.g. 1800 = 1.800)
    
    Returns:
        dict: API response with market details
    """
    url = "http://localhost:3000/api/market/create"
    
    payload = {
        "homeTeam": home_team,
        "awayTeam": away_team,
        "gameTimestamp": game_timestamp,
        "oddsApiId": odds_api_id
    }
    
    # Add odds if provided
    if home_odds and away_odds:
        payload["homeOdds"] = int(home_odds)
        payload["awayOdds"] = int(away_odds)
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error creating market: {e}")
        return {"error": str(e)}

def get_all_markets() -> List[Dict[str, Any]]:
    """
    Fetches all existing betting markets from the API
    
    Returns:
        List of market objects with details including:
        - address: Contract address of the market
        - homeTeam: Name of home team
        - awayTeam: Name of away team
        - gameTimestamp: Unix timestamp of game start
        - oddsApiId: ID from odds API
        - homeOdds: Current home team odds (as integer with 3 decimal precision, e.g., 1941 for 1.941)
        - awayOdds: Current away team odds (as integer with 3 decimal precision, e.g., 1051 for 1.051)
        - gameStarted: Whether the game has started
        - gameEnded: Whether the game has ended
        - oddsSet: Whether odds have been set
        - isReadyForBetting: Whether market is ready for betting
    """
    url = "http://localhost:3000/api/markets"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching markets: {e}")
        return []

def update_market_odds(market_address: str, home_odds: int, away_odds: int) -> Dict[str, Any]:
    """
    Updates the odds for an existing market
    
    Args:
        market_address (str): The blockchain address of the market
        home_odds (int): Home team odds as integer with 3 decimal precision (e.g., 1941 for 1.941)
        away_odds (int): Away team odds as integer with 3 decimal precision (e.g., 1051 for 1.051)
        
    Note:
        Odds must be at least 1.000, represented as 1000 in the contract.
        Examples: 1.941 is stored as 1941, 10.51 is stored as 10510
    
    Returns:
        dict: API response with update details
    """
    url = f"http://localhost:3000/api/market/{market_address}/update-odds"
    
    payload = {
        "homeOdds": int(home_odds),
        "awayOdds": int(away_odds)
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error updating market odds: {e}")
        return {"error": str(e)}