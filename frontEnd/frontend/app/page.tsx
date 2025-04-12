"use client";

import { useEffect, useState } from "react";
import MarketsList from "../components/MarketsList";
import Faucet from "../components/Faucet";
import UserBetsList from "../components/UserBetsList";
import { Market, MarketStatus } from "../types/market";
import '@rainbow-me/rainbowkit/styles.css';
import {
  getDefaultConfig,
  RainbowKitProvider,
} from '@rainbow-me/rainbowkit';
import { WagmiProvider, useReadContract } from 'wagmi';
import { readContract } from 'wagmi/actions';
import { type Address, BaseError } from 'viem';
import {
  baseSepolia,
} from 'wagmi/chains';
import {
  QueryClientProvider,
  QueryClient,
} from "@tanstack/react-query";
import { ConnectButton } from '@rainbow-me/rainbowkit';

// Import ABIs from the correct paths
import MarketFactoryAbi from "../abis/contracts/MarketFactory.sol/MarketFactory.json";
import NBAMarketAbi from "../abis/contracts/NBAMarket.sol/NBAMarket.json";
import MarketOddsAbi from "../abis/contracts/MarketOdds.sol/MarketOdds.json";

const config = getDefaultConfig({
  appName: 'Bankrolled',
  projectId: 'YOUR_PROJECT_ID', // TODO: Replace with your actual RainbowKit Project ID
  chains: [baseSepolia],
  ssr: false,
});

// --- TODO: Replace with your ACTUAL deployed MarketFactory address ---
const MARKET_FACTORY_ADDRESS = "0x7019E65E2698d891C0a9633309e2D2eCaa21a3Df"; // Replace this placeholder

const usdxAddress = "0x96994C1D6df44b02AFf15A634C96989a656FC72F";

// Helper function to format odds/lines (similar to backend)
const formatContractValue = (value: bigint | number | undefined, decimals: number = 3): string => {
  if (value === undefined) return 'N/A';
  try {
    // Convert potential number to bigint first if necessary
    const bigIntValue = typeof value === 'number' ? BigInt(value) : value;
    // Format using fixed decimals (3 for odds)
    return (Number(bigIntValue) / (10 ** decimals)).toFixed(decimals);
  } catch (e) {
    console.error("Error formatting value:", value, e);
    return 'Error';
  }
};

// Helper to format spread points
// const formatSpreadPoints = (value: bigint | number | undefined): string => {
//     if (value === undefined) return 'N/A';
//     try {
//         const numValue = typeof value === 'number' ? value : Number(value);
//         const formatted = (numValue / 10).toFixed(1); // 1 decimal place
//         return numValue > 0 ? `+${formatted}` : formatted;
//     } catch (e) {
//         console.error("Error formatting spread:", value, e);
//         return 'Error';
//     }
// };

