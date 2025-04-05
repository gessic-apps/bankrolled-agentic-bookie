const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("NBAMarket", function () {
  let NBAMarket;
  let market;
  let owner;
  let oddsProvider;
  let resultsProvider;
  let addr3;
  let addrs;

  beforeEach(async function () {
    // Get signers
    [owner, oddsProvider, resultsProvider, addr3, ...addrs] = await ethers.getSigners();

    // Deploy NBAMarket contract
    NBAMarket = await ethers.getContractFactory("NBAMarket");
    
    // Current time + 1 day
    const gameTimestamp = Math.floor(Date.now() / 1000) + 86400;
    
    market = await NBAMarket.deploy(
      "Lakers",         // Home team
      "Celtics",        // Away team
      gameTimestamp,    // Game timestamp
      6000,             // Home odds (6.000)
      5000,             // Away odds (5.000)
      owner.address,    // Admin
      oddsProvider.address,  // Odds provider
      resultsProvider.address // Results provider
    );
    
    await market.deployed();
  });

  describe("Deployment", function () {
    it("Should set the correct game information", async function () {
      const info = await market.getMarketInfo();
      
      expect(info[0]).to.equal("Lakers");
      expect(info[1]).to.equal("Celtics");
      expect(info[3]).to.equal(6000);
      expect(info[4]).to.equal(5000);
      expect(info[5]).to.equal(false); // gameStarted
      expect(info[6]).to.equal(false); // gameEnded
      expect(info[7]).to.equal(true);  // oddsSet (since we provided initial odds)
      expect(info[8]).to.equal(0);     // Outcome.UNDECIDED
    });

    it("Should set the correct admin and providers", async function () {
      expect(await market.admin()).to.equal(owner.address);
      expect(await market.oddsProvider()).to.equal(oddsProvider.address);
      expect(await market.resultsProvider()).to.equal(resultsProvider.address);
    });
  });

  describe("Odds management", function () {
    it("Should update odds when called by odds provider", async function () {
      await market.connect(oddsProvider).updateOdds(5500, 6500);
      
      const info = await market.getMarketInfo();
      expect(info[3]).to.equal(5500);
      expect(info[4]).to.equal(6500);
      expect(info[7]).to.equal(true); // oddsSet should be true
    });

    it("Should fail when updating odds with zero values", async function () {
      await expect(
        market.connect(oddsProvider).updateOdds(0, 6500)
      ).to.be.revertedWith("Odds must be at least 1.000 (1000)");
      
      await expect(
        market.connect(oddsProvider).updateOdds(5500, 0)
      ).to.be.revertedWith("Odds must be at least 1.000 (1000)");
    });

    it("Should fail when updating odds from unauthorized address", async function () {
      await expect(
        market.connect(addr3).updateOdds(5500, 6500)
      ).to.be.revertedWith("Only odds provider can call this function");
    });

    it("Should fail when updating odds after game started", async function () {
      await market.connect(owner).startGame();
      
      await expect(
        market.connect(oddsProvider).updateOdds(5500, 6500)
      ).to.be.revertedWith("Game already started");
    });
    
    it("Should correctly identify if market is ready for betting", async function () {
      // Market should be ready for betting initially (since we provided odds in deployment)
      expect(await market.isReadyForBetting()).to.equal(true);
      
      // Market should not be ready when game has started
      await market.connect(owner).startGame();
      expect(await market.isReadyForBetting()).to.equal(false);
    });
    
    it("Should handle odds format correctly", async function () {
      // Update odds using integer format (1941 for 1.941 and 1051 for 1.051)
      await market.connect(oddsProvider).updateOdds(1941, 1051);
      
      // Check if odds were stored correctly
      expect(await market.homeOdds()).to.equal(1941);
      expect(await market.awayOdds()).to.equal(1051);
      
      // Verify oddsSet is true
      const info = await market.getMarketInfo();
      expect(info[7]).to.equal(true); // oddsSet
    });
    
    it("Should fail when providing invalid odds", async function () {
      // Odds should be at least 1.000 (stored as 1000)
      await expect(
        market.connect(oddsProvider).updateOdds(999, 1500)
      ).to.be.revertedWith("Odds must be at least 1.000 (1000)");
      
      await expect(
        market.connect(oddsProvider).updateOdds(1500, 999)
      ).to.be.revertedWith("Odds must be at least 1.000 (1000)");
    });
  });

  describe("Game state management", function () {
    it("Should mark game as started", async function () {
      await market.connect(owner).startGame();
      
      const info = await market.getMarketInfo();
      expect(info[5]).to.equal(true); // gameStarted
    });

    it("Should fail when non-admin tries to start game", async function () {
      await expect(
        market.connect(addr3).startGame()
      ).to.be.revertedWith("Only admin can call this function");
    });

    it("Should fail when starting an already started game", async function () {
      await market.connect(owner).startGame();
      
      await expect(
        market.connect(owner).startGame()
      ).to.be.revertedWith("Game already started");
    });
  });

  describe("Results management", function () {
    it("Should set home win result", async function () {
      await market.connect(resultsProvider).setResult(1);
      
      const info = await market.getMarketInfo();
      expect(info[8]).to.equal(1); // Outcome.HOME_WIN
      expect(info[6]).to.equal(true); // gameEnded
    });

    it("Should set away win result", async function () {
      await market.connect(resultsProvider).setResult(2);
      
      const info = await market.getMarketInfo();
      expect(info[8]).to.equal(2); // Outcome.AWAY_WIN
      expect(info[6]).to.equal(true); // gameEnded
    });

    it("Should fail when setting result from unauthorized address", async function () {
      await expect(
        market.connect(addr3).setResult(1)
      ).to.be.revertedWith("Only results provider can call this function");
    });

    it("Should fail when setting an invalid result", async function () {
      await expect(
        market.connect(resultsProvider).setResult(3)
      ).to.be.revertedWith("Invalid outcome");
    });

    it("Should fail when setting result for an already ended game", async function () {
      await market.connect(resultsProvider).setResult(1);
      
      await expect(
        market.connect(resultsProvider).setResult(2)
      ).to.be.revertedWith("Game already ended");
    });
  });

  describe("Provider management", function () {
    it("Should change odds provider", async function () {
      await market.connect(owner).changeOddsProvider(addr3.address);
      expect(await market.oddsProvider()).to.equal(addr3.address);
    });

    it("Should change results provider", async function () {
      await market.connect(owner).changeResultsProvider(addr3.address);
      expect(await market.resultsProvider()).to.equal(addr3.address);
    });

    it("Should fail when non-admin tries to change providers", async function () {
      await expect(
        market.connect(addr3).changeOddsProvider(addr3.address)
      ).to.be.revertedWith("Only admin can call this function");
      
      await expect(
        market.connect(addr3).changeResultsProvider(addr3.address)
      ).to.be.revertedWith("Only admin can call this function");
    });
  });
});