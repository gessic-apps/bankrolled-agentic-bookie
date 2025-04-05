import requests
import json

def create_market(home_team, away_team, game_timestamp, home_odds=None, away_odds=None):
    """
    Creates a new betting market by calling the smart contract API
    
    Args:
        home_team (str): Name of the home team
        away_team (str): Name of the away team
        game_timestamp (int): Unix timestamp of the game start time
        home_odds (int, optional): Home team odds in 3-decimal format (e.g. 2000 = 2.000)
        away_odds (int, optional): Away team odds in 3-decimal format (e.g. 1800 = 1.800)
    
    Returns:
        dict: API response with market details
    """
    url = "http://localhost:3000/api/market/create"
    
    payload = {
        "homeTeam": home_team,
        "awayTeam": away_team,
        "gameTimestamp": game_timestamp
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