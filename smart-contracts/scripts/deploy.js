const { ethers } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  
  console.log("Deploying contracts with the account:", deployer.address);
  console.log("Account balance:", (await deployer.getBalance()).toString());

  // Deploy MarketFactory contract
  const MarketFactory = await ethers.getContractFactory("MarketFactory");
  
  // For demonstration, we're using the deployer address as both providers
  // In production, you would use dedicated addresses for these roles
  const factory = await MarketFactory.deploy(
    deployer.address, // odds provider
    deployer.address  // results provider
  );
  
  await factory.deployed();
  
  console.log("MarketFactory deployed to:", factory.address);
  
  // Optional: Deploy a sample market for testing
  // if (process.env.DEPLOY_SAMPLE_MARKET === "true") {
  //   console.log("Deploying a sample NBA market...");
    
  //   // Current time + 1 day
  //   const gameTimestamp = Math.floor(Date.now() / 1000) + 86400;
    
  //   const tx = await factory.createMarket(
  //     "Lakers",    // Home team
  //     "Celtics",   // Away team
  //     gameTimestamp,
  //     6000,        // Home odds (60.00%)
  //     5000         // Away odds (50.00%)
  //   );
    
  //   const receipt = await tx.wait();
    
  //   // Find the MarketCreated event to get the market address
  //   const marketCreatedEvent = receipt.events.find(event => event.event === "MarketCreated");
  //   const marketAddress = marketCreatedEvent.args[0];
    
  //   console.log("Sample NBA market deployed to:", marketAddress);
  // }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });