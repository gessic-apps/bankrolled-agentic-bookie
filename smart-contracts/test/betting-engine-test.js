const { expect } = require("chai");
const { ethers } = require("hardhat");

// Enum definition (mirroring BettingEngine.sol)
const BetType = {
    MONEYLINE: 0,
    SPREAD: 1,
    TOTAL: 2
};

describe("BettingEngine", function () {
  let BettingEngine;
  let engine;
  let owner;
  let marketMock;
  let usdx;
  let liquidityPool;
  let user1;
  let user2;
  let addrs;

  beforeEach(async function () {
    // Get signers
    [owner, marketMock, user1, user2, ...addrs] = await ethers.getSigners();

    // Deploy USDX token
    const USDX = await ethers.getContractFactory("USDX");
    usdx = await USDX.deploy();
    await usdx.deployed();
    
    // Deploy LiquidityPool
    const LiquidityPool = await ethers.getContractFactory("LiquidityPool");
    liquidityPool = await LiquidityPool.deploy(usdx.address);
    await liquidityPool.deployed();
    
    // Fund users with USDX
    await usdx.transfer(user1.address, ethers.utils.parseUnits("1000", 6));
    await usdx.transfer(user2.address, ethers.utils.parseUnits("1000", 6));
    
    // Deploy BettingEngine with market mock as the market
    BettingEngine = await ethers.getContractFactory("BettingEngine");
    engine = await BettingEngine.deploy(
      marketMock.address,
      usdx.address,
      liquidityPool.address,
      ethers.utils.parseUnits("100000", 6) // 100k max exposure
    );
    
    await engine.deployed();
    
    // Set up LiquidityPool
    await liquidityPool.authorizeMarket(engine.address);
    await usdx.transfer(liquidityPool.address, ethers.utils.parseUnits("50000", 6));
    await liquidityPool.fundMarket(engine.address, ethers.utils.parseUnits("10000", 6));
    
    // Approve engine to spend user tokens
    await usdx.connect(user1).approve(engine.address, ethers.utils.parseUnits("1000", 6));
    await usdx.connect(user2).approve(engine.address, ethers.utils.parseUnits("1000", 6));
  });

  describe("Initialization", function () {
    it("Should be initialized with correct addresses and values", async function () {
      expect(await engine.marketAddress()).to.equal(marketMock.address);
      expect(await engine.usdx()).to.equal(usdx.address);
      expect(await engine.liquidityPool()).to.equal(liquidityPool.address);
      expect(await engine.maxExposure()).to.equal(ethers.utils.parseUnits("100000", 6));
      expect(await engine.currentExposure()).to.equal(0);
    });
  });

  describe("Bet placement", function () {
    it("Should allow placing a bet when called by market", async function () {
      // Place a bet as the market contract
      await engine.connect(marketMock).placeBet(
        user1.address,
        ethers.utils.parseUnits("100", 6), // 100 USDX
        BetType.MONEYLINE, // betType
        true, // isBettingOnHomeOrOver
        2000, // odds (2.000)
        0 // line (not applicable for ML)
      );
      
      // Get the bet details
      const betDetails = await engine.getBetDetails(0);
      
      expect(betDetails.bettor).to.equal(user1.address);
      expect(betDetails.amount).to.equal(ethers.utils.parseUnits("100", 6));
      expect(betDetails.potentialWinnings).to.equal(ethers.utils.parseUnits("100", 6)); // (100 * 2.0 - 100)
      expect(betDetails.betType).to.equal(BetType.MONEYLINE);
      expect(betDetails.isBettingOnHomeOrOver).to.equal(true);
      expect(betDetails.line).to.equal(0);
      expect(betDetails.odds).to.equal(2000);
      expect(betDetails.settled).to.equal(false);
      expect(betDetails.won).to.equal(false);
      
      // Check that exposure was updated
      expect(await engine.currentExposure()).to.equal(ethers.utils.parseUnits("100", 6)); // Exposure is potential winnings
      
      // Check that user's bets are tracked
      const userBets = await engine.getBettorBets(user1.address);
      expect(userBets.length).to.equal(1);
      expect(userBets[0]).to.equal(0);
    });
    
    it("Should fail when not called by the market", async function () {
      await expect(
        engine.connect(owner).placeBet(
          user1.address,
          ethers.utils.parseUnits("100", 6),
          BetType.MONEYLINE, // betType
          true, // isBettingOnHomeOrOver
          2000, // odds
          0 // line
        )
      ).to.be.revertedWith("Only the market contract can call this function");
    });
    
    it("Should fail when bet would exceed max exposure", async function () {
      // Set a very low max exposure
      await engine.connect(marketMock).updateMaxExposure(ethers.utils.parseUnits("50", 6));
      
      // Try to place a bet with high potential winnings
      await expect(
        engine.connect(marketMock).placeBet(
          user1.address,
          ethers.utils.parseUnits("100", 6),
          BetType.MONEYLINE, // betType
          true, // isBettingOnHomeOrOver
          2000, // odds (2.000), potential winnings = 100
          0 // line
        )
      ).to.be.revertedWith("Market cannot accept this bet size with current exposure");
    });
  });

  describe("Bet settlement", function () {
    beforeEach(async function () {
      // Place some bets first
      // Bet 1: User 1 on Home, 100 @ 2.0 odds
      await engine.connect(marketMock).placeBet(
        user1.address,
        ethers.utils.parseUnits("100", 6),
        BetType.MONEYLINE,
        true, // home team
        2000, // 2.000 odds
        0
      );
      
      // Bet 2: User 2 on Away, 200 @ 1.5 odds
      await engine.connect(marketMock).placeBet(
        user2.address,
        ethers.utils.parseUnits("200", 6),
        BetType.MONEYLINE,
        false, // away team
        1500, // 1.500 odds
        0
      );
    });
    
    it("Should settle bets correctly with home team win (Moneyline)", async function () {
      // Initial balances
      const initialUser1Balance = await usdx.balanceOf(user1.address);
      const initialUser2Balance = await usdx.balanceOf(user2.address);
      
      // Settle with home team win (scores don't matter for ML settlement in engine directly)
      await engine.connect(marketMock).settleBets(100, 99); // Home Score > Away Score
      
      // Check bet status
      const bet1 = await engine.getBetDetails(0);
      const bet2 = await engine.getBetDetails(1);
      
      expect(bet1.settled).to.equal(true);
      expect(bet1.won).to.equal(true); // User 1 bet on Home, Home won
      expect(bet2.settled).to.equal(true);
      expect(bet2.won).to.equal(false); // User 2 bet on Away, Away lost
      
      // Check final balances
      const finalUser1Balance = await usdx.balanceOf(user1.address);
      const finalUser2Balance = await usdx.balanceOf(user2.address);
      
      // User1 winnings: 100 * (2000 / 1000) = 200 (includes stake)
      expect(finalUser1Balance.sub(initialUser1Balance)).to.equal(ethers.utils.parseUnits("200", 6));
      
      // User2 lost their stake
      expect(finalUser2Balance).to.equal(initialUser2Balance); // No change as stake was transferred on bet placement
      
      // Exposure should be cleared
      expect(await engine.currentExposure()).to.equal(0);
    });
    
    it("Should settle bets correctly with away team win (Moneyline)", async function () {
      // Initial balances
      const initialUser1Balance = await usdx.balanceOf(user1.address);
      const initialUser2Balance = await usdx.balanceOf(user2.address);
      
      // Settle with away team win
      await engine.connect(marketMock).settleBets(99, 100); // Home Score < Away Score
      
      // Check bet status
      const bet1 = await engine.getBetDetails(0);
      const bet2 = await engine.getBetDetails(1);
      
      expect(bet1.settled).to.equal(true);
      expect(bet1.won).to.equal(false); // User 1 bet on Home, Home lost
      expect(bet2.settled).to.equal(true);
      expect(bet2.won).to.equal(true); // User 2 bet on Away, Away won
      
      // Check final balances
      const finalUser1Balance = await usdx.balanceOf(user1.address);
      const finalUser2Balance = await usdx.balanceOf(user2.address);
      
      // User 1 lost their stake
      expect(finalUser1Balance).to.equal(initialUser1Balance);
      
      // User2 winnings: 200 * (1500 / 1000) = 300 (includes stake)
      expect(finalUser2Balance.sub(initialUser2Balance)).to.equal(ethers.utils.parseUnits("300", 6));

      // Exposure should be cleared
      expect(await engine.currentExposure()).to.equal(0);
    });
    
    it("Should fail when not called by the market", async function () {
      await expect(
        engine.connect(owner).settleBets(100, 99)
      ).to.be.revertedWith("Only the market contract can call this function");
    });
  });

  describe("Exposure management", function () {
    it("Should update max exposure correctly", async function () {
      await engine.connect(marketMock).updateMaxExposure(ethers.utils.parseUnits("200000", 6));
      expect(await engine.maxExposure()).to.equal(ethers.utils.parseUnits("200000", 6));
    });
    
    it("Should fail to lower max exposure below current exposure", async function () {
      // Place a bet to create exposure
      await engine.connect(marketMock).placeBet(
        user1.address,
        ethers.utils.parseUnits("100", 6),
        BetType.MONEYLINE,
        true,
        2000, // 2.000 odds, potential winnings = 100 USDX
        0
      );
      
      // Current exposure is 100 USDX (potential winnings)
      expect(await engine.currentExposure()).to.equal(ethers.utils.parseUnits("100", 6));

      // Try to set max exposure below current exposure
      await expect(
        engine.connect(marketMock).updateMaxExposure(ethers.utils.parseUnits("50", 6))
      ).to.be.revertedWith("New max exposure cannot be less than current exposure");
    });
  });
});