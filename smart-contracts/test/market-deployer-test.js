const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("MarketDeployer", function () {
  let MarketDeployer, MarketFactory, MarketOdds, NBAMarket;
  let deployer, factory;
  let owner, oddsProvider, resultsProvider, addr3;
  let usdx, liquidityPool;
  let addrs;

  beforeEach(async function () {
    // Get signers
    [owner, oddsProvider, resultsProvider, addr3, ...addrs] = await ethers.getSigners();

    // Get Contract Factories
    NBAMarket = await ethers.getContractFactory("NBAMarket");
    MarketOdds = await ethers.getContractFactory("MarketOdds");
    MarketDeployer = await ethers.getContractFactory("MarketDeployer");
    MarketFactory = await ethers.getContractFactory("MarketFactory");

    // Deploy USDX and LiquidityPool
    const USDX = await ethers.getContractFactory("USDX");
    usdx = await USDX.deploy();
    await usdx.deployed();

    const LiquidityPool = await ethers.getContractFactory("LiquidityPool");
    liquidityPool = await LiquidityPool.deploy(usdx.address);
    await liquidityPool.deployed();

    // Fund liquidity pool
    await usdx.transfer(liquidityPool.address, ethers.utils.parseUnits("500000", 6));

    // Deploy MarketDeployer
    deployer = await MarketDeployer.deploy();
    await deployer.deployed();

    // Deploy market factory
    factory = await MarketFactory.deploy(
      oddsProvider.address,
      resultsProvider.address,
      usdx.address,
      liquidityPool.address,
      deployer.address
    );
    await factory.deployed();

    // Set the market factory in the liquidity pool
    await liquidityPool.setMarketFactory(factory.address);
  });

  describe("Deployment", function () {
    it("Should deploy MarketDeployer successfully", async function () {
      expect(deployer.address).to.not.equal(ethers.constants.AddressZero);
    });

    it("Should set the MarketDeployer in MarketFactory", async function() {
      expect(await factory.deployer()).to.equal(deployer.address);
    });
  });

  describe("Market creation with MarketDeployer", function () {
    it("Should create market with both deployer steps", async function () {
      const gameTimestamp = Math.floor(Date.now() / 1000) + 86400;
      const initialFunding = ethers.utils.parseUnits("10000", 6);

      // Example odds/lines
      const homeOdds = 1900; // 1.900
      const awayOdds = 1900; // 1.900
      const drawOdds = 0;    // 0 for NBA (no draws)
      const homeSpreadPoints = -75; // -7.5
      const homeSpreadOdds = 1950; // 1.950
      const awaySpreadOdds = 1850; // 1.850
      const totalPoints = 2105; // 210.5
      const overOdds = 1900; // 1.900
      const underOdds = 1900; // 1.900

      // Step 1: Deploy Odds Contract directly with deployer
      const oddsContractAddress = await deployer.deployOddsContract(
        factory.address,
        oddsProvider.address,
        homeOdds,
        awayOdds,
        drawOdds,
        homeSpreadPoints,
        homeSpreadOdds,
        awaySpreadOdds,
        totalPoints,
        overOdds,
        underOdds
      );

      // Step 2: Deploy Market Contract directly with deployer
      const marketAddress = await deployer.deployMarketContract(
        "Lakers",
        "Celtics",
        gameTimestamp,
        "NBA_GAME_123",
        owner.address,
        oddsProvider.address,
        resultsProvider.address,
        usdx.address,
        liquidityPool.address,
        oddsContractAddress,
        initialFunding
      );

      // Verify the contracts were created properly
      const marketContract = await NBAMarket.attach(marketAddress);
      const marketOddsContract = await MarketOdds.attach(oddsContractAddress);

      // Verify odds configuration
      const odds = await marketOddsContract.getFullOdds();
      expect(odds._homeOdds).to.equal(homeOdds);
      expect(odds._awayOdds).to.equal(awayOdds);
      expect(odds._totalPoints).to.equal(totalPoints);

      // Verify market configuration
      const details = await marketContract.getMarketDetails();
      expect(details._homeTeam).to.equal("Lakers");
      expect(details._awayTeam).to.equal("Celtics");
    });

    it("Should create market through MarketFactory using MarketDeployer", async function () {
      const gameTimestamp = Math.floor(Date.now() / 1000) + 86400;
      const initialFunding = ethers.utils.parseUnits("8000", 6);
      
      const tx = await factory.createMarket(
        "Knicks",
        "Bulls",
        gameTimestamp,
        "NBA_GAME_456",
        1900, // homeOdds
        2000, // awayOdds
        0,    // drawOdds
        -30,  // homeSpreadPoints
        1900, // homeSpreadOdds
        1900, // awaySpreadOdds
        1995, // totalPoints
        1900, // overOdds
        1900, // underOdds
        initialFunding
      );
      
      const receipt = await tx.wait();
      const marketCreatedEvent = receipt.events?.find(e => e.event === 'MarketCreated');
      expect(marketCreatedEvent).to.exist;
      
      const marketAddress = marketCreatedEvent.args.marketAddress;
      const oddsContractAddress = marketCreatedEvent.args.oddsContractAddress;
      
      // Verify contracts were created
      expect(marketAddress).to.not.equal(ethers.constants.AddressZero);
      expect(oddsContractAddress).to.not.equal(ethers.constants.AddressZero);
      
      // Verify the contracts were configured correctly
      const marketContract = await NBAMarket.attach(marketAddress);
      const details = await marketContract.getMarketDetails();
      expect(details._homeTeam).to.equal("Knicks");
      expect(details._awayTeam).to.equal("Bulls");
    });
  });
});