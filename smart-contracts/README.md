# Bankrolled Agent Bookie Smart Contracts

Smart contracts for an autonomous, decentralized sportsbook that operates through various agents.

## Overview

This project implements the core smart contracts for a decentralized sportsbook focused on NBA games:

- `USDX.sol`: ERC20 token with 1M supply used for betting
- `LiquidityPool.sol`: Manages the sportsbook's funds
- `NBAMarket.sol`: Individual betting market for an NBA game
- `BettingEngine.sol`: Handles the betting logic and settlement for a market
- `MarketFactory.sol`: Factory contract to deploy new markets

## System Architecture

1. The system starts with 1M USDX tokens in the Liquidity Pool
2. When a market is created, an NBAMarket contract is deployed along with its BettingEngine
3. The Liquidity Pool transfers funds to the BettingEngine
4. Users can place bets on markets using USDX tokens through the NBAMarket contract
5. The NBAMarket delegates the bet handling to its BettingEngine contract
6. When a bet is placed, funds are locked in the BettingEngine contract
7. After the game ends, the results provider sets the outcome in the NBAMarket
8. The NBAMarket triggers the BettingEngine to settle all bets
9. Winning bets are paid out, and remaining funds are returned to the Liquidity Pool

## Setup

### Prerequisites

- Node.js (v14+)
- npm or yarn

### Installation

```bash
cd smart-contracts
npm install
```

## Development

### Compile contracts

```bash
npm run compile
```

### Run tests

```bash
npm test
```

### Local deployment

Start a local Hardhat node:

```bash
npx hardhat node
```

Deploy the contracts in sequence:

```bash
# 1. Deploy USDX token and Liquidity Pool
npx hardhat run scripts/deploy-liquidity.js --network localhost

# 2. Deploy Market Factory
npx hardhat run scripts/deploy-factory.js --network localhost
```

## Creating Markets and Placing Bets

### Create a Market

```bash
npx hardhat run scripts/create-market.js --network <network> "Lakers" "Celtics" 1680307200 "NBA_LAL_BOS_20230405" 1850 2000 50000
```

Parameters:
- Home team name
- Away team name
- Game timestamp (Unix timestamp)
- Odds API ID (for reference)
- Home odds (optional, in basis points, e.g., 1850 = 1.85)
- Away odds (optional, in basis points)
- Market funding (optional, in USDX tokens)

### Place a Bet

```bash
npx hardhat run scripts/place-bet.js --network <network> <marketAddress> <betAmount> <onHomeTeam>
```

Parameters:
- Market address
- Bet amount in USDX tokens
- onHomeTeam: true to bet on home team, false to bet on away team

### Settle a Market

```bash
npx hardhat run scripts/settle-market.js --network <network> <marketAddress> <outcome>
```

Parameters:
- Market address
- Outcome: 1 for home win, 2 for away win

## Contract Functionality

### USDX Token

- ERC20 token with 6 decimals
- 1M initial supply
- Used for all betting operations

### Liquidity Pool

- Holds the main reserve of USDX tokens
- Authorizes markets to receive funds
- Provides funding to markets when created
- Receives unused funds when markets are settled

### NBAMarket

- Constructor initializes market with game details, administrative addresses, and creates a BettingEngine
- Functions to update odds, mark game as started, and set results
- Delegates bet placement to its associated BettingEngine
- Triggers bet settlement on the BettingEngine when results are reported

### BettingEngine

- Handles betting logic, including tracking bets and managing exposure
- Receives funding from the Liquidity Pool
- Processes bet placement requests from the NBAMarket
- Settles bets when triggered by the NBAMarket
- Returns unused funds to the Liquidity Pool after settlement

### MarketFactory

- Creates new markets with game details
- Authorizes and funds markets through the Liquidity Pool
- Tracks all deployed markets
- Allows creation with default or custom provider addresses
- Admin can update default provider addresses and transfer admin role

## Odds Format

The contracts use a decimal odds format with the following conventions:

1. Decimal odds (like those used in European sportsbooks) are stored as integers by multiplying by 1000 for 3 decimal precision:
   - 1.941 odds are stored as 1941
   - 10.51 odds are stored as 10510
   - 2.000 odds are stored as 2000

2. The contract provides a single way to update odds:
   - `updateOdds(uint256 homeOdds, uint256 awayOdds)` - Direct update with integer values (multiplied by 1000)

3. Odds must always be at least 1.000 (stored as 1000)

4. A market without odds set is indicated by:
   - `oddsSet == false`
   - Both home and away odds values are 0 or less than 1000

5. Markets without odds set are not ready for betting, which can be checked with `isReadyForBetting()`

## License

MIT