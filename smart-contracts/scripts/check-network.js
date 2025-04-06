// Simple script to check network connection and balance
const ethers = require('ethers');

async function main() {
  try {
    // Get provider from environment or use default
    const providerUrl = "https://base-sepolia-rpc.publicnode.com";
    const provider = new ethers.providers.JsonRpcProvider(providerUrl);
    
    // Get account from private key
    const privateKey = "3af88304b5895668955e5926564b5b4d3c4bc6fb965f43bb9ea97b7fd5655413";
    if (!privateKey) {
      console.error("ERROR: PRIVATE_KEY not set in environment");
      process.exit(1);
    }
    
    const wallet = new ethers.Wallet(privateKey, provider);
    
    // Get network info
    const network = await provider.getNetwork();
    console.log('Using account:', wallet.address);
    console.log('Network name:', network.name);
    console.log('Network chainId:', network.chainId);
    
    // Get balance
    const balance = await provider.getBalance(wallet.address);
    console.log('Account balance:', ethers.utils.formatEther(balance), 'ETH');
    
    // Get gas price
    const gasPrice = await provider.getGasPrice();
    console.log('Gas price:', ethers.utils.formatUnits(gasPrice, 'gwei'), 'gwei');
    
    if (network.chainId !== 84532) {
      console.error(`ERROR: Expected Base Sepolia (chainId 84532), but connected to network with chainId ${network.chainId}`);
      process.exit(1);
    }
    
    if (parseFloat(ethers.utils.formatEther(balance)) < 0.01) {
      console.warn(`WARNING: Low account balance (${ethers.utils.formatEther(balance)} ETH). Deployment may fail.`);
    }
    
    console.log("Network check: Successful connection to Base Sepolia");
  } catch (error) {
    console.error("ERROR:", error.message);
    process.exit(1);
  }
}

main();
