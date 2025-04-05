/**
 * Script to place a bet on a market
 */
const { ethers } = require('hardhat');
const { 
    getDefaultWallet,
    setupProvider 
} = require('../utils/wallet-helper');
const fs = require('fs');
const path = require('path');

async function main() {
    try {
        // Get command line arguments
        const args = process.argv.slice(2);
        if (args.length < 3) {
            console.error('Usage: npx hardhat run scripts/place-bet.js --network <network> <marketAddress> <betAmount> <onHomeTeam>');
            console.error('  marketAddress: Address of the market to bet on');
            console.error('  betAmount: Amount to bet in USDX tokens');
            console.error('  onHomeTeam: true to bet on home team, false to bet on away team');
            process.exit(1);
        }

        const marketAddress = args[0];
        const betAmount = args[1]; // Amount in tokens (e.g., "10" for 10 USDX)
        const onHomeTeam = args[2].toLowerCase() === 'true';

        // Setup provider and wallet
        const provider = setupProvider();
        const wallet = getDefaultWallet(provider);
        
        console.log(`Using wallet address: ${wallet.address}`);
        console.log(`Market address: ${marketAddress}`);
        console.log(`Bet amount: ${betAmount} USDX`);
        console.log(`Betting on: ${onHomeTeam ? 'Home Team' : 'Away Team'}`);

        // Read deployed contracts info
        const deployedContractsPath = path.join(__dirname, "../deployed-contracts.json");
        let deployedContracts = {};
        
        if (fs.existsSync(deployedContractsPath)) {
            const fileContent = fs.readFileSync(deployedContractsPath, "utf8");
            deployedContracts = JSON.parse(fileContent);
        } else {
            throw new Error("deployed-contracts.json not found");
        }

        // Connect to USDX token
        const USDX = await ethers.getContractFactory('USDX', wallet);
        const usdx = USDX.attach(deployedContracts.usdx);

        // Connect to the Market
        const NBAMarket = await ethers.getContractFactory('NBAMarket', wallet);
        const market = NBAMarket.attach(marketAddress);

        // Get market info
        const marketInfo = await market.getMarketInfo();
        console.log(`\nMarket: ${marketInfo[0]} vs ${marketInfo[1]}`);
        console.log(`Home odds: ${marketInfo[4] / 1000}`);
        console.log(`Away odds: ${marketInfo[5] / 1000}`);
        console.log(`Ready for betting: ${await market.isReadyForBetting()}`);

        if (!await market.isReadyForBetting()) {
            throw new Error("Market is not ready for betting");
        }

        // Convert bet amount to USDX units (6 decimals)
        const betAmountInTokens = ethers.utils.parseUnits(betAmount, 6);

        // Check USDX balance
        const balance = await usdx.balanceOf(wallet.address);
        console.log(`USDX Balance: ${ethers.utils.formatUnits(balance, 6)} USDX`);

        if (balance.lt(betAmountInTokens)) {
            throw new Error(`Insufficient USDX balance. Have ${ethers.utils.formatUnits(balance, 6)}, need ${betAmount}`);
        }

        // Approve USDX spend
        console.log("Approving USDX tokens for betting...");
        const approveTx = await usdx.approve(marketAddress, betAmountInTokens);
        await approveTx.wait();
        console.log(`Approval transaction hash: ${approveTx.hash}`);

        // Place the bet
        console.log("\nPlacing bet...");
        const betTx = await market.placeBet(betAmountInTokens, onHomeTeam);
        await betTx.wait();
        console.log(`Bet placed successfully! Transaction hash: ${betTx.hash}`);

        // Get user's bets
        const userBets = await market.getBettorBets(wallet.address);
        const latestBet = userBets[userBets.length - 1];
        const betDetails = await market.getBetDetails(latestBet);

        console.log("\nBet details:");
        console.log(`Bet ID: ${latestBet}`);
        console.log(`Amount: ${ethers.utils.formatUnits(betDetails[1], 6)} USDX`);
        console.log(`Potential winnings: ${ethers.utils.formatUnits(betDetails[2], 6)} USDX`);
        console.log(`Team: ${betDetails[3] ? 'Home Team' : 'Away Team'}`);
        console.log(`Total payout if won: ${ethers.utils.formatUnits(betDetails[1].add(betDetails[2]), 6)} USDX`);

        console.log("\nBet placed successfully! ✅");
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