import json
import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

def get_bankrolled_predictions() -> Dict[str, Any]:
    """
    Loads and returns predictions data from the Bankrolled prediction history.
    
    Returns:
        dict: A structure containing prediction data including user performance metrics
    """
    try:
        # Define the path to the predictions JSON file
        predictions_path = os.path.join(os.path.dirname(__file__), "predictions_last_two_days.json")
        
        # Read and parse the JSON file
        with open(predictions_path, 'r') as f:
            predictions_data = json.load(f)
        
        print(f"Successfully loaded predictions data with {len(predictions_data.get('predictions', []))} entries")
        return predictions_data
    except FileNotFoundError:
        print(f"Error: Predictions file not found at {predictions_path}", file=sys.stderr)
        return {"error": "Predictions file not found", "predictions": []}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in predictions file", file=sys.stderr)
        return {"error": "Invalid JSON in predictions file", "predictions": []}
    except Exception as e:
        print(f"An unexpected error occurred loading predictions: {e}", file=sys.stderr)
        return {"error": str(e), "predictions": []}

def find_predictions_for_market(market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Finds relevant predictions for a specific market by matching team names and date.
    
    Args:
        market_data (dict): Market data containing team names and event date
    
    Returns:
        list: List of matching predictions from Bankrolled data
    """
    try:
        # Get all predictions
        all_predictions = get_bankrolled_predictions()
        
        if "error" in all_predictions:
            return []
        
        # Extract market details
        home_team = market_data.get("homeTeam", "").lower()
        away_team = market_data.get("awayTeam", "").lower()
        event_date = market_data.get("eventDate")
        
        # If we don't have team names, we can't match
        if not home_team or not away_team:
            return []
        
        # Find matching predictions
        matching_predictions = []
        
        for prediction in all_predictions.get("predictions", []):
            pred_home = prediction.get("homeTeam", "").lower()
            pred_away = prediction.get("awayTeam", "").lower()
            pred_date = prediction.get("eventDate")
            
            # Check for team name match (in either order, since data might vary)
            teams_match = (
                (home_team in pred_home or pred_home in home_team) and 
                (away_team in pred_away or pred_away in away_team)
            ) or (
                (home_team in pred_away or pred_away in home_team) and 
                (away_team in pred_home or pred_home in away_team)
            )
            
            # Check if dates are within 1 day (handle different date formats)
            dates_match = False
            if event_date and pred_date:
                try:
                    # Try to parse dates and check if they're close
                    # This assumes ISO format but should handle flexibility
                    market_dt = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
                    pred_dt = datetime.fromisoformat(pred_date.replace('Z', '+00:00'))
                    date_diff = abs((market_dt - pred_dt).total_seconds())
                    dates_match = date_diff < 86400  # Within 24 hours
                except (ValueError, TypeError):
                    # If date parsing fails, fall back to string comparison
                    dates_match = event_date[:10] == pred_date[:10]  # Compare just the date part
            
            if teams_match and (dates_match or not event_date or not pred_date):
                matching_predictions.append(prediction)
        
        print(f"Found {len(matching_predictions)} matching predictions for {home_team} vs {away_team}")
        return matching_predictions
    
    except Exception as e:
        print(f"Error finding predictions for market: {e}", file=sys.stderr)
        return []

def analyze_user_prediction_accuracy(predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes prediction data to identify sharp users and prediction trends.
    
    Args:
        predictions (list): List of predictions to analyze
    
    Returns:
        dict: Analysis results including sharp users and prediction trends
    """
    if not predictions:
        return {
            "sharpUsers": [],
            "predictionTrends": {
                "homeMoneyline": 0,
                "awayMoneyline": 0,
                "drawPredictions": 0,
                "overPredictions": 0,
                "underPredictions": 0,
                "homeSpreadPredictions": 0,
                "awaySpreadPredictions": 0
            },
            "sharpUserCount": 0,
            "totalPredictions": 0
        }
    
    try:
        # Track users and their prediction accuracy
        users = {}
        
        # Track overall prediction trends
        trends = {
            "homeMoneyline": 0,
            "awayMoneyline": 0,
            "drawPredictions": 0,
            "overPredictions": 0,
            "underPredictions": 0,
            "homeSpreadPredictions": 0,
            "awaySpreadPredictions": 0
        }
        
        # Process each prediction
        for prediction in predictions:
            user_id = prediction.get("userId", "unknown")
            prediction_type = prediction.get("predictionType", "").lower()
            prediction_outcome = prediction.get("outcome", "").lower()
            was_correct = prediction.get("wasCorrect", False)
            
            # Track user performance
            if user_id not in users:
                users[user_id] = {
                    "total": 0,
                    "correct": 0,
                    "accuracy": 0.0,
                    "predictions": []
                }
            
            users[user_id]["total"] += 1
            if was_correct:
                users[user_id]["correct"] += 1
            users[user_id]["accuracy"] = users[user_id]["correct"] / users[user_id]["total"]
            users[user_id]["predictions"].append({
                "type": prediction_type,
                "outcome": prediction_outcome,
                "wasCorrect": was_correct
            })
            
            # Track prediction trends
            if prediction_type == "moneyline":
                if prediction_outcome == "home":
                    trends["homeMoneyline"] += 1
                elif prediction_outcome == "away":
                    trends["awayMoneyline"] += 1
                elif prediction_outcome == "draw":
                    trends["drawPredictions"] += 1
            elif prediction_type == "total":
                if prediction_outcome == "over":
                    trends["overPredictions"] += 1
                elif prediction_outcome == "under":
                    trends["underPredictions"] += 1
            elif prediction_type == "spread":
                if prediction_outcome == "home":
                    trends["homeSpreadPredictions"] += 1
                elif prediction_outcome == "away":
                    trends["awaySpreadPredictions"] += 1
        
        # Identify sharp users (>45% accuracy with at least 5 predictions)
        sharp_users = []
        for user_id, data in users.items():
            if data["accuracy"] >= 0.45 and data["total"] >= 5:
                sharp_users.append({
                    "userId": user_id,
                    "accuracy": data["accuracy"],
                    "totalPredictions": data["total"],
                    "correctPredictions": data["correct"],
                    "predictionHistory": data["predictions"]
                })
        
        return {
            "sharpUsers": sharp_users,
            "predictionTrends": trends,
            "sharpUserCount": len(sharp_users),
            "totalPredictions": len(predictions),
            "allUsers": len(users)
        }
    
    except Exception as e:
        print(f"Error analyzing prediction accuracy: {e}", file=sys.stderr)
        return {
            "error": str(e),
            "sharpUsers": [],
            "predictionTrends": {},
            "sharpUserCount": 0,
            "totalPredictions": 0
        }