// New component to handle market fetching and display
function MarketDisplay() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // 1. Read the list of deployed market addresses from the factory
  const { data: marketAddresses, error: factoryError, isLoading: factoryLoading } = useReadContract({
    address: MARKET_FACTORY_ADDRESS as Address, // Cast to Address type
    abi: MarketFactoryAbi.abi,
    functionName: 'getDeployedMarkets',
  });

  // 2. Fetch details for each market address when the list is available
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
      setError(""); // Clear previous errors
      console.log("Fetching details for markets:", marketAddresses);

      try {
        const marketsDataPromises = (marketAddresses as Address[]).map(async (marketAddress): Promise<Market | null> => {
          try {
            // Fetch Market Details from NBAMarket
            const marketDetailsResult = await readContract(config, {
              address: marketAddress,
              abi: NBAMarketAbi.abi,
              functionName: 'getMarketDetails',
            }) as any; // Use 'any' for now, define specific types later if needed
            console.log("Market Details:", marketDetailsResult);
            // Fetch MarketOdds Contract address from NBAMarket
             const marketOddsAddressResult = await readContract(config, {
                address: marketAddress,
                abi: NBAMarketAbi.abi,
                functionName: 'getMarketOddsContract',
            }) as Address | undefined;

            let oddsData: any = {}; // Default empty odds
            if (marketOddsAddressResult && marketOddsAddressResult !== "0x0000000000000000000000000000000000000000") {
                // Fetch Odds from MarketOdds contract
                 oddsData = await readContract(config, {
                    address: marketOddsAddressResult,
                    abi: MarketOddsAbi.abi,
                    functionName: 'getFullOdds',
                }) as any; // Use 'any', define types later
            } else {
                console.warn(`Market ${marketAddress} has no MarketOdds contract linked.`);
            }

            // Destructure and map data to Market type
            const [
                _homeTeam,          // string
                _awayTeam,          // string
                _gameTimestamp,     // bigint (uint256)
                _oddsApiId,         // string
                numericStatus,      // number (MarketStatus enum -> uint8)
                _resultSettled,     // boolean
                _homeScore,         // bigint (uint8)
                _awayScore          // bigint (uint8)
             ] = marketDetailsResult;
             console.log("marketDetailsResult", _resultSettled, _homeScore, _awayScore );
             // Derive boolean flags from the numeric status
             const gameStarted: boolean = numericStatus >= MarketStatus.STARTED; // STARTED, SETTLED, CANCELLED
             const gameEnded: boolean = numericStatus >= MarketStatus.SETTLED; // SETTLED, CANCELLED
             const oddsSet: boolean = numericStatus >= MarketStatus.OPEN; // OPEN, STARTED, SETTLED, CANCELLED (assuming odds remain set)

            return {
              address: marketAddress,
              homeTeam: _homeTeam,
              awayTeam: _awayTeam,
              gameTimestamp: _gameTimestamp.toString(),
              oddsApiId: _oddsApiId,
              homeOdds: formatContractValue(oddsData?._homeOdds),
              awayOdds: formatContractValue(oddsData?._awayOdds),
              drawOdds: formatContractValue(oddsData?._drawOdds),
              // TODO: Add spread and total odds formatting

              // Use derived status flags
              gameStarted: gameStarted,
              gameEnded: gameEnded,
              oddsSet: oddsSet,
              // Assign the numeric status directly to outcome, aligning with MarketStatus enum
              outcome: Number(numericStatus), 
              isReadyForBetting: oddsSet && !gameStarted,
            };
          } catch (marketError) {
            console.error(`Error fetching details for market ${marketAddress}:`, marketError);
            // Check instance of BaseError (imported from viem)
            if (marketError instanceof BaseError) {
                // Ensure error message is handled safely
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

    // Trigger fetch when marketAddresses are loaded and not empty, or if factory loading finished
     if (marketAddresses || !factoryLoading) {
       fetchMarketDetails();
     }

  // Dependency array: fetch details when marketAddresses array changes or factory loading state changes
  }, [marketAddresses, factoryLoading, config]); // Include config in dependency array

  // Handle factory loading/error state
  useEffect(() => {
    if (factoryLoading) {
      setLoading(true);
      setError("");
    } else if (factoryError) {
      setLoading(false);
      // Check instance of BaseError (imported from viem)
      if (factoryError instanceof BaseError) {
        setError(`Failed to fetch market list from Factory: ${factoryError.shortMessage}. Check Factory Address and Network.`);
      } else if (factoryError instanceof Error) { // Check for standard Error
        setError(`Failed to fetch market list: ${factoryError.message}`);
      } else {
        setError(`Failed to fetch market list: An unknown error occurred.`);
      }
      console.error("Error fetching market addresses:", factoryError);
    }
    // No 'else' needed here as the other useEffect handles setting loading to false after details are fetched
  }, [factoryLoading, factoryError]);

  // Render logic moved here
  return (
    <>
      <h1 className="text-3xl font-bold mb-6">NBA Betting Markets</h1>
      {loading ? (
        <div className="text-center py-10">
           <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" role="status">
            <span className="sr-only">Loading...</span>
          </div>
          <p className="mt-2">Loading markets from blockchain...</p>
        </div>
      ) : error ? (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <p>{error}</p>
        </div>
      ) : (
        <MarketsList usdxAddress={usdxAddress} markets={markets} />
      )}

      {!loading && !error && (
         <UserBetsList markets={markets} />
      )}
    </>
  );
}

// Main Home component sets up providers and renders MarketDisplay
export default function Home() {
  // QueryClient needs to be instantiated outside the component that uses useQuery/useReadContract
  // or memoized to avoid recreating it on every render.
  const [queryClient] = useState(() => new QueryClient());

  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <RainbowKitProvider>
          <main className="container mx-auto px-4 py-8">
            <div className="flex justify-end mb-4">
                <ConnectButton />
            </div>
            <Faucet />
            {/* Render the component that uses the hooks inside the providers */}
            <MarketDisplay />
          </main>
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}
