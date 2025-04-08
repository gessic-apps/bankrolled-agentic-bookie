"use client";

import { useEffect, useState } from "react";
import MarketsList from "../components/MarketsList";
import Faucet from "../components/Faucet";
import UserBetsList from "../components/UserBetsList";
import { Market } from "../types/market";
import '@rainbow-me/rainbowkit/styles.css';
import {
  getDefaultConfig,
  RainbowKitProvider,
} from '@rainbow-me/rainbowkit';
import { WagmiProvider } from 'wagmi';
import {
  baseSepolia, // Removed baseSepolia
  polygon,
  optimism,
  arbitrum,
  base, // Added base
} from 'wagmi/chains';
import {
  QueryClientProvider,
  QueryClient,
} from "@tanstack/react-query";
import { ConnectButton } from '@rainbow-me/rainbowkit';


const config = getDefaultConfig({
  appName: 'Bankrolled',
  projectId: 'YOUR_PROJECT_ID', // TODO: Replace with your actual RainbowKit Project ID
  chains: [baseSepolia],
  // chains: [base], // Use Base Mainnet
  ssr: false, // If your dApp uses server side rendering (SSR)
});

// Define USDX address for Base Mainnet
const usdxAddress = "0xb0175c78b647E84b9cff8cAFE70Eee8aF12f6eA1";

export default function Home() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const queryClient = new QueryClient();
  const API_URL = "http://localhost:3000"; // TODO: Update if your API URL is different for mainnet
  // const usdxAddress = "0x0000000000000000000000000000000000000000"; // Removed placeholder

  useEffect(() => {
    const fetchMarkets = async () => {
      try {
        setLoading(true);
        // Fetch markets from your backend API
        // This API should ideally return markets compatible with Base Mainnet contracts
        const response = await fetch(`${API_URL}/api/markets`);

        if (!response.ok) {
          throw new Error(`Failed to fetch markets: ${response.statusText}`);
        }

        const data = await response.json();
         // TODO: Ensure the market data includes the correct contract addresses for Base Mainnet
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
  }, []); // TODO: Consider adding API_URL to dependency array if it can change

  return (
    <WagmiProvider config={config}>
    <QueryClientProvider client={queryClient}>
      <RainbowKitProvider>
      <main className="container mx-auto px-4 py-8">
        <div className="flex justify-end mb-4"> {/* Position ConnectButton */}
            <ConnectButton />
        </div>
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
         // Pass the mainnet USDX address to MarketsList
        <MarketsList usdxAddress={usdxAddress} markets={markets} />
      )}

      {/* Display user bets below the markets list */}
      {/* Pass the fetched markets to the UserBetsList component */}
      {!loading && !error && (
         <UserBetsList markets={markets} />
      )}
    </main>
      </RainbowKitProvider>
    </QueryClientProvider>
  </WagmiProvider>


  );
}
