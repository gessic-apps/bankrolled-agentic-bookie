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
        url = f"{api_url}/api/market/{market_address}/exposure-details"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
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
        # Fetch exposure details from the API
        exposure_data = fetch_market_exposure_details(market_address, api_url)
        
        # Check if there was an error in fetching data
        if "error" in exposure_data:
            return exposure_data
        
        # Organize data by bet type and side
        organized_data = {
            "moneyline": {
                "home": {
                    "max_exposure": exposure_data.get("homeMoneylineMaxExposure", 0),
                    "current_exposure": exposure_data.get("homeMoneylineCurrentExposure", 0)
                },
                "away": {
                    "max_exposure": exposure_data.get("awayMoneylineMaxExposure", 0),
                    "current_exposure": exposure_data.get("awayMoneylineCurrentExposure", 0)
                }
            },
            "draw": {
                "draw": {
                    "max_exposure": exposure_data.get("drawMaxExposure", 0),
                    "current_exposure": exposure_data.get("drawCurrentExposure", 0)
                }
            },
            "spread": {
                "home": {
                    "max_exposure": exposure_data.get("homeSpreadMaxExposure", 0),
                    "current_exposure": exposure_data.get("homeSpreadCurrentExposure", 0)
                },
                "away": {
                    "max_exposure": exposure_data.get("awaySpreadMaxExposure", 0),
                    "current_exposure": exposure_data.get("awaySpreadCurrentExposure", 0)
                }
            },
            "total": {
                "over": {
                    "max_exposure": exposure_data.get("overMaxExposure", 0),
                    "current_exposure": exposure_data.get("overCurrentExposure", 0)
                },
                "under": {
                    "max_exposure": exposure_data.get("underMaxExposure", 0),
                    "current_exposure": exposure_data.get("underCurrentExposure", 0)
                }
            },
            "global": {
                "max_exposure": exposure_data.get("maxExposure", 0),
                "current_exposure": exposure_data.get("currentExposure", 0)
            }
        }
        
        return organized_data
    except Exception as e:
        error_message = f"An unexpected error occurred in get_market_exposure_by_type: {e}"
        print(error_message, file=sys.stderr)
        return {
            "status": "error",
            "message": error_message,
            "market_address": market_address
        }