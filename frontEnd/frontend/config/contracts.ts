// Contract addresses for the application
// In production, these would typically come from environment variables
import {  localhost } from 'wagmi/chains';
// import { baseSepolia } from 'wagmi/chains';

export const CONTRACT_ADDRESSES = {
  // Market Factory contract address
  MARKET_FACTORY_ADDRESS: "",
  
  // USDX token contract address
  USDX_ADDRESS: "",
  
  // Expected chain ID for the deployed contracts
  // EXPECTED_CHAIN_ID: 84532, // Base Sepolia testnet
  EXPECTED_CHAIN_ID: 31337, // localhost hardhat
};

// Wagmi configuration
export const WAGMI_CONFIG = {
  APP_NAME: 'Bankrolled',
  
  // Replace with your actual RainbowKit Project ID in production
  PROJECT_ID: 'YOUR_PROJECT_ID',
  
  // Default RPC URL for fallback provider
  // In production, use environment variables for sensitive values
  // RPC_URL: 'https://base-sepolia.g.alchemy.com/v2/eU1jQGAZyansfxyaBRIHQrBQh1Y0bIQi',
  RPC_URL: 'http://127.0.0.1:8545',
};

export const SELECTED_NETWORK = localhost;
// export const SELECTED_NETWORK = baseSepolia;

// export const RPC