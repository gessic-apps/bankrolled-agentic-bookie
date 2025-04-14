#!/usr/bin/env python3
import json
from typing import Dict, List, Any, Optional

from .models import MarketState, RiskRecommendation
from .simulator import MonteCarloSimulator

def analyze_market_risk(
    market_data: Dict[str, Any],
    exposure_distribution: Optional[Dict[str, float]] = None,
    num_simulations: int = 10000
) -> Dict[str, Any]:
    """
    Analyze the risk for a specific market using Monte Carlo simulations.
    
    This function is the main entry point for the risk manager agent to use.
    
    Args:
        market_data: Market information including address, odds, exposure, etc.
        exposure_distribution: Optional breakdown of exposure by bet type and outcome
        num_simulations: Number of simulations to run (default: 10000)
        
    Returns:
        Dict with risk assessment and recommendations
    """
    try:
        # Create MarketState object from input data
        market_state = MarketState(
            market_address=market_data.get("address", ""),
            oddsApiId=market_data.get("oddsApiId", ""),
            status=market_data.get("status", ""),
            current_exposure=float(market_data.get("currentExposure", 0)),
            max_exposure=float(market_data.get("maxExposure", 0)),
            home_odds=float(market_data.get("homeOdds", 0)) / 1000,  # Convert from integer format
            away_odds=float(market_data.get("awayOdds", 0)) / 1000,
            home_spread_points=float(market_data.get("homeSpreadPoints", 0)) / 10,
            home_spread_odds=float(market_data.get("homeSpreadOdds", 0)) / 1000,
            away_spread_odds=float(market_data.get("awaySpreadOdds", 0)) / 1000,
            total_points=float(market_data.get("totalPoints", 0)) / 10,
            over_odds=float(market_data.get("overOdds", 0)) / 1000,
            under_odds=float(market_data.get("underOdds", 0)) / 1000
        )
        
        # Add exposure distribution if provided
        if exposure_distribution:
            market_state.exposure_home = exposure_distribution.get("home", 0.0)
            market_state.exposure_away = exposure_distribution.get("away", 0.0)
            market_state.exposure_over = exposure_distribution.get("over", 0.0)
            market_state.exposure_under = exposure_distribution.get("under", 0.0)
            market_state.exposure_home_spread = exposure_distribution.get("home_spread", 0.0)
            market_state.exposure_away_spread = exposure_distribution.get("away_spread", 0.0)
        else:
            # If no distribution provided, estimate a reasonable distribution based on current exposure
            total_exposure = market_state.current_exposure
            if total_exposure > 0:
                # Default distribution: 40% moneyline, 35% spread, 25% total
                market_state.exposure_home = total_exposure * 0.20
                market_state.exposure_away = total_exposure * 0.20
                market_state.exposure_home_spread = total_exposure * 0.175
                market_state.exposure_away_spread = total_exposure * 0.175
                market_state.exposure_over = total_exposure * 0.125
                market_state.exposure_under = total_exposure * 0.125
        
        # Run the simulation
        simulator = MonteCarloSimulator(num_simulations=num_simulations)
        recommendation = simulator.run_simulation(market_state)
        
        # Convert recommendation to dictionary for return
        result = {
            "market_address": recommendation.market_address,
            "risk_status": recommendation.risk_status,
            "risk_factors": recommendation.risk_factors,
            "recommended_actions": {}
        }
        
        # Add odds adjustment recommendations if present
        odds_adjustments = {}
        if recommendation.new_home_odds:
            odds_adjustments["home_odds"] = recommendation.new_home_odds
        if recommendation.new_away_odds:
            odds_adjustments["away_odds"] = recommendation.new_away_odds
        if recommendation.new_home_spread_odds:
            odds_adjustments["home_spread_odds"] = recommendation.new_home_spread_odds
        if recommendation.new_away_spread_odds:
            odds_adjustments["away_spread_odds"] = recommendation.new_away_spread_odds
        if recommendation.new_over_odds:
            odds_adjustments["over_odds"] = recommendation.new_over_odds
        if recommendation.new_under_odds:
            odds_adjustments["under_odds"] = recommendation.new_under_odds
            
        if odds_adjustments:
            result["recommended_actions"]["odds_adjustments"] = odds_adjustments
        
        # Add liquidity recommendation if needed
        if recommendation.liquidity_needed > 0:
            result["recommended_actions"]["liquidity"] = {
                "amount_needed": recommendation.liquidity_needed
            }
        
        # Add bet size limits if recommended
        if recommendation.max_bet_size is not None:
            result["recommended_actions"]["bet_limits"] = {
                "max_bet_size": recommendation.max_bet_size,
                "time_based": recommendation.time_based_limits,
                "limit_sides": {
                    "home": recommendation.limit_home_side,
                    "away": recommendation.limit_away_side,
                    "over": recommendation.limit_over_side,
                    "under": recommendation.limit_under_side
                }
            }
        
        # Include detailed rationale
        result["detailed_rationale"] = recommendation.detailed_rationale
        
        return result
    
    except Exception as e:
        # Return error information
        return {
            "status": "error",
            "message": f"Error in risk analysis: {str(e)}",
            "market_address": market_data.get("address", "unknown")
        }


