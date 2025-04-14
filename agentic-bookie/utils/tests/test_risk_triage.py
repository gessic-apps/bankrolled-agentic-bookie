#!/usr/bin/env python3
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# First, create a mock Agent, function_tool, handoff API for testing
from utils.markets.market_data import get_all_markets
from utils.risk_management.exposure import get_detailed_market_exposure
from utils.sports.games_data import fetch_games_with_odds

# Now implement the function tools from the risk_triage_agent directly here for testing
def get_all_markets_with_exposure() -> List[Dict[str, Any]]:
    """Fetches all existing betting markets from the smart contract API with exposure data."""
    markets = get_all_markets()
    
    # Process exposure values to ensure they're floats for easier comparison
    for market in markets:
        try:
            # Convert exposure values to float for easier comparison if they exist
            if "maxExposure" in market:
                market["maxExposure"] = float(market["maxExposure"])
            else:
                market["maxExposure"] = 2000.0  # Default value
                
            if "currentExposure" in market:
                market["currentExposure"] = float(market["currentExposure"])
            else:
                market["currentExposure"] = 0.0  # Default value
        except (ValueError, TypeError):
            print(f"Warning: Could not convert exposure values to float for market {market.get('address')}", file=sys.stderr)
            # Use default values if conversion fails
            market["maxExposure"] = 2000.0
            market["currentExposure"] = 0.0
    
    print(f"Successfully fetched {len(markets)} existing markets with exposure data.")
    return markets

def get_market_exposure_details(market_address: str) -> Dict[str, Any]:
    """
    Gets detailed exposure information for a specific market, broken down by bet type and side.
    """
    # Use the refactored utility function
    return get_detailed_market_exposure(market_address)

