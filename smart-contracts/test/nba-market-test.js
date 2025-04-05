const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("NBAMarket", function () {
  let NBAMarket;
  let market;
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

    // Deploy USDX token
    const USDX = await ethers.getContractFactory("USDX");
    usdx = await USDX.deploy();
    await usdx.deployed();
    
    // Deploy LiquidityPool
    const LiquidityPool = await ethers.getContractFactory("LiquidityPool");
    liquidityPool = await LiquidityPool.deploy(usdx.address);
    await liquidityPool.deployed();
    
    // Fund users with USDX
    await usdx.transfer(addr3.address, ethers.utils.parseUnits("1000", 6));

    // Deploy NBAMarket contract
    NBAMarket = await ethers.getContractFactory("NBAMarket");
    
    // Current time + 1 day
    const gameTimestamp = Math.floor(Date.now() / 1000) + 86400;
    
    market = await NBAMarket.deploy(
      "Lakers",         // Home team
      "Celtics",        // Away team
      gameTimestamp,    // Game timestamp
      "NBA_GAME_123",   // oddsApiId
      6000,             // Home odds (6.000)
      5000,             // Away odds (5.000)
      owner.address,    // Admin
      oddsProvider.address,  // Odds provider
      resultsProvider.address, // Results provider
      usdx.address,    // USDX token address
      liquidityPool.address,    // Liquidity pool address
      ethers.utils.parseUnits("100000", 6) // Max exposure (100k USDX)
    );
    
    await market.deployed();
    
    // Get the betting engine address
    const bettingEngineAddress = await market.bettingEngine();
    
    // Set up market for testing
    await liquidityPool.authorizeMarket(bettingEngineAddress);
    await usdx.transfer(liquidityPool.address, ethers.utils.parseUnits("50000", 6));
    await liquidityPool.fundMarket(bettingEngineAddress, ethers.utils.parseUnits("10000", 6));
    
    // Approve betting engine to spend user tokens
    await usdx.connect(addr3).approve(bettingEngineAddress, ethers.utils.parseUnits("1000", 6));
  });

  describe("Deployment", function () {
    it("Should set the correct game information", async function () {
      const homeTeam = await market.getHomeTeam();
      const awayTeam = await market.getAwayTeam();
      const odds = await market.getOdds();
      const status = await market.getGameStatus();
      
      expect(homeTeam).to.equal("Lakers");
      expect(awayTeam).to.equal("Celtics");
      expect(odds[0]).to.equal(6000);
      expect(odds[1]).to.equal(5000);
      expect(status[0]).to.equal(false); // gameStarted
      expect(status[1]).to.equal(false); // gameEnded
      expect(status[2]).to.equal(true);  // oddsSet (since we provided initial odds)
      expect(status[3]).to.equal(0);     // Outcome.UNDECIDED
    });

    it("Should set the correct admin and providers", async function () {
      expect(await market.admin()).to.equal(owner.address);
      expect(await market.oddsProvider()).to.equal(oddsProvider.address);
      expect(await market.resultsProvider()).to.equal(resultsProvider.address);
    });
    
    it("Should create a BettingEngine instance", async function () {
      const bettingEngineAddress = await market.bettingEngine();
      expect(bettingEngineAddress).to.not.equal(ethers.constants.AddressZero);
    });
  });

  describe("Odds management", function () {
    it("Should update odds when called by odds provider", async function () {
      await market.connect(oddsProvider).updateOdds(5500, 6500);
      
      const odds = await market.getOdds();
      const status = await market.getGameStatus();
      expect(odds[0]).to.equal(5500);
      expect(odds[1]).to.equal(6500);
      expect(status[2]).to.equal(true); // oddsSet should be true
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
      ).to.be.reverted;
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
  });

  describe("Game state management", function () {
    it("Should mark game as started", async function () {
      await market.connect(owner).startGame();
      
      const status = await market.getGameStatus();
      expect(status[0]).to.equal(true); // gameStarted
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

  describe("Results and settlement", function () {
    it("Should set home win result", async function () {
      await market.connect(resultsProvider).setResult(1);
      
      const status = await market.getGameStatus();
      expect(status[3]).to.equal(1); // Outcome.HOME_WIN
      expect(status[1]).to.equal(true); // gameEnded
    });

    it("Should set away win result", async function () {
      await market.connect(resultsProvider).setResult(2);
      
      const status = await market.getGameStatus();
      expect(status[3]).to.equal(2); // Outcome.AWAY_WIN
      expect(status[1]).to.equal(true); // gameEnded
    });

    it("Should fail when setting result from unauthorized address", async function () {
      await expect(
        market.connect(addr3).setResult(1)
      ).to.be.reverted;
    });

    it("Should fail when setting an invalid result", async function () {
      await expect(
        market.connect(resultsProvider).setResult(3)
      ).to.be.reverted;
    });

    it("Should fail when setting result for an already ended game", async function () {
      await market.connect(resultsProvider).setResult(1);
      
      await expect(
        market.connect(resultsProvider).setResult(2)
      ).to.be.reverted;
    });
    
    it("Should allow emergency settlement by admin", async function () {
      // Place a bet first
      await market.connect(addr3).placeBet(ethers.utils.parseUnits("100", 6), true);
      
      // Start game but don't set result yet
      await market.connect(owner).startGame();
      
      // Set result via admin (to test emergency settlement)
      await market.connect(resultsProvider).setResult(1);
      
      // The market should now be ended and settled
      const status = await market.getGameStatus();
      expect(status[1]).to.equal(true); // gameEnded
    });
  });

  describe("Betting functionality", function () {
    it("Should allow placing a bet when market is ready", async function () {
      // Place a bet
      await market.connect(addr3).placeBet(ethers.utils.parseUnits("100", 6), true);
      
      // Check that bet was recorded
      const bettorBets = await market.getBettorBets(addr3.address);
      expect(bettorBets.length).to.equal(1);
      
      // Get bet details
      const betDetails = await market.getBetDetails(bettorBets[0]);
      expect(betDetails[0]).to.equal(addr3.address); // bettor
      expect(betDetails[1]).to.equal(ethers.utils.parseUnits("100", 6)); // amount
      expect(betDetails[3]).to.equal(true); // onHomeTeam
    });
    
    it("Should fail to place bet when game has started", async function () {
      await market.connect(owner).startGame();
      
      await expect(
        market.connect(addr3).placeBet(ethers.utils.parseUnits("100", 6), true)
      ).to.be.reverted;
    });
    
    it("Should fail to place bet with zero amount", async function () {
      await expect(
        market.connect(addr3).placeBet(0, true)
      ).to.be.reverted;
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