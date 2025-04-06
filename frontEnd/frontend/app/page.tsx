"use client";

import { useEffect, useState } from "react";
import MarketsList from "../components/MarketsList";
import Faucet from "../components/Faucet";
import { Market } from "../types/market";
import '@rainbow-me/rainbowkit/styles.css';
import {
  getDefaultConfig,
  RainbowKitProvider,
} from '@rainbow-me/rainbowkit';
import { WagmiProvider } from 'wagmi';
import {
  mainnet,
  polygon,
  optimism,
  arbitrum,
  base,
} from 'wagmi/chains';
import {
  QueryClientProvider,
  QueryClient,
} from "@tanstack/react-query";
import { ConnectButton } from '@rainbow-me/rainbowkit';


const config = getDefaultConfig({
  appName: 'Bankrolled',
  projectId: 'YOUR_PROJECT_ID',
  chains: [mainnet, polygon, optimism, arbitrum, base],
  ssr: false, // If your dApp uses server side rendering (SSR)
});


export default function Home() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const queryClient = new QueryClient();
  const API_URL = "http://localhost:3000"; // Default API URL

  useEffect(() => {
    const fetchMarkets = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_URL}/api/markets`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch markets: ${response.statusText}`);
        }
        
        const data = await response.json();
        setMarkets(data);
        setError("");
      } catch (err: any) {
        console.error("Error fetching markets:", err);
        setError(err.message || "Failed to load markets");
      } finally {
        setLoading(false);
      }
    };

    fetchMarkets();
  }, []);

  return (
    <WagmiProvider config={config}>
    <QueryClientProvider client={queryClient}>
      <RainbowKitProvider>
      <main className="container mx-auto px-4 py-8">
      <ConnectButton />
      <Faucet />

      <h1 className="text-3xl font-bold mb-6">NBA Betting Markets</h1>
      
      {loading ? (
        <div className="text-center py-10">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" role="status">
            <span className="sr-only">Loading...</span>
          </div>
          <p className="mt-2">Loading markets...</p>
        </div>
      ) : error ? (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <p>{error}</p>
          <p className="text-sm mt-1">Make sure the API server is running at {API_URL}</p>
        </div>
      ) : (
        <MarketsList markets={markets} />
      )}
    </main>
      </RainbowKitProvider>
    </QueryClientProvider>
  </WagmiProvider>

    
  );
}
