# Sportsbook Risk Simulator

A Monte Carlo simulation tool for sportsbook risk management. This simulator helps manage odds, liquidity, and betting limits for a decentralized sportsbook.

## Features

- Runs thousands of Monte Carlo simulations to estimate risk
- Models user betting behaviors with realistic patterns
- Recommends optimal odds adjustments
- Determines appropriate betting limits
- Calculates required market liquidity
- Provides comprehensive risk metrics (VaR, Expected Shortfall, etc.)
- Beautiful CLI output with detailed recommendations

## Installation

```bash
npm install
npm run build
```

## Usage

### Run with sample data

```bash
npm run start run-sample
```

### Run with custom market data

```bash
npm run start run-custom --home-odds 1.9 --away-odds 2.1 --liquidity 100000
```

### Run with JSON input

```bash
cat market-data.json | npm run start run-json
```

Example JSON input:

```json
{
  "market": {
    "id": "market-12345",
    "name": "Barcelona vs Real Madrid",
    "currentOdds": {
      "home": 2.5,
      "away": 2.8,
      "draw": 3.4
    },
    "currentLiquidity": 75000,
    "betLimits": {
      "home": 5000,
      "away": 5000,
      "draw": 3000
    },
    "exposures": {
      "home": -1500,
      "away": 2000,
      "draw": 500
    },
    "marketType": "moneyline",
    "sport": "Soccer",
    "league": "La Liga"
  },
  "config": {
    "numSimulations": 2000,
    "numUsers": 300,
    "avgBetsPerUser": 2.0,
    "riskTolerance": 0.7,
    "targetMargin": 0.04,
    "maxExposurePercentage": 0.25,
    "oddsAdjustmentFactor": 0.6
  }
}
```

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| numSimulations | Number of Monte Carlo simulations | 1000 |
| numUsers | Number of simulated users | 200 |
| avgBetsPerUser | Average bets per user | 1.5 |
| riskTolerance | Risk tolerance (0-1 scale) | 0.6 |
| targetMargin | Target profit margin | 0.05 (5%) |
| maxExposurePercentage | Maximum exposure as % of liquidity | 0.3 (30%) |
| oddsAdjustmentFactor | How aggressively to adjust odds | 0.5 |
| bettingPeriodHours | Duration of betting period | 3 hours |
| maxOddsVariation | Maximum allowed odds adjustment | 0.1 (10%) |

## Risk Metrics

The simulator provides the following risk metrics:

- **Value at Risk (95%)**: Maximum loss at 95% confidence level
- **Expected Shortfall**: Average loss in worst 5% of scenarios
- **Sharpe Ratio**: Risk-adjusted return metric
- **Max Drawdown**: Worst-case loss scenario
- **Exposure Concentration**: How balanced the book's exposure is