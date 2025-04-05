const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("MarketFactory", function () {
  let MarketFactory;
  let NBAMarket;
  let factory;
  let owner;
  let oddsProvider;
  let resultsProvider;
  let addr3;
  let addrs;

  beforeEach(async function () {
    // Get signers
    [owner, oddsProvider, resultsProvider, addr3, ...addrs] = await ethers.getSigners();

    // Deploy the contracts
    NBAMarket = await ethers.getContractFactory("NBAMarket");
    MarketFactory = await ethers.getContractFactory("MarketFactory");
    
    factory = await MarketFactory.deploy(
      oddsProvider.address,
      resultsProvider.address
    );
    
    await factory.deployed();
  });

  describe("Deployment", function () {
    it("Should set the correct admin and default providers", async function () {
      expect(await factory.admin()).to.equal(owner.address);
      expect(await factory.defaultOddsProvider()).to.equal(oddsProvider.address);
      expect(await factory.defaultResultsProvider()).to.equal(resultsProvider.address);
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
        6000,  // 6.000 odds
        5000   // 5.000 odds
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
      const info = await marketContract.getMarketInfo();
      expect(info[0]).to.equal("Lakers");
      expect(info[1]).to.equal("Celtics");
      expect(info[3]).to.equal(6000);
      expect(info[4]).to.equal(5000);
      
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
        5500,  // 5.500 odds
        6500,  // 6.500 odds
        addr3.address,
        addr3.address
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
      const info = await marketContract.getMarketInfo();
      expect(info[0]).to.equal("Warriors");
      expect(info[1]).to.equal("Bulls");
      
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
        gameTimestamp
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
      const info = await marketContract.getMarketInfo();
      expect(info[0]).to.equal("Heat");
      expect(info[1]).to.equal("Suns");
      expect(info[3]).to.equal(0); // homeOdds should be 0
      expect(info[4]).to.equal(0); // awayOdds should be 0
      expect(info[7]).to.equal(false); // oddsSet should be false
      
      // Market should not be ready for betting yet
      expect(await marketContract.isReadyForBetting()).to.equal(false);
      
      // After updating odds, market should be ready for betting
      await marketContract.connect(oddsProvider).updateOdds(1850, 2000);
      expect(await marketContract.isReadyForBetting()).to.equal(true);
    });
    
    it("Should fail when non-admin tries to create market", async function () {
      const gameTimestamp = Math.floor(Date.now() / 1000) + 86400;
      
      await expect(
        factory.connect(addr3).createMarket(
          "Lakers",
          "Celtics",
          gameTimestamp,
          6000,
          5000
        )
      ).to.be.revertedWith("Only admin can call this function");
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
      ).to.be.revertedWith("Only admin can call this function");
      
      await expect(
        factory.connect(addr3).setDefaultResultsProvider(addr3.address)
      ).to.be.revertedWith("Only admin can call this function");
    });

    it("Should fail when transferring admin to zero address", async function () {
      await expect(
        factory.transferAdmin(ethers.constants.AddressZero)
      ).to.be.revertedWith("New admin cannot be zero address");
    });
  });
});