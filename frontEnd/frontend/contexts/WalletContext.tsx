"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useAccount, useReadContract, useWalletClient } from 'wagmi';
import { Address, createWalletClient, http, WalletClient } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { CONTRACT_ADDRESSES, WAGMI_CONFIG } from '../config/contracts';
import { ethers, BrowserProvider, Signer } from 'ethers';

// ERC20 standard ABI for balanceOf and decimals
const tokenAbi = [
  {
    "constant": true,
    "inputs": [{"name": "_owner", "type": "address"}],
    "name": "balanceOf",
    "outputs": [{"name": "balance", "type": "uint256"}],
    "type": "function"
  },
  {
    "constant": true,
    "inputs": [],
    "name": "decimals",
    "outputs": [{"name": "", "type": "uint8"}],
    "type": "function"
  }
];

interface WalletContextType {
  managedAddress: string | null;
  displayAddress: string | null;
  isManagedWallet: boolean;
  balance: bigint | undefined;
  formattedBalance: string;
  isLoading: boolean;
  isError: boolean;
  refreshBalance: () => void;
  tokenDecimals: number;
  getManagedSigner: () => Promise<Signer | null>;
  getEthersSigner: () => Promise<Signer | null>;
  signTransactionWithManagedWallet: (txData: any) => Promise<string | null>;
  loadManagedWallet: () => void; // New method to reload managed wallet state
}

const WalletContext = createContext<WalletContextType>({
  managedAddress: null,
  displayAddress: null,
  isManagedWallet: false,
  balance: undefined,
  formattedBalance: '0.00',
  isLoading: false,
  isError: false,
  refreshBalance: () => {},
  tokenDecimals: 6,
  getManagedSigner: async () => null,
  getEthersSigner: async () => null,
  signTransactionWithManagedWallet: async () => null,
  loadManagedWallet: () => {},
});

export const useWallet = () => useContext(WalletContext);

export const WalletProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { address, isConnected } = useAccount();
  const { data: walletClient } = useWalletClient();
  const [managedAddress, setManagedAddress] = useState<string | null>(null);
  const [isManagedWallet, setIsManagedWallet] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [privateKey, setPrivateKey] = useState<`0x${string}` | null>(null);

  // Refresh balance function
  const refreshBalance = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
  }, []);

  // Function to load/reload managed wallet state from localStorage
  const loadManagedWallet = useCallback(() => {
    if (typeof window === 'undefined') return;
    
    const storedPrivateKey = localStorage.getItem("bankrolled-wallet");
    const walletType = localStorage.getItem("bankrolled-wallet-type");
    
    if (storedPrivateKey && walletType === "managed") {
      try {
        const account = privateKeyToAccount(storedPrivateKey as `0x${string}`);
        setManagedAddress(account.address);
        setIsManagedWallet(true);
        setPrivateKey(storedPrivateKey as `0x${string}`);
        console.log("Loaded managed wallet:", account.address);
      } catch (error) {
        console.error("Error loading managed account:", error);
      }
    } else {
      setIsManagedWallet(false);
      setPrivateKey(null);
    }
  }, []);

  // Load managed wallet on initial mount
  useEffect(() => {
    loadManagedWallet();
  }, [loadManagedWallet]);

  // Determine which address to use
  const displayAddress = address || managedAddress;

  // Set up listener for faucet events
  useEffect(() => {
    const handleFaucetEvent = () => {
      setTimeout(refreshBalance, 1000);
    };

    window.addEventListener('faucet-success', handleFaucetEvent);
    return () => {
      window.removeEventListener('faucet-success', handleFaucetEvent);
    };
  }, [refreshBalance]);

  // Get token decimals
  const { data: decimals } = useReadContract({
    address: CONTRACT_ADDRESSES.USDX_ADDRESS as Address,
    abi: tokenAbi,
    functionName: 'decimals',
  });

  // Get balance with refetch capability
  const { 
    data: balance, 
    isError, 
    isLoading, 
    refetch 
  } = useReadContract({
    address: CONTRACT_ADDRESSES.USDX_ADDRESS as Address,
    abi: tokenAbi,
    functionName: 'balanceOf',
    args: [displayAddress as Address],
    //@ts-expect-error TO DO fix
    enabled: !!displayAddress,
  });

  // Refresh when trigger changes
  useEffect(() => {
    if (displayAddress) {
      refetch();
    }
  }, [refreshTrigger, displayAddress, refetch]);

  // Auto-refresh every 15 seconds
  useEffect(() => {
    const interval = setInterval(refreshBalance, 15000);
    return () => clearInterval(interval);
  }, [refreshBalance]);

  // Format balance
  const tokenDecimals = decimals !== undefined ? Number(decimals) : 6;
  
  let formattedBalance = '0.00';
  if (balance) {
    formattedBalance = (Number(balance) / 10**tokenDecimals).toFixed(2);
  }

  // Get a signer for the managed wallet
  const getManagedSigner = useCallback(async (): Promise<Signer | null> => {
    if (!privateKey || !isManagedWallet) return null;

    try {
      // Create a provider
      const provider = new ethers.JsonRpcProvider(WAGMI_CONFIG.RPC_URL);
      
      // Create wallet from private key
      const wallet = new ethers.Wallet(privateKey, provider);
      
      return wallet;
    } catch (error) {
      console.error("Error creating managed wallet signer:", error);
      return null;
    }
  }, [privateKey, isManagedWallet]);

  // Convert WalletClient to Ethers Signer for connected wallet
  const getEthersSigner = useCallback(async (): Promise<Signer | null> => {
    if (!walletClient || !isConnected) return null;

    try {
      const { account, chain, transport } = walletClient;
      
      if (!account || !chain || !transport) {
        console.warn("WalletClient is missing required properties");
        return null;
      }
      
      const network = {
        chainId: chain.id,
        name: chain.name,
      };
      
      const provider = new BrowserProvider(transport, network);
      
      if (!account.address) {
        console.warn("WalletClient account is missing address");
        return null;
      }
      
      const signer = await provider.getSigner(account.address);
      return signer;
    } catch (error) {
      console.error("Error getting ethers signer:", error);
      return null;
    }
  }, [walletClient, isConnected]);
  
  // Sign a transaction with the managed wallet
  const signTransactionWithManagedWallet = useCallback(async (txData: any): Promise<string | null> => {
    if (!isManagedWallet || !privateKey) {
      console.error("No managed wallet available for signing");
      return null;
    }
    
    try {
      const signer = await getManagedSigner();
      if (!signer) {
        throw new Error("Failed to get signer for managed wallet");
      }
      
      // Send the transaction and wait for receipt
      const tx = await signer.sendTransaction(txData);
      console.log("Transaction sent:", tx.hash);
      
      // Wait for transaction to be mined
      const receipt = await tx.wait();
      
      if (!receipt) {
        throw new Error("Transaction failed to be mined");
      }
      
      return tx.hash;
    } catch (error) {
      console.error("Error signing transaction with managed wallet:", error);
      return null;
    }
  }, [isManagedWallet, privateKey, getManagedSigner]);

  // Context value
  const value: WalletContextType = {
    managedAddress,
    displayAddress,
    isManagedWallet,
    //@ts-expect-error TO DO fix
    balance,
    formattedBalance,
    isLoading,
    isError,
    refreshBalance,
    tokenDecimals,
    getManagedSigner,
    getEthersSigner,
    signTransactionWithManagedWallet,
    loadManagedWallet,
  };

  return (
    <WalletContext.Provider value={value}>
      {children}
    </WalletContext.Provider>
  );
};

export default WalletProvider;