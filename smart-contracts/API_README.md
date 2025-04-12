# Smart Contracts API Server

This API server allows you to deploy and interact with the betting market smart contracts for both NBA and Soccer markets through simple HTTP endpoints. The system supports both standard win/lose markets and markets with draw odds for soccer.

## Setup

### Prerequisites

- Node.js (v14+)
- npm or yarn
- A local or remote Ethereum node (like Hardhat, Ganache, or a testnet)

### Installation

```bash
# Install dependencies
npm install

# Compile contracts (first time setup)
npm run compile
```

### Configuration

Create a `.env` file in the root directory with the following:

```
# Server Configuration
PORT=3002
NODE_ENV=development

# Blockchain Configuration
# For local development, leave PRIVATE_KEY empty to use the default Hardhat account
# PRIVATE_KEY=your_private_key_here

# For testnet deployment
# TESTNET_RPC_URL=your_testnet_rpc_url_here
```

## Running the Server

### For Development

1. Start a local Ethereum node:
```bash
npm run node
```

2. Start the API server in development mode:
```bash
npm run dev
```

### For Production

Using PM2 for process management:

```bash
# Start the API server with PM2
npm run start:pm2

# Stop the server
npm run stop:pm2

# Restart the server
npm run restart:pm2
```

## API Endpoints

### Health Check

```
GET /api/health
```

Returns server status.

### Deploy MarketFactory

```
POST /api/deploy/factory
```

Request Body:
```json
{
  "oddsProviderAddress": "0x...",
  "resultsProviderAddress": "0x..."
}
```

Deploys a new MarketFactory contract.

### Create New Market

```
POST /api/market/create
```

#### NBA Market Example:
```json
{
  "homeTeam": "Lakers",
  "awayTeam": "Celtics",
  "gameTimestamp": 1680307200,
  "homeOdds": 1850,      // Optional, 1.850 odds (3 decimal precision)
  "awayOdds": 2000,      // Optional, 2.000 odds (3 decimal precision)
  "drawOdds": 0,         // Set to 0 for NBA markets (no draw option)
  "homeSpreadPoints": -75,
  "homeSpreadOdds": 1910,
  "awaySpreadOdds": 1910,
  "totalPoints": 2105,
  "overOdds": 1910,
  "underOdds": 1910,
  "marketFunding": 50000 // Optional funding amount in USDX
}
```

#### Soccer Market Example (with Draw Odds):
```json
{
  "homeTeam": "Arsenal",
  "awayTeam": "Manchester City",
  "gameTimestamp": 1680307200,
  "homeOdds": 2500,      // 2.500 odds
  "awayOdds": 2800,      // 2.800 odds
  "drawOdds": 3000,      // 3.000 odds for draw outcome
  "homeSpreadPoints": 0,  // Typically not used in soccer, set to 0 
  "homeSpreadOdds": 0,
  "awaySpreadOdds": 0,
  "totalPoints": 0,      // Typically not used in soccer, set to 0
  "overOdds": 0,
  "underOdds": 0,
  "marketFunding": 50000
}
```

Creates a new market for the specified sport. If odds fields are omitted, creates a market without initial odds. Draw odds should be set for soccer markets and left as 0 for NBA markets.

### Update Odds

```
POST /api/market/:address/update-odds
```

#### NBA Market Example:
```json
{
  "homeOdds": 1800,       // 1.800 odds (3 decimal precision) 
  "awayOdds": 2100,       // 2.100 odds (3 decimal precision)
  "drawOdds": 0,          // Always 0 for NBA markets
  "homeSpreadPoints": -45,
  "homeSpreadOdds": 1910,
  "awaySpreadOdds": 1910,
  "totalPoints": 2155,
  "overOdds": 1910,
  "underOdds": 1910
}
```

#### Soccer Market Example:
```json
{
  "homeOdds": 2600,       // 2.600 odds
  "awayOdds": 2700,       // 2.700 odds
  "drawOdds": 2950,       // 2.950 odds for draw outcome
  "homeSpreadPoints": 0,  // Typically not used in soccer
  "homeSpreadOdds": 0,
  "awaySpreadOdds": 0,
  "totalPoints": 0,
  "overOdds": 0,
  "underOdds": 0
}
```

Updates the odds for a specific market. All parameters are required, but can be set to 0 for unused fields (like spread and totals in soccer).

### Update Game Status

```
POST /api/market/:address/game-status
```

Request Body (to start game):
```json
{
  "action": "start"
}
```

Request Body (to set result):
```json
{
  "action": "set-result",
  "homeScore": 112,
  "awayScore": 109
}
```

For Soccer with Draw Result:
```json
{
  "action": "set-result",
  "homeScore": 1,
  "awayScore": 1  // Equal scores will settle as a draw
}
```

Updates the game status (start game or set result). When setting results, provide the actual scores instead of an "outcome" value. For soccer matches, equal scores will settle draw bets as winners.

