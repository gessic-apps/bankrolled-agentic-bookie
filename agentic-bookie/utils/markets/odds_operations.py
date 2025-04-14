#!/usr/bin/env python3
import sys
from typing import List, Dict, Any

from ..config import SUPPORTED_SPORT_KEYS
from ..sports.games_data import fetch_games_with_odds
from ..markets.market_data import get_all_markets
from ..markets.odds_management import update_odds_for_multiple_markets, check_market_odds

def fetch_and_update_all_markets() -> Dict[str, Any]:
    """Fetches games with odds, gets existing markets, and updates all market odds in a single operation."""
    # Step 1: Fetch games with odds for all supported sports
    print("Fetching games with odds for all supported sports...")
    games_with_odds = fetch_games_with_odds(SUPPORTED_SPORT_KEYS)
    print(f"Found {len(games_with_odds)} games with complete odds data")
    
    if not games_with_odds:
        return {
            "status": "error", 
            "message": "No games with odds found from The Odds API",
            "total_markets_with_odds": 0,
            "total_markets_updated": 0
        }
    
    # Step 2: Create a mapping from odds_api_id to odds data for efficient lookup
    odds_api_id_to_odds = {
        game["odds_api_id"]: game["odds"] 
        for game in games_with_odds
    }
    print(f"Created mapping for {len(odds_api_id_to_odds)} games by odds API ID")
    
    # Step 3: Get existing markets directly from the API
    print("Fetching existing markets from platform API...")
    existing_markets = get_all_markets()
    print(f"Found {len(existing_markets)} existing markets")
    
    if not existing_markets:
        return {
            "status": "error", 
            "message": "No existing markets found from the platform API",
            "total_markets_with_odds": len(odds_api_id_to_odds),
            "total_markets_updated": 0
        }
    
    # Step 4: Match markets with odds and prepare update data
    markets_for_update = []
    markets_with_existing_odds = 0
    
    for market in existing_markets:
        odds_api_id = market.get("oddsApiId")
        market_address = market.get("address")
        
        if not (odds_api_id and market_address):
            print(f"Warning: Market missing oddsApiId or address: {market}")
            continue
            
        # First check if this market already has odds
        odds_status = check_market_odds(market_address)
        if odds_status.get("has_odds"):
            markets_with_existing_odds += 1
            print(f"Skipping market {market_address} as it already has odds set")
            continue
            
        # Check if we have odds for this market
        if odds_api_id in odds_api_id_to_odds:
            odds_data = odds_api_id_to_odds[odds_api_id]
            
            # Create a market data entry with all required fields
            market_data = {
                "market_address": market_address,
                "home_odds": odds_data.get("home_odds"),
                "away_odds": odds_data.get("away_odds"),
                "draw_odds": odds_data.get("draw_odds"),
                "home_spread_points": odds_data.get("home_spread_points"),
                "home_spread_odds": odds_data.get("home_spread_odds"),
                "away_spread_odds": odds_data.get("away_spread_odds"),
                "total_points": odds_data.get("total_points"),
                "over_odds": odds_data.get("over_odds"),
                "under_odds": odds_data.get("under_odds")
            }
            
            # Ensure all required odds data is present
            if all(v is not None for k, v in market_data.items() if k != "draw_odds"):
                markets_for_update.append(market_data)
            else:
                print(f"Warning: Incomplete odds data for market {market_address} (odds API ID: {odds_api_id})")
    
    # Step 5: Update all markets with available odds data
    print(f"Preparing to update {len(markets_for_update)} markets with available odds data")
    
    if not markets_for_update:
        return {
            "status": "info",
            "message": f"No new markets need odds updates. {markets_with_existing_odds} markets already have odds set.",
            "total_markets_with_odds": len(odds_api_id_to_odds),
            "total_existing_markets": len(existing_markets),
            "total_markets_with_existing_odds": markets_with_existing_odds,
            "total_new_markets_updated": 0
        }
    
    # Perform the batch update
    update_results = update_odds_for_multiple_markets(markets_for_update)
    
    # Step 6: Return combined result summary
    return {
        "status": "success",
        "message": f"Set odds for {update_results['successful_updates']} new markets. Skipped {markets_with_existing_odds} markets that already had odds.",
        "total_markets_with_odds": len(odds_api_id_to_odds),
        "total_existing_markets": len(existing_markets),
        "total_markets_with_existing_odds": markets_with_existing_odds,
        "total_new_markets_matched": len(markets_for_update),
        "total_new_markets_updated": update_results["successful_updates"],
        "failed_updates": update_results["failed_updates"],
        "detailed_results": update_results["results"]
    }