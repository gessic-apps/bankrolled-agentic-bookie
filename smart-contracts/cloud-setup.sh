#!/bin/bash

# Cloud Deployment Script for Smart Contracts API Server

# Text formatting
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up the Smart Contracts API Server on cloud...${NC}"

# Update system packages
echo -e "${YELLOW}Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Install required dependencies
echo -e "${YELLOW}Installing required dependencies...${NC}"
sudo apt-get install -y curl git build-essential

# Install Node.js 16.x
echo -e "${YELLOW}Installing Node.js 16.x...${NC}"
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt-get install -y nodejs

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js installation failed. Please check the error messages above.${NC}"
    exit 1
fi

# Install PM2 globally
echo -e "${YELLOW}Installing PM2 globally...${NC}"
sudo npm install -g pm2

# Create app directory
echo -e "${YELLOW}Creating application directory...${NC}"
mkdir -p ~/bankrolled-agent-bookie
cd ~/bankrolled-agent-bookie

# Clone the repository (or use existing files)
if [ -d "smart-contracts" ]; then
    echo -e "${YELLOW}Using existing smart-contracts directory...${NC}"
    cd smart-contracts
else
    echo -e "${YELLOW}Cloning repository...${NC}"
    git clone https://github.com/your-username/bankrolled-agent-bookie.git .
    cd smart-contracts
fi

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
npm install

# Compile contracts
echo -e "${YELLOW}Compiling smart contracts...${NC}"
npm run compile

# Setup .env file with production settings
echo -e "${YELLOW}Setting up .env file...${NC}"
cat > .env << EOF
# Server Configuration
PORT=3000
NODE_ENV=production

# Blockchain Configuration
# Add your configuration here
PRIVATE_KEY=your_private_key_here
TESTNET_RPC_URL=your_testnet_rpc_url_here
EOF

echo -e "${YELLOW}Please edit the .env file with your actual private key and RPC URL${NC}"
echo -e "${YELLOW}Run: nano .env${NC}"

# Setup firewall (if using cloud instance)
echo -e "${YELLOW}Setting up firewall...${NC}"
sudo ufw allow ssh
sudo ufw allow 3000/tcp
sudo ufw --force enable

# Setup PM2 to start on boot
echo -e "${YELLOW}Setting up PM2 to start on boot...${NC}"
pm2 startup
sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u $USER --hp $HOME

# Start the API server with PM2
echo -e "${YELLOW}Starting the API server with PM2...${NC}"
npm run start:pm2
pm2 save

echo -e "${GREEN}Setup completed!${NC}"
echo -e "${GREEN}API server is now running on http://your-server-ip:3000${NC}"
echo -e "${GREEN}You can test the API using Postman with the included collection.${NC}"
echo -e "${YELLOW}Note: Make sure to update the .env file with your actual private key and RPC URL${NC}"
echo -e "${YELLOW}To check server status, run: pm2 monit${NC}"