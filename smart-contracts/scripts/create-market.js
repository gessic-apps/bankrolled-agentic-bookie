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
        console.error('Usage: npx hardhat run scripts/create-market.js --network <network> <homeTeam> <awayTeam> <gameTimestamp> <oddsApiId> [homeOdds] [awayOdds] [homeSpreadPoints] [homeSpreadOdds] [awaySpreadOdds] [totalPoints] [overOdds] [underOdds] [marketFunding]');
        console.error('Example: npx hardhat run scripts/create-market.js --network localhost "Lakers" "Celtics" 1680307200 "NBA_2023_LAL_BOS" 1850 2000 -75 1910 1910 2105 1910 1910 50000');
        console.error('Note: If moneyline odds are omitted (0), the market will be created without odds. All odds/lines are optional.');
        console.error('      marketFunding is optional (in USDX tokens)');
        process.exit(1);
    }
    
    const homeTeam = args[0];
    const awayTeam = args[1];
    const gameTimestamp = parseInt(args[2]);
    const oddsApiId = args[3];
    // Parse odds and lines, defaulting to 0 if not provided
    const homeOdds = args[4] ? parseInt(args[4]) : 0;
    const awayOdds = args[5] ? parseInt(args[5]) : 0;
    const homeSpreadPoints = args[6] ? parseInt(args[6]) : 0; // e.g., -75 for -7.5
    const homeSpreadOdds = args[7] ? parseInt(args[7]) : 0;
    const awaySpreadOdds = args[8] ? parseInt(args[8]) : 0;
    const totalPoints = args[9] ? parseInt(args[9]) : 0; // e.g., 2105 for 210.5
    const overOdds = args[10] ? parseInt(args[10]) : 0;
    const underOdds = args[11] ? parseInt(args[11]) : 0;
    const marketFunding = args[12] ? parseFloat(args[12]) : 0; // In USDX tokens
    
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
            console.log(`Moneyline: Home ${homeOdds} (${homeOdds/1000}) | Away ${awayOdds} (${awayOdds/1000})`);
        }
        if (homeSpreadOdds > 0 && awaySpreadOdds > 0) {
             // Display spread with one decimal place
            const displaySpread = homeSpreadPoints / 10;
            console.log(`Spread: Home ${displaySpread > 0 ? '+' : ''}${displaySpread} (${homeSpreadOdds/1000}) | Away ${-displaySpread > 0 ? '+' : ''}${-displaySpread} (${awaySpreadOdds/1000})`);
        }
        if (overOdds > 0 && underOdds > 0) {
             // Display total with one decimal place
            const displayTotal = totalPoints / 10;
            console.log(`Total: Over ${displayTotal} (${overOdds/1000}) | Under ${displayTotal} (${underOdds/1000})`);
        }
        
        if (homeOdds === 0) {
            console.log('Creating market without initial odds/lines');
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
        console.log(`Using wallet address: ${wallet.address}`);     
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
        
        // Always use createMarket; pass 0 for unprovided odds/lines
        tx = await marketFactory.createMarket(
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
            homeOdds,
            awayOdds,
            homeSpreadPoints,
            homeSpreadOdds,
            awaySpreadOdds,
            totalPoints,
            overOdds,
            underOdds,
            fundingAmount
        );
        
        console.log(`Transaction hash: ${tx.hash}`);
        
        // Wait for transaction to be mined
        console.log("Waiting for transaction confirmation...");
        const receipt = await tx.wait();
        
        console.log(`Transaction confirmed in block: ${receipt.blockNumber}`);
        console.log(`Gas used: ${receipt.gasUsed.toString()}`);
        
        // Find the MarketCreated event to get the market and odds addresses
        const marketFactoryInterface = new ethers.utils.Interface(marketFactory.interface.abi); // Get Interface from contract instance
        // Updated event signature: MarketCreated(address,address,string,string,uint256,string,uint256)
        const marketCreatedEventTopic = ethers.utils.id("MarketCreated(address,address,string,string,uint256,string,uint256)"); 

        const marketEventLog = receipt.logs.find(log => 
            log.topics[0] === marketCreatedEventTopic && log.address.toLowerCase() === marketFactory.address.toLowerCase()
        );
        
        if (marketEventLog) {
            const eventData = marketFactoryInterface.parseLog(marketEventLog);
            const marketAddress = eventData.args.marketAddress;
            const oddsContractAddress = eventData.args.oddsContractAddress;
            console.log(`\n✅ Market created successfully!`);
            console.log(`   NBAMarket Address: ${marketAddress}`);
            console.log(`   MarketOdds Address: ${oddsContractAddress}`);
            
            // Write market address to file for easy reference
            const marketsFile = path.join(__dirname, "../created-markets.json");
            let markets = [];
            
            if (fs.existsSync(marketsFile)) {
                const fileContent = fs.readFileSync(marketsFile, "utf8");
                markets = JSON.parse(fileContent);
            }
            
            markets.push({
                marketAddress: marketAddress, // Renamed for clarity
                oddsContractAddress: oddsContractAddress, // Added
                homeTeam,
                awayTeam,
                gameTimestamp,
                oddsApiId,
                homeOdds,
                awayOdds,
                homeSpreadPoints,
                homeSpreadOdds,
                awaySpreadOdds,
                totalPoints,
                overOdds,
                underOdds,
                createdAt: Math.floor(Date.now() / 1000)
            });
            
            fs.writeFileSync(marketsFile, JSON.stringify(markets, null, 2));
            console.log(`Market information saved to created-markets.json`);
        } else {
            console.error("❌ ERROR: Couldn't find MarketCreated event in transaction receipt. Market might not have been created correctly.");
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