"use client";

import React, { useEffect } from 'react';
import { useManagedAccount } from './ManagedAccountProvider';
import { privateKeyToAccount } from 'viem/accounts';
import { createWalletClient, http } from 'viem';
import { SELECTED_NETWORK } from '../config/contracts';

// This component doesn't render anything but sets up the necessary event listeners
// to intercept transaction signing requests and handle them with our stored private key
export const ManagedAccountSigner: React.FC = () => {
  const { account: managedAccount } = useManagedAccount();

  useEffect(() => {
    // Only attach the listener if we have a managed account 
    // and we're in a browser environment with localStorage
    if (!managedAccount || typeof window === 'undefined' || 
        !localStorage.getItem('bankrolled-wallet') || 
        localStorage.getItem('bankrolled-wallet-type') !== 'managed') {
      return;
    }

    // Flag to ensure we don't create multiple listeners
    let isListenerAttached = false;

    // Create a function to intercept ethereum provider requests
    const handleEthereumRequests = async (event: any) => {
      if (!event.detail || !event.detail.method) return;

      const { method, params } = event.detail;
      
      // Only handle specific signing methods
      if (['eth_sign', 'personal_sign', 'eth_signTransaction', 'eth_sendTransaction'].includes(method)) {
        // Prevent default handling
        event.preventDefault();
        event.stopPropagation();
        
        try {
          // Get the stored private key
          const privateKey = localStorage.getItem('bankrolled-wallet');
          if (!privateKey) throw new Error('No stored private key found');
          
          // Create account from private key
          const account = privateKeyToAccount(privateKey as `0x${string}`);
          
          // Create a wallet client with our private key
          const localWalletClient = createWalletClient({
            account,
            chain: SELECTED_NETWORK,
            transport: http()
          });
          
          let result;
          
          // Handle different signing methods
          switch (method) {
            case 'eth_sign':
            case 'personal_sign':
              result = await localWalletClient.signMessage({
                message: params[0] as string,
              });
              break;
            
            case 'eth_signTransaction':
              result = await localWalletClient.signTransaction(params[0]);
              break;
              
            case 'eth_sendTransaction':
              result = await localWalletClient.sendTransaction(params[0]);
              break;
              
            default:
              throw new Error(`Unsupported method: ${method}`);
          }
          
          // Dispatch a custom event with the result
          window.dispatchEvent(
            new CustomEvent('ethereum_response', {
              detail: { id: event.detail.id, result }
            })
          );
        } catch (error) {
          console.error('Error handling managed account request:', error);
          
          // Dispatch error event
          window.dispatchEvent(
            new CustomEvent('ethereum_response', {
              detail: { id: event.detail.id, error }
            })
          );
        }
      }
    };

    // Only attach if not already attached
    if (!isListenerAttached) {
      isListenerAttached = true;
      window.addEventListener('ethereum_request', handleEthereumRequests);
    }
    
    // Clean up when component unmounts
    return () => {
      if (isListenerAttached) {
        window.removeEventListener('ethereum_request', handleEthereumRequests);
        isListenerAttached = false;
      }
    };
  }, [managedAccount]);

  // This component doesn't render anything
  return null;
};

export default ManagedAccountSigner;