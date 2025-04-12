export interface Market {
  id: string;
  name: string;
  currentOdds: {
    home: number; // Decimal odds
    away: number;
    draw?: number; // Optional for markets with draw possibility
    [key: string]: number | undefined;
  };
  currentLiquidity: number; // Total liquidity allocated to this market
  betLimits: {
    home: number;
    away: number;
    draw?: number;
    [key: string]: number | undefined;
  };
  impliedProbabilities: {
    home: number;
    away: number;
    draw?: number;
    [key: string]: number | undefined;
  };
  exposures: {
    home: number; // Current liability on home team
    away: number; // Current liability on away team
    draw?: number; // Current liability on draw
    [key: string]: number | undefined;
  };
  marketType: 'moneyline' | 'spread' | 'totals' | 'other';
  marketStatus: 'open' | 'suspended' | 'settled';
  startTime: Date;
  sport: string;
  league: string;
}

export interface SimulationConfig {
  numSimulations: number;
  numUsers: number;
  avgBetsPerUser: number;
  maxBankroll: number; // Maximum capital allocated
  riskTolerance: number; // 0-1 scale, higher means more aggressive
  targetMargin: number; // Target profit margin
  maxExposurePercentage: number; // Maximum exposure as percentage of liquidity
  oddsAdjustmentFactor: number; // How aggressively to adjust odds
  bettingPeriodHours: number; // How many hours to simulate
  maxOddsVariation: number; // Maximum allowed deviation from fair odds
}

export interface UserProfile {
  id: string;
  betSizeTendency: number; // 0-1 scale, higher means larger bets
  sharpness: number; // 0-1 scale, higher means better at finding value
  favoriteOutcomesBias: number; // 0-1 scale, tendency to bet on favorites
  chasePattern: number; // 0-1 scale, tendency to chase losses
  variability: number; // 0-1 scale, consistency in behavior
}

export interface Bet {
  userId: string;
  marketId: string;
  outcome: 'home' | 'away' | 'draw';
  stake: number;
  odds: number;
  expectedValue: number;
  timestamp: Date;
}

export interface SimulationResult {
  updatedMarket: Market;
  profitLoss: number;
  recommendedActions: {
    oddsAdjustments: {
      home: number;
      away: number;
      draw?: number;
      [key: string]: number | undefined;
    };
    liquidityAdjustment: number; // Positive means add liquidity, negative means remove
    betLimitAdjustments: {
      home: number;
      away: number;
      draw?: number;
      [key: string]: number | undefined;
    };
  };
  riskMetrics: {
    valueAtRisk: number; // 95% VaR
    expectedShortfall: number; // Expected loss beyond VaR
    sharpeRatio: number; // Risk-adjusted return
    maxDrawdown: number; // Maximum observed drawdown
    exposureConcentration: number; // How concentrated the exposure is
  };
  simulationStats: {
    totalBets: number;
    avgBetSize: number;
    betOutcomeDistribution: {
      home: number;
      away: number;
      draw?: number;
      [key: string]: number | undefined;
    };
    worstCaseScenario: number;
    bestCaseScenario: number;
  };
}
