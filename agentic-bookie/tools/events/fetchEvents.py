#!/usr/bin/env python3
import os
import requests
from typing import List, Dict, Any, TypedDict, Optional
from datetime import datetime
import dotenv
import sys
from pathlib import Path

# Add the project root to path to find the .env file
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Load environment variables
dotenv.load_dotenv(dotenv_path=str(project_root / '.env'))

class TeamInfo(TypedDict):
    id: str
    name: str
    abbreviation: str
    
class GameEvent(TypedDict):
    id: str
    start_time: int  # Unix timestamp
    home_team: TeamInfo
    away_team: TeamInfo
    status: str
    league: str

def fetch_nba_games_today() -> List[GameEvent]:
    """
    Fetches today's NBA games from the sports API.
    
    Returns:
        List[GameEvent]: A list of NBA games scheduled for today
    """
    api_key = os.getenv("SPORTS_API_KEY")
    if not api_key:
        raise ValueError("SPORTS_API_KEY not found in environment variables")
    
    # Get today's date in the required format
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Fetching NBA games for {today}")
    
    # API endpoint for NBA games
    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/scores"
    params = {
        "apiKey": api_key
    }
    
    try:
        response = requests.get(url, params=params)
        # Print response for debugging
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        
        response.raise_for_status()
        
        games_data = response.json()
        result: List[GameEvent] = []
        
        for game in games_data:
            # Convert ISO timestamp to Unix timestamp
            start_time_iso = game.get("commence_time")
            if not start_time_iso:
                continue
                
            start_time = int(datetime.fromisoformat(start_time_iso.replace("Z", "+00:00")).timestamp())
            
            # Extract team names - API returns home_team and away_team as strings
            home_team_name = game.get("home_team", "")
            away_team_name = game.get("away_team", "")
            
            if not home_team_name or not away_team_name:
                continue
                
            # Extract abbreviations from team names (simplified approach)
            home_abbr = ''.join(word[0] for word in home_team_name.split()[:2])
            away_abbr = ''.join(word[0] for word in away_team_name.split()[:2])
                
            game_event: GameEvent = {
                "id": game.get("id", ""),
                "start_time": start_time,
                "home_team": {
                    "id": game.get("id", "") + "_home",  # Generate an ID since API doesn't provide one
                    "name": home_team_name,
                    "abbreviation": home_abbr.upper()
                },
                "away_team": {
                    "id": game.get("id", "") + "_away",  # Generate an ID since API doesn't provide one
                    "name": away_team_name, 
                    "abbreviation": away_abbr.upper()
                },
                "status": "scheduled" if not game.get("completed", False) else "completed",
                "league": "NBA"
            }
            
            result.append(game_event)

        return result
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching NBA games: {e}")
        return []

if __name__ == "__main__":
    # Test the function
    games = fetch_nba_games_today()
    print(f"Found {len(games)} NBA games today:")
    print(games)
    # for game in games:
    #     print(f"{game['away_team']['name']} @ {game['home_team']['name']} - {datetime.fromtimestamp(game['start_time'])}")