require("@nomiclabs/hardhat-waffle");
require("@nomiclabs/hardhat-ethers");
require('dotenv').config();

/**
 * @type import('hardhat/config').HardhatUserConfig
 */
module.exports = {
  defaultNetwork: "baseSepolia",
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 1
      },
      viaIR: true
    }
  },
  networks: {
    // localhost: {
    //   url: "http://127.0.0.1:8545"
    // },
    // hardhat: {
    //   chainId: 31337
    // },
    baseSepolia: {
      url: process.env.BASE_SEPOLIA_RPC_URL || "https://base-sepolia-rpc.publicnode.com",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      chainId: 84532,
      gasPrice: 1500000000, // 1.5 gwei
      gas: 8000000, // Gas limit
      blockGasLimit: 8000000,
      timeout: 60000 // 60 seconds
    },
    // testnet: {
    //   url: process.env.TESTNET_RPC_URL || "",
    //   accounts: process.env.PRIVATE_KEY !== undefined ? [process.env.PRIVATE_KEY] : []
    // }
  },
  paths: {
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  }
};