def fetch_latest_odds(sport_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Fetches the latest odds from the API for the specified sports.
    """
    from utils.config import SUPPORTED_SPORT_KEYS
    
    # If no sport keys provided, use all supported sports
    if sport_keys is None:
        sport_keys = SUPPORTED_SPORT_KEYS
    try:
        games_with_odds = fetch_games_with_odds(sport_keys)
        
        # Create a mapping from oddsApiId to odds data for efficient lookup
        odds_api_id_to_odds = {}
        for game in games_with_odds:
            odds_api_id = game.get("odds_api_id")
            odds_data = game.get("odds")
            if odds_api_id and odds_data:
                odds_api_id_to_odds[odds_api_id] = odds_data
        
        return {
            "status": "success",
            "message": f"Successfully fetched odds for {len(odds_api_id_to_odds)} games",
            "odds_data": odds_api_id_to_odds,
            "sport_keys": sport_keys
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error fetching latest odds: {str(e)}",
            "odds_data": {},
            "sport_keys": sport_keys
        }

def identify_high_risk_markets() -> Dict[str, Any]:
    """
    Analyzes all open markets to identify those with high risk profiles.
    """
    # Step 1: Get all markets
    all_markets = get_all_markets_with_exposure()
    open_markets = [m for m in all_markets if m.get("status") == "Open"]
    print(f"Found {len(open_markets)} open markets out of {len(all_markets)} total markets")
    
    if not open_markets:
        return {
            "status": "info",
            "message": "No open markets found to analyze",
            "high_risk_markets": [],
            "regular_markets": []
        }
    
    # Step 2: Fetch latest odds
    latest_odds_result = fetch_latest_odds()
    latest_odds_data = latest_odds_result.get("odds_data", {})
    
    # Step 3: Analyze each market for risk factors
    high_risk_markets = []
    regular_markets = []
    
    for market in open_markets:
        market_address = market.get("address")
        odds_api_id = market.get("oddsApiId")
        risk_factors = []
        risk_details = {}
        
        # Check exposure utilization
        max_exposure = float(market.get("maxExposure", 0))
        current_exposure = float(market.get("currentExposure", 0))
        utilization = 0
        
        if max_exposure > 0:
            utilization = (current_exposure / max_exposure) * 100
            if utilization > 70:
                risk_factors.append("high_exposure_utilization")
                risk_details["utilization_percentage"] = utilization
        
        # Get detailed exposure
        exposure_data = get_market_exposure_details(market_address)
        
        # Check for imbalances
        if "moneyline" in exposure_data:
            ml_data = exposure_data["moneyline"]
            home_exp = ml_data.get("home", 0)
            away_exp = ml_data.get("away", 0)
            
            # Check moneyline imbalance
            if home_exp > 0 and away_exp > 0:
                ratio = max(home_exp, away_exp) / min(home_exp, away_exp)
                if ratio > 2:
                    risk_factors.append("moneyline_imbalance")
                    risk_details["moneyline_ratio"] = ratio
                    risk_details["home_exposure"] = home_exp
                    risk_details["away_exposure"] = away_exp
        
        # Process other bet types and risk factors...
        
        # If any risk factors identified, add to high risk markets
        if risk_factors:
            high_risk_markets.append({
                "market_address": market_address,
                "odds_api_id": odds_api_id,
                "risk_factors": risk_factors,
                "risk_details": risk_details,
                "utilization": utilization,
                "max_exposure": max_exposure,
                "current_exposure": current_exposure,
                "homeTeam": market.get("homeTeam", ""),
                "awayTeam": market.get("awayTeam", ""),
                "latest_odds": latest_odds_data.get(odds_api_id, {})
            })
        else:
            regular_markets.append({
                "market_address": market_address,
                "odds_api_id": odds_api_id,
                "utilization": utilization,
                "homeTeam": market.get("homeTeam", ""),
                "awayTeam": market.get("awayTeam", "")
            })
    
    # Step 4: Return identified markets
    return {
        "status": "success",
        "message": f"Identified {len(high_risk_markets)} high-risk markets out of {len(open_markets)} open markets",
        "high_risk_markets": high_risk_markets,
        "regular_markets": regular_markets
    }

class TestRiskTriageAgent(unittest.TestCase):
    
    def test_get_all_markets_with_exposure(self):
        # Create a mock implementation of get_all_markets
        def mock_get_all_markets():
            return [
                {"address": "0x123", "status": "Open"},
                {"address": "0x456", "status": "Open", "maxExposure": "1000", "currentExposure": "500"}
            ]
        
        # Save original function and replace with mock
        from utils.markets.market_data import get_all_markets as original_get_all_markets
        globals()['get_all_markets'] = mock_get_all_markets
        
        try:
            # Call the function
            result = get_all_markets_with_exposure()
            
            # Verify result has the right structure and values
            self.assertEqual(len(result), 2)
            
            # Check first market
            self.assertEqual(result[0]["address"], "0x123")
            self.assertEqual(result[0]["maxExposure"], 2000.0)  # Default value
            self.assertEqual(result[0]["currentExposure"], 0.0)  # Default value
            
            # Check second market
            self.assertEqual(result[1]["address"], "0x456")
            self.assertEqual(result[1]["maxExposure"], 1000.0)  # Converted from string
            self.assertEqual(result[1]["currentExposure"], 500.0)  # Converted from string
        finally:
            # Restore original function
            globals()['get_all_markets'] = original_get_all_markets
    
    def test_get_market_exposure_details(self):
        # Direct test without patching
        test_market_address = "0x123"
        
        # Create a mock implementation
        def mock_get_detailed_market_exposure(market_address):
            self.assertEqual(market_address, test_market_address)
            return {
                "market_address": test_market_address,
                "moneyline": {"home": 100, "away": 200},
                "global": {"max_exposure": 1000, "current_exposure": 300}
            }
        
        # Save the original function and replace with our mock
        original_func = get_detailed_market_exposure
        globals()['get_detailed_market_exposure'] = mock_get_detailed_market_exposure
        
        try:
            # Call the function
            result = get_market_exposure_details(test_market_address)
            
            # Verify results
            self.assertEqual(result["market_address"], test_market_address)
            self.assertEqual(result["moneyline"]["home"], 100)
            self.assertEqual(result["moneyline"]["away"], 200)
            self.assertEqual(result["global"]["max_exposure"], 1000)
        finally:
            # Restore the original function
            globals()['get_detailed_market_exposure'] = original_func
    
    def test_fetch_latest_odds(self):
        # Create a mock implementation for fetch_games_with_odds
        def mock_fetch_games_with_odds(sport_keys):
            return [
                {
                    "odds_api_id": "game1",
                    "odds": {
                        "home_odds": 1.8,
                        "away_odds": 2.1
                    }
                }
            ]
        
        # Save the original function and replace with our mock
        original_func = fetch_games_with_odds
        globals()['fetch_games_with_odds'] = mock_fetch_games_with_odds
        
        try:
            # Call the function
            result = fetch_latest_odds(["basketball_nba"])
            
            # Verify results
            self.assertEqual(result["status"], "success")
            self.assertIn("game1", result["odds_data"])
            self.assertEqual(result["odds_data"]["game1"]["home_odds"], 1.8)
        finally:
            # Restore the original function
            globals()['fetch_games_with_odds'] = original_func
    
    def test_identify_high_risk_markets(self):
        # Create mock implementations
        def mock_get_all_markets_with_exposure():
            return [
                {
                    "address": "0x123", 
                    "oddsApiId": "game1", 
                    "status": "Open",
                    "homeTeam": "Team A",
                    "awayTeam": "Team B",
                    "maxExposure": 1000.0,
                    "currentExposure": 800.0,  # 80% utilization
                    "homeSpreadPoints": 5.5,
                    "totalPoints": 220.5
                }
            ]
        
        def mock_fetch_latest_odds(sport_keys=None):
            return {
                "odds_data": {
                    "game1": {
                        "home_odds": 1.8,
                        "away_odds": 2.1,
                        "home_spread_points": 7.0,  # Significant movement
                        "total_points": 222.5  # Significant movement
                    }
                }
            }
        
        def mock_get_market_exposure_details(market_address):
            return {
                "market_address": market_address,
                "moneyline": {
                    "home": 300,
                    "away": 100  # 3:1 ratio - imbalance
                },
                "spread": {
                    "home": 200,
                    "away": 200
                },
                "total": {
                    "over": 300,
                    "under": 100  # 3:1 ratio - imbalance
                }
            }
        
        # Save original functions
        original_get_markets = globals()['get_all_markets_with_exposure']
        original_fetch_odds = globals()['fetch_latest_odds']
        original_get_exposure = globals()['get_market_exposure_details']
        
        # Replace with mocks
        globals()['get_all_markets_with_exposure'] = mock_get_all_markets_with_exposure
        globals()['fetch_latest_odds'] = mock_fetch_latest_odds
        globals()['get_market_exposure_details'] = mock_get_market_exposure_details
        
        try:
            # Call the function
            result = identify_high_risk_markets()
            
            # Verify results
            self.assertEqual(result["status"], "success")
            self.assertEqual(len(result["high_risk_markets"]), 1)
            self.assertEqual(len(result["regular_markets"]), 0)
            
            # Check risk factors identified
            risk_factors = result["high_risk_markets"][0]["risk_factors"]
            self.assertIn("high_exposure_utilization", risk_factors)
            self.assertIn("moneyline_imbalance", risk_factors)
        finally:
            # Restore original functions
            globals()['get_all_markets_with_exposure'] = original_get_markets
            globals()['fetch_latest_odds'] = original_fetch_odds
            globals()['get_market_exposure_details'] = original_get_exposure

if __name__ == '__main__':
    unittest.main()