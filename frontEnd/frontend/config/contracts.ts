// Contract addresses for the application
// In production, these would typically come from environment variables

export const CONTRACT_ADDRESSES = {
  // Market Factory contract address
  MARKET_FACTORY_ADDRESS: "0x3A14799B74b73a63b5ca29023946E0EB3A7E6085",
  
  // USDX token contract address
  USDX_ADDRESS: "0x8c58FdAFa2653BcaE7159EDaB2Be0d1522a3744D",
  
  // Expected chain ID for the deployed contracts
  // EXPECTED_CHAIN_ID: 84532, // Base Sepolia testnet
  EXPECTED_CHAIN_ID: 31337, // Base Sepolia testnet
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