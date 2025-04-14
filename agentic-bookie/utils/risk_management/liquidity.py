#!/usr/bin/env python3
import sys
import requests
from typing import Dict, Any, Optional

from ..config import API_URL

def add_liquidity_to_market(market_address: str, amount: int) -> Dict[str, Any]:
    """
    Adds liquidity to a specific market.
    
    Args:
        market_address: The blockchain address of the market
        amount: The amount of liquidity to add (typically in the smallest unit of the token)
        
    Returns:
        dict: API response with liquidity addition details
    """
    if not API_URL:
        print("Error: Cannot add liquidity, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}
    
    payload = {
        "amount": amount
    }
    
    try:
        url = f"{API_URL}/api/market/{market_address}/add-liquidity"
        print(f"Attempting to add liquidity: POST {url} with payload: {payload}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Successfully added liquidity to market {market_address}. Response: {result}")
        return {
            "status": "success",
            "market_address": market_address,
            "amount_added": amount,
            "result": result
        }
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error adding liquidity to market {market_address}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error adding liquidity to market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except Exception as e:
        error_message = f"An unexpected error occurred in add_liquidity_to_market: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}

def get_liquidity_pool_info() -> Dict[str, Any]:
    """
    Gets information about the global liquidity pool.
    
    Returns:
        dict: Information about the liquidity pool including total liquidity,
              allocated liquidity, and available liquidity
    """
    if not API_URL:
        print("Error: Cannot get liquidity pool info, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}
    
    try:
        url = f"{API_URL}/api/liquidity-pool"
        response = requests.get(url)
        response.raise_for_status()
        result = response.json()
        print(f"Successfully fetched liquidity pool information.")
        return {
            "status": "success",
            "pool_info": result
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching liquidity pool info: {e}", file=sys.stderr)
        return {"status": "error", "message": str(e)}
    except Exception as e:
        print(f"An unexpected error occurred in get_liquidity_pool_info: {e}", file=sys.stderr)
        return {"status": "error", "message": str(e)}

def reduce_market_funding(market_address: str, amount: int) -> Dict[str, Any]:
    """
    Reduces the total funding (and thus max exposure) allocated to a specific market from the central liquidity pool.
    
    Args:
        market_address: The blockchain address of the market
        amount: The amount to reduce funding by
        
    Returns:
        dict: API response with funding reduction details
    """
    if not API_URL:
        print("Error: Cannot reduce market funding, API_URL is not configured.", file=sys.stderr)
        return {"status": "error", "message": "API_URL not configured"}

    if amount <= 0:
        return {"status": "warning", "message": "Reduction amount must be positive.", "market_address": market_address}

    payload = {
        "bettingEngineAddress": market_address,
        "amount": amount
    }

    try:
        url = f"{API_URL}/api/liquidity-pool/reduce-market-funding"
        print(f"Attempting to reduce market funding: POST {url} with payload: {payload}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Successfully reduced funding for market {market_address} by {amount}. Response: {result}")
        return {
            "status": "success",
            "market_address": market_address,
            "amount_reduced": amount,
            "result": result
        }
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error reducing funding for market {market_address}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error reducing funding for market {market_address}: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}
    except Exception as e:
        error_message = f"An unexpected error occurred in reduce_market_funding: {e}"
        print(error_message, file=sys.stderr)
        return {"status": "error", "message": error_message, "market_address": market_address}

if __name__ == "__main__":
    # Test functions
    import sys
    
    # Setup test data
    test_market_address = "0x1234567890abcdef1234567890abcdef12345678"
    test_amount = 1000
    
    # Run tests
    print("Testing add_liquidity_to_market...")
    result = add_liquidity_to_market(test_market_address, test_amount)
    print(f"Result: {result}")
    
    print("\nTesting get_liquidity_pool_info...")
    result = get_liquidity_pool_info()
    print(f"Result: {result}")
    
    print("\nTesting reduce_market_funding...")
    result = reduce_market_funding(test_market_address, test_amount)
    print(f"Result: {result}")