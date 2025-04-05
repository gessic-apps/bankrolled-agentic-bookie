# Bankrolled Agent Bookie Smart Contracts

Smart contracts for an autonomous, decentralized sportsbook that operates through various agents.

## Overview

This project implements the core smart contracts for a decentralized sportsbook focused on NBA games:

- `NBAMarket.sol`: Individual betting market for an NBA game
- `MarketFactory.sol`: Factory contract to deploy new markets

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

Deploy to local node:

```bash
npm run deploy:local
```

### Testnet deployment

Set your environment variables:

```bash
export TESTNET_RPC_URL="https://your-testnet-rpc-url"
export PRIVATE_KEY="your-private-key"
```

Deploy to testnet:

```bash
npm run deploy:testnet
```

## Creating Markets

To create markets for today's NBA games:

```bash
export FACTORY_ADDRESS="your-deployed-factory-address"
npx hardhat run scripts/create-markets.js --network localhost
```

## Contract Functionality

### NBAMarket

- Constructor initializes market with game details and administrative addresses
- Functions to update odds, mark game as started, and set results
- Only designated addresses can update odds and results
- Admin can change odds provider and results provider addresses
- Markets track whether odds have been set with the `oddsSet` flag

### MarketFactory

- Creates new markets with game details
- Tracks all deployed markets
- Allows creation with default or custom provider addresses
- Provides a convenience function to create markets without initial odds
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