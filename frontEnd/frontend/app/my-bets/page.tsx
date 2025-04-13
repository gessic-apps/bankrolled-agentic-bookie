"use client";

import { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WagmiProvider, useAccount, useConfig } from 'wagmi';
import { readContract } from 'wagmi/actions';
import { type Address, BaseError } from 'viem';
import { getDefaultConfig, RainbowKitProvider } from '@rainbow-me/rainbowkit';
// import { baseSepolia } from 'wagmi/chains';
import '@rainbow-me/rainbowkit/styles.css';
import { HeroUIProvider } from "@heroui/react";
import UserBetsList from "../../components/UserBetsList";
import { ConnectButton } from '@rainbow-me/rainbowkit';
import SidebarNav from "../../components/SidebarNav";
import ThemeToggle from "../../components/ThemeToggle";
import FaucetButton from "../../components/FaucetButton";
import { Market } from '../../types/market';
import MarketFactoryABI from '../../abis/contracts/MarketFactory.sol/MarketFactory.json';
import NBAMarketABI from '../../abis/contracts/NBAMarket.sol/NBAMarket.json';

import { WAGMI_CONFIG, CONTRACT_ADDRESSES, SELECTED_NETWORK } from '../../config/contracts';

const config = getDefaultConfig({
  appName: WAGMI_CONFIG.APP_NAME,
  projectId: WAGMI_CONFIG.PROJECT_ID,
  chains: [
    SELECTED_NETWORK
  ],
  ssr: false,
});

function MyBetsPageComponent() {
  const { address, isConnected } = useAccount();
  const wagmiConfig = useConfig();
  const [markets, setMarkets] = useState<Market[]>([]);
  const [isLoadingMarkets, setIsLoadingMarkets] = useState(false);
  const [marketError, setMarketError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMarkets = async () => {
      if (!isConnected || !CONTRACT_ADDRESSES.MARKET_FACTORY_ADDRESS) {
        setMarkets([]);
        return;
      }
      setIsLoadingMarkets(true);
      setMarketError(null);
      setMarkets([]);

      try {
        const marketAddresses = await readContract(wagmiConfig, {
          address: CONTRACT_ADDRESSES.MARKET_FACTORY_ADDRESS as Address,
          abi: MarketFactoryABI.abi,
          functionName: 'getDeployedMarkets',
        }) as Address[] | undefined;

        if (!marketAddresses || marketAddresses.length === 0) {
          setIsLoadingMarkets(false);
          return;
        }

        const marketDetailsPromises = marketAddresses.map(async (marketAddress) => {
          try {
            const [homeTeam, awayTeam] = await Promise.all([
              readContract(wagmiConfig, {
                address: marketAddress,
                abi: NBAMarketABI.abi,
                functionName: 'homeTeam',
              }) as Promise<string>,
              readContract(wagmiConfig, {
                address: marketAddress,
                abi: NBAMarketABI.abi,
                functionName: 'awayTeam',
              }) as Promise<string>
            ]);

            return { address: marketAddress, homeTeam, awayTeam } as Market;
          } catch (err) {
            console.error(`Error fetching details for market ${marketAddress}:`, err);
            if (err instanceof BaseError) {
                setMarketError((prev) => prev ? `${prev}; Market ${marketAddress} fetch error: ${err.shortMessage}` : `Market ${marketAddress} fetch error: ${err.shortMessage}`);
            } else if (err instanceof Error) {
                setMarketError((prev) => prev ? `${prev}; Market ${marketAddress} fetch error: ${err.message}` : `Market ${marketAddress} fetch error: ${err.message}`);
            }
            return null;
          }
        });

        const settledMarketDetails = await Promise.allSettled(marketDetailsPromises);

        const fetchedMarkets = settledMarketDetails
          .filter(result => result.status === 'fulfilled' && result.value !== null)
          .map(result => (result as PromiseFulfilledResult<Market>).value);

        setMarkets(fetchedMarkets);

      } catch (err) {
        console.error("Failed to fetch markets:", err);
        setMarketError("Could not load markets from the blockchain.");
        if (err instanceof BaseError) {
            setMarketError(`Market Factory fetch error: ${err.shortMessage}`);
        } else if (err instanceof Error) {
            setMarketError(`Market Factory fetch error: ${err.message}`);
        }
      } finally {
        setIsLoadingMarkets(false);
      }
    };

    fetchMarkets();
  }, [isConnected, address, wagmiConfig]);

  return (
    <div className="main-container">
      <SidebarNav />
      <div className="content-area">
        <header className="sticky top-0 z-10 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow">
          <div className="container mx-auto px-4 py-4 flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-800 dark:text-white">My Bets</h1>
            <div className="flex items-center gap-4">
              <FaucetButton />
              <ThemeToggle />
              <ConnectButton />
            </div>
          </div>
        </header>
        <main className="container mx-auto px-4 py-8">
          {isLoadingMarkets && <p>Loading markets...</p>}
          {marketError && <p className="text-red-500">Error loading markets: {marketError}</p>}
          <UserBetsList markets={markets} />
        </main>
      </div>
    </div>
  );
}

export default function MyBetsPage() {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <RainbowKitProvider>
          <HeroUIProvider>
            <MyBetsPageComponent />
          </HeroUIProvider>
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}