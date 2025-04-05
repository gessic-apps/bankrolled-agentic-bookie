const { expect } = require("chai");
const { ethers } = require("hardhat");

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
        true, // bet on home team
        2000 // 2.000 odds
      );
      
      // Get the bet details
      const betDetails = await engine.getBetDetails(0);
      
      expect(betDetails[0]).to.equal(user1.address); // bettor
      expect(betDetails[1]).to.equal(ethers.utils.parseUnits("100", 6)); // amount
      expect(betDetails[2]).to.equal(ethers.utils.parseUnits("100", 6)); // potentialWinnings (100 * 2.0 - 100 = 100)
      expect(betDetails[3]).to.equal(true); // onHomeTeam
      expect(betDetails[4]).to.equal(false); // settled
      expect(betDetails[5]).to.equal(false); // won
      
      // Check that exposure was updated
      expect(await engine.currentExposure()).to.equal(ethers.utils.parseUnits("100", 6));
      
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
          true,
          2000
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
          true,
          2000 // 2.000 odds, meaning 100 USDX potential winnings
        )
      ).to.be.revertedWith("Market cannot accept this bet size with current exposure");
    });
  });

  describe("Bet settlement", function () {
    beforeEach(async function () {
      // Place some bets first
      await engine.connect(marketMock).placeBet(
        user1.address,
        ethers.utils.parseUnits("100", 6),
        true, // home team
        2000 // 2.000 odds
      );
      
      await engine.connect(marketMock).placeBet(
        user2.address,
        ethers.utils.parseUnits("200", 6),
        false, // away team
        1500 // 1.500 odds
      );
    });
    
    it("Should settle bets correctly with home team win", async function () {
      // Initial balances
      const initialUser1Balance = await usdx.balanceOf(user1.address);
      const initialUser2Balance = await usdx.balanceOf(user2.address);
      
      // Settle with home team win (outcome 1)
      await engine.connect(marketMock).settleBets(1);
      
      // Check bet status
      const bet1 = await engine.getBetDetails(0);
      const bet2 = await engine.getBetDetails(1);
      
      expect(bet1[4]).to.equal(true); // settled
      expect(bet1[5]).to.equal(true); // won
      expect(bet2[4]).to.equal(true); // settled
      expect(bet2[5]).to.equal(false); // lost
      
      // Check final balances
      const finalUser1Balance = await usdx.balanceOf(user1.address);
      const finalUser2Balance = await usdx.balanceOf(user2.address);
      
      // User1 should get their bet amount (100) + winnings (100) = 200
      expect(finalUser1Balance.sub(initialUser1Balance)).to.equal(ethers.utils.parseUnits("200", 6));
      
      // User2 should not get anything back
      expect(finalUser2Balance).to.equal(initialUser2Balance);
      
      // LiquidityPool should receive the remaining funds
      // await liquidityPool.returnFunds is called inside settleBets
    });
    
    it("Should settle bets correctly with away team win", async function () {
      // Initial balances
      const initialUser1Balance = await usdx.balanceOf(user1.address);
      const initialUser2Balance = await usdx.balanceOf(user2.address);
      
      // Settle with away team win (outcome 2)
      await engine.connect(marketMock).settleBets(2);
      
      // Check bet status
      const bet1 = await engine.getBetDetails(0);
      const bet2 = await engine.getBetDetails(1);
      
      expect(bet1[4]).to.equal(true); // settled
      expect(bet1[5]).to.equal(false); // lost
      expect(bet2[4]).to.equal(true); // settled
      expect(bet2[5]).to.equal(true); // won
      
      // Check final balances
      const finalUser1Balance = await usdx.balanceOf(user1.address);
      const finalUser2Balance = await usdx.balanceOf(user2.address);
      
      // User1 should not get anything back
      expect(finalUser1Balance).to.equal(initialUser1Balance);
      
      // User2 should get their bet amount (200) + winnings (100) = 300
      expect(finalUser2Balance.sub(initialUser2Balance)).to.equal(ethers.utils.parseUnits("300", 6));
    });
    
    it("Should fail when not called by the market", async function () {
      await expect(
        engine.connect(owner).settleBets(1)
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
        true,
        2000 // 2.000 odds, creating 100 USDX exposure
      );
      
      // Try to set max exposure below current exposure
      await expect(
        engine.connect(marketMock).updateMaxExposure(ethers.utils.parseUnits("50", 6))
      ).to.be.revertedWith("New max exposure must be >= current exposure");
    });
  });
});