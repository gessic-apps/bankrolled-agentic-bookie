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
    <div className="my-4 p-4 border rounded shadow bg-white dark:bg-gray-800 dark:border-gray-700">
      <h2 className="text-xl font-semibold mb-3 text-gray-800 dark:text-white">Test Token Faucet</h2>
      {isConnected ? (
        <>
          <p className="mb-3 text-sm text-gray-600 dark:text-gray-400">
            Connected as: <code className="text-xs bg-gray-100 dark:bg-gray-700 p-1 rounded font-mono break-all">{address}</code>
          </p>
          <button
            onClick={handleFaucetRequest}
            disabled={loading}
            className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed dark:focus:ring-offset-gray-800"
          >
            {loading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Requesting...
              </>
            ) : (
              'Get 1000 Test USDX'
            )}
          </button>
          {message && <p className="mt-3 text-sm font-medium text-green-600 dark:text-green-400">{message}</p>}
          {error && <p className="mt-3 text-sm font-medium text-red-600 dark:text-red-400">{error}</p>}
        </>
      ) : (
        <p className="text-sm text-yellow-600 dark:text-yellow-400">Please connect your wallet to use the faucet.</p>
      )}
    </div>
  );
} 