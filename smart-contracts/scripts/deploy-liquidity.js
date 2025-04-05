// Script to deploy the USDX token and liquidity pool
const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("Deploying USDX token and Liquidity Pool...");

  // Get the deployer
  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with the account:", deployer.address);

  // Deploy the USDX token
  const USDX = await ethers.getContractFactory("USDX");
  const usdxToken = await USDX.deploy();
  await usdxToken.deployed();
  console.log("USDX token deployed to:", usdxToken.address);

  // Deploy the Liquidity Pool
  const LiquidityPool = await ethers.getContractFactory("LiquidityPool");
  const liquidityPool = await LiquidityPool.deploy(usdxToken.address);
  await liquidityPool.deployed();
  console.log("Liquidity Pool deployed to:", liquidityPool.address);

  // Transfer 500k USDX tokens to the liquidity pool (keep some for user betting)
  const initialSupply = ethers.utils.parseUnits("500000", 6); // 500k tokens with 6 decimals
  await usdxToken.transfer(liquidityPool.address, initialSupply);
  console.log("Transferred 500k USDX tokens to Liquidity Pool");
  
  // Check balance of liquidity pool
  const lpBalance = await usdxToken.balanceOf(liquidityPool.address);
  console.log("Liquidity Pool balance:", ethers.utils.formatUnits(lpBalance, 6), "USDX");

  // Get the current deployed contract addresses
  const deployedContractsPath = path.join(__dirname, "../deployed-contracts.json");
  let deployedContracts = {};
  
  if (fs.existsSync(deployedContractsPath)) {
    const fileContent = fs.readFileSync(deployedContractsPath, "utf8");
    deployedContracts = JSON.parse(fileContent);
  }

  // Add the new contracts to the deployed contracts
  deployedContracts.usdx = usdxToken.address;
  deployedContracts.liquidityPool = liquidityPool.address;

  // Write the updated contracts to the deployed-contracts.json file
  fs.writeFileSync(deployedContractsPath, JSON.stringify(deployedContracts, null, 2));
  console.log("Deployment information saved to deployed-contracts.json");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });