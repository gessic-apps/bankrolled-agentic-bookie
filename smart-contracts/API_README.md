# Smart Contracts API Server

This API server allows you to deploy and interact with the NBA betting market smart contracts through simple HTTP endpoints.

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

Request Body:
```json
{
  "homeTeam": "Lakers",
  "awayTeam": "Celtics",
  "gameTimestamp": 1680307200,
  "homeOdds": 1850,  // Optional, 1.850 odds (3 decimal precision)
  "awayOdds": 2000   // Optional, 2.000 odds (3 decimal precision)
}
```

Creates a new NBA market. If homeOdds and awayOdds are omitted, creates a market without initial odds.

### Update Odds

```
POST /api/market/:address/update-odds
```

Request Body:
```json
{
  "homeOdds": 1941,  // 1.941 odds (3 decimal precision)
  "awayOdds": 1051   // 1.051 odds (3 decimal precision)
}
```

Updates the odds for a specific market.

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
  "outcome": 1  // 1 for home win, 2 for away win
}
```

Updates the game status (start game or set result).

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

### Update Odds Script

```bash
node scripts/update-odds.js <marketAddress> <homeOdds> <awayOdds>

# Example:
node scripts/update-odds.js 0x1234... 1941 1051
```

Each script uses the appropriate role signer for the operation being performed.