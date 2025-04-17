"use client";

import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WagmiProvider, useReadContract } from 'wagmi';
import { readContract } from 'wagmi/actions';
import { getDefaultConfig, RainbowKitProvider } from '@rainbow-me/rainbowkit';
import { type Address, BaseError } from 'viem';
import '@rainbow-me/rainbowkit/styles.css';
import { HeroUIProvider } from "@heroui/react";
import MarketsList from "../../components/MarketsList";
// Faucet now in header
import FaucetButton from "../../components/FaucetButton";
import CreateAccountButton from "../../components/CreateAccountButton";
import TokenBalance from "../../components/TokenBalance";
import { Market, MarketStatus } from "../../types/market";

// Import ABIs
import MarketFactoryAbi from "../../abis/contracts/MarketFactory.sol/MarketFactory.json";
import NBAMarketAbi from "../../abis/contracts/NBAMarket.sol/NBAMarket.json";
import MarketOddsAbi from "../../abis/contracts/MarketOdds.sol/MarketOdds.json";

// Import contract addresses from central config
import { CONTRACT_ADDRESSES, SELECTED_NETWORK, WAGMI_CONFIG } from '../../config/contracts';

// Configure Wagmi client
const config = getDefaultConfig({
  appName: WAGMI_CONFIG.APP_NAME,
  projectId: WAGMI_CONFIG.PROJECT_ID,
  chains: [SELECTED_NETWORK],
  ssr: false,
});

// Helper function to format contract values
const formatContractValue = (value: bigint | number | undefined, decimals: number = 3): string => {
  if (value === undefined) return 'N/A';
  try {
    const bigIntValue = typeof value === 'number' ? BigInt(value) : value;
    return (Number(bigIntValue) / (10 ** decimals)).toFixed(decimals);
  } catch (e) {
    console.error("Error formatting value:", value, e);
    return 'Error';
  }
};

// Market Display Component
function AllMarketsDisplay() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Read market addresses from factory
  const { data: marketAddresses, error: factoryError, isLoading: factoryLoading } = useReadContract({
    address: CONTRACT_ADDRESSES.MARKET_FACTORY_ADDRESS as Address,
    abi: MarketFactoryAbi.abi,
    functionName: 'getDeployedMarkets',
  });

  // Fetch market details
  useEffect(() => {
    const fetchMarketDetails = async () => {
      if (!Array.isArray(marketAddresses) || marketAddresses.length === 0) {
        if (!factoryLoading) {
          setMarkets([]);
          setLoading(false);
        }
        return;
      }

      setLoading(true);
      setError("");
      console.log("Fetching details for markets:", marketAddresses);

      try {
        const marketsDataPromises = (marketAddresses as Address[]).map(async (marketAddress): Promise<Market | null> => {
          try {
            // Fetch Market Details
            const marketDetailsResult = await readContract(config, {
              address: marketAddress,
              abi: NBAMarketAbi.abi,
              functionName: 'getMarketDetails',
            }) as any;

            // Fetch MarketOdds Contract address
            const marketOddsAddressResult = await readContract(config, {
              address: marketAddress,
              abi: NBAMarketAbi.abi,
              functionName: 'getMarketOddsContract',
            }) as Address | undefined;

            let oddsData: any = {};
            if (marketOddsAddressResult && marketOddsAddressResult !== "0x0000000000000000000000000000000000000000") {
              // Fetch Odds
              oddsData = await readContract(config, {
                address: marketOddsAddressResult,
                abi: MarketOddsAbi.abi,
                functionName: 'getFullOdds',
              }) as any;
            } else {
              console.warn(`Market ${marketAddress} has no MarketOdds contract linked.`);
            }

            // Destructure data
            const [
              _homeTeam,
              _awayTeam,
              _gameTimestamp,
              _oddsApiId,
              numericStatus,
              _resultSettled,
              _homeScore,
              _awayScore
            ] = marketDetailsResult;
console.log(_resultSettled, _homeScore, _awayScore)
            // Create status flags
            const gameStarted: boolean = numericStatus >= MarketStatus.STARTED;
            const gameEnded: boolean = numericStatus >= MarketStatus.SETTLED;
            const oddsSet: boolean = numericStatus >= MarketStatus.OPEN;

            return {
              address: marketAddress,
              homeTeam: _homeTeam,
              awayTeam: _awayTeam,
              gameTimestamp: _gameTimestamp.toString(),
              oddsApiId: _oddsApiId,
              homeOdds: formatContractValue(oddsData?._homeOdds),
              awayOdds: formatContractValue(oddsData?._awayOdds),
              drawOdds: formatContractValue(oddsData?._drawOdds),
              gameStarted: gameStarted,
              gameEnded: gameEnded,
              oddsSet: oddsSet,
              outcome: Number(numericStatus),
              isReadyForBetting: oddsSet && !gameStarted,
            };
          } catch (marketError) {
            console.error(`Error fetching details for market ${marketAddress}:`, marketError);
            if (marketError instanceof BaseError) {
              const errorMsg = marketError.shortMessage || marketError.message || "Unknown contract error";
              setError((prevError) => prevError ? `${prevError}; Contract Error on ${marketAddress}: ${errorMsg}` : `Contract Error on ${marketAddress}: ${errorMsg}`);
            }
            return null;
          }
        });

        const resolvedMarkets = (await Promise.all(marketsDataPromises)).filter(m => m !== null) as Market[];
        setMarkets(resolvedMarkets);
      } catch (err: any) {
        console.error("Error fetching market details:", err);
        setError(err.message || "Failed to load market details");
      } finally {
        setLoading(false);
      }
    };

    if (marketAddresses || !factoryLoading) {
      fetchMarketDetails();
    }
  }, [marketAddresses, factoryLoading, config]);

  // Handle loading/error states
  useEffect(() => {
    if (factoryLoading) {
      setLoading(true);
      setError("");
    } else if (factoryError) {
      setLoading(false);
      if (factoryError instanceof BaseError) {
        setError(`Failed to fetch market list from Factory: ${factoryError.shortMessage}. Check Factory Address and Network.`);
      } else if (factoryError instanceof Error) {
        setError(`Failed to fetch market list: ${factoryError.message}`);
      } else {
        setError(`Failed to fetch market list: An unknown error occurred.`);
      }
      console.error("Error fetching market addresses:", factoryError);
    }
  }, [factoryLoading, factoryError]);

  return (
    <>
      <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-white">All Available Markets</h2>
      {loading ? (
        <div className="flex justify-center items-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      ) : error ? (
        <div className="bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-100 px-4 py-3 rounded-lg">
          <p>{error}</p>
        </div>
      ) : (
        <MarketsList usdxAddress={CONTRACT_ADDRESSES.USDX_ADDRESS} markets={markets} />
      )}
    </>
  );
}

export default function Home() {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <RainbowKitProvider>
          <HeroUIProvider>
            <div className="content-area">
              <header className="sticky top-0 z-10 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow">
                <div className="container mx-auto px-4 py-4 flex justify-between items-center">
                  <h1 className="text-2xl font-bold text-gray-800 dark:text-white">All Markets</h1>
                  <div className="flex items-center gap-4">
                    <TokenBalance />
                    <FaucetButton />
                    <CreateAccountButton />
                  </div>
                </div>
              </header>
              <main className="container mx-auto px-4 py-8">
                <AllMarketsDisplay />
              </main>
            </div>
          </HeroUIProvider>
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}
