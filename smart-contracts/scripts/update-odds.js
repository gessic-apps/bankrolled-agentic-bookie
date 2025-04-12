/**
 * Script to update odds for a market using a private key
 * NOTE: This script now interacts with the separate MarketOdds contract.
 */
const { ethers } = require('hardhat');
const { 
    signAndSendTransaction,
    getRoleSigner, // Need this to interact with NBAMarket first
    setupProvider 
} = require('../utils/wallet-helper');
const NBAMarketJson = require('../artifacts/contracts/NBAMarket.sol/NBAMarket.json');
const MarketOddsJson = require('../artifacts/contracts/MarketOdds.sol/MarketOdds.json'); // Add MarketOdds ABI

async function main() {
    // Get command line arguments
    const args = process.argv.slice(2);
    
    if (args.length < 8) { // Need market address + 7 values
        console.error('Usage: node update-odds.js <marketAddress> <homeOdds> <awayOdds> <drawOdds> <homeSpreadPoints> <homeSpreadOdds> <awaySpreadOdds> <totalPoints> <overOdds> <underOdds>');
        console.error('Example: node update-odds.js 0x123... 1850 2000 3000 -75 1910 1910 2105 1910 1910');
        console.error('Note: Provide all values. Use 0 for lines/odds you don\'t want to set (but ensure valid combinations)');
        process.exit(1);
    }
    
    const marketAddress = args[0];
    const homeOdds = parseInt(args[1]);
    const awayOdds = parseInt(args[2]);
    const drawOdds = parseInt(args[3]);
    const homeSpreadPoints = parseInt(args[4]); // e.g., -75 for -7.5
    const homeSpreadOdds = parseInt(args[5]);
    const awaySpreadOdds = parseInt(args[6]);
    const totalPoints = parseInt(args[7]); // e.g., 2105 for 210.5
    const overOdds = parseInt(args[8]);
    const underOdds = parseInt(args[9]);
    
    // Validate inputs
    if (!ethers.utils.isAddress(marketAddress)) {
        console.error('Invalid market address format');
        process.exit(1);
    }
    
    if (isNaN(homeOdds) || isNaN(awayOdds) || isNaN(drawOdds) || isNaN(homeSpreadPoints) || isNaN(homeSpreadOdds) || isNaN(awaySpreadOdds) || isNaN(totalPoints) || isNaN(overOdds) || isNaN(underOdds)) {
        console.error('All odds and points values must be valid numbers');
        process.exit(1);
    }
    
    // Basic validation - more comprehensive checks are in the contract
    if (homeOdds < 1000 || awayOdds < 1000) {
        console.error('Moneyline odds must be at least 1.000 (1000)');
        process.exit(1);
    }
    
    try {
        // Setup provider and odds provider signer
        const provider = setupProvider();
        const oddsSigner = getRoleSigner('oddsProvider', provider);
        if (!oddsSigner) throw new Error("Could not get signer for oddsProvider role.");
        
        console.log(`Updating odds for market ${marketAddress}...`);
        console.log(`ML: Home ${homeOdds} | Away ${awayOdds} | Draw ${drawOdds}`);
        console.log(`Spread: Home ${homeSpreadPoints/10} (${homeSpreadOdds}) | Away ${-homeSpreadPoints/10} (${awaySpreadOdds})`);
        console.log(`Total: Over ${totalPoints/10} (${overOdds}) | Under ${totalPoints/10} (${underOdds})`);
        
        // 1. Get the MarketOdds contract address from the NBAMarket contract
        console.log("Fetching MarketOdds contract address from NBAMarket...");
        const nbaMarketContract = new ethers.Contract(marketAddress, NBAMarketJson.abi, provider); // Use provider for read-only call
        const marketOddsAddress = await nbaMarketContract.getMarketOddsContract();
        console.log(`MarketOdds contract address: ${marketOddsAddress}`);

        if (!marketOddsAddress || marketOddsAddress === ethers.constants.AddressZero) {
            throw new Error(`MarketOdds contract address not found or is zero address for market ${marketAddress}`);
        }

        // Sign and send transaction as the odds provider
        // 2. Send the transaction to the MarketOdds contract address
        const result = await signAndSendTransaction({
            contractAddress: marketOddsAddress, // Target the MarketOdds contract
            contractAbi: MarketOddsJson.abi,   // Use MarketOdds ABI
            method: 'updateOdds',
            params: [ // Ensure correct order and type
                homeOdds,
                awayOdds,
                drawOdds,
                homeSpreadPoints,
                homeSpreadOdds,
                awaySpreadOdds,
                totalPoints,
                overOdds,
                underOdds
            ],
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