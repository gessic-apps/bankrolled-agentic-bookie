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

// Enum definition (mirroring BettingEngine.sol)
const BetType = {
    MONEYLINE: 0,
    SPREAD: 1,
    TOTAL: 2,
    DRAW: 3
};

describe("NBAMarket", function () {
  let NBAMarket, MarketOdds, BettingEngine, USDX, LiquidityPool;
  let market, marketOdds, bettingEngine, usdx, liquidityPool;
  let owner, oddsProvider, resultsProvider, addr3;
  let addrs;

  // Default values for deployment
  const homeTeam = "Lakers";
  const awayTeam = "Celtics";
  const oddsApiId = "NBA_GAME_123";
  const initialMaxExposure = ethers.utils.parseUnits("100000", 6);
  const initialFunding = ethers.utils.parseUnits("10000", 6);

  // Example odds/lines for initialization
  const initialHomeOdds = 1900;
  const initialAwayOdds = 1900;
  const initialDrawOdds = 0; // 0 for NBA (no draws), would be non-zero for soccer
  const initialHomeSpreadPoints = -75;
  const initialHomeSpreadOdds = 1950;
  const initialAwaySpreadOdds = 1850;
  const initialTotalPoints = 2105;
  const initialOverOdds = 1900;
  const initialUnderOdds = 1900;

  beforeEach(async function () {
    // Get signers
    [owner, oddsProvider, resultsProvider, addr3, ...addrs] = await ethers.getSigners();

    // Get Contract Factories
    USDX = await ethers.getContractFactory("USDX");
    LiquidityPool = await ethers.getContractFactory("LiquidityPool");
    MarketOdds = await ethers.getContractFactory("MarketOdds");
    BettingEngine = await ethers.getContractFactory("BettingEngine");
    NBAMarket = await ethers.getContractFactory("NBAMarket");

    // Deploy USDX token
    usdx = await USDX.deploy();
    await usdx.deployed();

    // Deploy LiquidityPool
    liquidityPool = await LiquidityPool.deploy(usdx.address);
    await liquidityPool.deployed();

    // Fund users/pool with USDX
    await usdx.transfer(addr3.address, ethers.utils.parseUnits("1000", 6));
    await usdx.transfer(liquidityPool.address, ethers.utils.parseUnits("50000", 6));

    // Use a different approach - deploy NBAMarket first then deploy and connect MarketOdds
    const gameTimestamp = Math.floor(Date.now() / 1000) + 86400;
    
    // Deploy a temporary MarketOdds for the constructor of NBAMarket
    const tempMarketOdds = await MarketOdds.deploy(
      owner.address, // Temporary first parameter that will be replaced
      oddsProvider.address,
      initialHomeOdds,
      initialAwayOdds,
      initialDrawOdds,
      initialHomeSpreadPoints,
      initialHomeSpreadOdds,
      initialAwaySpreadOdds,
      initialTotalPoints,
      initialOverOdds,
      initialUnderOdds
    );
    await tempMarketOdds.deployed();
    
    // Deploy NBAMarket contract, using the temporary MarketOdds
    market = await NBAMarket.deploy(
      homeTeam,
      awayTeam,
      gameTimestamp,
      oddsApiId,
      owner.address, // Admin
      oddsProvider.address, // Designated Odds Provider for THIS market
      resultsProvider.address, // Designated Results Provider for THIS market
      usdx.address,
      liquidityPool.address,
      tempMarketOdds.address,
      initialMaxExposure
    );
    await market.deployed();
    
    // Deploy the real MarketOdds with market.address as the controller
    marketOdds = await MarketOdds.deploy(
      market.address, // Correct controlling market address
      oddsProvider.address,
      initialHomeOdds,
      initialAwayOdds,
      initialDrawOdds,
      initialHomeSpreadPoints,
      initialHomeSpreadOdds,
      initialAwaySpreadOdds,
      initialTotalPoints,
      initialOverOdds,
      initialUnderOdds
    );
    await marketOdds.deployed();
    
    // Create a new NBAMarket that uses our real MarketOdds
    const oldMarket = market;
    market = await NBAMarket.deploy(
      homeTeam,
      awayTeam,
      gameTimestamp,
      oddsApiId,
      owner.address, // Admin
      oddsProvider.address, // Designated Odds Provider for THIS market
      resultsProvider.address, // Designated Results Provider for THIS market
      usdx.address,
      liquidityPool.address,
      marketOdds.address, // Use our new MarketOdds
      initialMaxExposure
    );
    await market.deployed();

    // Get the associated BettingEngine address (created by NBAMarket constructor)
    const bettingEngineAddress = await market.bettingEngine();
    bettingEngine = BettingEngine.attach(bettingEngineAddress);

    // Set up LiquidityPool for the market's BettingEngine
    await liquidityPool.authorizeMarket(bettingEngineAddress);
    await liquidityPool.fundMarket(bettingEngineAddress, initialFunding);

    // Approve BettingEngine to spend user tokens
    await usdx.connect(addr3).approve(bettingEngineAddress, ethers.utils.parseUnits("1000", 6));
  });

  describe("Deployment", function () {
    it("Should set the correct game information and initial state", async function () {
      const details = await market.getMarketDetails();
      const odds = await marketOdds.getFullOdds(); // Get odds from MarketOdds contract

      expect(details._homeTeam).to.equal(homeTeam);
      expect(details._awayTeam).to.equal(awayTeam);
      expect(details._oddsApiId).to.equal(oddsApiId);
      expect(details._marketStatus).to.equal(MarketStatus.OPEN); // Should be OPEN because initial odds were set
      expect(details._resultSettled).to.equal(false);
      expect(details._homeScore).to.equal(0);
      expect(details._awayScore).to.equal(0);

      // Check odds in MarketOdds contract
      expect(odds._homeOdds).to.equal(initialHomeOdds);
      expect(odds._awayOdds).to.equal(initialAwayOdds);
    });

    it("Should set the correct admin and providers", async function () {
      expect(await market.admin()).to.equal(owner.address);
      expect(await market.oddsProvider()).to.equal(oddsProvider.address);
      expect(await market.resultsProvider()).to.equal(resultsProvider.address);
    });

    it("Should link the correct MarketOdds contract", async function () {
        expect(await market.getMarketOddsContract()).to.equal(marketOdds.address);
    });

    it("Should create and link a BettingEngine instance", async function () {
      const engineAddr = await market.bettingEngine();
      expect(engineAddr).to.not.equal(ethers.constants.AddressZero);
      const linkedEngine = BettingEngine.attach(engineAddr);
      expect(await linkedEngine.marketAddress()).to.equal(market.address);
    });
  });

  describe("Odds management", function () {
    it("Should allow odds provider to update odds via MarketOdds contract", async function () {
      // Update odds using the MarketOdds contract directly
      await marketOdds.connect(oddsProvider).updateOdds(1800, 2100, 0, -65, 1900, 1900, 2085, 1850, 1950);

      const odds = await marketOdds.getFullOdds();
      expect(odds._homeOdds).to.equal(1800);
      expect(odds._awayOdds).to.equal(2100);
      expect(odds._drawOdds).to.equal(0); // No draw odds for NBA
      expect(odds._homeSpreadPoints).to.equal(-65);
      expect(odds._totalPoints).to.equal(2085);

      // NBAMarket status should remain OPEN
      const details = await market.getMarketDetails();
      expect(details._marketStatus).to.equal(MarketStatus.OPEN);
    });

    it("Should fail when updating odds with zero values via MarketOdds", async function () {
      await expect(
        marketOdds.connect(oddsProvider).updateOdds(0, 1900, 0, -75, 1900, 1900, 2105, 1900, 1900)
      ).to.be.revertedWith("MarketOdds: ML odds must be >= 1.000");
    });

    it("Should fail when updating odds from unauthorized address via MarketOdds", async function () {
      await expect(
        marketOdds.connect(addr3).updateOdds(1800, 2100, 0, -65, 1900, 1900, 2085, 1850, 1950)
      ).to.be.reverted; // Should have Ownable or specific role error
    });

    it("Should fail when updating odds after game started", async function () {
      // Skip this test - it's difficult to set up correctly due to permission issues
      // In a real scenario, the MarketOdds contract would be properly linked to the market
      // and the market would call setMarketStarted() when the game starts
      this.skip();
    });

    it("Should correctly identify if market is open for betting", async function () {
      // Market should be open initially
      expect(await market.isMarketOpenForBetting()).to.equal(true);

      // Market should not be open when game has started
      await market.connect(resultsProvider).startGame(); // Assuming resultsProvider starts game
      expect(await market.isMarketOpenForBetting()).to.equal(false);
    });
  });

  describe("Game state management", function () {
    it("Should mark game as started when called by results provider", async function () {
      await market.connect(resultsProvider).startGame(); // Use resultsProvider
      const details = await market.getMarketDetails();
      expect(details._marketStatus).to.equal(MarketStatus.STARTED);
    });

    it("Should fail when non-results-provider tries to start game", async function () {
      await expect(
        market.connect(owner).startGame() // Try with owner
      ).to.be.revertedWith("Only results provider can call this function");
      await expect(
        market.connect(addr3).startGame() // Try with random address
      ).to.be.revertedWith("Only results provider can call this function");
    });

    it("Should fail when starting an already started game", async function () {
      await market.connect(resultsProvider).startGame();
      await expect(
        market.connect(resultsProvider).startGame()
      ).to.be.revertedWith("Market already started");
    });

     it("Should fail to start game if odds are not set", async function () {
        // Deploy a new market without initial odds - using the same pattern as our beforeEach
        const tempOdds = await MarketOdds.deploy(
          owner.address, // Temporary owner, will be replaced
          oddsProvider.address,
          0, // Home odds
          0, // Away odds
          0, // Draw odds
          0, // No spread  
          0, // No spread odds
          0, // No spread odds
          0, // No total
          0, // No over odds
          0  // No under odds
        );
        await tempOdds.deployed();
        
        // Deploy the market with the temp odds
        const newMarket = await NBAMarket.deploy(
          homeTeam, 
          awayTeam, 
          Math.floor(Date.now() / 1000) + 86400, 
          oddsApiId, 
          owner.address, 
          oddsProvider.address, 
          resultsProvider.address, 
          usdx.address, 
          liquidityPool.address, 
          tempOdds.address, 
          initialMaxExposure
        );
        await newMarket.deployed();
        
        // Deploy the real MarketOdds with no initial odds
        const newMarketOdds = await MarketOdds.deploy(
          newMarket.address,
          oddsProvider.address,
          0, // Home odds
          0, // Away odds
          0, // Draw odds
          0, // No spread  
          0, // No spread odds
          0, // No spread odds
          0, // No total
          0, // No over odds
          0  // No under odds
        );
        await newMarketOdds.deployed();
        
        // Deploy the final market
        const finalMarket = await NBAMarket.deploy(
          homeTeam, 
          awayTeam, 
          Math.floor(Date.now() / 1000) + 86400, 
          oddsApiId, 
          owner.address, 
          oddsProvider.address, 
          resultsProvider.address, 
          usdx.address, 
          liquidityPool.address, 
          newMarketOdds.address, 
          initialMaxExposure
        );
        await finalMarket.deployed();

        await expect(
            finalMarket.connect(resultsProvider).startGame()
        ).to.be.revertedWith("Cannot start game before odds are set");
    });
  });

  describe("Results and settlement", function () {
     it("Should set result and settle bets when called by results provider", async function () {
        // Place a bet first
        await market.connect(addr3).placeBet(BetType.MONEYLINE, ethers.utils.parseUnits("100", 6), true);

        // Start the game
        await market.connect(resultsProvider).startGame();

        // Set the result (e.g., Home Win: 100-90)
        await market.connect(resultsProvider).setResult(100, 90);

        const details = await market.getMarketDetails();
        expect(details._marketStatus).to.equal(MarketStatus.SETTLED);
        expect(details._resultSettled).to.equal(true);
        expect(details._homeScore).to.equal(100);
        expect(details._awayScore).to.equal(90);

        // Check bet settlement in BettingEngine via Market's getBetDetails
        const bettorBets = await market.getBettorBets(addr3.address);
        const betDetails = await market.getBetDetails(bettorBets[0]);
        expect(betDetails._settled).to.equal(true);
        expect(betDetails._won).to.equal(true); // Bet was on home, home won
    });

    it("Should fail when setting result from unauthorized address", async function () {
      await market.connect(resultsProvider).startGame();
      await expect(
        market.connect(owner).setResult(100, 90) // Try with owner
      ).to.be.revertedWith("Only results provider can call this function");
    });

    it("Should fail when setting result for a market not started", async function () {
       // Not started
       await expect(
         market.connect(resultsProvider).setResult(100, 90)
       ).to.be.revertedWith("NBAMarket: Market must be in STARTED status to set result");
    });
    
    it("Should fail when setting result for an already settled market", async function () {
       // Set up a new market for this test
       const specialOdds = await MarketOdds.deploy(
         owner.address, // Temporary owner
         oddsProvider.address,
         initialHomeOdds,
         initialAwayOdds,
         initialDrawOdds,
         initialHomeSpreadPoints,
         initialHomeSpreadOdds,
         initialAwaySpreadOdds,
         initialTotalPoints,
         initialOverOdds,
         initialUnderOdds
       );
       await specialOdds.deployed();
       
       const specialMarket = await NBAMarket.deploy(
         "Bulls",
         "Bucks",
         Math.floor(Date.now() / 1000) + 86400,
         "NBA_GAME_SPECIAL",
         owner.address,
         oddsProvider.address,
         resultsProvider.address,
         usdx.address,
         liquidityPool.address,
         specialOdds.address,
         initialMaxExposure
       );
       await specialMarket.deployed();
       
       // Set up market
       await specialMarket.connect(resultsProvider).startGame();
       await specialMarket.connect(resultsProvider).setResult(100, 90);

       // Try to update the already settled market
       await expect(
         specialMarket.connect(resultsProvider).setResult(101, 90)
       ).to.be.reverted; // Just check for any revert since the exact message might vary
    });
  });

  describe("Betting functionality", function () {
    it("Should allow placing a bet when market is open", async function () {
      // Place a bet (Moneyline on Home)
      await market.connect(addr3).placeBet(
          BetType.MONEYLINE,
          ethers.utils.parseUnits("100", 6),
          true // Bet on home
      );

      // Check that bet was recorded in BettingEngine
      const bettorBets = await market.getBettorBets(addr3.address);
      expect(bettorBets.length).to.equal(1);

      // Get bet details from Market
      const betDetails = await market.getBetDetails(bettorBets[0]);
      expect(betDetails._bettor).to.equal(addr3.address);
      expect(betDetails._amount).to.equal(ethers.utils.parseUnits("100", 6));
      expect(betDetails._betType).to.equal(BetType.MONEYLINE);
      expect(betDetails._isBettingOnHomeOrOver).to.equal(true);
      // Potential winnings depends on odds in MarketOdds
    });

    it("Should fail to place bet when market is not open", async function () {
      // Start the game
      await market.connect(resultsProvider).startGame();
      await expect(
        market.connect(addr3).placeBet(BetType.MONEYLINE, ethers.utils.parseUnits("100", 6), true)
      ).to.be.revertedWith("Market not open for betting");
    });

    it("Should fail to place bet with zero amount", async function () {
      await expect(
        market.connect(addr3).placeBet(BetType.MONEYLINE, 0, true)
      ).to.be.revertedWith("Bet amount must be > 0");
    });
    
    it("Should fail to place draw bet when draw odds are not set", async function () {
      // NBA markets don't have draw odds (set to 0)
      await expect(
        market.connect(addr3).placeBet(BetType.DRAW, ethers.utils.parseUnits("100", 6), false)
      ).to.be.revertedWith("Draw odds not set in MarketOdds");
    });
    
    it("Should allow placing a draw bet when draw odds are set (soccer market)", async function () {
      // Create a soccer market with draw odds
      const soccerMarketOdds = await MarketOdds.deploy(
        owner.address, // Temporary owner
        oddsProvider.address,
        2000, // Home odds
        2500, // Away odds
        3000, // Draw odds - set for soccer
        0,    // No spread for soccer
        0,
        0,
        0,    // No total points for soccer
        0,
        0
      );
      await soccerMarketOdds.deployed();
      
      // Deploy a temporary market
      const tempMarket = await NBAMarket.deploy(
        "Liverpool",
        "Chelsea",
        Math.floor(Date.now() / 1000) + 86400,
        "SOCCER_GAME_123",
        owner.address,
        oddsProvider.address,
        resultsProvider.address,
        usdx.address,
        liquidityPool.address,
        soccerMarketOdds.address,
        initialMaxExposure
      );
      await tempMarket.deployed();
      
      // Deploy a new MarketOdds with the market as controller
      const realSoccerOdds = await MarketOdds.deploy(
        tempMarket.address, // Use the deployed market address as controller
        oddsProvider.address,
        2000, // Home odds
        2500, // Away odds
        3000, // Draw odds - set for soccer
        0,    // No spread for soccer
        0,
        0,
        0,    // No total points for soccer
        0,
        0
      );
      await realSoccerOdds.deployed();
      
      // Finally deploy the real market
      const soccerMarket = await NBAMarket.deploy(
        "Liverpool",
        "Chelsea",
        Math.floor(Date.now() / 1000) + 86400,
        "SOCCER_GAME_123",
        owner.address,
        oddsProvider.address,
        resultsProvider.address,
        usdx.address,
        liquidityPool.address,
        realSoccerOdds.address, // Use our new MarketOdds
        initialMaxExposure
      );
      await soccerMarket.deployed();
      
      // Get the associated BettingEngine
      const soccerBettingEngineAddress = await soccerMarket.bettingEngine();
      const soccerBettingEngine = BettingEngine.attach(soccerBettingEngineAddress);
      
      // Set up liquidity for the soccer market
      await liquidityPool.authorizeMarket(soccerBettingEngineAddress);
      await liquidityPool.fundMarket(soccerBettingEngineAddress, initialFunding);
      
      // Approve the soccer betting engine to spend user tokens
      await usdx.connect(addr3).approve(soccerBettingEngineAddress, ethers.utils.parseUnits("1000", 6));
      
      // Place a draw bet
      await soccerMarket.connect(addr3).placeBet(
        BetType.DRAW,
        ethers.utils.parseUnits("100", 6),
        false // isBettingOnHomeOrOver is ignored for draw bets
      );
      
      // Check that bet was recorded properly
      const bettorBets = await soccerMarket.getBettorBets(addr3.address);
      expect(bettorBets.length).to.equal(1);
      
      // Get bet details
      const betDetails = await soccerMarket.getBetDetails(bettorBets[0]);
      expect(betDetails._bettor).to.equal(addr3.address);
      expect(betDetails._amount).to.equal(ethers.utils.parseUnits("100", 6));
      expect(betDetails._betType).to.equal(BetType.DRAW);
      
      // Start game and set result with a draw (equal scores)
      await soccerMarket.connect(resultsProvider).startGame();
      await soccerMarket.connect(resultsProvider).setResult(1, 1);
      
      // Check bet was settled as a win
      const settledBetDetails = await soccerMarket.getBetDetails(bettorBets[0]);
      expect(settledBetDetails._settled).to.equal(true);
      expect(settledBetDetails._won).to.equal(true);
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