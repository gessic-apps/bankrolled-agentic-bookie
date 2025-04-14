#!/usr/bin/env python3
import unittest
from unittest.mock import patch, MagicMock
import sys

from ..markets.market_data import get_all_markets, check_event_exists

class TestMarketData(unittest.TestCase):
    @patch('utils.api.client.api_get')
    def test_get_all_markets_success(self, mock_api_get):
        # Setup mock response
        mock_api_get.return_value = [
            {"address": "0x123", "oddsApiId": "game1", "status": "Open"},
            {"address": "0x456", "oddsApiId": "game2", "status": "Pending"},
            {"address": "0x789", "oddsApiId": "game3", "status": "Settled"}
        ]
        
        result = get_all_markets()
        
        # Assertions
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["oddsApiId"], "game1")
        self.assertEqual(result[1]["oddsApiId"], "game2")
        self.assertEqual(result[2]["oddsApiId"], "game3")
        
        # Check isReadyForBetting field
        self.assertTrue(result[0]["isReadyForBetting"])  # Open status
        self.assertTrue(result[1]["isReadyForBetting"])  # Pending status
        self.assertFalse(result[2]["isReadyForBetting"])  # Settled status
        
        # Verify API was called with correct endpoint
        mock_api_get.assert_called_once_with("/api/markets")
    
    @patch('utils.api.client.api_get')
    def test_get_all_markets_invalid_response(self, mock_api_get):
        # Setup mock to return non-list response
        mock_api_get.return_value = {"error": "Invalid response"}
        
        result = get_all_markets()
        
        # Should return empty list for invalid response
        self.assertEqual(result, [])
    
    @patch('utils.api.client.api_get')
    def test_get_all_markets_exception(self, mock_api_get):
        # Setup mock to raise exception
        mock_api_get.side_effect = Exception("API error")
        
        result = get_all_markets()
        
        # Should return empty list when exception occurs
        self.assertEqual(result, [])
    
    def test_check_event_exists_found(self):
        # Test when the game ID exists in the markets
        existing_markets = [
            {"oddsApiId": "game1", "address": "0x123"},
            {"oddsApiId": "game2", "address": "0x456"}
        ]
        
        result = check_event_exists("game1", existing_markets)
        self.assertTrue(result)
    
    def test_check_event_exists_not_found(self):
        # Test when the game ID doesn't exist in the markets
        existing_markets = [
            {"oddsApiId": "game1", "address": "0x123"},
            {"oddsApiId": "game2", "address": "0x456"}
        ]
        
        result = check_event_exists("game3", existing_markets)
        self.assertFalse(result)
    
    def test_check_event_exists_empty_markets(self):
        # Test with empty markets list
        result = check_event_exists("game1", [])
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()