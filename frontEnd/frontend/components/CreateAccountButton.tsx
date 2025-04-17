"use client";

import React, { useState, useEffect, useRef } from "react";
import { ConnectButton } from "@rainbow-me/rainbowkit";
import { generatePrivateKey, privateKeyToAccount } from "viem/accounts";
import { useAccount, useDisconnect } from "wagmi";
import { useWallet } from "../contexts/WalletContext";

const CreateAccountButton = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [privateKey, setPrivateKey] = useState<string | null>(null);
  const [showOptions, setShowOptions] = useState(false);
  const [isCreatingAccount, setIsCreatingAccount] = useState(false);
  const { isConnected } = useAccount();
  const { disconnect } = useDisconnect();
  const [showAccountDetails, setShowAccountDetails] = useState(false);
  const [showPrivateKey, setShowPrivateKey] = useState(false);
  const detailsRef = useRef<HTMLDivElement>(null);
  const { isManagedWallet, managedAddress, displayAddress, refreshBalance, loadManagedWallet } = useWallet();
  console.log("displayAddress", displayAddress);
  // Handle clicks outside of the account details dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (detailsRef.current && !detailsRef.current.contains(event.target as Node)) {
        setShowAccountDetails(false);
        setShowPrivateKey(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const createNewAccount = async () => {
    try {
      // Set loading state to show spinner
      setIsCreatingAccount(true);
      
      // Generate a new private key
      const newPrivateKey = generatePrivateKey();
      setPrivateKey(newPrivateKey);
      
      // Store the private key in local storage
      localStorage.setItem("bankrolled-wallet", newPrivateKey);
      localStorage.setItem("bankrolled-wallet-type", "managed");
      
      // Create account from private key 
      const account = privateKeyToAccount(newPrivateKey);
      
      // Fund the account with a small amount of ETH for gas
      try {
        console.log('Funding new wallet with ETH for gas...');
        
        // Make multiple attempts to fund the wallet
        let fundingSuccess = false;
        let attempts = 0;
        const maxAttempts = 3;
        
        while (!fundingSuccess && attempts < maxAttempts) {
          attempts++;
          
          try {
            const fundResponse = await fetch('/api/fund-wallet', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ address: account.address }),
            });
            
            const fundData = await fundResponse.json();
            console.log(`Wallet funding attempt ${attempts} result:`, fundData);
            
            if (fundData.success) {
              fundingSuccess = true;
              console.log('Successfully funded wallet with ETH');
              
              // Wait a moment for the transaction to be mined
              await new Promise(resolve => setTimeout(resolve, 3000));
            } else {
              console.warn(`Warning: Failed to fund wallet with ETH on attempt ${attempts}`, fundData.error);
              // Wait before retrying
              await new Promise(resolve => setTimeout(resolve, 2000));
            }
          } catch (attemptError) {
            console.error(`Error funding wallet on attempt ${attempts}:`, attemptError);
            // Wait before retrying
            await new Promise(resolve => setTimeout(resolve, 2000));
          }
        }
        
        if (!fundingSuccess) {
          console.warn('Warning: Failed to fund wallet with ETH after multiple attempts');
          // Continue anyway, as we'll try again when user places a bet
        }
      } catch (fundError) {
        console.error('Error in wallet funding process:', fundError);
        // Continue anyway, as we'll try again when user places a bet
      }
      
      // Update wallet state immediately to reflect managed account connection
      loadManagedWallet();
      
      // Show the private key modal
      setIsOpen(true);
      
      // Trigger refresh after wallet creation
      setTimeout(() => {
        refreshBalance();
        loadManagedWallet(); // Load the wallet state again after a delay to ensure it's updated
        // Clear loading state after everything is done
        setIsCreatingAccount(false);
      }, 500);
    } catch (error) {
      console.error('Error creating new account:', error);
      alert('Failed to create new account. Please try again.');
      // Make sure to clear loading state on error
      setIsCreatingAccount(false);
    }
  };
  
  const useExistingWallet = () => {
    // Simply hide options and let user connect via RainbowKit
    setShowOptions(false);
  };
  
  const handleAccountCreation = () => {
    // Show options for account creation
    setShowOptions(true);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const handleDisconnect = () => {
    if (isConnected) {
      // If connected via RainbowKit, disconnect
      disconnect();
    }
    
    // Clear managed wallet state
    localStorage.removeItem("bankrolled-wallet-type");
    localStorage.removeItem("bankrolled-wallet");
    setShowAccountDetails(false);
    
    // Update wallet state immediately
    loadManagedWallet();
    
    // Refresh display after disconnecting
    setTimeout(() => {
      refreshBalance();
      loadManagedWallet(); // Load again after a delay to ensure state is updated
    }, 500);
  };

  const formatAddress = (address: string | undefined | null) => {
    if (!address) return '';
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  // If connected via RainbowKit, show standard RainbowKit button
  if (isConnected && !isManagedWallet) {
    return <ConnectButton />;
  }

  // If using our managed wallet, show our custom connected state
  if (isManagedWallet && managedAddress) {
    return (
      <div className="relative" ref={detailsRef}>
        <button 
          onClick={() => setShowAccountDetails(!showAccountDetails)} 
          className="flex items-center bg-green-100 text-green-800 px-4 py-2 rounded-md hover:bg-green-200 transition-colors shadow-sm"
        >
          <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
          <span className="text-sm font-medium">Connected (Managed)</span>
        </button>
        
        {showAccountDetails && (
          <div className="absolute right-0 mt-2 w-72 bg-white rounded-md shadow-lg border border-gray-200 z-50 dark:bg-gray-800 dark:border-gray-700">
            <div className="p-4">
              <div className="flex items-center mb-3">
                <div className="mb-1 text-sm text-gray-600 dark:text-gray-400">Connected Address:</div>
                <span className="ml-2 text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full dark:bg-blue-900 dark:text-blue-200">
                  Managed
                </span>
              </div>
              <div className="font-mono text-xs bg-gray-100 p-2 rounded mb-3 dark:bg-gray-700 dark:text-gray-300">
                {formatAddress(managedAddress)}
              </div>
              <div className="text-xs text-gray-500 mb-3 dark:text-gray-400">
                This is a managed wallet created by the app. Your private key is stored locally on your device.
              </div>
              <button 
                    onClick={() => copyToClipboard(managedAddress || "")}
                    className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                  >
                    Copy to Clipboard
                </button>
              
              {showPrivateKey ? (
                <div className="mb-3">
                  <div className="text-xs text-amber-800 dark:text-amber-200 mb-1">
                    Private Key (Keep this secret!):
                  </div>
                  <div className="font-mono text-xs bg-gray-100 p-2 rounded mb-2 overflow-x-auto dark:bg-gray-700 dark:text-gray-300 text-amber-800 dark:text-amber-200">
                    {localStorage.getItem("bankrolled-wallet")}
                  </div>
                  <button 
                    onClick={() => copyToClipboard(localStorage.getItem("bankrolled-wallet") || "")}
                    className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                  >
                    Copy to Clipboard
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setShowPrivateKey(true)}
                  className="w-full mb-3 bg-amber-100 text-amber-800 px-3 py-2 rounded-md text-sm hover:bg-amber-200 transition-colors dark:bg-amber-900 dark:text-amber-100 dark:hover:bg-amber-800"
                >
                  Show Private Key
                </button>
              )}
              
              <button 
                onClick={handleDisconnect}
                className="w-full bg-red-100 text-red-700 px-3 py-2 rounded-md text-sm hover:bg-red-200 transition-colors dark:bg-red-900 dark:text-red-100 dark:hover:bg-red-800"
              >
                Disconnect
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Default state - not connected
  return (
    <>
      {showOptions ? (
        <div className="flex flex-col space-y-2">
          <button 
            onClick={createNewAccount} 
            className="bg-primary text-white px-4 py-2 rounded-md hover:bg-primary/90 flex items-center justify-center"
            disabled={isCreatingAccount}
          >
            {isCreatingAccount ? (
              <>
                <svg className="animate-spin h-4 w-4 mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Creating Account...
              </>
            ) : (
              "Create Account For Me"
            )}
          </button>
          <button 
            onClick={useExistingWallet} 
            className="border border-gray-300 bg-transparent px-4 py-2 rounded-md hover:bg-gray-100"
            disabled={isCreatingAccount}
          >
            Use My Own Wallet
          </button>
        </div>
      ) : (
        <button 
          onClick={handleAccountCreation} 
          className="bg-primary text-white px-4 py-2 rounded-md hover:bg-primary/90"
        >
          Connect Wallet
        </button>
      )}

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <div className="mb-4">
              <h2 className="text-xl font-semibold">Your Account Has Been Created!</h2>
            </div>
            
            <div className="mt-4 space-y-4">
              <p>
                We&apos;ve created a wallet for you! Below is your password that can be used to recover your account.
                Please save this password somewhere safe!
              </p>
              
              <div className="p-2 bg-gray-100 rounded-md">
                <code className="text-xs break-all">{privateKey}</code>
              </div>
              
              <button 
                onClick={() => copyToClipboard(privateKey || "")}
                className="w-full border border-gray-300 bg-transparent px-4 py-2 rounded-md hover:bg-gray-100"
              >
                Copy to Clipboard
              </button>
              
              <div className="text-sm text-gray-500">
                <p>Important: This password is your private key and gives complete access to your account.</p>
                <p>Never share it with anyone and keep it in a safe place.</p>
              </div>
              
              <button 
                onClick={() => {
                  setIsOpen(false);
                  // Ensure wallet state is updated when closing the modal
                  loadManagedWallet();
                }}
                className="w-full bg-primary text-white px-4 py-2 rounded-md hover:bg-primary/90 mt-4"
              >
                I&apos;ve Saved My Password
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default CreateAccountButton;