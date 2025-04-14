#!/usr/bin/env python3
import random
import numpy as np
from typing import Dict, List, Tuple, Any, Optional

from .models import MarketState, RiskRecommendation

class MonteCarloSimulator:
    """
    Monte Carlo simulation tool for sports betting risk management.
    
    This tool simulates potential outcomes of events and bets to help
    the risk manager make decisions about odds adjustments, liquidity,
    and bet limits.
    """

    def __init__(self, num_simulations: int = 10000):
        """
        Initialize the Monte Carlo simulator.
        
        Args:
            num_simulations: Number of simulations to run (default: 10000)
        """
        self.num_simulations = num_simulations
    
    def _implied_probability(self, decimal_odds: float) -> float:
        """Convert decimal odds to implied probability."""
        return 1.0 / decimal_odds if decimal_odds > 0 else 0.0
    
    def _simulate_event_outcome(self, home_prob: float, away_prob: float) -> str:
        """Simulate a single event outcome based on implied probabilities."""
        # Normalize probabilities to account for the vig
        total_prob = home_prob + away_prob
        norm_home_prob = home_prob / total_prob
        
        # Simulate outcome
        if random.random() < norm_home_prob:
            return "home"
        else:
            return "away"
    
    def _simulate_point_total(self, total_points: float, over_prob: float, under_prob: float) -> float:
        """Simulate the total points in a game based on the line and probabilities."""
        # Normalize probabilities
        total_prob = over_prob + under_prob
        norm_over_prob = over_prob / total_prob
        
        # Determine if it's over or under
        is_over = random.random() < norm_over_prob
        
        # Generate a plausible point total based on the line
        # More likely to be closer to the line, with some variance
        std_dev = total_points * 0.15  # Reasonable standard deviation
        
        if is_over:
            # Generate a value likely to be over the line
            return max(total_points + abs(random.normalvariate(0, std_dev)), total_points + 0.5)
        else:
            # Generate a value likely to be under the line
            return max(0, min(total_points - abs(random.normalvariate(0, std_dev)), total_points - 0.5))
    
    def _simulate_spread_outcome(self, home_spread: float, home_spread_prob: float, away_spread_prob: float) -> Tuple[float, str]:
        """Simulate the final spread outcome based on the line and probabilities."""
        # Normalize probabilities
        total_prob = home_spread_prob + away_spread_prob
        norm_home_cover_prob = home_spread_prob / total_prob
        
        # Determine if home team covers the spread
        home_covers = random.random() < norm_home_cover_prob
        
        # Generate a plausible margin of victory
        std_dev = abs(home_spread) * 0.5 + 3.0  # Reasonable standard deviation
        
        if home_covers:
            # Home team covers the spread
            # If it's a negative spread (home favored), they need to win by more
            # If it's a positive spread (away favored), they just need to lose by less
            if home_spread <= 0:
                margin = home_spread - abs(random.normalvariate(0, std_dev))  # Win by more than the spread
            else:
                margin = -abs(random.normalvariate(0, std_dev))  # Lose by less than the spread
        else:
            # Home team doesn't cover
            if home_spread <= 0:
                margin = home_spread + abs(random.normalvariate(0, std_dev))  # Win by less than the spread or lose
            else:
                margin = home_spread + abs(random.normalvariate(0, std_dev))  # Lose by more than the spread
        
        # Negative margin means home team won by that amount, positive means away team won
        result = "home_cover" if home_covers else "away_cover"
        return margin, result
    
    def _simulate_potential_bets(self, market: MarketState) -> List[Dict[str, Any]]:
        """Simulate the potential bets that might be placed on this market."""
        # Convert odds to probabilities
        home_prob = self._implied_probability(market.home_odds)
        away_prob = self._implied_probability(market.away_odds)
        over_prob = self._implied_probability(market.over_odds)
        under_prob = self._implied_probability(market.under_odds)
        home_spread_prob = self._implied_probability(market.home_spread_odds)
        away_spread_prob = self._implied_probability(market.away_spread_odds)
        
        # Current bet distribution influences future bets
        # Calculate exposure ratios
        total_exposure = max(0.1, market.current_exposure)  # Avoid division by zero
        home_ratio = market.exposure_home / total_exposure if market.exposure_home > 0 else 0.33
        away_ratio = market.exposure_away / total_exposure if market.exposure_away > 0 else 0.33
        over_ratio = market.exposure_over / total_exposure if market.exposure_over > 0 else 0.33
        under_ratio = market.exposure_under / total_exposure if market.exposure_under > 0 else 0.33
        home_spread_ratio = market.exposure_home_spread / total_exposure if market.exposure_home_spread > 0 else 0.33
        away_spread_ratio = market.exposure_away_spread / total_exposure if market.exposure_away_spread > 0 else 0.33
        
        # Invert ratios to simulate bettors being more attracted to outcomes with less exposure
        # This simulates "sharp" money that identifies value
        inv_home_ratio = 1 - (home_ratio / (home_ratio + away_ratio))
        inv_away_ratio = 1 - (away_ratio / (home_ratio + away_ratio))
        inv_over_ratio = 1 - (over_ratio / (over_ratio + under_ratio))
        inv_under_ratio = 1 - (under_ratio / (over_ratio + under_ratio))
        inv_home_spread_ratio = 1 - (home_spread_ratio / (home_spread_ratio + away_spread_ratio))
        inv_away_spread_ratio = 1 - (away_spread_ratio / (home_spread_ratio + away_spread_ratio))
        
        # Simulate bets
        simulated_bets = []
        
        # Number of bets is related to market liquidity and exposure
        liquidity_factor = min(1.0, (market.max_exposure - market.current_exposure) / market.max_exposure)
        num_bets = int(random.normalvariate(50, 20) * liquidity_factor)
        
        for _ in range(num_bets):
            bet_type = random.choices(
                ["moneyline", "spread", "total"], 
                weights=[0.5, 0.3, 0.2], 
                k=1
            )[0]
            
            if bet_type == "moneyline":
                outcome = random.choices(
                    ["home", "away"], 
                    weights=[home_prob * inv_home_ratio, away_prob * inv_away_ratio],
                    k=1
                )[0]
                odds = market.home_odds if outcome == "home" else market.away_odds
            elif bet_type == "spread":
                outcome = random.choices(
                    ["home_spread", "away_spread"], 
                    weights=[home_spread_prob * inv_home_spread_ratio, away_spread_prob * inv_away_spread_ratio],
                    k=1
                )[0]
                odds = market.home_spread_odds if outcome == "home_spread" else market.away_spread_odds
            else:  # total
                outcome = random.choices(
                    ["over", "under"], 
                    weights=[over_prob * inv_over_ratio, under_prob * inv_under_ratio],
                    k=1
                )[0]
                odds = market.over_odds if outcome == "over" else market.under_odds
            
            # Bet size tends to be higher on favorites and more certain outcomes
            # Pareto distribution for bet sizes (many small bets, few large ones)
            base_amount = random.paretovariate(3) * 50
            # Adjust bet size based on odds (higher on favorites)
            odds_factor = 2.0 / odds if odds > 1.0 else 1.0
            bet_amount = min(base_amount * odds_factor, market.max_exposure * 0.1)
            
            simulated_bets.append({
                "bet_type": bet_type,
                "outcome": outcome,
                "amount": bet_amount,
                "odds": odds
            })
        
        return simulated_bets

    def _calculate_pnl(self, simulated_bets: List[Dict[str, Any]], 
                       winner: str, 
                       total_points: float, 
                       spread_result: str, 
                       line_total: float, 
                       home_spread: float) -> float:
        """Calculate the profit/loss for a set of simulated bets given the actual outcome."""
        total_pnl = 0.0
        
        for bet in simulated_bets:
            bet_type = bet["bet_type"]
            outcome = bet["outcome"]
            amount = bet["amount"]
            odds = bet["odds"]
            
            if bet_type == "moneyline":
                if outcome == winner:
                    # Winning bet
                    total_pnl -= amount * (odds - 1)
                else:
                    # Losing bet
                    total_pnl += amount
            
            elif bet_type == "total":
                if (outcome == "over" and total_points > line_total) or \
                   (outcome == "under" and total_points < line_total):
                    # Winning bet
                    total_pnl -= amount * (odds - 1)
                elif (outcome == "over" and total_points < line_total) or \
                     (outcome == "under" and total_points > line_total):
                    # Losing bet
                    total_pnl += amount
                # Exact push not handled here (assume no bets in that case)
            
            elif bet_type == "spread":
                if (outcome == "home_spread" and spread_result == "home_cover") or \
                   (outcome == "away_spread" and spread_result == "away_cover"):
                    # Winning bet
                    total_pnl -= amount * (odds - 1)
                else:
                    # Losing bet
                    total_pnl += amount
        
        return total_pnl

    def run_simulation(self, market: MarketState) -> RiskRecommendation:
        """
        Run Monte Carlo simulations to assess risk and determine optimal risk management strategy.
        
        Args:
            market: The current state of the market including odds and exposure
            
        Returns:
            RiskRecommendation: Detailed risk management recommendations
        """
        # Initialize result variables
        pnl_results = []
        exposure_results = []
        
        # Convert odds to probabilities
        home_prob = self._implied_probability(market.home_odds)
        away_prob = self._implied_probability(market.away_odds)
        over_prob = self._implied_probability(market.over_odds)
        under_prob = self._implied_probability(market.under_odds)
        home_spread_prob = self._implied_probability(market.home_spread_odds)
        away_spread_prob = self._implied_probability(market.away_spread_odds)
        
        # Run simulations
        for _ in range(self.num_simulations):
            # Simulate game result (who wins)
            winner = self._simulate_event_outcome(home_prob, away_prob)
            
            # Simulate total points
            total_points = self._simulate_point_total(market.total_points, over_prob, under_prob)
            
            # Simulate spread outcome
            _, spread_result = self._simulate_spread_outcome(market.home_spread_points, home_spread_prob, away_spread_prob)
            
            # Simulate bets that might be placed
            simulated_bets = self._simulate_potential_bets(market)
            
            # Calculate the bookmaker's P&L for this simulation
            pnl = self._calculate_pnl(
                simulated_bets, 
                winner, 
                total_points, 
                spread_result, 
                market.total_points, 
                market.home_spread_points
            )
            
            pnl_results.append(pnl)
            
            # Calculate maximum exposure in this simulation
            total_home_exposure = sum(bet["amount"] for bet in simulated_bets 
                                     if (bet["bet_type"] == "moneyline" and bet["outcome"] == "home") or
                                        (bet["bet_type"] == "spread" and bet["outcome"] == "home_spread"))
            
            total_away_exposure = sum(bet["amount"] for bet in simulated_bets 
                                     if (bet["bet_type"] == "moneyline" and bet["outcome"] == "away") or
                                        (bet["bet_type"] == "spread" and bet["outcome"] == "away_spread"))
            
            total_over_exposure = sum(bet["amount"] for bet in simulated_bets 
                                     if bet["bet_type"] == "total" and bet["outcome"] == "over")
            
            total_under_exposure = sum(bet["amount"] for bet in simulated_bets 
                                      if bet["bet_type"] == "total" and bet["outcome"] == "under")
            
            # Current + simulated exposure
            max_sim_exposure = max(
                market.exposure_home + total_home_exposure,
                market.exposure_away + total_away_exposure,
                market.exposure_over + total_over_exposure,
                market.exposure_under + total_under_exposure
            )
            
            exposure_results.append(max_sim_exposure)
        
        # Analyze simulation results
        pnl_results = np.array(pnl_results)
        exposure_results = np.array(exposure_results)
        
        # Calculate key risk metrics
        expected_pnl = np.mean(pnl_results)
        pnl_std = np.std(pnl_results)
        var_95 = np.percentile(pnl_results, 5)  # 95% VaR (5th percentile of P&L)
        cvar_95 = np.mean(pnl_results[pnl_results <= var_95])  # Conditional VaR
        max_expected_exposure = np.percentile(exposure_results, 95)  # 95th percentile of exposure
        
        # Initialize recommendation with market address
        recommendation = RiskRecommendation(market_address=market.market_address)
        recommendation.risk_factors = []
        
        # Determine risk status based on metrics
        if var_95 < -market.max_exposure * 0.5 or max_expected_exposure > market.max_exposure * 0.9:
            recommendation.risk_status = "critical"
        elif var_95 < -market.max_exposure * 0.3 or max_expected_exposure > market.max_exposure * 0.8:
            recommendation.risk_status = "high"
        elif var_95 < -market.max_exposure * 0.2 or max_expected_exposure > market.max_exposure * 0.7:
            recommendation.risk_status = "elevated"
        else:
            recommendation.risk_status = "normal"
        
        # Check for specific risk factors
        # Imbalanced exposure
        if (market.exposure_home > market.exposure_away * 3) or (market.exposure_away > market.exposure_home * 3):
            recommendation.risk_factors.append("severe_moneyline_imbalance")
        elif (market.exposure_home > market.exposure_away * 1.5) or (market.exposure_away > market.exposure_home * 1.5):
            recommendation.risk_factors.append("moneyline_imbalance")
            
        if (market.exposure_over > market.exposure_under * 3) or (market.exposure_under > market.exposure_over * 3):
            recommendation.risk_factors.append("severe_total_imbalance")
        elif (market.exposure_over > market.exposure_under * 1.5) or (market.exposure_under > market.exposure_over * 1.5):
            recommendation.risk_factors.append("total_imbalance")
            
        if (market.exposure_home_spread > market.exposure_away_spread * 3) or (market.exposure_away_spread > market.exposure_home_spread * 3):
            recommendation.risk_factors.append("severe_spread_imbalance")
        elif (market.exposure_home_spread > market.exposure_away_spread * 1.5) or (market.exposure_away_spread > market.exposure_home_spread * 1.5):
            recommendation.risk_factors.append("spread_imbalance")
        
        # Liquidity concerns
        if max_expected_exposure > market.max_exposure * 0.8:
            recommendation.risk_factors.append("high_exposure_risk")
            # Calculate additional liquidity needed
            liquidity_buffer = 1.2  # Add 20% buffer
            recommendation.liquidity_needed = int((max_expected_exposure * liquidity_buffer) - market.max_exposure)
            if recommendation.liquidity_needed < 0:
                recommendation.liquidity_needed = 0
        
        # Negative expected value
        if expected_pnl < 0:
            recommendation.risk_factors.append("negative_expected_value")
        
        # High variance
        if pnl_std > market.max_exposure * 0.3:
            recommendation.risk_factors.append("high_variance")
        
        # Determine which side(s) to limit based on exposure imbalance
        if "severe_moneyline_imbalance" in recommendation.risk_factors:
            if market.exposure_home > market.exposure_away:
                recommendation.limit_home_side = True
            else:
                recommendation.limit_away_side = True
                
        if "severe_total_imbalance" in recommendation.risk_factors:
            if market.exposure_over > market.exposure_under:
                recommendation.limit_over_side = True
            else:
                recommendation.limit_under_side = True
        
        # Adjust odds to balance the book if needed
        # The more severe the imbalance, the greater the adjustment
        base_adjustment = 0.05  # 5% base adjustment
        
        # Moneyline odds adjustments
        if "moneyline_imbalance" in recommendation.risk_factors or "severe_moneyline_imbalance" in recommendation.risk_factors:
            severity = 2.0 if "severe_moneyline_imbalance" in recommendation.risk_factors else 1.0
            if market.exposure_home > market.exposure_away:
                # Decrease home odds (less attractive) and increase away odds (more attractive)
                recommendation.new_home_odds = market.home_odds * (1 - base_adjustment * severity)
                recommendation.new_away_odds = market.away_odds * (1 + base_adjustment * severity)
            else:
                # Decrease away odds (less attractive) and increase home odds (more attractive)
                recommendation.new_home_odds = market.home_odds * (1 + base_adjustment * severity)
                recommendation.new_away_odds = market.away_odds * (1 - base_adjustment * severity)
        
        # Total odds adjustments
        if "total_imbalance" in recommendation.risk_factors or "severe_total_imbalance" in recommendation.risk_factors:
            severity = 2.0 if "severe_total_imbalance" in recommendation.risk_factors else 1.0
            if market.exposure_over > market.exposure_under:
                # Decrease over odds (less attractive) and increase under odds (more attractive)
                recommendation.new_over_odds = market.over_odds * (1 - base_adjustment * severity)
                recommendation.new_under_odds = market.under_odds * (1 + base_adjustment * severity)
            else:
                # Decrease under odds (less attractive) and increase over odds (more attractive)
                recommendation.new_over_odds = market.over_odds * (1 + base_adjustment * severity)
                recommendation.new_under_odds = market.under_odds * (1 - base_adjustment * severity)
        
        # Spread odds adjustments
        if "spread_imbalance" in recommendation.risk_factors or "severe_spread_imbalance" in recommendation.risk_factors:
            severity = 2.0 if "severe_spread_imbalance" in recommendation.risk_factors else 1.0
            if market.exposure_home_spread > market.exposure_away_spread:
                # Decrease home spread odds (less attractive) and increase away spread odds (more attractive)
                recommendation.new_home_spread_odds = market.home_spread_odds * (1 - base_adjustment * severity)
                recommendation.new_away_spread_odds = market.away_spread_odds * (1 + base_adjustment * severity)
            else:
                # Decrease away spread odds (less attractive) and increase home spread odds (more attractive)
                recommendation.new_home_spread_odds = market.home_spread_odds * (1 + base_adjustment * severity)
                recommendation.new_away_spread_odds = market.away_spread_odds * (1 - base_adjustment * severity)
        
        # Set max bet size limits for high risk markets
        if recommendation.risk_status in ["high", "critical"]:
            # Base max bet on current exposure
            recommendation.max_bet_size = int(market.max_exposure * 0.05)  # 5% of max exposure
            recommendation.time_based_limits = True
        
        # Generate detailed rationale
        recommendation.detailed_rationale = self._generate_detailed_rationale(
            market, recommendation, expected_pnl, var_95, cvar_95, pnl_std, max_expected_exposure
        )
        
        return recommendation
    
    def _generate_detailed_rationale(self, 
                                    market: MarketState,
                                    recommendation: RiskRecommendation,
                                    expected_pnl: float,
                                    var_95: float,
                                    cvar_95: float,
                                    pnl_std: float,
                                    max_expected_exposure: float) -> str:
        """Generate a detailed explanation of the risk assessment and recommendations."""
        rationale = f"Risk Assessment for Market {market.market_address} (API ID: {market.oddsApiId}):\n\n"
        
        # Current market state
        rationale += "Current Market State:\n"
        rationale += f"- Current/Max Exposure: ${market.current_exposure:.2f}/${market.max_exposure:.2f} " \
                    f"({(market.current_exposure/market.max_exposure*100):.1f}% utilized)\n"
        rationale += f"- Current Moneyline Odds: Home {market.home_odds:.2f}, Away {market.away_odds:.2f}\n"
        rationale += f"- Current Spread: Home {market.home_spread_points:.1f} at {market.home_spread_odds:.2f}, " \
                    f"Away at {market.away_spread_odds:.2f}\n"
        rationale += f"- Current Total: {market.total_points:.1f}, Over {market.over_odds:.2f}, Under {market.under_odds:.2f}\n\n"
        
        # Exposure distribution
        rationale += "Exposure Distribution:\n"
        total_exposure = market.exposure_home + market.exposure_away + market.exposure_over + \
                        market.exposure_under + market.exposure_home_spread + market.exposure_away_spread
        
        if total_exposure > 0:
            rationale += f"- Moneyline: Home ${market.exposure_home:.2f} ({(market.exposure_home/total_exposure*100):.1f}%), " \
                        f"Away ${market.exposure_away:.2f} ({(market.exposure_away/total_exposure*100):.1f}%)\n"
            rationale += f"- Total: Over ${market.exposure_over:.2f} ({(market.exposure_over/total_exposure*100):.1f}%), " \
                        f"Under ${market.exposure_under:.2f} ({(market.exposure_under/total_exposure*100):.1f}%)\n"
            rationale += f"- Spread: Home ${market.exposure_home_spread:.2f} ({(market.exposure_home_spread/total_exposure*100):.1f}%), " \
                        f"Away ${market.exposure_away_spread:.2f} ({(market.exposure_away_spread/total_exposure*100):.1f}%)\n\n"
        else:
            rationale += "- No current exposure data available\n\n"
        
        # Simulation results
        rationale += "Monte Carlo Simulation Results:\n"
        rationale += f"- Expected P&L: ${expected_pnl:.2f}\n"
        rationale += f"- 95% Value at Risk (VaR): ${abs(var_95):.2f}\n"
        rationale += f"- 95% Conditional VaR (Expected Shortfall): ${abs(cvar_95):.2f}\n"
        rationale += f"- P&L Standard Deviation: ${pnl_std:.2f}\n"
        rationale += f"- 95th Percentile Expected Exposure: ${max_expected_exposure:.2f}\n\n"
        
        # Risk status explanation
        rationale += f"Risk Status: {recommendation.risk_status.upper()}\n"
        if recommendation.risk_factors:
            rationale += "Risk Factors Identified:\n"
            for factor in recommendation.risk_factors:
                rationale += f"- {factor.replace('_', ' ').title()}\n"
        else:
            rationale += "No significant risk factors identified.\n"
        rationale += "\n"
        
        # Recommendations explanation
        rationale += "Recommended Actions:\n"
        
        # Odds adjustments
        has_odds_adjustments = any([
            recommendation.new_home_odds, recommendation.new_away_odds,
            recommendation.new_over_odds, recommendation.new_under_odds,
            recommendation.new_home_spread_odds, recommendation.new_away_spread_odds
        ])
        
        if has_odds_adjustments:
            rationale += "1. Odds Adjustments:\n"
            
            if recommendation.new_home_odds and recommendation.new_away_odds:
                home_change = (recommendation.new_home_odds / market.home_odds - 1) * 100
                away_change = (recommendation.new_away_odds / market.away_odds - 1) * 100
                rationale += f"   - Moneyline: Home {market.home_odds:.2f} → {recommendation.new_home_odds:.2f} ({home_change:+.1f}%), " \
                            f"Away {market.away_odds:.2f} → {recommendation.new_away_odds:.2f} ({away_change:+.1f}%)\n"
                
                # Explain moneyline adjustment reasoning
                if home_change < 0:
                    rationale += f"     Decreasing home odds to discourage additional home bets due to " \
                                f"high exposure (${market.exposure_home:.2f}).\n"
                else:
                    rationale += f"     Increasing home odds to encourage more home bets to balance " \
                                f"the higher away exposure (${market.exposure_away:.2f}).\n"
            
            if recommendation.new_over_odds and recommendation.new_under_odds:
                over_change = (recommendation.new_over_odds / market.over_odds - 1) * 100
                under_change = (recommendation.new_under_odds / market.under_odds - 1) * 100
                rationale += f"   - Total: Over {market.over_odds:.2f} → {recommendation.new_over_odds:.2f} ({over_change:+.1f}%), " \
                            f"Under {market.under_odds:.2f} → {recommendation.new_under_odds:.2f} ({under_change:+.1f}%)\n"
                
                # Explain total adjustment reasoning
                if over_change < 0:
                    rationale += f"     Decreasing over odds to discourage additional over bets due to " \
                                f"high exposure (${market.exposure_over:.2f}).\n"
                else:
                    rationale += f"     Increasing over odds to encourage more over bets to balance " \
                                f"the higher under exposure (${market.exposure_under:.2f}).\n"
            
            if recommendation.new_home_spread_odds and recommendation.new_away_spread_odds:
                home_spread_change = (recommendation.new_home_spread_odds / market.home_spread_odds - 1) * 100
                away_spread_change = (recommendation.new_away_spread_odds / market.away_spread_odds - 1) * 100
                rationale += f"   - Spread: Home {market.home_spread_odds:.2f} → {recommendation.new_home_spread_odds:.2f} ({home_spread_change:+.1f}%), " \
                            f"Away {market.away_spread_odds:.2f} → {recommendation.new_away_spread_odds:.2f} ({away_spread_change:+.1f}%)\n"
                
                # Explain spread adjustment reasoning
                if home_spread_change < 0:
                    rationale += f"     Decreasing home spread odds to discourage additional home spread bets due to " \
                                f"high exposure (${market.exposure_home_spread:.2f}).\n"
                else:
                    rationale += f"     Increasing home spread odds to encourage more home spread bets to balance " \
                                f"the higher away spread exposure (${market.exposure_away_spread:.2f}).\n"
        
        # Liquidity needs
        if recommendation.liquidity_needed > 0:
            rationale += f"2. Liquidity Management:\n" \
                        f"   - Add ${recommendation.liquidity_needed:.2f} in liquidity to handle projected exposure\n" \
                        f"   - Current max exposure (${market.max_exposure:.2f}) is insufficient for projected " \
                        f"95th percentile exposure (${max_expected_exposure:.2f})\n"
        
        # Bet limits
        if recommendation.max_bet_size is not None:
            rationale += f"3. Bet Size Limits:\n" \
                        f"   - Set maximum bet size to ${recommendation.max_bet_size:.2f}\n"
            
            if recommendation.limit_home_side:
                rationale += f"   - Apply stricter limits on home bets due to high existing exposure\n"
            if recommendation.limit_away_side:
                rationale += f"   - Apply stricter limits on away bets due to high existing exposure\n"
            if recommendation.limit_over_side:
                rationale += f"   - Apply stricter limits on over bets due to high existing exposure\n"
            if recommendation.limit_under_side:
                rationale += f"   - Apply stricter limits on under bets due to high existing exposure\n"
            
            if recommendation.time_based_limits:
                rationale += f"   - Implement time-based bet size reduction as game approaches\n"
        
        # Overall assessment
        rationale += "\nOverall Assessment:\n"
        
        if recommendation.risk_status == "normal":
            rationale += "This market shows balanced betting patterns with manageable risk exposure. " \
                        "The simulation indicates a positive expected value with reasonable variance. " \
                        "Minor adjustments may optimize profitability, but no urgent action is required."
        
        elif recommendation.risk_status == "elevated":
            rationale += "This market shows some concerning patterns with moderately elevated risk. " \
                        f"With a VaR of ${abs(var_95):.2f}, there's a 5% chance of losses exceeding this amount. " \
                        "The recommended odds adjustments should help rebalance the book without disrupting market liquidity."
        
        elif recommendation.risk_status == "high":
            rationale += "This market presents significant risk with highly imbalanced exposure. " \
                        f"The VaR of ${abs(var_95):.2f} indicates substantial potential downside. " \
                        "Both odds adjustments and liquidity management are recommended to mitigate risk " \
                        "while maintaining market viability."
        
        elif recommendation.risk_status == "critical":
            rationale += "URGENT ATTENTION REQUIRED: This market has critical risk exposure with extreme imbalance. " \
                        f"Simulations show a 5% chance of losses exceeding ${abs(var_95):.2f}, with average worst-case " \
                        f"losses of ${abs(cvar_95):.2f}. Immediate implementation of all recommended actions is " \
                        "essential to prevent significant potential losses."
        
        return rationale