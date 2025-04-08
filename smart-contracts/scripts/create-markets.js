const { ethers } = require("hardhat");
const axios = require("axios");

async function main() {
  const [deployer] = await ethers.getSigners();
  
  console.log("Creating markets with the account:", deployer.address);
  
  // Read deployed contract addresses from file
  const deployedContractsPath = require('path').join(__dirname, '../deployed-contracts.json');
  const deployedContracts = require(deployedContractsPath);
  
  const factoryAddress = deployedContracts.marketFactory;
  
  if (!factoryAddress) {
    console.error("No factory address found in deployed-contracts.json. Please deploy the factory first");
    process.exit(1);
  }
  
  // Get the factory contract instance
  const factory = await ethers.getContractAt("MarketFactory", factoryAddress);
  
  // Fetch NBA games - in a real implementation, you would use a reliable sports API
  // This is a placeholder that demonstrates the concept
  console.log("Fetching NBA games for today...");
  
  try {
    // This is a placeholder API call - you'd need a real sports data API subscription
    // const response = await axios.get('https://api.example.com/nba/games/today');
    // const games = response.data.games;
    
    // For demonstration, using hardcoded sample data
    const games = [
      {
        homeTeam: "Lakers",
        awayTeam: "Celtics",
        startTime: Math.floor(Date.now() / 1000) + 86400, // tomorrow
        homeOdds: 1900, 
        awayOdds: 1900,
        homeSpreadPoints: -55, // -5.5
        homeSpreadOdds: 1910,
        awaySpreadOdds: 1910,
        totalPoints: 2155, // 215.5
        overOdds: 1910,
        underOdds: 1910
      },
      {
        homeTeam: "Warriors",
        awayTeam: "Bulls",
        startTime: Math.floor(Date.now() / 1000) + 90000, // tomorrow + 1 hour
        homeOdds: 2100, 
        awayOdds: 1800,
        homeSpreadPoints: -80, // -8.0
        homeSpreadOdds: 1900,
        awaySpreadOdds: 1900,
        totalPoints: 2205, // 220.5
        overOdds: 1850,
        underOdds: 1950
      }
    ];
    
    console.log(`Found ${games.length} NBA games for today`);
    
    // Create a market for each game
    for (const game of games) {
      console.log(`Creating market for ${game.awayTeam} @ ${game.homeTeam}`);
      
      const tx = await factory.createMarket(
        game.homeTeam,
        game.awayTeam,
        game.startTime,
        `NBA_${game.homeTeam}_${game.awayTeam}_${Math.floor(game.startTime/86400)}`, // Unique oddsApiId
        game.homeOdds,
        game.awayOdds,
        game.homeSpreadPoints,
        game.homeSpreadOdds,
        game.awaySpreadOdds,
        game.totalPoints,
        game.overOdds,
        game.underOdds,
        ethers.utils.parseUnits("50000", 6)  // 50k USDX funding per market
      );
      
      const receipt = await tx.wait();
      
      // Find the MarketCreated event to get the market and odds addresses
      const marketFactoryInterface = new ethers.utils.Interface(factory.interface.abi); // Get Interface from contract instance
      const marketCreatedEventTopic = ethers.utils.id("MarketCreated(address,address,string,string,uint256,string,uint256)");
      
      const marketEventLog = receipt.logs.find(log => 
        log.topics[0] === marketCreatedEventTopic && log.address.toLowerCase() === factoryAddress.toLowerCase()
      );

      if (marketEventLog) {
         const eventData = marketFactoryInterface.parseLog(marketEventLog);
         const marketAddress = eventData.args.marketAddress;
         const oddsContractAddress = eventData.args.oddsContractAddress;
         console.log(`  Market created at address: ${marketAddress}`);
         console.log(`  Associated Odds contract: ${oddsContractAddress}`);
      } else {
          console.error(`  Could not find MarketCreated event for ${game.homeTeam} vs ${game.awayTeam}`);
      }
    }
    
    console.log("All markets created successfully");
    
  } catch (error) {
    console.error("Error creating markets:", error);
    process.exit(1);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });