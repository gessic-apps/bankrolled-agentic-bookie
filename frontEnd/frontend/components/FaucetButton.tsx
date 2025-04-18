"use client";

import React, { useState } from 'react';
import { useWallet } from '../contexts/WalletContext';

export default function FaucetButton() {
  const { displayAddress, refreshBalance } = useWallet();
  const [loading, setLoading] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [isError, setIsError] = useState(false);

  // Determine if we should enable the button
  const isButtonEnabled = !!displayAddress;

  const handleFaucetRequest = async () => {
    if (!displayAddress) {
      setToastMessage('Please connect your wallet first.');
      setIsError(true);
      setShowToast(true);
      setTimeout(() => setShowToast(false), 3000);
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('/api/faucet', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ address: displayAddress }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || data.message || `Faucet request failed: ${response.statusText}`);
      }

      setToastMessage(data.message || 'Successfully minted 10 USDX tokens! Check your balance.');
      setIsError(false);
      setShowToast(true);
      setTimeout(() => setShowToast(false), 5000);
      
      // Refresh the balance
      refreshBalance();
      
      // Dispatch a custom event to notify other components (like TokenBalance)
      window.dispatchEvent(new Event('faucet-success'));
    } catch (err: any) {
      console.error('Faucet error:', err);
      setToastMessage(err.message || 'Failed to request tokens.');
      setIsError(true);
      setShowToast(true);
      setTimeout(() => setShowToast(false), 3000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative tooltip">
      <button
        onClick={handleFaucetRequest}
        disabled={loading || !isButtonEnabled}
        className="flex items-center justify-center px-3 py-1.5 rounded-lg bg-yellow-500 hover:bg-yellow-600 text-white font-medium text-sm shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        aria-label={isButtonEnabled ? "Get free coins" : "Connect wallet to get free coins"}
      >
        {loading ? (
          <>
            <svg className="animate-spin h-4 w-4 mr-1.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Minting Test USDX...</span>
          </>
        ) : (
          <>
            <svg 
              xmlns="http://www.w3.org/2000/svg" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2" 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              className="h-4 w-4 mr-1.5"
            >
              <circle cx="12" cy="12" r="8" />
              <path d="M12 6v12" />
              <path d="M6 12h12" />
            </svg>
            <span>Get Coins</span>
          </>
        )}
        <span className="tooltip-text">{isButtonEnabled ? "Click to get 10 free USDX tokens for betting" : "Connect your wallet first to get free tokens"}</span>
      </button>
      
      {/* Toast notification */}
      {showToast && (
        <div className={`absolute top-full right-0 mt-2 z-50 p-3 rounded-lg shadow-lg text-sm w-64 text-white ${isError ? 'bg-red-500' : 'bg-green-500'}`}>
          {toastMessage}
        </div>
      )}
    </div>
  );
}