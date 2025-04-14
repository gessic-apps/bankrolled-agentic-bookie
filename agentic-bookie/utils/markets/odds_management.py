#!/usr/bin/env python3
import sys
from typing import Dict, Any, List, Optional
from typing_extensions import TypedDict

from ..api.client import api_post, api_get
from ..config import API_URL

class OddsData(TypedDict, total=False):
    market_address: str
    home_odds: float
    away_odds: float
    draw_odds: Optional[float]
    home_spread_points: float
    home_spread_odds: float
    away_spread_odds: float
    total_points: float
    over_odds: float
    under_odds: float

class BatchUpdateResult(TypedDict):
    status: str
    total_markets: int
    successful_updates: int
    failed_updates: int
    results: List[Dict[str, Any]]

def update_odds_for_market(
    market_address: str,
    home_odds: float,
    away_odds: float,
    draw_odds: Optional[float],
    home_spread_points: float,
    home_spread_odds: float,
    away_spread_odds: float,
    total_points: float,
    over_odds: float,
    under_odds: float
) -> Dict[str, Any]:
    """Updates all odds types (moneyline including draw, spread, total) for a specific market."""
    # Convert decimal floats/points to integer format
    # Odds: decimal * 1000
    # Points: decimal * 10 (for spreads and totals line)
    try:
        payload = {
            "homeOdds": int(home_odds * 1000),
            "awayOdds": int(away_odds * 1000),
            "drawOdds": int(draw_odds * 1000) if draw_odds is not None and draw_odds >= 1.0 else 0,
            "homeSpreadPoints": int(home_spread_points * 10),
            "homeSpreadOdds": int(home_spread_odds * 1000),
            "awaySpreadOdds": int(away_spread_odds * 1000),
            "totalPoints": int(total_points * 10),
            "overOdds": int(over_odds * 1000),
            "underOdds": int(under_odds * 1000)
        }
    except (ValueError, TypeError) as e:
        error_message = f"Error converting odds/points to integer format: {e}. Input: home_odds={home_odds}, away_odds={away_odds}, draw_odds={draw_odds}, home_spread_points={home_spread_points}, home_spread_odds={home_spread_odds}, away_spread_odds={away_spread_odds}, total_points={total_points}, over_odds={over_odds}, under_odds={under_odds}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}

    try:
        endpoint = f"/api/market/{market_address}/update-odds"
        result = api_post(endpoint, payload)
        print(f"Successfully updated full odds for market {market_address}. Response: {result}")
        # Report success with the original decimal odds/points for clarity
        return {
            "status": "success",
            "market_address": market_address,
            "decimal_odds_set": {
                "home": home_odds, "away": away_odds, "draw": draw_odds,
                "home_spread_points": home_spread_points, "home_spread_odds": home_spread_odds, "away_spread_odds": away_spread_odds,
                "total_points": total_points, "over_odds": over_odds, "under_odds": under_odds
            }
        }
    except Exception as e:
        error_message = f"Error updating odds for market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}

