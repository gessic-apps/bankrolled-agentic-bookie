#!/usr/bin/env node
import { program } from 'commander';
import { RiskSimulator } from './simulator';
import { Market, SimulationConfig } from './types';
import { createSampleMarket, createDefaultConfig, printSimulationResults, decimalToImpliedProbability } from './utils';

// Set up the CLI program
program
  .name('sportsbook-risk-simulator')
  .description('Monte Carlo simulator for sportsbook risk management')
  .version('1.0.0');

// Command to run simulation with sample data
program
  .command('run-sample')
  .description('Run a simulation with sample market data')
  .option('-s, --simulations <number>', 'Number of Monte Carlo simulations', (val) => parseInt(val), 1000)
  .option('-u, --users <number>', 'Number of simulated users', (val) => parseInt(val), 200)
  .option('-b, --bets-per-user <number>', 'Average bets per user', (val) => parseFloat(val), 1.5)
  .option('-r, --risk-tolerance <number>', 'Risk tolerance (0-1)', (val) => parseFloat(val), 0.6)
  .option('-m, --target-margin <number>', 'Target profit margin', (val) => parseFloat(val), 0.05)
  .option('-e, --max-exposure <number>', 'Maximum exposure as percentage of liquidity', (val) => parseFloat(val), 0.3)
  .option('-a, --adjustment-factor <number>', 'Odds adjustment factor', (val) => parseFloat(val), 0.5)
  .action((options) => {
    // Create a sample market
    const market = createSampleMarket();
    
    // Create config with custom options
    const config: SimulationConfig = {
      ...createDefaultConfig(),
      numSimulations: options.simulations,
      numUsers: options.users,
      avgBetsPerUser: options.betsPerUser,
      riskTolerance: options.riskTolerance,
      targetMargin: options.targetMargin,
      maxExposurePercentage: options.maxExposure,
      oddsAdjustmentFactor: options.adjustmentFactor
    };
    
    // Run the simulation
    const simulator = new RiskSimulator(market, config);
    const result = simulator.runSimulation();
    
    // Print results
    printSimulationResults(market, config, result);
  });

// Command to run simulation with custom market data
program
  .command('run-custom')
  .description('Run a simulation with custom market data')
  .option('-s, --simulations <number>', 'Number of Monte Carlo simulations', (val) => parseInt(val), 1000)
  .option('-u, --users <number>', 'Number of simulated users', (val) => parseInt(val), 200)
  .option('-b, --bets-per-user <number>', 'Average bets per user', (val) => parseFloat(val), 1.5)
  .option('-r, --risk-tolerance <number>', 'Risk tolerance (0-1)', (val) => parseFloat(val), 0.6)
  .option('-m, --target-margin <number>', 'Target profit margin', (val) => parseFloat(val), 0.05)
  .option('-e, --max-exposure <number>', 'Maximum exposure as percentage of liquidity', (val) => parseFloat(val), 0.3)
  .option('-a, --adjustment-factor <number>', 'Odds adjustment factor', (val) => parseFloat(val), 0.5)
  .option('-i, --market-id <string>', 'Market ID')
  .option('-n, --market-name <string>', 'Market name')
  .option('-ho, --home-odds <number>', 'Home team odds (decimal)', (val) => parseFloat(val))
  .option('-ao, --away-odds <number>', 'Away team odds (decimal)', (val) => parseFloat(val))
  .option('-do, --draw-odds <number>', 'Draw odds (decimal)', (val) => parseFloat(val))
  .option('-l, --liquidity <number>', 'Current market liquidity', (val) => parseFloat(val), 50000)
  .option('-hl, --home-limit <number>', 'Home team bet limit', (val) => parseFloat(val), 5000)
  .option('-al, --away-limit <number>', 'Away team bet limit', (val) => parseFloat(val), 5000)
  .option('-dl, --draw-limit <number>', 'Draw bet limit', (val) => parseFloat(val), 3000)
  .option('-he, --home-exposure <number>', 'Current home exposure', (val) => parseFloat(val), 0)
  .option('-ae, --away-exposure <number>', 'Current away exposure', (val) => parseFloat(val), 0)
  .option('-de, --draw-exposure <number>', 'Current draw exposure', (val) => parseFloat(val), 0)
  .option('-t, --market-type <string>', 'Market type (moneyline, spread, totals, other)', 'moneyline')
  .option('-sp, --sport <string>', 'Sport name', 'Soccer')
  .option('-lg, --league <string>', 'League name', 'English Premier League')
  .action((options) => {
    try {
      if (!options.homeOdds || !options.awayOdds) {
        console.error('Error: Home odds and away odds are required');
        process.exit(1);
      }
      
      // Create a market with the provided options
      const market: Market = {
        id: options.marketId || 'market-' + Math.floor(Math.random() * 10000),
        name: options.marketName || 'Custom Market',
        currentOdds: {
          home: options.homeOdds,
          away: options.awayOdds,
          draw: options.drawOdds
        },
        impliedProbabilities: {
          home: decimalToImpliedProbability(options.homeOdds),
          away: decimalToImpliedProbability(options.awayOdds),
          draw: options.drawOdds ? decimalToImpliedProbability(options.drawOdds) : undefined
        },
        currentLiquidity: options.liquidity,
        betLimits: {
          home: options.homeLimit,
          away: options.awayLimit,
          draw: options.drawLimit
        },
        exposures: {
          home: options.homeExposure,
          away: options.awayExposure,
          draw: options.drawExposure
        },
        marketType: options.marketType as 'moneyline' | 'spread' | 'totals' | 'other',
        marketStatus: 'open',
        startTime: new Date(Date.now() + 3 * 60 * 60 * 1000), // Default to 3 hours from now
        sport: options.sport,
        league: options.league
      };
      
      // Create config with custom options
      const config: SimulationConfig = {
        ...createDefaultConfig(),
        numSimulations: options.simulations,
        numUsers: options.users,
        avgBetsPerUser: options.betsPerUser,
        riskTolerance: options.riskTolerance,
        targetMargin: options.targetMargin,
        maxExposurePercentage: options.maxExposure,
        oddsAdjustmentFactor: options.adjustmentFactor
      };
      
      // Run the simulation
      const simulator = new RiskSimulator(market, config);
      const result = simulator.runSimulation();
      
      // Print results
      printSimulationResults(market, config, result);
      
    } catch (error: unknown) {
      console.error('Error:', (error as Error).message);
      process.exit(1);
    }
  });

