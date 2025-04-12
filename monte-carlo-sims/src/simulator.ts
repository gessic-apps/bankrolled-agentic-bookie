import { Market, SimulationConfig, UserProfile, Bet, SimulationResult } from './types';
import * as math from 'mathjs';

export class RiskSimulator {
  private market: Market;
  private config: SimulationConfig;
  private userProfiles: UserProfile[] = [];
  private simulatedBets: Bet[] = [];
  private outcomes: ('home' | 'away' | 'draw')[] = [];

  constructor(market: Market, config: SimulationConfig) {
    this.market = { ...market };
    this.config = config;
    this.outcomes = ['home', 'away'];
    if (market.currentOdds.draw !== undefined) {
      this.outcomes.push('draw');
    }
  }

  /**
   * Generate synthetic user profiles for simulation
   */
  private generateUserProfiles(): void {
    this.userProfiles = [];
    
    for (let i = 0; i < this.config.numUsers; i++) {
      this.userProfiles.push({
        id: `user-${i}`,
        // Randomize user characteristics with some skew toward middle values
        betSizeTendency: math.random(0.1, 0.9),
        sharpness: math.random(0.1, 0.9),
        favoriteOutcomesBias: math.random(0.1, 0.9),
        chasePattern: math.random(0.1, 0.9),
        variability: math.random(0.1, 0.9)
      });
    }
  }

  /**
   * Calculate true fair odds based on implied probabilities
   */
  private calculateFairOdds(): Record<string, number> {
    const fairOdds: Record<string, number> = {};
    let totalImpliedProb = 0;
    
    // First calculate total implied probability
    for (const outcome of this.outcomes) {
      if (this.market.impliedProbabilities[outcome] !== undefined) {
        totalImpliedProb += this.market.impliedProbabilities[outcome]!;
      }
    }
    
    // Remove the overround to get fair probabilities
    const fairProbabilities: Record<string, number> = {};
    for (const outcome of this.outcomes) {
      if (this.market.impliedProbabilities[outcome] !== undefined) {
        fairProbabilities[outcome] = this.market.impliedProbabilities[outcome]! / totalImpliedProb;
        // Convert to decimal odds: odds = 1 / probability
        fairOdds[outcome] = 1 / fairProbabilities[outcome];
      }
    }
    
    return fairOdds;
  }

  /**
   * Simulate bets based on user profiles and market conditions
   */
  private simulateBets(): Bet[] {
    const bets: Bet[] = [];
    const fairOdds = this.calculateFairOdds();
    
    const startTime = new Date(this.market.startTime);
    const endTime = new Date(startTime.getTime() + this.config.bettingPeriodHours * 60 * 60 * 1000);
    
    // For each user
    for (const user of this.userProfiles) {
      // Determine how many bets this user makes
      const numBets = Math.max(1, Math.round(
        this.config.avgBetsPerUser * (1 + (math.random(-0.5, 0.5) * user.variability))
      ));
      
      for (let i = 0; i < numBets; i++) {
        // Pick a random time for this bet
        const betTime = new Date(
          startTime.getTime() + math.random() * (endTime.getTime() - startTime.getTime())
        );
        
        // User evaluates the odds for each outcome
        const perceivedValue: Record<string, number> = {};
        let bestOutcome: string | null = null;
        let highestValue = -Infinity;
        
        for (const outcome of this.outcomes) {
          if (this.market.currentOdds[outcome] === undefined) continue;
          
          // Sharper users can better estimate true probabilities
          const estimationError = (1 - user.sharpness) * math.random(-0.2, 0.2);
          const perceivedProb = 1 / fairOdds[outcome] * (1 + estimationError);
          
          // Calculate perceived edge
          const bookOdds = this.market.currentOdds[outcome]!;
          const perceivedEdge = (bookOdds * perceivedProb) - 1;
          
          // Apply favoritism bias (users tend to overvalue favorites)
          const isFavorite = this.market.impliedProbabilities[outcome]! > 0.5;
          const favoriteAdjustment = isFavorite ? user.favoriteOutcomesBias * 0.1 : 0;
          
          // Final perceived value
          perceivedValue[outcome] = perceivedEdge + favoriteAdjustment;
          
          if (perceivedValue[outcome] > highestValue) {
            highestValue = perceivedValue[outcome];
            bestOutcome = outcome;
          }
        }
        
        // Only place bet if there's perceived positive value
        if (bestOutcome && perceivedValue[bestOutcome] > 0.01) {
          // Determine bet size based on user's tendency and perceived edge
          const maxBetLimit = this.market.betLimits[bestOutcome]!;
          const baseBetSize = maxBetLimit * user.betSizeTendency * 0.5;
          const edgeFactor = Math.min(perceivedValue[bestOutcome] * 10, 2); // Cap at 2x
          
          let betSize = Math.min(
            baseBetSize * edgeFactor,
            maxBetLimit
          );
          
          // Add some randomness
          betSize = betSize * (1 + math.random(-0.2, 0.2) * user.variability);
          betSize = Math.round(betSize * 100) / 100; // Round to 2 decimal places
          
          const selectedOdds = this.market.currentOdds[bestOutcome]!;
          
          bets.push({
            userId: user.id,
            marketId: this.market.id,
            outcome: bestOutcome as 'home' | 'away' | 'draw',
            stake: betSize,
            odds: selectedOdds,
            expectedValue: perceivedValue[bestOutcome],
            timestamp: betTime
          });
        }
      }
    }
    
    // Sort bets by timestamp
    return bets.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  }

