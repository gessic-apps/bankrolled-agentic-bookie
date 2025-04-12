/**
 * Script to place a bet on a market (moneyline, spread, or total)
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
        if (args.length < 4) {
            console.error('Usage: npx hardhat run scripts/place-bet.js --network <network> <marketAddress> <betAmount> <betType> <betSide>');
            console.error('  marketAddress: Address of the market');
            console.error('  betAmount: Amount in USDX tokens (e.g., \"10\")');
            console.error('  betType: \"moneyline\", \"spread\", or \"total\"');
            console.error('  betSide: ');
            console.error('    - For moneyline/spread: \"home\" or \"away\"');
            console.error('    - For total: \"over\" or \"under\"');
            process.exit(1);
        }

        const marketAddress = args[0];
        const betAmount = args[1]; // Amount in tokens (e.g., "10" for 10 USDX)
        const betTypeStr = args[2].toLowerCase();
        const betSideStr = args[3].toLowerCase();

        // Validate bet type
        let betTypeEnum;
        if (betTypeStr === 'moneyline') {
            betTypeEnum = 0; // Corresponds to BettingEngine.BetType.MONEYLINE
        } else if (betTypeStr === 'spread') {
            betTypeEnum = 1; // Corresponds to BettingEngine.BetType.SPREAD
        } else if (betTypeStr === 'total') {
            betTypeEnum = 2; // Corresponds to BettingEngine.BetType.TOTAL
        } else if (betTypeStr === 'draw') {
            betTypeEnum = 3; // Corresponds to BettingEngine.BetType.DRAW
        } else {
            console.error('Invalid betType. Must be \"moneyline\", \"spread\", \"total\", or \"draw\"');
            process.exit(1);
        }

        // Validate bet side based on type
        let isBettingOnHomeOrOver;
        if (betTypeEnum === 0 || betTypeEnum === 1) { // Moneyline or Spread
            if (betSideStr === 'home') {
                isBettingOnHomeOrOver = true;
            } else if (betSideStr === 'away') {
                isBettingOnHomeOrOver = false;
            } else {
                console.error('Invalid betSide for moneyline/spread. Must be \"home\" or \"away\"');
                process.exit(1);
            }
        } else if (betTypeEnum === 2) { // Total
            if (betSideStr === 'over') {
                isBettingOnHomeOrOver = true;
            } else if (betSideStr === 'under') {
                isBettingOnHomeOrOver = false;
            } else {
                console.error('Invalid betSide for total. Must be \"over\" or \"under\"');
                process.exit(1);
            }
        } else if (betTypeEnum === 3) { // Draw
            // For draw bets, the side parameter isn't used but we'll set it to true for consistency
            isBettingOnHomeOrOver = true;
            console.log('Draw bet selected - side parameter is ignored for draw bets');
        }

        // Setup provider and wallet
        const provider = setupProvider();
        const wallet = getDefaultWallet(provider);
        
        console.log(`Using wallet address: ${wallet.address}`);
        console.log(`Market address: ${marketAddress}`);
        console.log(`Bet amount: ${betAmount} USDX`);
        console.log(`Bet Type: ${betTypeStr}`);
        console.log(`Bet Side: ${betSideStr}`);

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

        // Get market info - use new getters
        const details = await market.getMarketDetails();
        const fullOdds = await market.getFullOdds();
        const marketStatus = details._marketStatus; // Enum index

        console.log(`\nMarket: ${details._homeTeam} vs ${details._awayTeam}`);
        console.log(`Status: ${marketStatus}`); // TODO: Map index to string?
        console.log(`Moneyline: Home ${fullOdds._homeOdds/1000} | Away ${fullOdds._awayOdds/1000}`);
        console.log(`Spread: Home ${fullOdds._homeSpreadPoints/10} (${fullOdds._homeSpreadOdds/1000}) | Away ${-fullOdds._homeSpreadPoints/10} (${fullOdds._awaySpreadOdds/1000})`);
        console.log(`Total: Over ${fullOdds._totalPoints/10} (${fullOdds._overOdds/1000}) | Under ${fullOdds._totalPoints/10} (${fullOdds._underOdds/1000})`);

        // Check if market is open (assuming 1 is OPEN state)
        if (marketStatus !== 1) {
            throw new Error(`Market is not open for betting (Status: ${marketStatus})`);
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
        // Call the updated placeBet function
        const betTx = await market.placeBet(
            betTypeEnum, 
            betAmountInTokens, 
            isBettingOnHomeOrOver
        );
        await betTx.wait();
        console.log(`Bet placed successfully! Transaction hash: ${betTx.hash}`);

        // Get user's bets
        const userBets = await market.getBettorBets(wallet.address);
        const latestBetId = userBets[userBets.length - 1];
        const betDetails = await market.getBetDetails(latestBetId);

        // betDetails mapping: [bettor, amount, potentialWinnings, betType, isBettingOnHomeOrOver, line, odds, settled, won]
        console.log("\nBet details:");
        console.log(`Bet ID: ${latestBetId}`);
        console.log(`Amount: ${ethers.utils.formatUnits(betDetails.amount, 6)} USDX`);
        console.log(`Potential winnings: ${ethers.utils.formatUnits(betDetails.potentialWinnings, 6)} USDX`);
        console.log(`Bet Type: ${betDetails.betType}`); // Shows enum index
        console.log(`Side: ${betDetails.isBettingOnHomeOrOver}`); // true=Home/Over, false=Away/Under
        console.log(`Line: ${betDetails.line.toString()}`); // Spread or Total points line
        console.log(`Odds: ${betDetails.odds.toString()} (${betDetails.odds / 1000})`);
        console.log(`Total payout if won: ${ethers.utils.formatUnits(betDetails.amount.add(betDetails.potentialWinnings), 6)} USDX`);

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