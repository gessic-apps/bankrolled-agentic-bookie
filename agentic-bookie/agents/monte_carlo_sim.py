import numpy as np
import random
from typing import Dict, Any, Tuple, List
import json

# Import the decorator
from agents import function_tool

# Removed TypedDict definitions for simplification

@function_tool
def run_market_simulation(
    market_id: str,
    current_odds_json: str, # Expect JSON string for odds
    current_liquidity: float,
    time_to_event: float, # e.g., in hours or days
    current_exposure_json: str, # Expect JSON string for exposure
    num_simulations: int, # Removed default
    confidence_level: float # Removed default
) -> float: # Simplified return type to single float (VaR)
    """
    Runs simplified Monte Carlo simulations, returning only the Value at Risk (VaR).

    Args:
        market_id: Unique identifier for the market.
        current_odds_json: JSON string representing the dictionary of current odds.
        current_liquidity: Current available liquidity in the market.
        time_to_event: Time remaining until the market resolves.
        current_exposure_json: JSON string representing the dictionary of current exposure.
        num_simulations: The number of simulation paths to run (Required).
        confidence_level: The confidence level for risk metrics, e.g., 0.95 for 95% (Required).

    Returns:
        The calculated Value at Risk (VaR) as a float.
    """

    print(f"Starting SIMPLIFIED Monte Carlo simulation (JSON inputs, Float output) for market: {market_id}")

    # Parse JSON inputs
    try:
        current_odds: Dict[str, float] = json.loads(current_odds_json)
        if not isinstance(current_odds, dict):
             raise ValueError("Parsed current_odds_json is not a dictionary")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing current_odds_json for market {market_id}: {e}. Input: {current_odds_json}")
        return 0.0 # Return default float on error

    try:
        current_exposure: Dict[str, float] = json.loads(current_exposure_json)
        if not isinstance(current_exposure, dict):
             raise ValueError("Parsed current_exposure_json is not a dictionary")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing current_exposure_json for market {market_id}: {e}. Input: {current_exposure_json}")
        return 0.0 # Return default float on error

    # --- Simulation Logic (Mostly unchanged) ---
    true_probabilities = {outcome: 1.0 / odds for outcome, odds in current_odds.items()}
    prob_sum = sum(true_probabilities.values())
    if prob_sum <= 0: # Check for non-positive sum
        print(f"Warning: Sum of implied probabilities is non-positive ({prob_sum}) for market {market_id}.")
        return 0.0
    true_probabilities = {outcome: prob / prob_sum for outcome, prob in true_probabilities.items()}
    outcomes = list(current_odds.keys())
    if not outcomes:
        print(f"Warning: No outcomes found for market {market_id}.")
        return 0.0

    # Ensure weights are valid before passing to random.choices
    weights = [true_probabilities.get(o, 0.0) for o in outcomes]
    if any(w < 0 for w in weights) or sum(weights) <= 0:
        print(f"Warning: Invalid weights calculated for market {market_id}. Weights: {weights}")
        return 0.0

    simulation_results = []
    for i in range(num_simulations):
        simulated_exposure = current_exposure.copy()
        try:
            # Ensure weights sum to a positive number before choice
            if sum(weights) > 0:
                 winning_outcome = random.choices(outcomes, weights=weights, k=1)[0]
            else: # Should not happen if check above worked, but as fallback
                 print(f"Skipping simulation {i} due to zero weight sum.")
                 continue
        except ValueError as e:
            print(f"Error during outcome simulation for market {market_id}: {e}. Weights: {weights}")
            continue
        profit_loss = 0
        for outcome, exposure in simulated_exposure.items():
            if outcome not in current_odds:
                 print(f"Warning: Exposure found for outcome '{outcome}' which is not in current_odds for market {market_id}")
                 continue
            # Ensure odds are valid before calculation
            outcome_odds = current_odds[outcome]
            if not isinstance(outcome_odds, (int, float)) or outcome_odds < 1:
                 print(f"Warning: Invalid odds ({outcome_odds}) for outcome '{outcome}' in market {market_id}")
                 # Decide how to handle: skip outcome, assign default loss/profit, etc.
                 continue # Skipping this outcome calculation for safety
            
            if outcome == winning_outcome:
                profit_loss -= exposure * (outcome_odds - 1)
            else:
                profit_loss += exposure
        simulation_results.append(profit_loss)

    if not simulation_results:
        print(f"Warning: No simulation results generated for market {market_id}. Returning zero metrics.")
        return 0.0

    # --- Analyze Simulation Results ---
    simulation_results_np = np.array(simulation_results)
    expected_profit = np.mean(simulation_results_np) # Still calculate for logging
    percentile_value = (1 - confidence_level) * 100
    value_at_risk = -np.percentile(simulation_results_np, percentile_value) if simulation_results_np.size > 0 and percentile_value > 0 else (-np.min(simulation_results_np) if simulation_results_np.size > 0 else 0.0)

    print(f"Simplified Simulation Complete for market: {market_id}")
    print(f"Expected P/L (calculated but not returned): {expected_profit:.2f}, VaR ({confidence_level*100}%): {value_at_risk:.2f}")

    # Return only the Value at Risk as a float
    return float(value_at_risk)

# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Market data
    market = {
        'market_id': 'EPL_Match_ManUtd_vs_Liverpool',
        'current_odds': {'ManUtd': 2.5, 'Draw': 3.0, 'Liverpool': 2.8},
        # Example with potentially invalid odds for testing parse logic
        # 'current_odds': {'ManUtd': 2.5, 'Draw': 0.5, 'Liverpool': 2.8},
        'current_liquidity': 100000.0,
        'time_to_event': 48.0, # hours
        'current_exposure': {'ManUtd': 5000.0, 'Draw': 2000.0, 'Liverpool': 6000.0},
    }

    # Convert dicts to JSON strings for the call
    odds_json = json.dumps(market['current_odds'])
    exposure_json = json.dumps(market['current_exposure'])

    # Define required args for local test
    test_num_simulations = 5000
    test_confidence_level = 0.95

    var_result = run_market_simulation(
        market_id=market['market_id'],
        current_odds_json=odds_json,
        current_liquidity=market['current_liquidity'],
        time_to_event=market['time_to_event'],
        current_exposure_json=exposure_json,
        num_simulations=test_num_simulations, # Pass explicitly
        confidence_level=test_confidence_level # Pass explicitly
    )

    print("--- Simplified Simulation Result (Float VaR output) ---")
    print(f"Value at Risk: {var_result}")
