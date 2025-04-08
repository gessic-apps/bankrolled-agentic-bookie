/**
 * Script to settle a market by setting the final scores
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
        if (args.length < 3) { // Need network, market address, home score, away score
            console.error('Usage: npx hardhat run scripts/settle-market.js --network <network> <marketAddress> <homeScore> <awayScore>');
            console.error('  marketAddress: Address of the market to settle');
            console.error('  homeScore: Final score of the home team');
            console.error('  awayScore: Final score of the away team');
            process.exit(1);
        }

        const marketAddress = args[0];
        const homeScore = parseInt(args[1]);
        const awayScore = parseInt(args[2]);

        if (isNaN(homeScore) || isNaN(awayScore) || homeScore < 0 || awayScore < 0) {
            console.error('Scores must be non-negative integers.');
            process.exit(1);
        }

        // Setup provider and wallet (use results provider)
        const provider = setupProvider();
        const resultsProvider = getRoleSigner('resultsProvider', provider);
        
        console.log(`Using results provider address: ${resultsProvider.address}`);
        console.log(`Market address: ${marketAddress}`);
        console.log(`Setting final score: Home ${homeScore} - Away ${awayScore}`);

        // Connect to the Market
        const NBAMarket = await ethers.getContractFactory('NBAMarket', resultsProvider);
        const market = NBAMarket.attach(marketAddress);

        // Get market info (assuming a getter like getMarketDetails exists)
        // Note: The old getMarketInfo index mapping is no longer valid
        // Let's get specific details instead or use the new getMarketDetails
        const details = await market.getMarketDetails(); 
        console.log(`\nMarket: ${details._homeTeam} vs ${details._awayTeam}`);
        
        const currentStatus = details._marketStatus; // Assuming enum index 0=PENDING, 1=OPEN, 2=STARTED, 3=SETTLED, 4=CANCELLED
        if (currentStatus === 3 || currentStatus === 4) { // SETTLED or CANCELLED
            throw new Error(`Market cannot be settled. Current status: ${currentStatus}`);
        }
        if (details._resultSettled) {
            throw new Error("Result has already been settled for this market.");
        }

        // Set the result using scores
        console.log("\nSetting result and settling market...");
        const tx = await market.setResult(homeScore, awayScore);
        const receipt = await tx.wait();
        console.log(`Market result set successfully! Transaction hash: ${tx.hash}`);
        console.log(`Gas used: ${receipt.gasUsed.toString()}`);

        // Get updated market info
        const updatedDetails = await market.getMarketDetails();
        console.log(`\nMarket is now settled. Final Score: Home ${updatedDetails._homeScore}, Away ${updatedDetails._awayScore}`);
        console.log(`New Status: ${updatedDetails._marketStatus}`);
        
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