const { ethers } = require("hardhat");
const axios = require("axios");

async function main() {
  const [deployer] = await ethers.getSigners();
  
  console.log("Creating markets with the account:", deployer.address);
  
  // You would need to replace this with your deployed factory address
  const factoryAddress = process.env.FACTORY_ADDRESS;
  
  if (!factoryAddress) {
    console.error("Please set the FACTORY_ADDRESS environment variable");
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
        homeOdds: 6000, // 60.00%
        awayOdds: 5000  // 50.00%
      },
      {
        homeTeam: "Warriors",
        awayTeam: "Bulls",
        startTime: Math.floor(Date.now() / 1000) + 90000, // tomorrow + 1 hour
        homeOdds: 5500, // 55.00%
        awayOdds: 6500  // 65.00%
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
        game.homeOdds,
        game.awayOdds
      );
      
      const receipt = await tx.wait();
      
      // Find the MarketCreated event to get the market address
      const marketCreatedEvent = receipt.events.find(event => event.event === "MarketCreated");
      const marketAddress = marketCreatedEvent.args[0];
      
      console.log(`Market created at address: ${marketAddress}`);
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