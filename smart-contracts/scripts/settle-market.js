/**
 * Script to settle a market by setting the result
 */
const { ethers } = require('hardhat');
const { 
    getDefaultWallet,
    getRoleSigner,
    setupProvider 
} = require('../utils/wallet-helper');
const fs = require('fs');
const path = require('path');

async function main() {
    try {
        // Get command line arguments
        const args = process.argv.slice(2);
        if (args.length < 2) {
            console.error('Usage: npx hardhat run scripts/settle-market.js --network <network> <marketAddress> <outcome>');
            console.error('  marketAddress: Address of the market to settle');
            console.error('  outcome: 1 for home win, 2 for away win');
            process.exit(1);
        }

        const marketAddress = args[0];
        const outcome = parseInt(args[1]);

        if (![1, 2].includes(outcome)) {
            console.error('Outcome must be 1 (home win) or 2 (away win)');
            process.exit(1);
        }

        // Setup provider and wallet (use results provider)
        const provider = setupProvider();
        const resultsProvider = getRoleSigner('resultsProvider', provider);
        
        console.log(`Using results provider address: ${resultsProvider.address}`);
        console.log(`Market address: ${marketAddress}`);
        console.log(`Setting outcome: ${outcome === 1 ? 'HOME WIN' : 'AWAY WIN'}`);

        // Connect to the Market
        const NBAMarket = await ethers.getContractFactory('NBAMarket', resultsProvider);
        const market = NBAMarket.attach(marketAddress);

        // Get market info
        const marketInfo = await market.getMarketInfo();
        console.log(`\nMarket: ${marketInfo[0]} vs ${marketInfo[1]}`);
        
        if (marketInfo[8]) { // gameEnded
            throw new Error("Market has already been settled");
        }

        // Set the result
        console.log("\nSettling market...");
        const tx = await market.setResult(outcome);
        await tx.wait();
        console.log(`Market settled successfully! Transaction hash: ${tx.hash}`);

        // Get updated market info
        const updatedInfo = await market.getMarketInfo();
        console.log(`\nMarket is now settled. Outcome: ${updatedInfo[9] === 1 ? 'HOME WIN' : 'AWAY WIN'}`);
        
        console.log("\nBets have been automatically settled and payouts processed.");
        console.log("Remaining funds have been returned to the liquidity pool.");
        console.log("\nMarket settled successfully! ✅");
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