def bulk_analyze_markets(
    markets_data: List[Dict[str, Any]],
    exposure_distributions: Optional[Dict[str, Dict[str, float]]] = None,
    num_simulations: int = 5000
) -> Dict[str, Any]:
    """
    Analyze multiple markets in bulk to provide risk assessments and recommendations.
    
    Args:
        markets_data: List of market information dictionaries
        exposure_distributions: Optional dict mapping market addresses to their exposure distributions
        num_simulations: Number of simulations to run per market (default: 5000, reduced for bulk analysis)
        
    Returns:
        Dict with risk assessments and recommendations for all markets
    """
    results = {
        "markets": [],
        "summary": {
            "total_markets": len(markets_data),
            "critical_risk": 0,
            "high_risk": 0,
            "elevated_risk": 0,
            "normal_risk": 0,
            "total_liquidity_needed": 0,
            "markets_needing_odds_adjustment": 0
        }
    }
    
    for market_data in markets_data:
        # Skip markets that aren't open
        if market_data.get("status", "").lower() != "open":
            continue
            
        # Get exposure distribution for this market if available
        market_address = market_data.get("address", "")
        exposure_distribution = None
        if exposure_distributions and market_address in exposure_distributions:
            exposure_distribution = exposure_distributions[market_address]
        
        # Analyze this market
        market_result = analyze_market_risk(
            market_data=market_data,
            exposure_distribution=exposure_distribution,
            num_simulations=num_simulations
        )
        
        # Add to results
        results["markets"].append(market_result)
        
        # Update summary statistics
        risk_status = market_result.get("risk_status", "normal")
        if risk_status == "critical":
            results["summary"]["critical_risk"] += 1
        elif risk_status == "high":
            results["summary"]["high_risk"] += 1
        elif risk_status == "elevated":
            results["summary"]["elevated_risk"] += 1
        else:
            results["summary"]["normal_risk"] += 1
        
        # Add up total liquidity needed
        if "liquidity" in market_result.get("recommended_actions", {}):
            results["summary"]["total_liquidity_needed"] += market_result["recommended_actions"]["liquidity"].get("amount_needed", 0)
        
        # Count markets needing odds adjustments
        if "odds_adjustments" in market_result.get("recommended_actions", {}):
            results["summary"]["markets_needing_odds_adjustment"] +=1
    
    # Add overall risk assessment to summary
    if results["summary"]["critical_risk"] > 0:
        results["summary"]["overall_risk_level"] = "critical"
    elif results["summary"]["high_risk"] > 0:
        results["summary"]["overall_risk_level"] = "high"
    elif results["summary"]["elevated_risk"] > len(markets_data) * 0.1:  # More than 10% of markets
        results["summary"]["overall_risk_level"] = "elevated"
    else:
        results["summary"]["overall_risk_level"] = "normal"
    
    return results

if __name__ == "__main__":
    # Example usage
    market_data = {
        "address": "0x1234567890abcdef1234567890abcdef12345678",
        "oddsApiId": "basketball_nba_1234",
        "status": "Open",
        "currentExposure": 1500,
        "maxExposure": 5000,
        "homeOdds": 2100,        # 2.10 in decimal format
        "awayOdds": 1750,        # 1.75 in decimal format
        "homeSpreadPoints": -35,  # -3.5 in decimal format
        "homeSpreadOdds": 1900,   # 1.90 in decimal format
        "awaySpreadOdds": 2000,   # 2.00 in decimal format
        "totalPoints": 2225,      # 222.5 in decimal format
        "overOdds": 1950,         # 1.95 in decimal format
        "underOdds": 1950         # 1.95 in decimal format
    }
    
    # Sample exposure distribution
    exposure_distribution = {
        "home": 600,
        "away": 300,
        "over": 350,
        "under": 150,
        "home_spread": 50,
        "away_spread": 50
    }
    
    # Run risk analysis
    result = analyze_market_risk(market_data, exposure_distribution)
    print(json.dumps(result, indent=2))