### Get Market Info

```
GET /api/market/:address
```

Returns detailed information about a specific market.

### Get All Markets

```
GET /api/markets
```

Returns all markets deployed by the factory.

### Get All Deployed Contracts

```
GET /api/contracts
```

Returns all deployed contract addresses and data.

### Get Transaction Details

```
GET /api/tx/:txHash
```

Returns detailed information about a specific transaction, including:
- Transaction data (from, to, value, gas, etc.)
- Receipt information (block, status, gas used, etc.)
- Decoded event logs from the transaction

## Testing the API

### Using the Web UI

The server includes a simple web UI for testing. Access it by opening your browser to:

```
http://localhost:3002
```

The web UI allows you to:
- Deploy contracts
- Create markets
- Update odds
- View market information
- Explore transaction details

### Using Postman

1. Import the Postman collection from `postman-collection.json` (if available)
2. Set your environment variables:
   - `API_URL`: `http://localhost:3000` (for local testing)
   - `MARKET_ADDRESS`: (will be set after creating a market)

## Deployment to Cloud

1. Set up your cloud instance (AWS, DigitalOcean, etc.)
2. Install Node.js, npm, and PM2
3. Clone the repository
4. Configure your `.env` file with appropriate RPC URLs and private keys
5. Start the server with PM2:
```bash
npm run start:pm2
```

## Monitoring

You can monitor the PM2 processes with:

```bash
npx pm2 monit
```

Or get a status overview:

```bash
npx pm2 status
```

## Direct Transaction Scripts

The project includes several helper scripts for working directly with the contracts:

### Wallet Helper

The `utils/wallet-helper.js` module provides functions for signing transactions with different roles:

- Admin (deploys contracts, creates markets, starts games)
- Odds Provider (updates odds)
- Results Provider (sets game results)

This module works with local Hardhat accounts or real private keys (for testnet/mainnet).

### Deploy Factory Script

```bash
node scripts/deploy-factory.js
```

Deploys the MarketFactory contract and saves deployment info to a file.

### Create Market Script

```bash
node scripts/create-market.js <factoryAddress> <homeTeam> <awayTeam> <gameTimestamp> [homeOdds] [awayOdds]

# Example (with odds):
node scripts/create-market.js 0x1234... "Lakers" "Celtics" 1680307200 1850 2000

# Example (without odds):
node scripts/create-market.js 0x1234... "Lakers" "Celtics" 1680307200
```

### Place Bet

```
POST /api/market/:address/place-bet
```

NBA Market Bet Examples:
```json
// Moneyline bet on home team
{
  "amount": 100,
  "betType": "moneyline", 
  "betSide": "home",    
  "bettor": "0x90F79bf6EB2c4f870365E785982E1f101E93b906" 
}

// Spread bet on away team
{
  "amount": 100,
  "betType": "spread", 
  "betSide": "away",    
  "bettor": "0x90F79bf6EB2c4f870365E785982E1f101E93b906" 
}

// Total (over/under) bet
{
  "amount": 100,
  "betType": "total", 
  "betSide": "over",    
  "bettor": "0x90F79bf6EB2c4f870365E785982E1f101E93b906" 
}
```

Soccer Market Draw Bet Example:
```json
{
  "amount": 100,
  "betType": "draw", 
  "betSide": "draw",    // The betSide value is ignored for draw bets but "draw" is used for clarity
  "bettor": "0x90F79bf6EB2c4f870365E785982E1f101E93b906" 
}
```

Places a bet on a specific market. Valid betType values are:
- "moneyline": Bet on team to win (betSide must be "home" or "away")
- "spread": Bet on point spread (betSide must be "home" or "away")
- "total": Bet on total points (betSide must be "over" or "under") 
- "draw": Bet on a draw outcome (soccer only, betSide value is ignored)

### Update Odds Script

```bash
# NBA Market
node scripts/update-odds.js <marketAddress> <homeOdds> <awayOdds> <drawOdds> <homeSpreadPoints> <homeSpreadOdds> <awaySpreadOdds> <totalPoints> <overOdds> <underOdds>

# Example:
node scripts/update-odds.js 0x1234... 1850 2000 0 -75 1910 1910 2105 1910 1910

# Soccer Market (with draw odds)
node scripts/update-odds.js 0x1234... 2500 2800 3000 0 0 0 0 0 0
```

### Create Market Script

```bash
# NBA Market
node scripts/create-market.js "Lakers" "Celtics" 1680307200 "NBA_2023_LAL_BOS" 1850 2000 0 -75 1910 1910 2105 1910 1910 50000

# Soccer Market (with draw odds)
node scripts/create-market.js "Arsenal" "Manchester City" 1680307200 "SOCCER_2023_ARS_MCI" 2500 2800 3000 0 0 0 0 0 0 50000
```

Each script uses the appropriate role signer for the operation being performed.