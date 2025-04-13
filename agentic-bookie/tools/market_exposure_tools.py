import requests
import os
import sys
from typing import Dict, Any, List, Optional

def fetch_market_exposure_details(market_address: str, api_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetches detailed exposure information for a specific market, including 
    breakdown by bet type and side.
    
    Args:
        market_address (str): The blockchain address of the market
        api_url (str, optional): The base API URL (defaults to environment var or localhost)
        
    Returns:
        dict: Detailed exposure information for the market
    """
    if not api_url:
        api_url = os.getenv("API_URL", "http://localhost:3000")
    
    try:
        # First try the exposure-limits endpoint (based on Postman collection)
        url = f"{api_url}/api/market/{market_address}/exposure-limits"
        print(f"Attempting to fetch exposure details from: {url}")
        response = requests.get(url)
        response.raise_for_status()
        exposure_data = response.json()
        
        # If that doesn't work, try getting general market data
        if not exposure_data or "error" in exposure_data:
            url = f"{api_url}/api/market/{market_address}"
            print(f"Falling back to general market data: {url}")
            response = requests.get(url)
            response.raise_for_status()
            exposure_data = response.json()
            
        return exposure_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching market exposure details: {e}", file=sys.stderr)
        return {"error": str(e), "market_address": market_address}

def set_bet_type_exposure_limit(market_address: str, bet_type: str, side: str, 
                               limit: int, api_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Sets exposure limit for a specific bet type and side within a market.
    
    Args:
        market_address (str): The blockchain address of the market
        bet_type (str): The type of bet ('moneyline', 'spread', 'total', 'draw')
        side (str): The side of the bet ('home', 'away', 'over', 'under', 'draw')
        limit (int): The exposure limit to set
        api_url (str, optional): The base API URL (defaults to environment var or localhost)
        
    Returns:
        dict: API response with result of the operation
    """
    if not api_url:
        api_url = os.getenv("API_URL", "http://localhost:3000")
    
    # Map bet_type and side to the parameter name expected by the API
    param_mapping = {
        ('moneyline', 'home'): 'homeMoneylineLimit',
        ('moneyline', 'away'): 'awayMoneylineLimit',
        ('draw', 'draw'): 'drawLimit',
        ('spread', 'home'): 'homeSpreadLimit',
        ('spread', 'away'): 'awaySpreadLimit',
        ('total', 'over'): 'overLimit',
        ('total', 'under'): 'underLimit'
    }
    
    key = (bet_type.lower(), side.lower())
    if key not in param_mapping:
        return {
            "status": "error",
            "error": f"Invalid bet type/side combination: {bet_type}/{side}",
            "valid_combinations": list(param_mapping.keys()),
            "market_address": market_address
        }
    
    param_name = param_mapping[key]
    payload = {param_name: limit}
    
    try:
        url = f"{api_url}/api/market/{market_address}/exposure-limits"
        print(f"Setting {bet_type}/{side} exposure limit to {limit} for market {market_address}...", file=sys.stderr)
        print(f"POST {url} with payload: {payload}", file=sys.stderr)
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Successfully set {bet_type}/{side} exposure limit. Response: {result}", file=sys.stderr)
        
        return {
            "status": "success",
            "market_address": market_address,
            "bet_type": bet_type,
            "side": side,
            "limit_set": limit,
            "result": result
        }
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error setting {bet_type}/{side} exposure limit for market {market_address}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        return {
            "status": "error",
            "message": error_message,
            "market_address": market_address,
            "bet_type": bet_type,
            "side": side
        }
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error setting {bet_type}/{side} exposure limit for market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {
            "status": "error",
            "message": error_message,
            "market_address": market_address,
            "bet_type": bet_type, 
            "side": side
        }
    except Exception as e:
        error_message = f"An unexpected error occurred in set_bet_type_exposure_limit: {e}"
        print(error_message, file=sys.stderr)
        return {
            "status": "error",
            "message": error_message,
            "market_address": market_address,
            "bet_type": bet_type,
            "side": side
        }

def get_market_exposure_by_type(market_address: str, api_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Gets current exposure values organized by bet type and side for a specific market.
    
    Args:
        market_address (str): The blockchain address of the market
        api_url (str, optional): The base API URL (defaults to environment var or localhost)
        
    Returns:
        dict: Organized exposure information by bet type and side
    """
    if not api_url:
        api_url = os.getenv("API_URL", "http://localhost:3000")
    
    try:
        # First try to get market details including exposure
        market_data = fetch_market_exposure_details(market_address, api_url)
        
        # Check if there was an error in fetching data
        if "error" in market_data:
            return market_data
        
        # Also try to get general market data to get maxExposure and currentExposure
        general_market_data = {}
        try:
            general_url = f"{api_url}/api/market/{market_address}"
            response = requests.get(general_url)
            response.raise_for_status()
            general_market_data = response.json()
        except Exception:
            # If we can't get general data, just use what we have
            general_market_data = market_data
            
        # Resolve field names based on API response structure
        # First, look for exposure limit fields
        home_ml_limit = market_data.get("homeMoneylineLimit", 0)
        away_ml_limit = market_data.get("awayMoneylineLimit", 0)
        draw_limit = market_data.get("drawLimit", 0)
        home_spread_limit = market_data.get("homeSpreadLimit", 0)
        away_spread_limit = market_data.get("awaySpreadLimit", 0)
        over_limit = market_data.get("overLimit", 0)
        under_limit = market_data.get("underLimit", 0)
        
        # Then look for current exposure fields (these might not be in the API)
        # If not available, default to 0
        home_ml_exposure = market_data.get("homeMoneylineExposure", 0)
        away_ml_exposure = market_data.get("awayMoneylineExposure", 0)
        draw_exposure = market_data.get("drawExposure", 0)
        home_spread_exposure = market_data.get("homeSpreadExposure", 0)
        away_spread_exposure = market_data.get("awaySpreadExposure", 0)
        over_exposure = market_data.get("overExposure", 0)
        under_exposure = market_data.get("underExposure", 0)
        
        # Get global exposure from general market data
        max_exposure = float(general_market_data.get("maxExposure", 0))
        current_exposure = float(general_market_data.get("currentExposure", 0))
        
        # Organize data by bet type and side
        organized_data = {
            "moneyline": {
                "home": {
                    "max_exposure": home_ml_limit,
                    "current_exposure": home_ml_exposure
                },
                "away": {
                    "max_exposure": away_ml_limit,
                    "current_exposure": away_ml_exposure
                }
            },
            "draw": {
                "draw": {
                    "max_exposure": draw_limit,
                    "current_exposure": draw_exposure
                }
            },
            "spread": {
                "home": {
                    "max_exposure": home_spread_limit,
                    "current_exposure": home_spread_exposure
                },
                "away": {
                    "max_exposure": away_spread_limit,
                    "current_exposure": away_spread_exposure
                }
            },
            "total": {
                "over": {
                    "max_exposure": over_limit,
                    "current_exposure": over_exposure
                },
                "under": {
                    "max_exposure": under_limit,
                    "current_exposure": under_exposure
                }
            },
            "global": {
                "max_exposure": max_exposure,
                "current_exposure": current_exposure
            }
        }
        
        # Add raw data for debugging/reference
        organized_data["raw_exposure_data"] = market_data
        organized_data["raw_market_data"] = general_market_data
        
        # Add basic stats to help with risk assessment
        if max_exposure > 0:
            organized_data["global"]["utilization_percentage"] = (current_exposure / max_exposure) * 100
        else:
            organized_data["global"]["utilization_percentage"] = 0
            
        return organized_data
    except Exception as e:
        error_message = f"An unexpected error occurred in get_market_exposure_by_type: {e}"
        print(error_message, file=sys.stderr)
        return {
            "status": "error",
            "message": error_message,
            "market_address": market_address
        }