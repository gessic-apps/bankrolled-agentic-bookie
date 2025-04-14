#!/usr/bin/env python3
import requests
import sys
from typing import Dict, Any, List, Optional

from ..config import API_URL

def api_get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Make a GET request to the platform API"""
    try:
        url = f"{API_URL}{endpoint}"
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error on GET {url}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        raise
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error on GET {url}: {e}"
        print(error_message, file=sys.stderr)
        raise
    except Exception as e:
        error_message = f"Unexpected error on GET {url}: {e}"
        print(error_message, file=sys.stderr)
        raise

def api_post(endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Make a POST request to the platform API"""
    try:
        url = f"{API_URL}{endpoint}"
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error on POST {url}: {e.response.status_code} - {e.response.text}"
        print(error_message, file=sys.stderr)
        raise
    except requests.exceptions.RequestException as e:
        error_message = f"Request Error on POST {url}: {e}"
        print(error_message, file=sys.stderr)
        raise
    except Exception as e:
        error_message = f"Unexpected error on POST {url}: {e}"
        print(error_message, file=sys.stderr)
        raise