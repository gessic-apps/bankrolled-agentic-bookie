const { expect } = require("chai");
const { ethers } = require("hardhat");

// Enum definition (mirroring BettingEngine.sol)
const BetType = {
  MONEYLINE: 0,
  SPREAD: 1,
  TOTAL: 2,
  DRAW: 3
};

describe("Market Exposure Management", function () {
  let MarketFactory, NBAMarket, BettingEngine, MarketOdds;
  let factory, market, bettingEngine, marketOdds;
  let owner, oddsProvider, resultsProvider, bettor1, bettor2;
  let usdx, liquidityPool;
  let deployerContract;
  let addrs;

  // Convert number to BigNumber with 6 decimals
  const toAmount = (value) => ethers.utils.parseUnits(value.toString(), 6);

  beforeEach(async function () {
    this.timeout(30000); // Longer timeout for this complex setup
    
    // Get signers
    [owner, oddsProvider, resultsProvider, bettor1, bettor2, ...addrs] = await ethers.getSigners();

    // Deploy USDX token with sufficient initial supply
    const USDX = await ethers.getContractFactory("USDX");
    usdx = await USDX.deploy();
    await usdx.deployed();
    
    // Mint more tokens if needed
    if ((await usdx.totalSupply()).lt(toAmount(10000000))) {
      const mintTx = await usdx.mint(owner.address, toAmount(10000000));
      await mintTx.wait();
    }

    // Deploy LiquidityPool
    const LiquidityPool = await ethers.getContractFactory("LiquidityPool");
    liquidityPool = await LiquidityPool.deploy(usdx.address);
    await liquidityPool.deployed();

    // Fund liquidity pool
    const lpFundTx = await usdx.transfer(liquidityPool.address, toAmount(1000000));
    await lpFundTx.wait();

    // Deploy MarketDeployer
    const MarketDeployer = await ethers.getContractFactory("MarketDeployer");
    deployerContract = await MarketDeployer.deploy();
    await deployerContract.deployed();

    // Deploy market factory
    MarketFactory = await ethers.getContractFactory("MarketFactory");
    factory = await MarketFactory.deploy(
      oddsProvider.address,
      resultsProvider.address,
      usdx.address,
      liquidityPool.address,
      deployerContract.address
    );
    await factory.deployed();

    // Set the market factory in the liquidity pool
    const setFactoryTx = await liquidityPool.setMarketFactory(factory.address);
    await setFactoryTx.wait();

    // Deploy a test market with minimal configuration
    const gameTimestamp = Math.floor(Date.now() / 1000) + 86400;
    const initialFunding = toAmount(100000);
    
    // Create the market
    const createTx = await factory.createMarket(
      "Lakers",
      "Celtics",
      gameTimestamp,
      "NBA_TEST_EXPOSURE",
      1900, // homeOdds
      1900, // awayOdds
      0,    // drawOdds
      -75,  // homeSpreadPoints
      1900, // homeSpreadOdds
      1900, // awaySpreadOdds
      2105, // totalPoints
      1900, // overOdds
      1900, // underOdds
      initialFunding
    );
    
    const receipt = await createTx.wait();
    const marketCreatedEvent = receipt.events?.find(e => e.event === 'MarketCreated');
    const marketAddress = marketCreatedEvent.args.marketAddress;
    const oddsContractAddress = marketCreatedEvent.args.oddsContractAddress;
    
    // Get contract instances
    NBAMarket = await ethers.getContractFactory("NBAMarket");
    market = await NBAMarket.attach(marketAddress);
    
    MarketOdds = await ethers.getContractFactory("MarketOdds");
    marketOdds = await MarketOdds.attach(oddsContractAddress);
    
    // Get the betting engine
    const bettingEngineAddress = await market.bettingEngine();
    BettingEngine = await ethers.getContractFactory("BettingEngine");
    bettingEngine = await BettingEngine.attach(bettingEngineAddress);
    
    // Transfer some tokens to each bettor
    await usdx.transfer(bettor1.address, toAmount(1000));
    await usdx.transfer(bettor2.address, toAmount(1000));
    
    // Approve betting engine to spend bettor tokens
    await usdx.connect(bettor1).approve(bettingEngineAddress, toAmount(1000));
    await usdx.connect(bettor2).approve(bettingEngineAddress, toAmount(1000));
  });

  describe("Market Exposure Limits", function () {
    it("Should set and get market-specific exposure limits", async function () {
      // Set exposure limits for different market types
      await market.setMarketExposureLimit(BetType.MONEYLINE, true, toAmount(5000)); // Home ML
      await market.setMarketExposureLimit(BetType.MONEYLINE, false, toAmount(6000)); // Away ML
      await market.setMarketExposureLimit(BetType.SPREAD, true, toAmount(4000)); // Home spread
      await market.setMarketExposureLimit(BetType.TOTAL, true, toAmount(3000)); // Over
      
      // Check the limits were set correctly
      const homeML = await market.getMarketExposure(BetType.MONEYLINE, true);
      const awayML = await market.getMarketExposure(BetType.MONEYLINE, false);
      const homeSpread = await market.getMarketExposure(BetType.SPREAD, true);
      const over = await market.getMarketExposure(BetType.TOTAL, true);
      
      expect(homeML.maxExposure).to.equal(toAmount(5000));
      expect(awayML.maxExposure).to.equal(toAmount(6000));
      expect(homeSpread.maxExposure).to.equal(toAmount(4000));
      expect(over.maxExposure).to.equal(toAmount(3000));
      
      // Current exposures should all be zero initially
      expect(homeML.currentExposure).to.equal(0);
      expect(awayML.currentExposure).to.equal(0);
      expect(homeSpread.currentExposure).to.equal(0);
      expect(over.currentExposure).to.equal(0);
    });
    
    it("Should set all market exposure limits at once", async function () {
      // Set all limits with one function call
      await market.setAllMarketExposureLimits(
        toAmount(5000), // homeMoneylineLimit
        toAmount(6000), // awayMoneylineLimit
        toAmount(3000), // drawLimit
        toAmount(4000), // homeSpreadLimit
        toAmount(4500), // awaySpreadLimit
        toAmount(3000), // overLimit
        toAmount(3500)  // underLimit
      );
      
      // Check all the limits using the getter functions
      const mlExposure = await market.getMoneylineExposure();
      const spreadExposure = await market.getSpreadExposure();
      const totalExposure = await market.getTotalExposure();
      
      // Verify moneyline limits
      expect(mlExposure.homeMaxExposure).to.equal(toAmount(5000));
      expect(mlExposure.awayMaxExposure).to.equal(toAmount(6000));
      expect(mlExposure.drawMax).to.equal(toAmount(3000));
      
      // Verify spread limits
      expect(spreadExposure.homeMaxExposure).to.equal(toAmount(4000));
      expect(spreadExposure.awayMaxExposure).to.equal(toAmount(4500));
      
      // Verify total limits
      expect(totalExposure.overMaxExposure).to.equal(toAmount(3000));
      expect(totalExposure.underMaxExposure).to.equal(toAmount(3500));
    });
    
    it("Should track market-specific exposures when placing bets", async function () {
      // Set exposure limits
      await market.setAllMarketExposureLimits(
        toAmount(5000), // homeMoneylineLimit
        toAmount(6000), // awayMoneylineLimit
        toAmount(3000), // drawLimit
        toAmount(4000), // homeSpreadLimit
        toAmount(4500), // awaySpreadLimit
        toAmount(3000), // overLimit
        toAmount(3500)  // underLimit
      );
      
      // Place a moneyline bet on home team
      await market.connect(bettor1).placeBet(
        BetType.MONEYLINE,
        toAmount(100),
        true // betting on home
      );
      
      // Place a spread bet on away team
      await market.connect(bettor2).placeBet(
        BetType.SPREAD,
        toAmount(200),
        false // betting on away
      );
      
      // Calculate expected exposures (at 1.9 odds)
      // 100 * (1.9 - 1) = 90 for home ML
      // 200 * (1.9 - 1) = 180 for away spread
      const expectedHomeMLExposure = toAmount(90);
      const expectedAwaySpreadExposure = toAmount(180);
      
      // Check exposures
      const mlExposure = await market.getMoneylineExposure();
      const spreadExposure = await market.getSpreadExposure();
      
      expect(mlExposure.homeCurrentExposure).to.equal(expectedHomeMLExposure);
      expect(spreadExposure.awayCurrentExposure).to.equal(expectedAwaySpreadExposure);
      
      // Global exposure should be the sum
      const globalExposure = await market.getExposureInfo();
      expect(globalExposure[1]).to.equal(expectedHomeMLExposure.add(expectedAwaySpreadExposure));
    });
    
    it("Should prevent bet placement when market-specific exposure limit is exceeded", async function () {
      // Set a very low exposure limit for home moneyline
      await market.setMarketExposureLimit(BetType.MONEYLINE, true, toAmount(50));
      
      // Try to place a bet that would exceed the limit (100 * (1.9-1) = 90 > 50)
      await expect(
        market.connect(bettor1).placeBet(
          BetType.MONEYLINE,
          toAmount(100),
          true // betting on home
        )
      ).to.be.revertedWith("BettingEngine: Market exposure limit exceeded");
      
      // Bet should succeed with a smaller amount that doesn't exceed the limit
      await market.connect(bettor1).placeBet(
        BetType.MONEYLINE,
        toAmount(50),
        true // betting on home
      );
      
      // Check that the exposure was updated
      const mlExposure = await market.getMoneylineExposure();
      expect(mlExposure.homeCurrentExposure).to.equal(toAmount(45)); // 50 * (1.9-1) = 45
    });
  });
});