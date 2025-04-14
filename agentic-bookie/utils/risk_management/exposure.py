#!/usr/bin/env python3
import sys
import requests
from typing import Dict, Any, Optional, List

from ..config import API_URL

def get_detailed_market_exposure(market_address: str) -> Dict[str, Any]:
    """
    Gets detailed exposure information for a specific market, broken down by bet type and side.
    
    Args:
        market_address (str): The blockchain address of the market
        
    Returns:
        dict: Detailed exposure information organized by bet type and side
    """
    if not API_URL:
        print("Error: Cannot get detailed market exposure, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}
    
    try:
        result = get_market_exposure_by_type(market_address)
        
        if "error" in result:
            # Try to get basic market info as a fallback
            try:
                url = f"{API_URL}/api/market/{market_address}"
                print(f"Falling back to basic market data from: {url}")
                response = requests.get(url)
                response.raise_for_status()
                market_data = response.json()
                
                # Create a simplified exposure model from the general market data
                max_exposure = float(market_data.get("maxExposure", 0))
                current_exposure = float(market_data.get("currentExposure", 0))
                
                # Calculate a utilization percentage
                utilization = 0
                if max_exposure > 0:
                    utilization = (current_exposure / max_exposure) * 100
                
                simplified_result = {
                    "global": {
                        "max_exposure": max_exposure,
                        "current_exposure": current_exposure,
                        "utilization_percentage": utilization
                    },
                    "warning": "Detailed exposure breakdown not available - showing global values only",
                    "raw_market_data": market_data
                }
                
                print(f"Created simplified exposure model for market {market_address}: utilization {utilization:.1f}%")
                return simplified_result
            except Exception as e:
                print(f"Error fetching basic market data: {e}", file=sys.stderr)
                return result  # Return the original error
        
        print(f"Detailed exposure for market {market_address} fetched successfully")
        return result
    except Exception as e:
        error_message = f"Unexpected error in get_detailed_market_exposure: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}

def set_specific_bet_type_limit(
    market_address: str,
    bet_type: str,
    side: str,
    limit: int
) -> Dict[str, Any]:
    """
    Sets an exposure limit for a specific bet type and side within a market.
    
    Args:
        market_address (str): The blockchain address of the market
        bet_type (str): The type of bet ('moneyline', 'spread', 'total', 'draw')
        side (str): The side of the bet ('home', 'away', 'over', 'under', 'draw')
        limit (int): The exposure limit to set
        
    Returns:
        dict: Result of the operation
    """
    if not API_URL:
        print("Error: Cannot set bet type limit, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}
    
    print(f"Setting limit for {bet_type}/{side} to {limit} on market {market_address}")
    
    try:
        # Construct API endpoint based on bet type and side
        endpoint = None
        if bet_type == "moneyline":
            if side == "home":
                endpoint = "home-moneyline-limit"
            elif side == "away":
                endpoint = "away-moneyline-limit"
            elif side == "draw":
                endpoint = "draw-limit"
        elif bet_type == "spread":
            if side == "home":
                endpoint = "home-spread-limit"
            elif side == "away":
                endpoint = "away-spread-limit"
        elif bet_type == "total":
            if side == "over":
                endpoint = "over-limit"
            elif side == "under":
                endpoint = "under-limit"
        
        if not endpoint:
            return {"status": "error", "message": f"Invalid bet type ({bet_type}) or side ({side}) combination"}
        
        # Make API request
        url = f"{API_URL}/api/market/{market_address}/{endpoint}"
        payload = {"limit": limit}
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        return {
            "status": "success",
            "market_address": market_address,
            "bet_type": bet_type,
            "side": side,
            "limit": limit,
            "result": result
        }
    except requests.exceptions.RequestException as e:
        error_message = f"Request error setting bet type limit: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message}
    except Exception as e:
        error_message = f"Unexpected error in set_specific_bet_type_limit: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message}

def get_market_exposure_by_type(market_address: str) -> Dict[str, Any]:
    """
    Gets detailed breakdown of exposure by bet type for a specific market.
    
    Args:
        market_address (str): The blockchain address of the market
        
    Returns:
        dict: Detailed exposure by bet type
    """
    if not API_URL:
        print("Error: Cannot get market exposure by type, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}
    
    try:
        url = f"{API_URL}/api/market/{market_address}/exposure"
        response = requests.get(url)
        response.raise_for_status()
        exposure_data = response.json()
        
        # Normalize the data structure
        result = {
            "market_address": market_address,
            "moneyline": {
                "home": exposure_data.get("homeMoneylineExposure", 0),
                "away": exposure_data.get("awayMoneylineExposure", 0),
                "draw": exposure_data.get("drawExposure", 0),
            },
            "spread": {
                "home": exposure_data.get("homeSpreadExposure", 0),
                "away": exposure_data.get("awaySpreadExposure", 0),
            },
            "total": {
                "over": exposure_data.get("overExposure", 0),
                "under": exposure_data.get("underExposure", 0),
            },
            "global": {
                "current_exposure": exposure_data.get("currentExposure", 0),
                "max_exposure": exposure_data.get("maxExposure", 0),
            }
        }
        
        # Calculate utilization percentage
        if result["global"]["max_exposure"] > 0:
            result["global"]["utilization_percentage"] = (
                result["global"]["current_exposure"] / result["global"]["max_exposure"] * 100
            )
        else:
            result["global"]["utilization_percentage"] = 0
        
        # Calculate imbalance ratios
        moneyline_sum = result["moneyline"]["home"] + result["moneyline"]["away"]
        if moneyline_sum > 0:
            result["moneyline"]["home_percentage"] = result["moneyline"]["home"] / moneyline_sum * 100
            result["moneyline"]["away_percentage"] = result["moneyline"]["away"] / moneyline_sum * 100
            # Calculate imbalance ratio (higher value means more imbalanced)
            if result["moneyline"]["home"] > 0 and result["moneyline"]["away"] > 0:
                ratio = max(result["moneyline"]["home"], result["moneyline"]["away"]) / min(result["moneyline"]["home"], result["moneyline"]["away"])
                result["moneyline"]["imbalance_ratio"] = ratio
            else:
                result["moneyline"]["imbalance_ratio"] = 999  # Arbitrary high value for division by zero
        
        # Similar calculations for spread and totals
        spread_sum = result["spread"]["home"] + result["spread"]["away"]
        if spread_sum > 0:
            result["spread"]["home_percentage"] = result["spread"]["home"] / spread_sum * 100
            result["spread"]["away_percentage"] = result["spread"]["away"] / spread_sum * 100
            if result["spread"]["home"] > 0 and result["spread"]["away"] > 0:
                ratio = max(result["spread"]["home"], result["spread"]["away"]) / min(result["spread"]["home"], result["spread"]["away"])
                result["spread"]["imbalance_ratio"] = ratio
            else:
                result["spread"]["imbalance_ratio"] = 999
        
        total_sum = result["total"]["over"] + result["total"]["under"]
        if total_sum > 0:
            result["total"]["over_percentage"] = result["total"]["over"] / total_sum * 100
            result["total"]["under_percentage"] = result["total"]["under"] / total_sum * 100
            if result["total"]["over"] > 0 and result["total"]["under"] > 0:
                ratio = max(result["total"]["over"], result["total"]["under"]) / min(result["total"]["over"], result["total"]["under"])
                result["total"]["imbalance_ratio"] = ratio
            else:
                result["total"]["imbalance_ratio"] = 999
        
        return result
    except requests.exceptions.RequestException as e:
        error_message = f"Request error getting market exposure: {e}"
        print(error_message, file=sys.stderr)
        return {"error": error_message}
    except Exception as e:
        error_message = f"Unexpected error in get_market_exposure_by_type: {e}"
        print(error_message, file=sys.stderr)
        return {"error": error_message}

def set_market_exposure_limits(
    market_address: str,
    home_moneyline_limit: Optional[int] = None,
    away_moneyline_limit: Optional[int] = None,
    draw_limit: Optional[int] = None,
    home_spread_limit: Optional[int] = None,
    away_spread_limit: Optional[int] = None,
    over_limit: Optional[int] = None,
    under_limit: Optional[int] = None
) -> Dict[str, Any]:
    """Sets specific exposure limits for various bet types within a market. Only provided limits will be updated."""
    if not API_URL:
        print("Error: Cannot set exposure limits, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}

    payload = {}
    if home_moneyline_limit is not None: payload["homeMoneylineLimit"] = home_moneyline_limit
    if away_moneyline_limit is not None: payload["awayMoneylineLimit"] = away_moneyline_limit
    if draw_limit is not None: payload["drawLimit"] = draw_limit
    if home_spread_limit is not None: payload["homeSpreadLimit"] = home_spread_limit
    if away_spread_limit is not None: payload["awaySpreadLimit"] = away_spread_limit
    if over_limit is not None: payload["overLimit"] = over_limit
    if under_limit is not None: payload["underLimit"] = under_limit

    if not payload:
        return {"status": "warning", "message": "No limits provided to set.", "market_address": market_address}

    try:
        url = f"{API_URL}/api/market/{market_address}/exposure-limits"
        print(f"Attempting to set exposure limits: POST {url} with payload: {payload}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Successfully set exposure limits for market {market_address}. Response: {result}")
        return {
            "status": "success",
            "market_address": market_address,
            "limits_set": payload,
            "result": result
        }
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error setting exposure limits for market {market_address}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error setting exposure limits for market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except Exception as e:
         error_message = f"An unexpected error occurred in set_market_exposure_limits: {e}"
         print(error_message, file=sys.stderr)
         return {"status": "error", "message": error_message, "market_address": market_address}

if __name__ == "__main__":
    # Test the functions
    import json
    
    # Test market address
    test_market_address = "0x1234567890abcdef1234567890abcdef12345678"
    
    # Test get_detailed_market_exposure
    print("Testing get_detailed_market_exposure...")
    result = get_detailed_market_exposure(test_market_address)
    print(json.dumps(result, indent=2))
    
    # Test set_specific_bet_type_limit
    print("\nTesting set_specific_bet_type_limit...")
    result = set_specific_bet_type_limit(test_market_address, "moneyline", "home", 1000)
    print(json.dumps(result, indent=2))
    
    # Test set_market_exposure_limits
    print("\nTesting set_market_exposure_limits...")
    result = set_market_exposure_limits(
        test_market_address, 
        home_moneyline_limit=1000, 
        away_moneyline_limit=1000
    )
    print(json.dumps(result, indent=2))