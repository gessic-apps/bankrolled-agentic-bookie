// Contract addresses for the application
// In production, these would typically come from environment variables

export const CONTRACT_ADDRESSES = {
  // Market Factory contract address
  MARKET_FACTORY_ADDRESS: "0x901C93b664bb5a77085134a14c1EEC5573B5E6a8",
  
  // USDX token contract address
  USDX_ADDRESS: "0x0aC1360DC4A164BedAbc321a96D208ce7ce0c817",
  
  // Expected chain ID for the deployed contracts
  EXPECTED_CHAIN_ID: 84532, // Base Sepolia testnet
};

// Wagmi configuration
export const WAGMI_CONFIG = {
  APP_NAME: 'Bankrolled',
  
  // Replace with your actual RainbowKit Project ID in production
  PROJECT_ID: 'YOUR_PROJECT_ID',
  
  // Default RPC URL for fallback provider
  // In production, use environment variables for sensitive values
  RPC_URL: 'https://base-sepolia.g.alchemy.com/v2/eU1jQGAZyansfxyaBRIHQrBQh1Y0bIQi',
};