def update_odds_for_multiple_markets(markets_data: List[OddsData]) -> BatchUpdateResult:
    """Updates odds for multiple markets at once."""
    results = []
    print(f"Updating odds for {len(markets_data)} markets")
    
    for market_data in markets_data:
        try:
            # Extract market info
            market_address = market_data.get("market_address")
            if not market_address:
                results.append({"status": "error", "message": "Missing market_address in market data"})
                continue
                
            # Extract odds data
            home_odds = market_data.get("home_odds")
            away_odds = market_data.get("away_odds")
            draw_odds = market_data.get("draw_odds")
            home_spread_points = market_data.get("home_spread_points")
            home_spread_odds = market_data.get("home_spread_odds")
            away_spread_odds = market_data.get("away_spread_odds")
            total_points = market_data.get("total_points")
            over_odds = market_data.get("over_odds")
            under_odds = market_data.get("under_odds")
            
            # Validate essential data
            if any(v is None for v in [home_odds, away_odds, home_spread_points, home_spread_odds, 
                                      away_spread_odds, total_points, over_odds, under_odds]):
                results.append({
                    "status": "error", 
                    "message": "Missing required odds data",
                    "market_address": market_address
                })
                continue
                
            # Update the market using the single market update function
            result = update_odds_for_market(
                market_address=market_address,
                home_odds=home_odds,
                away_odds=away_odds,
                draw_odds=draw_odds,
                home_spread_points=home_spread_points,
                home_spread_odds=home_spread_odds,
                away_spread_odds=away_spread_odds,
                total_points=total_points,
                over_odds=over_odds,
                under_odds=under_odds
            )
            
            results.append(result)
            
        except Exception as e:
            error_message = f"An unexpected error occurred processing market: {e}"
            print(error_message, file=sys.stderr)
            results.append({
                "status": "error", 
                "message": error_message,
                "market_address": market_data.get("market_address", "unknown")
            })
    
    summary = {
        "status": "completed",
        "total_markets": len(markets_data),
        "successful_updates": sum(1 for r in results if r.get("status") == "success"),
        "failed_updates": sum(1 for r in results if r.get("status") == "error"),
        "results": results
    }
    
    print(f"Completed batch update of {summary['total_markets']} markets: {summary['successful_updates']} successful, {summary['failed_updates']} failed")
    return summary

def check_market_odds(market_address: str) -> Dict[str, Any]:
    """Checks if a specific market already has odds set via the API."""
    try:
        market_data = api_get(f"/api/market/{market_address}")

        # Check if ALL essential odds fields exist and are likely set (e.g., not 0 or null)
        # Check moneyline odds
        has_home_odds = market_data.get("homeOdds") is not None and market_data.get("homeOdds") != 0
        has_away_odds = market_data.get("awayOdds") is not None and market_data.get("awayOdds") != 0
        
        # Check spread odds
        has_home_spread_odds = market_data.get("homeSpreadOdds") is not None and market_data.get("homeSpreadOdds") != 0
        has_away_spread_odds = market_data.get("awaySpreadOdds") is not None and market_data.get("awaySpreadOdds") != 0
        has_home_spread_points = market_data.get("homeSpreadPoints") is not None
        
        # Check total odds
        has_over_odds = market_data.get("overOdds") is not None and market_data.get("overOdds") != 0
        has_under_odds = market_data.get("underOdds") is not None and market_data.get("underOdds") != 0
        has_total_points = market_data.get("totalPoints") is not None
        
        # Only consider odds as set if ALL required odds are present
        # Note: We don't check for drawOdds since that's only relevant for soccer
        has_moneyline = has_home_odds and has_away_odds
        has_spreads = has_home_spread_odds and has_away_spread_odds and has_home_spread_points
        has_totals = has_over_odds and has_under_odds and has_total_points
        
        # A market has complete odds only if all three types are set
        has_odds = has_moneyline and has_spreads and has_totals
        
        print(f"Market {market_address} odds status: {'Set' if has_odds else 'Not Set'}")
        return {
            "status": "success",
            "market_address": market_address,
            "has_odds": has_odds,
            # Optionally return the odds if found
            "odds_data": {
                "homeOdds": market_data.get("homeOdds"),
                "awayOdds": market_data.get("awayOdds"),
                "drawOdds": market_data.get("drawOdds"),
                "homeSpreadPoints": market_data.get("homeSpreadPoints"),
                "homeSpreadOdds": market_data.get("homeSpreadOdds"),
                "awaySpreadOdds": market_data.get("awaySpreadOdds"),
                "totalPoints": market_data.get("totalPoints"),
                "overOdds": market_data.get("overOdds"),
                "underOdds": market_data.get("underOdds")
            } if has_odds else None
        }
    except Exception as e:
        error_message = f"Error checking odds for market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address, "has_odds": None}