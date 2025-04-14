#!/usr/bin/env python3
import json
import os
import sys
from typing import Dict, List, Any, Optional

def get_bankrolled_predictions() -> Dict[str, Any]:
    """
    Retrieves Bankrolled prediction data from the last two days.
    This includes historical prediction records, user performance metrics, and market sentiment.
    
    Returns:
        dict: A structure containing prediction data and user performance metrics
    """
    try:
        # Path to the predictions data file
        predictions_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                        "predictions_last_two_days.json")
        
        # Check if file exists
        if not os.path.exists(predictions_file):
            return {
                "status": "error",
                "message": f"Predictions file not found at {predictions_file}",
                "predictions": []
            }
        
        # Read and parse the predictions file
        with open(predictions_file, 'r') as file:
            predictions_data = json.load(file)
        
        return {
            "status": "success",
            "message": f"Retrieved {len(predictions_data)} predictions",
            "predictions": predictions_data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving predictions: {str(e)}",
            "predictions": []
        }

def find_predictions_for_market(market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Finds predictions that match a specific market based on team names and optional date.
    
    Args:
        market_data: Dictionary containing homeTeam, awayTeam, and optionally eventDate
        
    Returns:
        List of matching predictions
    """
    # Get all predictions
    all_predictions = get_bankrolled_predictions()
    if all_predictions.get("status") != "success":
        print(f"Error: {all_predictions.get('message')}", file=sys.stderr)
        return []
    
    predictions = all_predictions.get("predictions", [])
    
    # Extract search criteria
    home_team = market_data.get("homeTeam", "").lower()
    away_team = market_data.get("awayTeam", "").lower()
    event_date = market_data.get("eventDate")
    
    # Find matching predictions
    matching_predictions = []
    for prediction in predictions:
        # Check if prediction matches the teams
        prediction_home = prediction.get("homeTeam", "").lower()
        prediction_away = prediction.get("awayTeam", "").lower()
        
        teams_match = (
            (home_team in prediction_home or prediction_home in home_team) and
            (away_team in prediction_away or prediction_away in away_team)
        )
        
        # If event date is provided, also check date match
        date_match = True
        if event_date and "eventTime" in prediction:
            prediction_date = prediction.get("eventTime", "").split("T")[0]  # Extract date part
            date_match = (event_date == prediction_date)
        
        if teams_match and date_match:
            matching_predictions.append(prediction)
    
    return matching_predictions

def analyze_user_prediction_accuracy(predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes the predictions to identify sharp users and betting trends.
    
    Args:
        predictions: List of predictions to analyze
        
    Returns:
        Dictionary with analysis results
    """
    if not predictions:
        return {
            "message": "No predictions to analyze",
            "trend_summary": "Insufficient data",
            "sharp_users": []
        }
    
    # Initialize counters
    user_predictions = {}
    side_counts = {
        "home": 0,
        "away": 0,
        "over": 0,
        "under": 0,
        "home_spread": 0,
        "away_spread": 0
    }
    
    # Process each prediction
    for prediction in predictions:
        user_id = prediction.get("userId", "unknown")
        prediction_type = prediction.get("predictionType", "").lower()
        prediction_side = prediction.get("predictionSide", "").lower()
        
        # Update user prediction count
        if user_id not in user_predictions:
            user_predictions[user_id] = {
                "total": 0,
                "correct": 0,
                "predictions": []
            }
        
        user_predictions[user_id]["total"] += 1
        if prediction.get("isCorrect", False):
            user_predictions[user_id]["correct"] += 1
        
        user_predictions[user_id]["predictions"].append({
            "type": prediction_type,
            "side": prediction_side,
            "correct": prediction.get("isCorrect", False)
        })
        
        # Update side counts
        if prediction_type == "moneyline":
            if prediction_side == "home":
                side_counts["home"] += 1
            elif prediction_side == "away":
                side_counts["away"] += 1
        elif prediction_type == "total":
            if prediction_side == "over":
                side_counts["over"] += 1
            elif prediction_side == "under":
                side_counts["under"] += 1
        elif prediction_type == "spread":
            if prediction_side == "home":
                side_counts["home_spread"] += 1
            elif prediction_side == "away":
                side_counts["away_spread"] += 1
    
    # Calculate accuracy for each user
    sharp_users = []
    for user_id, data in user_predictions.items():
        if data["total"] >= 3:  # Only consider users with at least 3 predictions
            accuracy = (data["correct"] / data["total"]) if data["total"] > 0 else 0
            if accuracy > 0.6:  # Only include users with >60% accuracy
                sharp_users.append({
                    "userId": user_id,
                    "accuracy": accuracy,
                    "total_predictions": data["total"],
                    "correct_predictions": data["correct"]
                })
    
    # Sort sharp users by accuracy (highest first)
    sharp_users.sort(key=lambda x: x["accuracy"], reverse=True)
    
    # Generate trend summary
    total_predictions = sum(side_counts.values())
    trend_summary = ""
    
    if total_predictions > 0:
        # Moneyline trend
        if side_counts["home"] + side_counts["away"] > 0:
            home_pct = (side_counts["home"] / (side_counts["home"] + side_counts["away"])) * 100
            away_pct = (side_counts["away"] / (side_counts["home"] + side_counts["away"])) * 100
            
            if home_pct > 65:
                trend_summary += f"Strong home team bias ({home_pct:.1f}% of moneyline predictions). "
            elif away_pct > 65:
                trend_summary += f"Strong away team bias ({away_pct:.1f}% of moneyline predictions). "
        
        # Totals trend
        if side_counts["over"] + side_counts["under"] > 0:
            over_pct = (side_counts["over"] / (side_counts["over"] + side_counts["under"])) * 100
            under_pct = (side_counts["under"] / (side_counts["over"] + side_counts["under"])) * 100
            
            if over_pct > 65:
                trend_summary += f"Strong over bias ({over_pct:.1f}% of totals predictions). "
            elif under_pct > 65:
                trend_summary += f"Strong under bias ({under_pct:.1f}% of totals predictions). "
        
        # Spread trend
        if side_counts["home_spread"] + side_counts["away_spread"] > 0:
            home_spread_pct = (side_counts["home_spread"] / (side_counts["home_spread"] + side_counts["away_spread"])) * 100
            away_spread_pct = (side_counts["away_spread"] / (side_counts["home_spread"] + side_counts["away_spread"])) * 100
            
            if home_spread_pct > 65:
                trend_summary += f"Strong home spread bias ({home_spread_pct:.1f}% of spread predictions). "
            elif away_spread_pct > 65:
                trend_summary += f"Strong away spread bias ({away_spread_pct:.1f}% of spread predictions). "
    
    if not trend_summary:
        trend_summary = "No strong bias detected in predictions."
    
    return {
        "message": f"Analyzed {len(predictions)} predictions from {len(user_predictions)} users",
        "trend_summary": trend_summary,
        "sharp_users": sharp_users[:5],  # Return top 5 sharp users
        "side_counts": side_counts,
        "total_users": len(user_predictions)
    }

if __name__ == "__main__":
    # Example usage
    print("Testing get_bankrolled_predictions():")
    result = get_bankrolled_predictions()
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Number of predictions: {len(result.get('predictions', []))}")
    
    print("\nTesting find_predictions_for_market():")
    market_data = {
        "homeTeam": "Los Angeles Lakers",
        "awayTeam": "Boston Celtics"
    }
    matching_predictions = find_predictions_for_market(market_data)
    print(f"Found {len(matching_predictions)} matching predictions")
    
    print("\nTesting analyze_user_prediction_accuracy():")
    analysis = analyze_user_prediction_accuracy(matching_predictions)
    print(f"Trend summary: {analysis['trend_summary']}")
    print(f"Number of sharp users identified: {len(analysis['sharp_users'])}")