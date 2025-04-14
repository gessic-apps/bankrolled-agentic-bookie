#!/usr/bin/env python3
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class MarketState:
    """Represents the current state of a betting market."""
    market_address: str
    oddsApiId: str
    status: str
    current_exposure: float
    max_exposure: float
    home_odds: float
    away_odds: float
    home_spread_points: float
    home_spread_odds: float
    away_spread_odds: float
    total_points: float
    over_odds: float
    under_odds: float
    # Distribution of exposure across bet types and outcomes
    exposure_home: float = 0.0
    exposure_away: float = 0.0
    exposure_over: float = 0.0
    exposure_under: float = 0.0
    exposure_home_spread: float = 0.0
    exposure_away_spread: float = 0.0

@dataclass
class RiskRecommendation:
    """Risk management recommendations for a specific market."""
    market_address: str
    # Odds adjustments
    new_home_odds: Optional[float] = None
    new_away_odds: Optional[float] = None
    new_home_spread_odds: Optional[float] = None
    new_away_spread_odds: Optional[float] = None
    new_over_odds: Optional[float] = None
    new_under_odds: Optional[float] = None
    # Liquidity management
    liquidity_needed: int = 0
    # Bet size limits
    max_bet_size: Optional[int] = None
    # Time-based bet limits
    time_based_limits: bool = False
    # Side-specific limits
    limit_home_side: bool = False
    limit_away_side: bool = False
    limit_over_side: bool = False
    limit_under_side: bool = False
    # Risk status and rationale
    risk_status: str = "normal"  # normal, elevated, high, critical
    risk_factors: List[str] = None
    detailed_rationale: str = ""
    
    def __post_init__(self):
        if self.risk_factors is None:
            self.risk_factors = []