  /**
   * Run a single Monte Carlo simulation
   */
  private runSingleSimulation(): {
    profitLoss: number;
    exposures: Record<string, number>;
    totalBets: number;
    betsPerOutcome: Record<string, number>;
    totalStaked: number;
  } {
    const bets = this.simulateBets();
    let profitLoss = 0;
    const exposures: Record<string, number> = {};
    const betsPerOutcome: Record<string, number> = {};
    let totalStaked = 0;
    
    // Initialize counters
    for (const outcome of this.outcomes) {
      exposures[outcome] = 0;
      betsPerOutcome[outcome] = 0;
    }
    
    // Process each bet
    for (const bet of bets) {
      totalStaked += bet.stake;
      betsPerOutcome[bet.outcome] += 1;
      
      // Calculate potential payout
      const potentialPayout = bet.stake * bet.odds;
      
      // Update exposures for each outcome
      for (const outcome of this.outcomes) {
        if (outcome === bet.outcome) {
          exposures[outcome] -= (potentialPayout - bet.stake);
        } else {
          exposures[outcome] += bet.stake;
        }
      }
    }
    
    // Determine which outcome actually happened (random based on true probabilities)
    const fairOdds = this.calculateFairOdds();
    const trueProbs: number[] = [];
    const outcomesList: string[] = [];
    
    for (const outcome of this.outcomes) {
      if (fairOdds[outcome]) {
        trueProbs.push(1 / fairOdds[outcome]);
        outcomesList.push(outcome);
      }
    }
    
    // Normalize probabilities
    const totalProb = trueProbs.reduce((sum, prob) => sum + prob, 0);
    const normalizedProbs = trueProbs.map(prob => prob / totalProb);
    
    // Cumulative distribution for sampling
    const cumulativeProbs = [];
    let cumulativeSum = 0;
    for (const prob of normalizedProbs) {
      cumulativeSum += prob;
      cumulativeProbs.push(cumulativeSum);
    }
    
    // Sample from distribution
    const randomValue = math.random();
    let actualOutcomeIndex = cumulativeProbs.findIndex(cumProb => randomValue <= cumProb);
    if (actualOutcomeIndex === -1) actualOutcomeIndex = outcomesList.length - 1;
    
    const actualOutcome = outcomesList[actualOutcomeIndex];
    
    // Calculate P&L based on the actual outcome
    profitLoss = exposures[actualOutcome];
    
    return {
      profitLoss,
      exposures,
      totalBets: bets.length,
      betsPerOutcome,
      totalStaked
    };
  }

