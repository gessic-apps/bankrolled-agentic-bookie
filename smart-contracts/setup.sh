#!/bin/bash

# Setup script for the Smart Contracts API Server

# Text formatting
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default network
NETWORK="localhost"
echo -e "${YELLOW}DEBUG: Initial NETWORK value: ${NETWORK}${NC}"

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --network)
            echo -e "${YELLOW}DEBUG: Found --network flag with value: $2${NC}"
            NETWORK="$2"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

echo -e "${YELLOW}DEBUG: NETWORK value after parsing args: ${NETWORK}${NC}"
echo -e "${GREEN}Setting up the Smart Contracts API Server on network: ${NETWORK}...${NC}"

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

# Clean previous artifacts and cache
echo -e "${YELLOW}Cleaning previous build artifacts...${NC}"
npx hardhat clean

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

# For Base Sepolia deployment
# BASE_SEPOLIA_RPC_URL=https://sepolia.base.org

# For other testnet deployment
# TESTNET_RPC_URL=your_testnet_rpc_url_here
EOF
fi

echo -e "${YELLOW}DEBUG: Checking network condition. NETWORK = ${NETWORK}${NC}"
# Only start local Hardhat node if using localhost network
if [ "$NETWORK" = "localhost" ]; then
    echo -e "${YELLOW}DEBUG: Condition '$NETWORK == localhost' is TRUE. Starting Hardhat node.${NC}"
    # Start Hardhat node in the background if not already running
    echo -e "${YELLOW}Starting Hardhat node in the background...${NC}"
    npx hardhat node > hardhat-node.log 2>&1 &
    HARDHAT_PID=$!

    # Wait for Hardhat node to start
    echo -e "${YELLOW}Waiting for Hardhat node to start...${NC}"
    sleep 5
else
    echo -e "${YELLOW}DEBUG: Condition '$NETWORK == localhost' is FALSE. Using external network: ${NETWORK}...${NC}"
    # Source .env file to get environment variables
    if [ -f .env ]; then
        echo -e "${YELLOW}DEBUG: Sourcing .env file and exporting variables...${NC}"
        set -a # Automatically export all variables defined from now on
        source .env
        set +a # Stop automatically exporting variables
        echo -e "${YELLOW}DEBUG: PRIVATE_KEY from env (if set): ${PRIVATE_KEY:-'Not Set'}${NC}"
    else
        echo -e "${YELLOW}DEBUG: .env file not found, not sourcing.${NC}"
    fi
    
    echo -e "${YELLOW}DEBUG: Checking network condition. NETWORK = ${NETWORK}${NC}"
    if [ "$NETWORK" = "baseSepolia" ]; then
        echo -e "${YELLOW}DEBUG: Condition '$NETWORK == baseSepolia' is TRUE. Running Base Sepolia checks.${NC}"
        if [ -z "$PRIVATE_KEY" ]; then
            echo -e "${RED}ERROR: PRIVATE_KEY environment variable must be set for Base Sepolia deployment.${NC}"
            echo -e "${YELLOW}Please add your private key to the .env file and run again.${NC}"
            exit 1
        fi
        
        if [ -z "$BASE_SEPOLIA_RPC_URL" ]; then
            echo -e "${YELLOW}Warning: BASE_SEPOLIA_RPC_URL not set, using default https://sepolia.base.org${NC}"
        fi
        
        # Verify network connectivity and account balance
        echo -e "${YELLOW}Verifying network connectivity and account balance...${NC}"
        
        # Create a simple script that doesn't rely on hardhat import
        TEMP_SCRIPT="scripts/check-network.js"
        echo -e "${YELLOW}DEBUG: Creating temporary script at ${TEMP_SCRIPT}${NC}"
        mkdir -p scripts
        cat > "$TEMP_SCRIPT" << 'EOF'
// Simple script to check network connection and balance
const ethers = require('ethers');

async function main() {
  try {
    // Get provider from environment or use default
    const providerUrl = process.env.BASE_SEPOLIA_RPC_URL || "https://base-sepolia-rpc.publicnode.com";
    console.log("DEBUG: Using provider URL:", providerUrl);
    const provider = new ethers.providers.JsonRpcProvider(providerUrl);
    
    // Get account from private key
    const privateKey = process.env.PRIVATE_KEY; // Use environment variable
    if (!privateKey) {
      console.error("ERROR: PRIVATE_KEY not set in environment for check-network.js");
      process.exit(1);
    }
    console.log("DEBUG: Using PRIVATE_KEY from environment for check-network.js");
    
    const wallet = new ethers.Wallet(privateKey, provider);
    
    // Get network info
    const network = await provider.getNetwork();
    console.log('Using account:', wallet.address);
    console.log('Network name:', network.name);
    console.log('Network chainId:', network.chainId);
    
    // Get balance
    const balance = await provider.getBalance(wallet.address);
    console.log('Account balance:', ethers.utils.formatEther(balance), 'ETH');
    
    // Get gas price
    const gasPrice = await provider.getGasPrice();
    console.log('Gas price:', ethers.utils.formatUnits(gasPrice, 'gwei'), 'gwei');
    
    if (network.chainId !== 84532) {
      console.error(`ERROR: Expected Base Sepolia (chainId 84532), but connected to network with chainId ${network.chainId}`);
      process.exit(1);
    }
    
    if (parseFloat(ethers.utils.formatEther(balance)) < 0.01) {
      console.warn(`WARNING: Low account balance (${ethers.utils.formatEther(balance)} ETH). Deployment may fail.`);
    }
    
    console.log("Network check: Successful connection to Base Sepolia");
  } catch (error) {
    console.error("ERROR:", error.message);
    process.exit(1);
  }
}

