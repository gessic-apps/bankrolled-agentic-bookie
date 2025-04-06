"use client";

import { useState } from 'react';
import { useAccount } from 'wagmi';

const BACKEND_API_URL = 'http://localhost:3000'; // Your backend server URL

export default function Faucet() {
  const { address, isConnected } = useAccount();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleFaucetRequest = async () => {
    if (!isConnected || !address) {
      setError('Please connect your wallet first.');
      setMessage('');
      return;
    }

    setLoading(true);
    setMessage('');
    setError('');

    try {
      const response = await fetch(`${BACKEND_API_URL}/api/faucet`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          address: address,
          amount: 1000, // Request 1000 USDX by default
        }),
      });
      console.log(await response);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || data.details || 'Faucet request failed');
      }

      setMessage(`Successfully received 1000 USDX! Transaction: ${data.transaction}`);
    } catch (err: any) {
      console.error('Faucet error:', err);
      setError(err.message || 'An error occurred while requesting tokens.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="my-4 p-4 border rounded shadow-sm bg-white">
      <h2 className="text-xl font-semibold mb-2">Token Faucet</h2>
      {isConnected ? (
        <>
          <p className="mb-2 text-sm">Connected: <code className="text-xs bg-gray-100 p-1 rounded break-all">{address}</code></p>
          <button
            onClick={handleFaucetRequest}
            disabled={loading}
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50 disabled:cursor-not-allowed transition duration-150 ease-in-out"
          >
            {loading ? 'Requesting...' : 'Get 1000 USDX'}
          </button>
          {message && <p className="text-green-600 mt-2 text-sm break-all">{message}</p>}
          {error && <p className="text-red-600 mt-2 text-sm break-all">{error}</p>}
        </>
      ) : (
        <p className="text-yellow-600">Please connect your wallet to use the faucet.</p>
      )}
    </div>
  );
} 