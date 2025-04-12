/**
 * Represents a betting market for NBA games
 */
export interface Market {
  /** Ethereum address of the market contract */
  address: string;
  
  /** Name of the home team */
  homeTeam: string;
  
  /** Name of the away team */
  awayTeam: string;
  
  /** Unix timestamp (in seconds) for when the game starts */
  gameTimestamp: string;
  
  /** Unique ID from the Odds API for this game */
  oddsApiId: string;
  
  /** Odds for the home team (in thousandths, e.g., 1850 = 1.85) */
  homeOdds: string;
  
  /** Odds for the away team (in thousandths, e.g., 2000 = 2.00) */
  awayOdds: string;
  
  /** Odds for a draw result (in thousandths, e.g., 2500 = 2.50). For NBA, this will be 0. */
  drawOdds: string;
  
  /** Whether the game has started */
  gameStarted: boolean;
  
  /** Whether the game has ended */
  gameEnded: boolean;
  
  /** Whether odds have been set for this market */
  oddsSet: boolean;
  
  /** Game outcome (0 = not set, 1 = home win, 2 = away win, 3 = draw) */
  outcome: number;
  
  /** Whether the market is ready for betting (has odds and game hasn't started) */
  isReadyForBetting: boolean;
}

// Add the enum corresponding to NBAMarket.sol MarketStatus
export enum MarketStatus {
  PENDING = 0,
  OPEN = 1,
  STARTED = 2,
  SETTLED = 3,
  CANCELLED = 4,
}