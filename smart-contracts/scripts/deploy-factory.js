/**
 * Script to deploy the Market Factory contract using a private key
 */
const { ethers } = require('hardhat');
const { 
    getDefaultWallet,
    getRoleSigner,
    setupProvider 
} = require('../utils/wallet-helper');
const fs = require('fs');
const path = require('path');

async function main() {
    try {
        // Setup provider and signers
        const provider = setupProvider();
        const deployer = await getDefaultWallet(provider);
        const oddsProvider = await getRoleSigner('oddsProvider', provider);
        const resultsProvider = await getRoleSigner('resultsProvider', provider);
        
        console.log(`Deploying from address: ${deployer.address}`);
        console.log(`Odds provider address: ${oddsProvider.address}`);
        console.log(`Results provider address: ${resultsProvider.address}`);
        
        // Read deployed contracts info
        const deployedContractsPath = path.join(__dirname, "../deployed-contracts.json");
        let deployedContracts = {};
        
        if (fs.existsSync(deployedContractsPath)) {
            const fileContent = fs.readFileSync(deployedContractsPath, "utf8");
            deployedContracts = JSON.parse(fileContent);
        } else {
            throw new Error("Please deploy the USDX token and Liquidity Pool first using deploy-liquidity.js");
        }
        
        // Check if USDX and LiquidityPool are deployed
        if (!deployedContracts.usdx || !deployedContracts.liquidityPool) {
            throw new Error("USDX token and Liquidity Pool must be deployed first");
        }
        
        console.log(`Using USDX token at: ${deployedContracts.usdx}`);
        console.log(`Using Liquidity Pool at: ${deployedContracts.liquidityPool}`);
        
        // Get contract factory
        const MarketFactory = await ethers.getContractFactory('MarketFactory', deployer);
        
        // Deploy contract
        console.log('Deploying MarketFactory...');
        const marketFactory = await MarketFactory.deploy(
            oddsProvider.address,
            resultsProvider.address,
            deployedContracts.usdx,
            deployedContracts.liquidityPool
        );
        
        // Wait for deployment to complete
        await marketFactory.deployed();
        
        console.log(`✅ MarketFactory deployed to: ${marketFactory.address}`);
        console.log(`Transaction hash: ${marketFactory.deployTransaction.hash}`);
        
        // Update the LiquidityPool with the MarketFactory address
        console.log("Setting MarketFactory in LiquidityPool...");
        const LiquidityPool = await ethers.getContractFactory('LiquidityPool', deployer);
        const liquidityPool = LiquidityPool.attach(deployedContracts.liquidityPool);
        
        const tx = await liquidityPool.setMarketFactory(marketFactory.address);
        await tx.wait();
        console.log("LiquidityPool updated with MarketFactory address");
        
        // Update deployed contracts
        deployedContracts.marketFactory = marketFactory.address;
        fs.writeFileSync(deployedContractsPath, JSON.stringify(deployedContracts, null, 2));
        console.log("Updated deployed-contracts.json with MarketFactory address");
        
        console.log("Deployment complete! ✅");
    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    }
}

// Execute main function
main()
    .then(() => process.exit(0))
    .catch(error => {
        console.error(error);
        process.exit(1);
    });