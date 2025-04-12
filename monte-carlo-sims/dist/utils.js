"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.decimalToImpliedProbability = decimalToImpliedProbability;
exports.calculateMarketMargin = calculateMarketMargin;
exports.printSimulationResults = printSimulationResults;
exports.createSampleMarket = createSampleMarket;
exports.createDefaultConfig = createDefaultConfig;
const cli_table3_1 = __importDefault(require("cli-table3"));
/**
 * Convert decimal odds to implied probability
 */
function decimalToImpliedProbability(decimalOdds) {
    return 1 / decimalOdds;
}
/**
 * Calculate market margin (overround)
 */
function calculateMarketMargin(market) {
    let totalImpliedProb = 0;
    Object.values(market.impliedProbabilities).forEach(prob => {
        if (prob !== undefined) {
            totalImpliedProb += prob;
        }
    });
    // Margin is how much over 100% the total implied probabilities are
    return totalImpliedProb - 1;
}
/**
 * Pretty print the simulation results to the console
 */
function printSimulationResults(market, config, result) {
    console.log('\n📊 SPORTSBOOK RISK SIMULATOR - MONTE CARLO ANALYSIS 📊\n');
    // Market details
    const marketTable = new cli_table3_1.default({
        head: ['Market Details', 'Value'],
        colWidths: [25, 55]
    });
    marketTable.push(['Market ID', market.id], ['Market Name', market.name], ['Sport/League', `${market.sport} / ${market.league}`], ['Market Type', market.marketType], ['Current Liquidity', `$${market.currentLiquidity.toLocaleString()}`], ['Start Time', market.startTime.toLocaleString()]);
    console.log(marketTable.toString());
    console.log('');
    // Simulation config
    const configTable = new cli_table3_1.default({
        head: ['Simulation Config', 'Value'],
        colWidths: [25, 25]
    });
    configTable.push(['Simulations', config.numSimulations.toLocaleString()], ['Simulated Users', config.numUsers.toLocaleString()], ['Avg. Bets Per User', config.avgBetsPerUser.toLocaleString()], ['Risk Tolerance', config.riskTolerance.toFixed(2)], ['Target Margin', `${(config.targetMargin * 100).toFixed(2)}%`], ['Max Exposure', `${(config.maxExposurePercentage * 100).toFixed(2)}%`], ['Betting Period', `${config.bettingPeriodHours} hours`]);
    console.log(configTable.toString());
    console.log('');
    // Original vs Updated Odds and Limits
    const oddsTable = new cli_table3_1.default({
        head: ['Outcome', 'Original Odds', 'Updated Odds', 'Δ', 'Original Limit', 'Updated Limit', 'Δ'],
        colWidths: [10, 15, 15, 10, 15, 15, 10]
    });
    for (const outcome of Object.keys(market.currentOdds)) {
        if (market.currentOdds[outcome] === undefined)
            continue;
        const originalOdds = market.currentOdds[outcome];
        const updatedOdds = result.updatedMarket.currentOdds[outcome];
        const oddsChange = ((updatedOdds / originalOdds) - 1) * 100;
        const originalLimit = market.betLimits[outcome];
        const updatedLimit = result.updatedMarket.betLimits[outcome];
        const limitChange = ((updatedLimit / originalLimit) - 1) * 100;
        oddsTable.push([
            outcome,
            originalOdds.toFixed(2),
            updatedOdds.toFixed(2),
            `${oddsChange > 0 ? '+' : ''}${oddsChange.toFixed(2)}%`,
            `$${originalLimit.toLocaleString()}`,
            `$${updatedLimit.toLocaleString()}`,
            `${limitChange > 0 ? '+' : ''}${limitChange.toFixed(2)}%`
        ]);
    }
    console.log('ODDS & LIMITS RECOMMENDATIONS:');
    console.log(oddsTable.toString());
    console.log('');
    // Liquidity recommendation
    console.log('LIQUIDITY RECOMMENDATION:');
    console.log(`Original: $${market.currentLiquidity.toLocaleString()}`);
    console.log(`Updated: $${result.updatedMarket.currentLiquidity.toLocaleString()}`);
    const liquidityChange = ((result.updatedMarket.currentLiquidity / market.currentLiquidity) - 1) * 100;
    console.log(`Change: ${liquidityChange > 0 ? '+' : ''}${liquidityChange.toFixed(2)}%`);
    console.log('');
    // Risk metrics
    const riskTable = new cli_table3_1.default({
        head: ['Risk Metric', 'Value'],
        colWidths: [25, 25]
    });
    riskTable.push(['Value at Risk (95%)', `$${result.riskMetrics.valueAtRisk.toLocaleString()}`], ['Expected Shortfall', `$${result.riskMetrics.expectedShortfall.toLocaleString()}`], ['Sharpe Ratio', result.riskMetrics.sharpeRatio.toFixed(3)], ['Max Drawdown', `$${result.riskMetrics.maxDrawdown.toLocaleString()}`], ['Exposure Concentration', `${(result.riskMetrics.exposureConcentration * 100).toFixed(2)}%`], ['Expected P&L', `$${result.profitLoss.toLocaleString()}`]);
    console.log('RISK ASSESSMENT:');
    console.log(riskTable.toString());
    console.log('');
    // Simulation stats
    const statsTable = new cli_table3_1.default({
        head: ['Simulation Stat', 'Value'],
        colWidths: [25, 25]
    });
    statsTable.push(['Total Bets', result.simulationStats.totalBets.toFixed(0)], ['Avg. Bet Size', `$${result.simulationStats.avgBetSize.toLocaleString()}`], ['Worst Case P&L', `$${result.simulationStats.worstCaseScenario.toLocaleString()}`], ['Best Case P&L', `$${result.simulationStats.bestCaseScenario.toLocaleString()}`]);
    console.log('SIMULATION STATISTICS:');
    console.log(statsTable.toString());
    // Bet distribution
    const distributionTable = new cli_table3_1.default({
        head: ['Outcome', 'Bet Distribution'],
        colWidths: [10, 25]
    });
    for (const outcome of Object.keys(result.simulationStats.betOutcomeDistribution)) {
        const distribution = result.simulationStats.betOutcomeDistribution[outcome];
        if (distribution !== undefined) {
            distributionTable.push([
                outcome,
                `${(distribution * 100).toFixed(2)}%`
            ]);
        }
    }
    console.log('\nBET DISTRIBUTION:');
    console.log(distributionTable.toString());
    console.log('');
}
/**
 * Create a sample market for testing
 */
function createSampleMarket() {
    // Current date/time
    const now = new Date();
    // Game starts in 3 hours
    const startTime = new Date(now.getTime() + 3 * 60 * 60 * 1000);
    const homeOdds = 1.8; // Slight favorite
    const awayOdds = 2.2;
    const drawOdds = 3.4;
    return {
        id: 'market-' + Math.floor(Math.random() * 10000),
        name: 'Manchester United vs. Liverpool',
        currentOdds: {
            home: homeOdds,
            away: awayOdds,
            draw: drawOdds
        },
        impliedProbabilities: {
            home: decimalToImpliedProbability(homeOdds),
            away: decimalToImpliedProbability(awayOdds),
            draw: decimalToImpliedProbability(drawOdds)
        },
        currentLiquidity: 50000,
        betLimits: {
            home: 5000,
            away: 5000,
            draw: 3000
        },
        exposures: {
            home: 0,
            away: 0,
            draw: 0
        },
        marketType: 'moneyline',
        marketStatus: 'open',
        startTime: startTime,
        sport: 'Soccer',
        league: 'English Premier League'
    };
}
/**
 * Create default simulation config
 */
function createDefaultConfig() {
    return {
        numSimulations: 1000,
        numUsers: 200,
        avgBetsPerUser: 1.5,
        maxBankroll: 1000000,
        riskTolerance: 0.6,
        targetMargin: 0.05,
        maxExposurePercentage: 0.3,
        oddsAdjustmentFactor: 0.5,
        bettingPeriodHours: 3,
        maxOddsVariation: 0.1
    };
}