  /**
   * Calculate optimal odds adjustments based on simulation results
   */
  private calculateOddsAdjustments(simResults: Array<ReturnType<typeof this.runSingleSimulation>>): {
    oddsAdjustments: Record<string, number>;
    betLimitAdjustments: Record<string, number>;
    liquidityAdjustment: number;
  } {
    // Calculate average exposures across simulations
    const avgExposures: Record<string, number> = {};
    for (const outcome of this.outcomes) {
      avgExposures[outcome] = 0;
    }
    
    // Calculate total bets per outcome
    const totalBetsPerOutcome: Record<string, number> = {};
    for (const outcome of this.outcomes) {
      totalBetsPerOutcome[outcome] = 0;
    }
    
    let totalSim = 0;
    let avgPL = 0;
    
    for (const sim of simResults) {
      totalSim++;
      avgPL += sim.profitLoss;
      
      for (const outcome of this.outcomes) {
        avgExposures[outcome] += sim.exposures[outcome];
        totalBetsPerOutcome[outcome] += sim.betsPerOutcome[outcome];
      }
    }
    
    // Average values
    avgPL /= totalSim;
    for (const outcome of this.outcomes) {
      avgExposures[outcome] /= totalSim;
      totalBetsPerOutcome[outcome] /= totalSim;
    }
    
    // Calculate odds adjustments based on exposures and desired margin
    const oddsAdjustments: Record<string, number> = {};
    const betLimitAdjustments: Record<string, number> = {};
    
    // Calculate total exposure across all outcomes
    const totalExposure = Object.values(avgExposures).reduce((sum, exp) => sum + Math.abs(exp), 0);
    const maxAllowedExposure = this.market.currentLiquidity * this.config.maxExposurePercentage;
    
    for (const outcome of this.outcomes) {
      // Adjust odds if exposure is too high on an outcome
      const exposureRatio = Math.abs(avgExposures[outcome]) / this.market.currentLiquidity;
      
      // Negative exposure means we lose if this outcome happens
      // We want to decrease odds (increase our margin) when exposure is negative (risky)
      const baseAdjustment = -avgExposures[outcome] / this.market.currentLiquidity * this.config.oddsAdjustmentFactor;
      
      // Limit the adjustment based on max variation config
      oddsAdjustments[outcome] = Math.max(
        -this.config.maxOddsVariation,
        Math.min(this.config.maxOddsVariation, baseAdjustment)
      );
      
      // Adjust bet limits based on betting patterns and exposure
      const currentLimit = this.market.betLimits[outcome];
      if (currentLimit !== undefined) {
        const bettingVolume = totalBetsPerOutcome[outcome];
        
        // Reduce limits if we have high exposure or increase them if exposure is low
        const exposureLimit = exposureRatio > this.config.maxExposurePercentage ? -0.2 : 0.1;
        const volumeAdjustment = (bettingVolume > this.config.avgBetsPerUser) ? -0.1 : 0.05;
        
        // Combined effect
        const limitAdjustmentPercent = exposureLimit + volumeAdjustment;
        betLimitAdjustments[outcome] = currentLimit * limitAdjustmentPercent;
      } else {
        betLimitAdjustments[outcome] = 0;
      }
    }
    
    // Calculate liquidity adjustment based on total exposure vs available liquidity
    let liquidityAdjustment = 0;
    if (totalExposure > maxAllowedExposure) {
      // Need more liquidity
      liquidityAdjustment = totalExposure - maxAllowedExposure;
    } else if (totalExposure < maxAllowedExposure * 0.5) {
      // Can reduce liquidity (but not too aggressively)
      liquidityAdjustment = Math.max(
        -this.market.currentLiquidity * 0.2, // Don't reduce by more than 20%
        maxAllowedExposure * 0.7 - totalExposure
      );
    }
    
    return {
      oddsAdjustments,
      betLimitAdjustments,
      liquidityAdjustment
    };
  }

  /**
   * Calculate risk metrics based on simulation results
   */
  private calculateRiskMetrics(simResults: Array<ReturnType<typeof this.runSingleSimulation>>): {
    valueAtRisk: number;
    expectedShortfall: number;
    sharpeRatio: number;
    maxDrawdown: number;
    exposureConcentration: number;
  } {
    // Extract P&L values from simulations
    const plValues = simResults.map(sim => sim.profitLoss);
    
    // Sort P&L for percentile calculations
    const sortedPL = [...plValues].sort((a, b) => a - b);
    
    // Calculate Value at Risk (95% VaR)
    const varIndex = Math.floor(sortedPL.length * 0.05);
    const valueAtRisk = -sortedPL[varIndex]; // Negative because VaR is typically positive when loss is negative
    
    // Calculate Expected Shortfall (average loss beyond VaR)
    const lossesExceedingVar = sortedPL.slice(0, varIndex);
    const expectedShortfall = lossesExceedingVar.length > 0
      ? -lossesExceedingVar.reduce((sum, val) => sum + val, 0) / lossesExceedingVar.length
      : 0;
    
    // Calculate average return and standard deviation for Sharpe ratio
    const avgReturn = plValues.reduce((sum, val) => sum + val, 0) / plValues.length;
    const variance = plValues.reduce((sum, val) => sum + Math.pow(val - avgReturn, 2), 0) / plValues.length;
    const stdDev = Math.sqrt(variance);
    
    // Sharpe ratio (using 0 as risk-free rate for simplicity)
    const sharpeRatio = stdDev !== 0 ? avgReturn / stdDev : 0;
    
    // Calculate max drawdown (maximum loss in any single simulation)
    const maxDrawdown = Math.min(...plValues);
    
    // Calculate exposure concentration (how imbalanced exposures are across outcomes)
    let totalExposure = 0;
    const avgExposures: Record<string, number> = {};
    
    for (const outcome of this.outcomes) {
      avgExposures[outcome] = 0;
    }
    
    for (const sim of simResults) {
      for (const outcome of this.outcomes) {
        avgExposures[outcome] += sim.exposures[outcome];
      }
    }
    
    // Average exposures across simulations
    for (const outcome of this.outcomes) {
      avgExposures[outcome] /= simResults.length;
      totalExposure += Math.abs(avgExposures[outcome]);
    }
    
    // Calculate how concentrated exposure is (0 means perfectly balanced, 1 means all on one outcome)
    let exposureConcentration = 0;
    if (totalExposure > 0) {
      let maxExposureRatio = 0;
      for (const outcome of this.outcomes) {
        const exposureRatio = Math.abs(avgExposures[outcome]) / totalExposure;
        maxExposureRatio = Math.max(maxExposureRatio, exposureRatio);
      }
      exposureConcentration = maxExposureRatio;
    }
    
    return {
      valueAtRisk,
      expectedShortfall,
      sharpeRatio,
      maxDrawdown,
      exposureConcentration
    };
  }

