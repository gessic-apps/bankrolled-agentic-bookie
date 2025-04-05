/**
 * Script to create a new market using a private key
 */
const { ethers } = require('hardhat');
const { 
    signAndSendTransaction,
    setupProvider 
} = require('../utils/wallet-helper');
const MarketFactoryJson = require('../artifacts/contracts/MarketFactory.sol/MarketFactory.json');

async function main() {
    // Get command line arguments
    const args = process.argv.slice(2);
    
    if (args.length < 4) {
        console.error('Usage: node create-market.js <factoryAddress> <homeTeam> <awayTeam> <gameTimestamp> [homeOdds] [awayOdds]');
        console.error('Example: node create-market.js 0x1234... "Lakers" "Celtics" 1680307200 1850 2000');
        console.error('Note: If homeOdds and awayOdds are omitted, the market will be created without initial odds');
        process.exit(1);
    }
    
    const factoryAddress = args[0];
    const homeTeam = args[1];
    const awayTeam = args[2];
    const gameTimestamp = parseInt(args[3]);
    const homeOdds = args[4] ? parseInt(args[4]) : undefined;
    const awayOdds = args[5] ? parseInt(args[5]) : undefined;
    
    // Validate inputs
    if (!ethers.utils.isAddress(factoryAddress)) {
        console.error('Invalid factory address format');
        process.exit(1);
    }
    
    if (isNaN(gameTimestamp)) {
        console.error('Game timestamp must be a valid number');
        process.exit(1);
    }
    
    if ((homeOdds && !awayOdds) || (!homeOdds && awayOdds)) {
        console.error('Both homeOdds and awayOdds must be provided or both omitted');
        process.exit(1);
    }
    
    try {
        // Setup provider
        const provider = setupProvider();
        
        console.log(`Creating market for ${homeTeam} vs ${awayTeam}...`);
        console.log(`Game timestamp: ${gameTimestamp} (${new Date(gameTimestamp * 1000).toLocaleString()})`);
        
        let result;
        
        if (homeOdds && awayOdds) {
            // Create market with odds
            console.log(`Home odds: ${homeOdds} (${homeOdds/1000})`);
            console.log(`Away odds: ${awayOdds} (${awayOdds/1000})`);
            
            result = await signAndSendTransaction({
                contractAddress: factoryAddress,
                contractAbi: MarketFactoryJson.abi,
                method: 'createMarket',
                params: [homeTeam, awayTeam, gameTimestamp, homeOdds, awayOdds],
                role: 'admin'  // This will use the admin's private key
            }, provider);
        } else {
            // Create market without odds
            console.log('Creating market without initial odds');
            
            result = await signAndSendTransaction({
                contractAddress: factoryAddress,
                contractAbi: MarketFactoryJson.abi,
                method: 'createMarketWithoutOdds',
                params: [homeTeam, awayTeam, gameTimestamp],
                role: 'admin'  // This will use the admin's private key
            }, provider);
        }
        
        if (result.success) {
            console.log(`✅ Market created successfully!`);
            console.log(`Transaction hash: ${result.transaction}`);
            console.log(`Block number: ${result.receipt.blockNumber}`);
            console.log(`Gas used: ${result.receipt.gasUsed}`);
            
            // Parse logs to get the market address
            const provider = setupProvider();
            const receipt = await provider.getTransactionReceipt(result.transaction);
            const factory = new ethers.Contract(factoryAddress, MarketFactoryJson.abi, provider);
            
            // Find MarketCreated event
            const eventName = 'MarketCreated';
            const event = receipt.logs
                .map(log => {
                    try {
                        return factory.interface.parseLog(log);
                    } catch (e) {
                        return null;
                    }
                })
                .filter(event => event !== null && event.name === eventName)[0];
            
            if (event) {
                const marketAddress = event.args[0];
                console.log(`Market address: ${marketAddress}`);
            }
        } else {
            console.error(`❌ Failed to create market: ${result.error}`);
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