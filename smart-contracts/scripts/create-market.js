/**
 * Script to create a new market using a private key
 */
const { ethers } = require('hardhat');
const { 
    getDefaultWallet,
    setupProvider 
} = require('../utils/wallet-helper');
const fs = require('fs');
const path = require('path');

async function main() {
    // Get command line arguments
    const args = process.argv.slice(2);
    
    if (args.length < 4) {
        console.error('Usage: npx hardhat run scripts/create-market.js --network <network> <homeTeam> <awayTeam> <gameTimestamp> <oddsApiId> [homeOdds] [awayOdds] [marketFunding]');
        console.error('Example: npx hardhat run scripts/create-market.js --network localhost "Lakers" "Celtics" 1680307200 "NBA_2023_LAL_BOS" 1850 2000 50000');
        console.error('Note: If homeOdds and awayOdds are omitted, the market will be created without initial odds');
        console.error('      marketFunding is optional and will use default if not provided (in USDX tokens)');
        process.exit(1);
    }
    
    const homeTeam = args[0];
    const awayTeam = args[1];
    const gameTimestamp = parseInt(args[2]);
    const oddsApiId = args[3];
    const homeOdds = args[4] ? parseInt(args[4]) : 0;
    const awayOdds = args[5] ? parseInt(args[5]) : 0;
    const marketFunding = args[6] ? parseFloat(args[6]) : 0; // In USDX tokens
    
    // Validate inputs
    if (isNaN(gameTimestamp)) {
        console.error('Game timestamp must be a valid number');
        process.exit(1);
    }
    
    try {
        // Setup provider and wallet
        const provider = setupProvider();
        const wallet = getDefaultWallet(provider);
        
        console.log(`Creating market for ${homeTeam} vs ${awayTeam}...`);
        console.log(`Game timestamp: ${gameTimestamp} (${new Date(gameTimestamp * 1000).toLocaleString()})`);
        console.log(`Odds API ID: ${oddsApiId}`);
        
        if (homeOdds > 0 && awayOdds > 0) {
            console.log(`Home odds: ${homeOdds} (${homeOdds/1000})`);
            console.log(`Away odds: ${awayOdds} (${awayOdds/1000})`);
        } else {
            console.log('Creating market without initial odds');
        }
        
        // Read deployed contracts info
        const deployedContractsPath = path.join(__dirname, "../deployed-contracts.json");
        let deployedContracts = {};
        
        if (fs.existsSync(deployedContractsPath)) {
            const fileContent = fs.readFileSync(deployedContractsPath, "utf8");
            deployedContracts = JSON.parse(fileContent);
        } else {
            throw new Error("deployed-contracts.json not found");
        }
        
        if (!deployedContracts.marketFactory) {
            throw new Error("Market Factory address not found in deployed-contracts.json");
        }
        
        // Get MarketFactory contract
        const MarketFactory = await ethers.getContractFactory('MarketFactory', wallet);
        const marketFactory = MarketFactory.attach(deployedContracts.marketFactory);
        
        console.log(`Using MarketFactory at: ${deployedContracts.marketFactory}`);
        
        // Prepare funding amount if provided
        const fundingAmount = marketFunding > 0 
            ? ethers.utils.parseUnits(marketFunding.toString(), 6) // Convert to USDX units (6 decimals)
            : 0;
            
        if (marketFunding > 0) {
            console.log(`Market funding: ${marketFunding} USDX`);
        } else {
            console.log('Using default market funding');
        }
        
        // Create the market
        console.log("\nCreating market...");
        let tx;
        
        if (homeOdds === 0 || awayOdds === 0) {
            // Create market without odds
            tx = await marketFactory.createMarketWithoutOdds(
                homeTeam,
                awayTeam,
                gameTimestamp,
                oddsApiId,
                fundingAmount
            );
        } else {
            // Create market with odds
            tx = await marketFactory.createMarket(
                homeTeam,
                awayTeam,
                gameTimestamp,
                oddsApiId,
                homeOdds,
                awayOdds,
                fundingAmount
            );
        }
        
        console.log(`Transaction hash: ${tx.hash}`);
        
        // Wait for transaction to be mined
        console.log("Waiting for transaction confirmation...");
        const receipt = await tx.wait();
        
        console.log(`Transaction confirmed in block: ${receipt.blockNumber}`);
        console.log(`Gas used: ${receipt.gasUsed.toString()}`);
        
        // Find MarketCreated event to get market address
        const marketCreatedEvent = receipt.events.find(e => e.event === 'MarketCreated');
        
        if (marketCreatedEvent) {
            const marketAddress = marketCreatedEvent.args[0];
            console.log(`\n✅ Market created successfully at address: ${marketAddress}`);
            
            // Write market address to file for easy reference
            const marketsFile = path.join(__dirname, "../created-markets.json");
            let markets = [];
            
            if (fs.existsSync(marketsFile)) {
                const fileContent = fs.readFileSync(marketsFile, "utf8");
                markets = JSON.parse(fileContent);
            }
            
            markets.push({
                address: marketAddress,
                homeTeam,
                awayTeam,
                gameTimestamp,
                oddsApiId,
                homeOdds,
                awayOdds,
                createdAt: Math.floor(Date.now() / 1000)
            });
            
            fs.writeFileSync(marketsFile, JSON.stringify(markets, null, 2));
            console.log(`Market information saved to created-markets.json`);
        } else {
            console.warn("Couldn't find MarketCreated event in transaction receipt");
        }
    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    }
}

// Execute main function
main()
    .then(() => process.exit(0))
    .catch(error => {
        console.error(error);
        process.exit(1);
    });