main();
EOF
        
        # Execute the script
        echo -e "${YELLOW}Running network check...${NC}"
        node "$TEMP_SCRIPT"
        
        # Check if the script ran successfully
        if [ $? -ne 0 ]; then
            echo -e "${RED}ERROR: Failed to connect to Base Sepolia. See error above.${NC}"
            exit 1
        fi
        
        echo -e "${GREEN}Successfully connected to Base Sepolia network.${NC}"
    else
        echo -e "${YELLOW}DEBUG: Condition '$NETWORK == baseSepolia' is FALSE.${NC}"
    fi
fi

# Deploy the contracts to specified network
echo -e "${YELLOW}Deploying contracts to ${NETWORK} network...${NC}"

# Function to execute a command with error handling
run_deploy_command() {
    local cmd_to_run="$1"
    local is_critical="$2"
    echo -e "${YELLOW}DEBUG: Preparing to run command: ${cmd_to_run}${NC}"
    echo -e "${YELLOW}Running: ${cmd_to_run}${NC}"
    
    # Execute the command and store the result
    if eval "${cmd_to_run}"; then
        echo -e "${GREEN}Command succeeded.${NC}"
    else
        local exit_code=$?
        echo -e "${RED}Command failed with exit code ${exit_code}.${NC}"
        echo -e "${RED}Deployment failed. Please check the error messages above.${NC}"
        
        echo -e "${YELLOW}DEBUG: Checking network condition inside error handler. NETWORK = ${NETWORK}${NC}"
        if [ "$NETWORK" = "baseSepolia" ]; then
            echo -e "${YELLOW}DEBUG: Condition '$NETWORK == baseSepolia' is TRUE in error handler.${NC}"
            echo -e "${YELLOW}Common issues for Base Sepolia:${NC}"
            echo -e "${YELLOW}1. Insufficient ETH balance${NC}"
            echo -e "${YELLOW}2. Incorrect RPC URL${NC}"
            echo -e "${YELLOW}3. Network congestion - try increasing gas price/limit${NC}"
            
            # Check gas price using the script we already created
            echo -e "${YELLOW}Checking current gas price...${NC}"
            node scripts/check-network.js
        else
            echo -e "${YELLOW}DEBUG: Condition '$NETWORK == baseSepolia' is FALSE in error handler.${NC}"
        fi
        
        if [ "${is_critical}" = "critical" ]; then
            echo -e "${RED}DEBUG: Critical step failed. Exiting.${NC}"
            exit 1
        fi
    fi
}

DEPLOY_CMD_LIQUIDITY="npm run deploy:liquidity -- --network ${NETWORK}"
echo -e "${YELLOW}1. Deploying USDX token and Liquidity Pool...${NC}"
run_deploy_command "${DEPLOY_CMD_LIQUIDITY}" "critical"

DEPLOY_CMD_FACTORY="npm run deploy:factory -- --network ${NETWORK}"
echo -e "${YELLOW}2. Deploying Market Factory...${NC}"
run_deploy_command "${DEPLOY_CMD_FACTORY}" "critical"

DEPLOY_CMD_MARKETS="npm run create:markets -- --network ${NETWORK}"
echo -e "${YELLOW}3. Creating sample markets...${NC}"
run_deploy_command "${DEPLOY_CMD_MARKETS}" "" # Not critical

# Check if PM2 is installed, install if not
if ! command -v pm2 &> /dev/null; then
    echo -e "${YELLOW}Installing PM2 globally...${NC}"
    npm install -g pm2
fi

# Start the API server with PM2
echo -e "${YELLOW}Starting the API server with PM2...${NC}"
npm run start:pm2

echo -e "${GREEN}Setup completed!${NC}"
echo -e "${GREEN}API server is now running on http://localhost:3002${NC}"
echo -e "${GREEN}You can test the API using Postman with the included collection or visit the web UI at http://localhost:3002${NC}"

echo -e "${YELLOW}DEBUG: Final network check. NETWORK = ${NETWORK}${NC}"
if [ "$NETWORK" = "localhost" ]; then
    echo -e "${YELLOW}DEBUG: Condition '$NETWORK == localhost' is TRUE at end of script.${NC}"
    echo -e "${YELLOW}Note: To stop all services, run: npm run stop:pm2 && kill $HARDHAT_PID${NC}"
else
    echo -e "${YELLOW}DEBUG: Condition '$NETWORK == localhost' is FALSE at end of script.${NC}"
    echo -e "${YELLOW}Note: Contracts have been deployed to ${NETWORK}. To stop API server, run: npm run stop:pm2${NC}"
    # This assumes chainId 84532 is only for baseSepolia, might need adjustment for other networks
    if [ "$NETWORK" = "baseSepolia" ]; then
         echo -e "${YELLOW}Contracts are deployed on ${NETWORK} chain with chainId 84532${NC}"
    fi
fi