  /**
   * Run the complete Monte Carlo simulation
   */
  public runSimulation(): SimulationResult {
    // Generate user profiles
    this.generateUserProfiles();
    
    // Run multiple simulations
    const simulationResults: Array<ReturnType<typeof this.runSingleSimulation>> = [];
    for (let i = 0; i < this.config.numSimulations; i++) {
      simulationResults.push(this.runSingleSimulation());
    }
    
    // Calculate recommendations based on simulation results
    const {
      oddsAdjustments,
      betLimitAdjustments,
      liquidityAdjustment
    } = this.calculateOddsAdjustments(simulationResults);
    
    // Calculate risk metrics
    const riskMetrics = this.calculateRiskMetrics(simulationResults);
    
    // Update market with recommendations
    const updatedMarket = { ...this.market };
    
    // Apply odds adjustments
    for (const outcome of this.outcomes) {
      if (updatedMarket.currentOdds[outcome] !== undefined) {
        // Apply adjustment as a percentage change to the current odds
        updatedMarket.currentOdds[outcome] = updatedMarket.currentOdds[outcome]! * (1 + oddsAdjustments[outcome]);
        // Round to 2 decimal places
        updatedMarket.currentOdds[outcome] = Math.round(updatedMarket.currentOdds[outcome]! * 100) / 100;
      }
      
      if (updatedMarket.betLimits[outcome] !== undefined) {
        // Apply bet limit adjustment
        updatedMarket.betLimits[outcome] = updatedMarket.betLimits[outcome]! + betLimitAdjustments[outcome];
        // Ensure bet limits stay positive and reasonable
        updatedMarket.betLimits[outcome] = Math.max(100, updatedMarket.betLimits[outcome]!);
        // Round to nearest 10
        updatedMarket.betLimits[outcome] = Math.round(updatedMarket.betLimits[outcome]! / 10) * 10;
      }
    }
    
    // Apply liquidity adjustment
    updatedMarket.currentLiquidity += liquidityAdjustment;
    // Ensure minimum liquidity
    updatedMarket.currentLiquidity = Math.max(1000, updatedMarket.currentLiquidity);
    // Round to nearest 100
    updatedMarket.currentLiquidity = Math.round(updatedMarket.currentLiquidity / 100) * 100;
    
    // Calculate simulation statistics
    const totalBets = simulationResults.reduce((sum, sim) => sum + sim.totalBets, 0) / simulationResults.length;
    
    const totalStaked = simulationResults.reduce((sum, sim) => sum + sim.totalStaked, 0);
    const avgBetSize = totalBets > 0 ? totalStaked / totalBets / simulationResults.length : 0;
    
    const betOutcomeDistribution: Record<string, number> = {};
    for (const outcome of this.outcomes) {
      const outcomeCount = simulationResults.reduce((sum, sim) => sum + sim.betsPerOutcome[outcome], 0);
      betOutcomeDistribution[outcome] = totalBets > 0 ? outcomeCount / totalBets / simulationResults.length : 0;
    }
    
    const plValues = simulationResults.map(sim => sim.profitLoss);
    const worstCaseScenario = Math.min(...plValues);
    const bestCaseScenario = Math.max(...plValues);
    
    // Calculate average P&L
    const avgProfitLoss = plValues.reduce((sum, val) => sum + val, 0) / plValues.length;
    
    return {
      updatedMarket,
      profitLoss: avgProfitLoss,
      recommendedActions: {
        oddsAdjustments: oddsAdjustments as any,
        liquidityAdjustment,
        betLimitAdjustments: betLimitAdjustments as any
      },
      riskMetrics,
      simulationStats: {
        totalBets,
        avgBetSize,
        betOutcomeDistribution: betOutcomeDistribution as any,
        worstCaseScenario,
        bestCaseScenario
      }
    };
  }
}
