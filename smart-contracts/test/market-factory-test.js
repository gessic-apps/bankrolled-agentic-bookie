const { expect } = require("chai");
const { ethers } = require("hardhat");

// Enum definition (mirroring NBAMarket.sol)
const MarketStatus = {
    PENDING: 0,
    OPEN: 1,
    STARTED: 2,
    SETTLED: 3,
    CANCELLED: 4
};

describe("MarketFactory", function () {
  let MarketFactory, MarketOdds, NBAMarket;
  let factory;
  let owner, oddsProvider, resultsProvider, addr3;
  let usdx, liquidityPool;
  let addrs;

  beforeEach(async function () {
    // Get signers
    [owner, oddsProvider, resultsProvider, addr3, ...addrs] = await ethers.getSigners();

    // Get Contract Factories
    NBAMarket = await ethers.getContractFactory("NBAMarket");
    MarketOdds = await ethers.getContractFactory("MarketOdds");
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

    // Deploy market factory
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
      // Using getDeployedMarkets which returns an array
      const deployedMarkets = await factory.getDeployedMarkets();
      expect(deployedMarkets.length).to.equal(0);
    });
  });

  describe("Market creation", function () {
    it("Should create market with initial odds using default providers", async function () {
      const gameTimestamp = Math.floor(Date.now() / 1000) + 86400;
      const initialFunding = ethers.utils.parseUnits("10000", 6);

      // Example odds/lines
      const homeOdds = 1900; // 1.900
      const awayOdds = 1900; // 1.900
      const homeSpreadPoints = -75; // -7.5
      const homeSpreadOdds = 1950; // 1.950
      const awaySpreadOdds = 1850; // 1.850
      const totalPoints = 2105; // 210.5
      const overOdds = 1900; // 1.900
      const underOdds = 1900; // 1.900

      const tx = await factory.createMarket(
        "Lakers",
        "Celtics",
        gameTimestamp,
        "NBA_GAME_123", // oddsApiId
        homeOdds,
        awayOdds,
        homeSpreadPoints,
        homeSpreadOdds,
        awaySpreadOdds,
        totalPoints,
        overOdds,
        underOdds,
        initialFunding
      );

      // Wait for transaction and get receipt to find event
      const receipt = await tx.wait();
      const marketCreatedEvent = receipt.events?.find(e => e.event === 'MarketCreated');
      expect(marketCreatedEvent).to.exist;

      const marketAddress = marketCreatedEvent.args.marketAddress;
      // Get marketOddsAddress from the deployed market, not the event
      // const marketOddsAddress = marketCreatedEvent.args.marketOddsAddress; 

      // Check market count
      const deployedMarkets = await factory.getDeployedMarkets();
      expect(deployedMarkets.length).to.equal(1);
      expect(deployedMarkets[0]).to.equal(marketAddress);

      // Create contract instances
      const marketContract = await NBAMarket.attach(marketAddress);
      // Get MarketOdds address from the NBAMarket contract
      const marketOddsAddress = await marketContract.getMarketOddsContract();
      const marketOddsContract = await MarketOdds.attach(marketOddsAddress);

      // Verify market details
      const details = await marketContract.getMarketDetails();
      expect(details._homeTeam).to.equal("Lakers");
      expect(details._awayTeam).to.equal("Celtics");
      expect(details._gameTimestamp).to.equal(gameTimestamp);
      expect(details._oddsApiId).to.equal("NBA_GAME_123");
      expect(details._marketStatus).to.equal(MarketStatus.OPEN); // Should be OPEN as odds were provided

      // Verify odds are set in MarketOdds contract
      const odds = await marketOddsContract.getFullOdds();
      expect(odds._homeOdds).to.equal(homeOdds);
      expect(odds._awayOdds).to.equal(awayOdds);
      expect(odds._homeSpreadPoints).to.equal(homeSpreadPoints);
      expect(odds._homeSpreadOdds).to.equal(homeSpreadOdds);
      expect(odds._awaySpreadOdds).to.equal(awaySpreadOdds);
      expect(odds._totalPoints).to.equal(totalPoints);
      expect(odds._overOdds).to.equal(overOdds);
      expect(odds._underOdds).to.equal(underOdds);

      // Verify providers in NBAMarket
      expect(await marketContract.admin()).to.equal(owner.address);
      expect(await marketContract.oddsProvider()).to.equal(oddsProvider.address);
      expect(await marketContract.resultsProvider()).to.equal(resultsProvider.address);

      // Verify NBAMarket knows its MarketOdds contract
      expect(await marketContract.getMarketOddsContract()).to.equal(marketOddsAddress);
    });

    it("Should create market with no initial odds", async function () {
      const gameTimestamp = Math.floor(Date.now() / 1000) + 86400;
      const initialFunding = ethers.utils.parseUnits("5000", 6);

      const tx = await factory.createMarket(
        "Heat",
        "Suns",
        gameTimestamp,
        "NBA_GAME_125", // oddsApiId
        0, // homeOdds
        0, // awayOdds
        0, // homeSpreadPoints
        0, // homeSpreadOdds
        0, // awaySpreadOdds
        0, // totalPoints
        0, // overOdds
        0, // underOdds
        initialFunding
      );

      const receipt = await tx.wait();
      const marketCreatedEvent = receipt.events?.find(e => e.event === 'MarketCreated');
      const marketAddress = marketCreatedEvent.args.marketAddress;
      // Get marketOddsAddress from the deployed market, not the event
      // const marketOddsAddress = marketCreatedEvent.args.marketOddsAddress; 

      const marketContract = await NBAMarket.attach(marketAddress);
      // Get MarketOdds address from the NBAMarket contract
      const marketOddsAddress = await marketContract.getMarketOddsContract();
      const marketOddsContract = await MarketOdds.attach(marketOddsAddress);

      // Verify market details
      const details = await marketContract.getMarketDetails();
      expect(details._homeTeam).to.equal("Heat");
      expect(details._awayTeam).to.equal("Suns");
      expect(details._marketStatus).to.equal(MarketStatus.PENDING); // Should be PENDING

      // Verify odds are NOT set in MarketOdds contract
      expect(await marketOddsContract.initialOddsSet()).to.equal(false);
      const odds = await marketOddsContract.getFullOdds();
      expect(odds._homeOdds).to.equal(0);
      expect(odds._awayOdds).to.equal(0);

      // Market should not be open for betting
      expect(await marketContract.isMarketOpenForBetting()).to.equal(false);

      // Now, update odds via the MarketOdds contract (using the designated oddsProvider)
      await marketOddsContract.connect(oddsProvider).updateOdds(
          1850, 1950, -55, 1900, 1900, 2055, 1880, 1920
      );

      // Verify odds are now set
      expect(await marketOddsContract.initialOddsSet()).to.equal(true);
      const updatedOdds = await marketOddsContract.getFullOdds();
      expect(updatedOdds._homeOdds).to.equal(1850);

      // Market should now be OPEN
      // Note: NBAMarket status doesn't automatically update when MarketOdds is updated.
      // The check `isMarketOpenForBetting` relies on NBAMarket status which is still PENDING.
      // To open the market, `startGame` needs to be called (after odds are set) OR an explicit `openMarket` function if added.
      // Current logic: Market opens implicitly if odds are set *at creation time*. 
      // If odds are set later, the market remains PENDING until `startGame` transitions it to STARTED.
      // Let's check the status is still PENDING
      const updatedDetails = await marketContract.getMarketDetails();
      expect(updatedDetails._marketStatus).to.equal(MarketStatus.PENDING);
      // And it's still not open for betting via the NBAMarket state
      expect(await marketContract.isMarketOpenForBetting()).to.equal(false);

      // TODO: Decide if a separate 'openMarket' function is needed or if the status updates implicitly
      // For now, the test verifies the odds were set in MarketOdds and the NBAMarket remains PENDING.
    });

    it("Should fail when non-admin tries to create market", async function () {
      const gameTimestamp = Math.floor(Date.now() / 1000) + 86400;
      await expect(
        factory.connect(addr3).createMarket(
          "Lakers", "Celtics", gameTimestamp, "ID", 1, 1, 1, 1, 1, 1, 1, 1, 0
        )
      ).to.be.reverted; // Should revert with default Ownable message or custom if added
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
      ).to.be.reverted; // Default Ownable message

      await expect(
        factory.connect(addr3).setDefaultResultsProvider(addr3.address)
      ).to.be.reverted; // Default Ownable message
    });

    it("Should fail when transferring admin to zero address", async function () {
      await expect(
        factory.transferAdmin(ethers.constants.AddressZero)
      ).to.be.reverted; // Default Ownable message
    });
  });
});