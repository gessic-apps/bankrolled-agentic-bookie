/**
 * Wallet helper utilities for signing transactions with a private key
 */
const { ethers } = require('ethers');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

// Cache for wallets to avoid recreating them
const walletCache = {};

/**
 * Gets an ethers Wallet instance from a private key or keystore file
 * @param {Object} options Options for creating the wallet
 * @param {string} [options.privateKey] Private key as a hex string
 * @param {string} [options.keystoreFile] Path to keystore file
 * @param {string} [options.keystorePassword] Password for keystore file
 * @param {string} [options.mnemonic] Mnemonic phrase
 * @param {string} [options.accountIndex=0] Account index to use with mnemonic
 * @param {string} [options.walletId] Optional ID to cache this wallet
 * @param {ethers.providers.Provider} provider Ethers provider to attach to wallet
 * @returns {ethers.Wallet} An ethers Wallet instance
 */
function getWallet(options, provider) {
    const {
        privateKey,
        keystoreFile,
        keystorePassword,
        mnemonic,
        accountIndex = 0,
        walletId
    } = options;

    // Check if wallet is cached
    if (walletId && walletCache[walletId]) {
        return walletCache[walletId].connect(provider);
    }

    let wallet;

    // Create wallet from private key
    if (privateKey) {
        wallet = new ethers.Wallet(privateKey);
    }
    // Create wallet from keystore file
    else if (keystoreFile && keystorePassword) {
        const keystore = fs.readFileSync(keystoreFile, 'utf8');
        wallet = ethers.Wallet.fromEncryptedJsonSync(keystore, keystorePassword);
    }
    // Create wallet from mnemonic
    else if (mnemonic) {
        const path = `m/44'/60'/0'/0/${accountIndex}`;
        wallet = ethers.Wallet.fromMnemonic(mnemonic, path);
    }
    // Use a random wallet for testing (NOT SECURE - only for local development)
    else {
        wallet = ethers.Wallet.createRandom();
        console.warn('Created a random wallet for testing. DO NOT use this in production!');
        console.log('Wallet address:', wallet.address);
        console.log('Private key:', wallet.privateKey);
    }

    // Connect wallet to provider
    if (provider) {
        wallet = wallet.connect(provider);
    }

    // Cache wallet if walletId is provided
    if (walletId) {
        walletCache[walletId] = wallet;
    }

    return wallet;
}

/**
 * Gets default wallet from environment variables
 * @param {ethers.providers.Provider} provider Ethers provider to attach to wallet
 * @returns {ethers.Wallet} Default wallet from environment variables
 */
function getDefaultWallet(provider) {
    // First try to use private key from .env
    if (process.env.PRIVATE_KEY) {
        return getWallet({ privateKey: process.env.PRIVATE_KEY, walletId: 'default' }, provider);
    }

    // Then try to use keystore file from .env
    if (process.env.KEYSTORE_FILE && process.env.KEYSTORE_PASSWORD) {
        return getWallet({ 
            keystoreFile: process.env.KEYSTORE_FILE, 
            keystorePassword: process.env.KEYSTORE_PASSWORD, 
            walletId: 'default' 
        }, provider);
    }

    // Then try to use mnemonic from .env
    if (process.env.MNEMONIC) {
        return getWallet({ 
            mnemonic: process.env.MNEMONIC, 
            accountIndex: process.env.ACCOUNT_INDEX || 0, 
            walletId: 'default' 
        }, provider);
    }

    // For development, use first signer from hardhat
    if (process.env.NODE_ENV === 'development') {
        try {
            // For local hardhat node, return first account (which has lots of ETH)
            const hardhatPrivateKey = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80';
            return getWallet({ privateKey: hardhatPrivateKey, walletId: 'hardhat0' }, provider);
        } catch (error) {
            console.warn('Error getting hardhat wallet:', error.message);
        }
    }

    // If all else fails, create a random wallet (only for testing!)
    console.warn('No wallet configuration found. Creating a random test wallet.');
    return getWallet({}, provider);
}

