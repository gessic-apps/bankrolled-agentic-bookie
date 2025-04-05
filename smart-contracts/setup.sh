#!/bin/bash

# Setup script for the Smart Contracts API Server

# Text formatting
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up the Smart Contracts API Server...${NC}"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js is not installed. Please install Node.js first.${NC}"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo -e "${RED}npm is not installed. Please install npm first.${NC}"
    exit 1
fi

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
npm install

# Compile contracts
echo -e "${YELLOW}Compiling smart contracts...${NC}"
npm run compile

# Check if .env file exists, create if not
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cat > .env << EOF
# Server Configuration
PORT=3002
NODE_ENV=development

# Blockchain Configuration
# For local development, leave PRIVATE_KEY empty to use the default Hardhat account
# PRIVATE_KEY=your_private_key_here

# For testnet deployment
# TESTNET_RPC_URL=your_testnet_rpc_url_here
EOF
fi

# Start Hardhat node in the background if not already running
echo -e "${YELLOW}Starting Hardhat node in the background...${NC}"
npx hardhat node > hardhat-node.log 2>&1 &
HARDHAT_PID=$!

# Wait for Hardhat node to start
echo -e "${YELLOW}Waiting for Hardhat node to start...${NC}"
sleep 5

# Check if PM2 is installed, install if not
if ! command -v pm2 &> /dev/null; then
    echo -e "${YELLOW}Installing PM2 globally...${NC}"
    npm install -g pm2
fi

# Start the API server with PM2
echo -e "${YELLOW}Starting the API server with PM2...${NC}"
npm run start:pm2

echo -e "${GREEN}Setup completed!${NC}"
echo -e "${GREEN}API server is now running on http://localhost:3000${NC}"
echo -e "${GREEN}You can test the API using Postman with the included collection.${NC}"
echo -e "${YELLOW}Note: To stop all services, run: npm run stop:pm2 && kill $HARDHAT_PID${NC}"