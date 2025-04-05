/**
 * Script to update odds for a market using a private key
 */
const { ethers } = require('hardhat');
const { 
    signAndSendTransaction,
    setupProvider 
} = require('../utils/wallet-helper');
const NBAMarketJson = require('../artifacts/contracts/NBAMarket.sol/NBAMarket.json');

async function main() {
    // Get command line arguments
    const args = process.argv.slice(2);
    
    if (args.length < 3) {
        console.error('Usage: node update-odds.js <marketAddress> <homeOdds> <awayOdds>');
        console.error('Example: node update-odds.js 0x1234... 1850 2000');
        process.exit(1);
    }
    
    const marketAddress = args[0];
    const homeOdds = parseInt(args[1]);
    const awayOdds = parseInt(args[2]);
    
    // Validate inputs
    if (!ethers.utils.isAddress(marketAddress)) {
        console.error('Invalid market address format');
        process.exit(1);
    }
    
    if (isNaN(homeOdds) || isNaN(awayOdds)) {
        console.error('Home odds and away odds must be valid numbers');
        process.exit(1);
    }
    
    if (homeOdds < 1000 || awayOdds < 1000) {
        console.error('Odds must be at least 1.000 (1000)');
        process.exit(1);
    }
    
    try {
        // Setup provider
        const provider = setupProvider();
        
        console.log(`Updating odds for market ${marketAddress}...`);
        console.log(`Home odds: ${homeOdds} (${homeOdds/1000})`);
        console.log(`Away odds: ${awayOdds} (${awayOdds/1000})`);
        
        // Sign and send transaction as the odds provider
        const result = await signAndSendTransaction({
            contractAddress: marketAddress,
            contractAbi: NBAMarketJson.abi,
            method: 'updateOdds',
            params: [homeOdds, awayOdds],
            role: 'oddsProvider'  // This will use the odds provider's private key
        }, provider);
        
        if (result.success) {
            console.log(`✅ Odds updated successfully!`);
            console.log(`Transaction hash: ${result.transaction}`);
            console.log(`Block number: ${result.receipt.blockNumber}`);
            console.log(`Gas used: ${result.receipt.gasUsed}`);
        } else {
            console.error(`❌ Failed to update odds: ${result.error}`);
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