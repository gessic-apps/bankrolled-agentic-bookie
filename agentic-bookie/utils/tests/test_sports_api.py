#!/usr/bin/env python3
import unittest
from unittest.mock import patch, MagicMock
import sys

from ..api.sports_api import fetch_odds_api

class TestSportsApi(unittest.TestCase):
    @patch('requests.get')
    def test_fetch_odds_api_success(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "test_game_1", "home_team": "Team A", "away_team": "Team B"},
            {"id": "test_game_2", "home_team": "Team C", "away_team": "Team D"}
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test with API key set
        with patch.dict('os.environ', {'SPORTS_API_KEY': 'test_key'}):
            with patch('utils.config.SPORTS_API_KEY', 'test_key'):
                result = fetch_odds_api('basketball_nba')
                
                # Assertions
                self.assertEqual(len(result), 2)
                self.assertEqual(result[0]["id"], "test_game_1")
                self.assertEqual(result[1]["id"], "test_game_2")
                
                # Verify API was called with correct parameters
                mock_get.assert_called_once()
                call_args = mock_get.call_args[0][0]
                self.assertEqual(call_args, "https://api.the-odds-api.com/v4/sports/basketball_nba/odds")
    
    @patch('requests.get')
    def test_fetch_odds_api_no_api_key(self, mock_get):
        # Test with API key not set
        with patch('utils.config.SPORTS_API_KEY', None):
            result = fetch_odds_api('basketball_nba')
            
            # Should return empty list and not call the API
            self.assertEqual(result, [])
            mock_get.assert_not_called()
    
    @patch('requests.get')
    def test_fetch_odds_api_request_exception(self, mock_get):
        # Setup mock to raise exception
        mock_get.side_effect = Exception("API error")
        
        # Test with API key set
        with patch.dict('os.environ', {'SPORTS_API_KEY': 'test_key'}):
            with patch('utils.config.SPORTS_API_KEY', 'test_key'):
                result = fetch_odds_api('basketball_nba')
                
                # Should return empty list when exception occurs
                self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main()