/**
 * Creates and returns a signer for the specified role
 * @param {string} role Role ("admin", "oddsProvider", "resultsProvider")
 * @param {ethers.providers.Provider} provider Ethers provider
 * @returns {ethers.Wallet} Wallet for the specified role
 */
function getRoleSigner(role, provider) {
    // For hardhat development network, use predefined accounts
    if (process.env.NODE_ENV === 'development') {
        // Map of hardhat's default private keys
        const hardhatAccounts = {
            admin:          '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80', // account 0
            oddsProvider:   '0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d', // account 1
            resultsProvider:'0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a', // account 2
            user1:          '0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6', // account 3
            user2:          '0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a', // account 4
        };

        if (hardhatAccounts[role]) {
            return getWallet({ 
                privateKey: hardhatAccounts[role], 
                walletId: `hardhat-${role}` 
            }, provider);
        }
    }

    // For production/testnet, use environment variables if available
    const envKey = `${role.toUpperCase()}_PRIVATE_KEY`;
    if (process.env[envKey]) {
        return getWallet({ 
            privateKey: process.env[envKey], 
            walletId: role 
        }, provider);
    }

    // Default back to the first account
    console.warn(`No specific wallet found for role ${role}. Using default wallet.`);
    return getDefaultWallet(provider);
}

/**
 * Creates a signed transaction for contract interaction
 * @param {Object} options Transaction options
 * @param {string} options.contractAddress Contract address
 * @param {Array} options.contractAbi Contract ABI
 * @param {string} options.method Method name to call
 * @param {Array} options.params Parameters for the method
 * @param {string} options.role Role for signing ("admin", "oddsProvider", "resultsProvider")
 * @param {ethers.providers.Provider} provider Ethers provider
 * @returns {Promise<Object>} Transaction details and receipt
 */
async function signAndSendTransaction(options, provider) {
    const {
        contractAddress,
        contractAbi,
        method,
        params = [],
        role = 'admin'
    } = options;

    try {
        // Get wallet based on role
        const wallet = getRoleSigner(role, provider);
        
        // Create contract instance with signer
        const contract = new ethers.Contract(contractAddress, contractAbi, wallet);
        
        // Estimate gas to avoid failures
        const gasEstimate = await contract.estimateGas[method](...params);
        
        // Add 20% buffer to gas estimate
        const gasLimit = gasEstimate.mul(120).div(100);
        
        // Send transaction
        const tx = await contract[method](...params, { gasLimit });
        
        // Wait for confirmation
        const receipt = await tx.wait();
        
        return {
            success: true,
            transaction: tx.hash,
            from: wallet.address,
            to: contractAddress,
            method,
            params,
            receipt: {
                blockNumber: receipt.blockNumber,
                blockHash: receipt.blockHash,
                gasUsed: receipt.gasUsed.toString(),
                status: receipt.status === 1 ? 'success' : 'failed'
            }
        };
    } catch (error) {
        return {
            success: false,
            error: error.message,
            method,
            params
        };
    }
}

/**
 * Setup a provider based on environment
 * @returns {ethers.providers.Provider} Ethers provider
 */
function setupProvider() {
    // For local development using Hardhat node
    if (process.env.NODE_ENV === 'development') {
        return new ethers.providers.JsonRpcProvider('http://localhost:8545');
    }
    
    // For testnet or mainnet
    if (process.env.TESTNET_RPC_URL) {
        return new ethers.providers.JsonRpcProvider(process.env.TESTNET_RPC_URL);
    }
    
    throw new Error('No RPC URL configured. Set TESTNET_RPC_URL in .env file.');
}

// Export utility functions
module.exports = {
    getWallet,
    getDefaultWallet,
    getRoleSigner,
    signAndSendTransaction,
    setupProvider
};