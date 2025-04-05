const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("MarketFactory", function () {
  let MarketFactory;
  let NBAMarket;
  let factory;
  let owner;
  let oddsProvider;
  let resultsProvider;
  let usdx;
  let liquidityPool;
  let addr3;
  let addrs;

  beforeEach(async function () {
    // Get signers
    [owner, oddsProvider, resultsProvider, addr3, ...addrs] = await ethers.getSigners();

    // Deploy the contracts
    NBAMarket = await ethers.getContractFactory("NBAMarket");
    
    // First deploy USDX and LiquidityPool (mocked for testing)
    const USDX = await ethers.getContractFactory("USDX");
    usdx = await USDX.deploy();
    await usdx.deployed();
    
    const LiquidityPool = await ethers.getContractFactory("LiquidityPool");
    liquidityPool = await LiquidityPool.deploy(usdx.address);
    await liquidityPool.deployed();
    
    // Set up liquidity pool with funds
    await usdx.transfer(liquidityPool.address, ethers.utils.parseUnits("500000", 6));
    
    // Fund addr3 with USDX for testing
    await usdx.transfer(addr3.address, ethers.utils.parseUnits("100000", 6));
    
    // Deploy market factory
    MarketFactory = await ethers.getContractFactory("MarketFactory");
    factory = await MarketFactory.deploy(
      oddsProvider.address,
      resultsProvider.address,
      usdx.address,
      liquidityPool.address
    );
    
    await factory.deployed();
    
    // Set the market factory in the liquidity pool
    await liquidityPool.setMarketFactory(factory.address);
  });

  describe("Deployment", function () {
    it("Should set the correct admin and default providers", async function () {
      expect(await factory.admin()).to.equal(owner.address);
      expect(await factory.defaultOddsProvider()).to.equal(oddsProvider.address);
      expect(await factory.defaultResultsProvider()).to.equal(resultsProvider.address);
      expect(await factory.usdx()).to.equal(usdx.address);
      expect(await factory.liquidityPool()).to.equal(liquidityPool.address);
    });

    it("Should start with zero deployed markets", async function () {
      expect(await factory.getDeployedMarketsCount()).to.equal(0);
    });
  });

  describe("Market creation", function () {
    it("Should create market with default providers", async function () {
      // Current time + 1 day
      const gameTimestamp = Math.floor(Date.now() / 1000) + 86400;
      
      const tx = await factory.createMarket(
        "Lakers",
        "Celtics",
        gameTimestamp,
        "NBA_GAME_123",  // oddsApiId
        6000,  // 6.000 odds
        5000,  // 5.000 odds
        ethers.utils.parseUnits("10000", 6) // 10k USDX funding
      );
      
      // Wait for transaction to be mined
      await tx.wait();
      
      // Check market count
      expect(await factory.getDeployedMarketsCount()).to.equal(1);
      
      // Get the created market address
      const marketAddress = await factory.deployedMarkets(0);
      
      // Create a contract instance for the deployed market
      const marketContract = await NBAMarket.attach(marketAddress);
      
      // Verify market data
      const homeTeam = await marketContract.getHomeTeam();
      const awayTeam = await marketContract.getAwayTeam();
      const odds = await marketContract.getOdds();
      
      expect(homeTeam).to.equal("Lakers");
      expect(awayTeam).to.equal("Celtics");
      expect(odds[0]).to.equal(6000);
      expect(odds[1]).to.equal(5000);
      
      // Verify admin and providers
      expect(await marketContract.admin()).to.equal(owner.address);
      expect(await marketContract.oddsProvider()).to.equal(oddsProvider.address);
      expect(await marketContract.resultsProvider()).to.equal(resultsProvider.address);
    });

    it("Should create market with custom providers", async function () {
      // Current time + 1 day
      const gameTimestamp = Math.floor(Date.now() / 1000) + 86400;
      
      const tx = await factory.createMarketWithCustomProviders(
        "Warriors",
        "Bulls",
        gameTimestamp,
        "NBA_GAME_124",  // oddsApiId
        5500,  // 5.500 odds
        6500,  // 6.500 odds
        addr3.address,
        addr3.address,
        ethers.utils.parseUnits("10000", 6) // 10k USDX funding
      );
      
      // Wait for transaction to be mined
      await tx.wait();
      
      // Check market count
      expect(await factory.getDeployedMarketsCount()).to.equal(1);
      
      // Get the created market address
      const marketAddress = await factory.deployedMarkets(0);
      
      // Create a contract instance for the deployed market
      const marketContract = await NBAMarket.attach(marketAddress);
      
      // Verify market data
      const homeTeam = await marketContract.getHomeTeam();
      const awayTeam = await marketContract.getAwayTeam();
      
      expect(homeTeam).to.equal("Warriors");
      expect(awayTeam).to.equal("Bulls");
      
      // Verify custom providers
      expect(await marketContract.oddsProvider()).to.equal(addr3.address);
      expect(await marketContract.resultsProvider()).to.equal(addr3.address);
    });

    it("Should create market with no odds", async function () {
      // Current time + 1 day
      const gameTimestamp = Math.floor(Date.now() / 1000) + 86400;
      
      const tx = await factory.createMarketWithoutOdds(
        "Heat",
        "Suns",
        gameTimestamp,
        "NBA_GAME_125",  // oddsApiId
        ethers.utils.parseUnits("10000", 6) // 10k USDX funding
      );
      
      // Wait for transaction to be mined
      await tx.wait();
      
      // Check market count
      expect(await factory.getDeployedMarketsCount()).to.equal(1);
      
      // Get the created market address
      const marketAddress = await factory.deployedMarkets(0);
      
      // Create a contract instance for the deployed market
      const marketContract = await NBAMarket.attach(marketAddress);
      
      // Verify market data
      const homeTeam = await marketContract.getHomeTeam();
      const awayTeam = await marketContract.getAwayTeam();
      const odds = await marketContract.getOdds();
      const status = await marketContract.getGameStatus();
      
      expect(homeTeam).to.equal("Heat");
      expect(awayTeam).to.equal("Suns");
      expect(odds[0]).to.equal(0); // homeOdds should be 0
      expect(odds[1]).to.equal(0); // awayOdds should be 0
      expect(status[2]).to.equal(false); // oddsSet should be false
      
      // Market should not be ready for betting yet
      expect(await marketContract.isReadyForBetting()).to.equal(false);
      
      // After updating odds, market should be ready for betting
      // Get the betting engine
      const bettingEngineAddress = await marketContract.bettingEngine();
      
      // Authorize addr3 to spend USDX
      await usdx.connect(addr3).approve(bettingEngineAddress, ethers.utils.parseUnits("1000", 6));
      
      // Update odds and check if market is ready for betting
      await marketContract.connect(oddsProvider).updateOdds(1850, 2000);
      expect(await marketContract.isReadyForBetting()).to.equal(true);
      
      // Place a bet to verify everything is working correctly
      await marketContract.connect(addr3).placeBet(ethers.utils.parseUnits("100", 6), true);
      
      // Verify the bet was recorded
      const bettorBets = await marketContract.getBettorBets(addr3.address);
      expect(bettorBets.length).to.equal(1);
    });
    
    it("Should fail when non-admin tries to create market", async function () {
      const gameTimestamp = Math.floor(Date.now() / 1000) + 86400;
      
      await expect(
        factory.connect(addr3).createMarket(
          "Lakers",
          "Celtics",
          gameTimestamp,
          "NBA_GAME_123",
          6000,
          5000,
          ethers.utils.parseUnits("10000", 6)
        )
      ).to.be.reverted;
    });
  });

  describe("Administrative functions", function () {
    it("Should update default odds provider", async function () {
      await factory.setDefaultOddsProvider(addr3.address);
      expect(await factory.defaultOddsProvider()).to.equal(addr3.address);
    });

    it("Should update default results provider", async function () {
      await factory.setDefaultResultsProvider(addr3.address);
      expect(await factory.defaultResultsProvider()).to.equal(addr3.address);
    });

    it("Should transfer admin role", async function () {
      await factory.transferAdmin(addr3.address);
      expect(await factory.admin()).to.equal(addr3.address);
    });

    it("Should fail when non-admin tries to update providers", async function () {
      await expect(
        factory.connect(addr3).setDefaultOddsProvider(addr3.address)
      ).to.be.reverted;
      
      await expect(
        factory.connect(addr3).setDefaultResultsProvider(addr3.address)
      ).to.be.reverted;
    });

    it("Should fail when transferring admin to zero address", async function () {
      await expect(
        factory.transferAdmin(ethers.constants.AddressZero)
      ).to.be.reverted;
    });
  });
});