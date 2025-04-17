"use client";

import React, { createContext, useContext, useEffect, useState } from 'react';
import { privateKeyToAccount, type Account } from 'viem/accounts';
import { createWalletClient, http } from 'viem';
import { SELECTED_NETWORK } from '../config/contracts';
import ManagedAccountSigner from './ManagedAccountSigner';

// Create context for the managed account
interface ManagedAccountContextType {
  account: Account | null;
  isLoaded: boolean;
  signMessage: (message: string) => Promise<`0x${string}`>;
  signTransaction: (transaction: any) => Promise<`0x${string}`>;
}

const ManagedAccountContext = createContext<ManagedAccountContextType>({
  account: null,
  isLoaded: false,
  signMessage: async () => '0x' as `0x${string}`,
  signTransaction: async () => '0x' as `0x${string}`,
});

export const useManagedAccount = () => useContext(ManagedAccountContext);

export const ManagedAccountProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [account, setAccount] = useState<Account | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [client, setClient] = useState<any>(null);

  useEffect(() => {
    // Check if we have a stored managed wallet
    const storedPrivateKey = localStorage.getItem("bankrolled-wallet");
    const walletType = localStorage.getItem("bankrolled-wallet-type");
    
    if (storedPrivateKey && walletType === "managed") {
      try {
        // Create the account from the private key
        const newAccount = privateKeyToAccount(storedPrivateKey as `0x${string}`);
        setAccount(newAccount);
        
        // Create a wallet client for signing
        const walletClient = createWalletClient({
          account: newAccount,
          chain: SELECTED_NETWORK,
          transport: http()
        });
        
        setClient(walletClient);
      } catch (error) {
        console.error("Error loading managed account:", error);
      }
    }
    
    setIsLoaded(true);
  }, []);

  // Function to sign messages with our private key
  const signMessage = async (message: string): Promise<`0x${string}`> => {
    if (!account || !client) {
      throw new Error("Managed account not available");
    }
    
    try {
      return await client.signMessage({ message });
    } catch (error) {
      console.error("Error signing message:", error);
      throw error;
    }
  };

  // Function to sign transactions with our private key
  const signTransaction = async (transaction: any): Promise<`0x${string}`> => {
    if (!account || !client) {
      throw new Error("Managed account not available");
    }
    
    try {
      return await client.signTransaction(transaction);
    } catch (error) {
      console.error("Error signing transaction:", error);
      throw error;
    }
  };

  return (
    <ManagedAccountContext.Provider
      value={{
        account,
        isLoaded,
        signMessage,
        signTransaction
      }}
    >
      {children}
      {/* Include the signer component if we have a managed account */}
      {account && <ManagedAccountSigner />}
    </ManagedAccountContext.Provider>
  );
};

export default ManagedAccountProvider;