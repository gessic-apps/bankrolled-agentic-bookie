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
        const deployer = getDefaultWallet(provider);
        const oddsProvider = getRoleSigner('oddsProvider', provider);
        const resultsProvider = getRoleSigner('resultsProvider', provider);
        
        console.log(`Deploying from address: ${deployer.address}`);
        console.log(`Odds provider address: ${oddsProvider.address}`);
        console.log(`Results provider address: ${resultsProvider.address}`);
        
        // Get contract factory
        const MarketFactory = await ethers.getContractFactory('MarketFactory', deployer);
        
        // Deploy contract
        console.log('Deploying MarketFactory...');
        const marketFactory = await MarketFactory.deploy(
            oddsProvider.address,
            resultsProvider.address
        );
        
        // Wait for deployment to complete
        await marketFactory.deployed();
        
        console.log(`✅ MarketFactory deployed to: ${marketFactory.address}`);
        console.log(`Transaction hash: ${marketFactory.deployTransaction.hash}`);
        
        // Save deployment info to a file
        const deploymentInfo = {
            networkName: 'hardhat',
            networkId: (await provider.getNetwork()).chainId,
            contracts: {
                marketFactory: {
                    address: marketFactory.address,
                    deployer: deployer.address,
                    oddsProvider: oddsProvider.address,
                    resultsProvider: resultsProvider.address,
                    deploymentTx: marketFactory.deployTransaction.hash,
                    deploymentBlock: await provider.getBlockNumber(),
                    deploymentTimestamp: Math.floor(Date.now() / 1000)
                }
            }
        };
        
        // Write deployment info to file
        const deploymentFile = path.join(__dirname, '..', 'deployment-info.json');
        fs.writeFileSync(deploymentFile, JSON.stringify(deploymentInfo, null, 2));
        console.log(`Deployment information saved to ${deploymentFile}`);
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