// Command to run simulation from JSON input
program
  .command('run-json')
  .description('Run a simulation with market data from JSON input')
  .action(() => {
    // Read JSON from stdin
    let jsonInput = '';
    
    process.stdin.on('data', (chunk) => {
      jsonInput += chunk;
    });
    
    process.stdin.on('end', () => {
      try {
        const data = JSON.parse(jsonInput);
        
        if (!data.market || !data.config) {
          console.error('Error: JSON input must contain market and config objects');
          process.exit(1);
        }
        
        // Ensure market has all required properties
        const market: Market = {
          id: data.market.id || 'market-' + Math.floor(Math.random() * 10000),
          name: data.market.name || 'JSON Market',
          currentOdds: data.market.currentOdds,
          impliedProbabilities: data.market.impliedProbabilities || {},
          currentLiquidity: data.market.currentLiquidity || 50000,
          betLimits: data.market.betLimits || {},
          exposures: data.market.exposures || {},
          marketType: data.market.marketType || 'moneyline',
          marketStatus: data.market.marketStatus || 'open',
          startTime: new Date(data.market.startTime) || new Date(Date.now() + 3 * 60 * 60 * 1000),
          sport: data.market.sport || 'Generic',
          league: data.market.league || 'Generic'
        };
        
        // Calculate implied probabilities if not provided
        if (Object.keys(market.impliedProbabilities).length === 0) {
          for (const outcome in market.currentOdds) {
            market.impliedProbabilities[outcome] = decimalToImpliedProbability(market.currentOdds[outcome] as number);
          }
        }
        
        // Default bet limits if not provided
        if (Object.keys(market.betLimits).length === 0) {
          for (const outcome in market.currentOdds) {
            market.betLimits[outcome] = 5000;
          }
        }
        
        // Default exposures if not provided
        if (Object.keys(market.exposures).length === 0) {
          for (const outcome in market.currentOdds) {
            market.exposures[outcome] = 0;
          }
        }
        
        // Create config with provided values, using defaults for missing values
        const defaultConfig = createDefaultConfig();
        const config: SimulationConfig = {
          ...defaultConfig,
          ...data.config
        };
        
        // Run the simulation
        const simulator = new RiskSimulator(market, config);
        const result = simulator.runSimulation();
        
        // Output results as JSON
        if (data.outputFormat === 'json') {
          console.log(JSON.stringify(result, null, 2));
        } else {
          // Print formatted results
          printSimulationResults(market, config, result);
        }
        
      } catch (error: unknown) {
        console.error('Error:', (error as Error).message);
        process.exit(1);
      }
    });
  });

// Parse arguments
program.parse();

// If no arguments, display help
if (process.argv.length === 2) {
  program.help();
}
