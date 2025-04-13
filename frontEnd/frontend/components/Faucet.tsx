"use client";

import { useState } from 'react';
import { useAccount } from 'wagmi';

export default function Faucet() {
  const { address, isConnected } = useAccount();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleFaucetRequest = async () => {
    if (!isConnected || !address) {
      setError('Please connect your wallet first.');
      return;
    }

    setLoading(true);
    setMessage('');
    setError('');

    try {
      const response = await fetch('/api/faucet', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ address }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || data.message || `Faucet request failed: ${response.statusText}`);
      }

      setMessage(data.message || `Successfully minted tokens! Tx: ${data.txHash || 'N/A'}`);
    } catch (err: any) {
      console.error('Faucet error:', err);
      setError(err.message || 'Failed to request tokens.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="my-6 p-5 border rounded-lg shadow-md bg-white dark:bg-gray-800 dark:border-gray-700">
      <div className="flex items-center gap-2 mb-3">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-primary" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
        </svg>
        <h2 className="text-xl font-bold text-gray-800 dark:text-white">Test Token Faucet</h2>
      </div>
      {isConnected ? (
        <>
          <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
            <p className="mb-1 text-sm text-gray-600 dark:text-gray-400">Connected Wallet:</p>
            <code className="block text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded-md font-mono truncate">{address}</code>
          </div>
          <button
            onClick={handleFaucetRequest}
            disabled={loading}
            className="w-full inline-flex items-center justify-center px-4 py-3 border border-transparent text-sm font-medium rounded-lg shadow-md text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed dark:focus:ring-offset-gray-800"
          >
            {loading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Requesting Tokens...
              </>
            ) : (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z" />
                  <path fillRule="evenodd" d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9zM4 13a1 1 0 011-1h1a1 1 0 110 2H5a1 1 0 01-1-1zm5-1a1 1 0 100 2h1a1 1 0 100-2H9z" clipRule="evenodd" />
                </svg>
                Get 1000 Test USDX
              </>
            )}
          </button>
          {message && (
            <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-900 rounded-lg">
              <p className="text-sm font-medium text-green-700 dark:text-green-300">{message}</p>
            </div>
          )}
          {error && (
            <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-900 rounded-lg">
              <p className="text-sm font-medium text-red-700 dark:text-red-300">{error}</p>
            </div>
          )}
        </>
      ) : (
        <div className="p-3 bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-900 rounded-lg">
          <p className="text-sm font-medium text-yellow-700 dark:text-yellow-300">
            Please connect your wallet using the button above to receive test tokens.
          </p>
        </div>
      )}
    </div>
  );
} 