"use client";

import { useState, useEffect } from "react";
import { useAccount, useConfig } from "wagmi";
import { readContract } from 'wagmi/actions';
import { type Address, zeroAddress, formatUnits, BaseError } from 'viem';
import { Market } from "../types/market";
import NBAMarketABI from '../abis/contracts/NBAMarket.sol/NBAMarket.json';
import BettingEngineABI from '../abis/contracts/BettingEngine.sol/BettingEngine.json';

// Type for the tuple returned by BettingEngine.getBetDetails
type BetDetailsTuple = [
  string, // bettor
  bigint, // amount
  bigint, // potentialWinnings
  number, // betType (uint8)
  boolean,// isBettingOnHomeOrOver
  bigint, // line
  bigint, // odds
  boolean,// settled
  boolean // won
];

// Define Bet type based on getBetDetails + add betId
type Bet = {
  betId: bigint; // Bet ID
  bettor: string;
  amount: bigint;
  potentialWinnings: bigint;
  betType: number;
  isBettingOnHomeOrOver: boolean;
  line: bigint;
  odds: bigint;
  settled: boolean;
  won: boolean;
};

// Extend Bet type to include market info for display purposes
type BetWithMarketInfo = Bet & {
  marketAddress: string;
  homeTeam: string;
  awayTeam: string;
};

type UserBetsListProps = {
  markets: Market[]; // Pass the list of markets from the parent page
};

export default function UserBetsList({ markets }: UserBetsListProps) {
  const { address, isConnected } = useAccount();
  const config = useConfig();
  const [userBets, setUserBets] = useState<BetWithMarketInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUserBets = async () => {
      if (!isConnected || !address || markets.length === 0) {
        setUserBets([]); // Clear bets if not connected or no markets
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      let allBets: BetWithMarketInfo[] = [];

      try {
         // --- Start Blockchain Fetch --- 
         const betPromises = markets.map(async (market) => {
          try {
            const bettingEngineAddress = await readContract(config, {
              address: market.address as Address,
              abi: NBAMarketABI.abi,
              functionName: 'bettingEngine',
            }) as Address | undefined;
            
            if (!bettingEngineAddress || bettingEngineAddress === zeroAddress) {
                console.warn(`No betting engine found for market ${market.address}`);
                return []; // Skip if no engine address
            }

            const betIds = await readContract(config, {
                address: bettingEngineAddress,
                abi: BettingEngineABI.abi,
                functionName: 'getBettorBets',
                args: [address as Address],
            }) as bigint[] | undefined;

            if (!betIds || betIds.length === 0) {
                 return []; // No bets for this user in this market
            }
            
            // Fetch details for each bet ID
            const betDetailsPromises = betIds.map(async (betId) => {
                 try {
                    const detailsTuple = await readContract(config, {
                        address: bettingEngineAddress,
                        abi: BettingEngineABI.abi,
                        functionName: 'getBetDetails',
                        args: [betId],
                    }) as BetDetailsTuple | undefined;

                    if (!detailsTuple) {
                        console.error(`Failed to fetch details for bet ID ${betId} in engine ${bettingEngineAddress}`);
                        return null;
                    }

                    // Format into Bet object
                    const betData: Bet = {
                        betId: betId,
                        bettor: detailsTuple[0],
                        amount: detailsTuple[1],
                        potentialWinnings: detailsTuple[2],
                        betType: detailsTuple[3],
                        isBettingOnHomeOrOver: detailsTuple[4],
                        line: detailsTuple[5],
                        odds: detailsTuple[6],
                        settled: detailsTuple[7],
                        won: detailsTuple[8],
                    };
                    // Combine with market info
                    return { 
                        ...betData, 
                        marketAddress: market.address, 
                        homeTeam: market.homeTeam, 
                        awayTeam: market.awayTeam 
                    } as BetWithMarketInfo;
                } catch (err) {
                    console.error(`Error fetching details for bet ${betId} in market ${market.address}:`, err);
                    if (err instanceof BaseError) {
                        setError((prev) => prev ? `${prev}; Bet ${betId} fetch error: ${err.shortMessage}` : `Bet ${betId} fetch error: ${err.shortMessage}`);
                    } else if (err instanceof Error) {
                        setError((prev) => prev ? `${prev}; Bet ${betId} fetch error: ${err.message}` : `Bet ${betId} fetch error: ${err.message}`);
                    }
                    return null;
                }
            });

            const detailedBetsResults = await Promise.allSettled(betDetailsPromises);
            // Filter out nulls (errors) and extract fulfilled values
            return detailedBetsResults
                .filter(result => result.status === 'fulfilled' && result.value !== null)
                .map(result => (result as PromiseFulfilledResult<BetWithMarketInfo>).value);

          } catch (err: any) {
            console.error(`Error processing market ${market.address} for user bets:`, err);
            return []; // Return empty array for this market on error
          }
        });

        // Wait for all market processing to settle
        const results = await Promise.allSettled(betPromises);

        // Aggregate bets from successful market fetches
        results.forEach(result => {
          if (result.status === 'fulfilled' && result.value) {
            allBets = allBets.concat(result.value);
          }
          // Optionally handle 'rejected' statuses if more granular error reporting is needed
        });
         // --- End Blockchain Fetch ---

        // Sort bets by ID (descending, newest first)
        allBets.sort((a, b) => Number(b.betId - a.betId));

        setUserBets(allBets);

      } catch (err: any) {
        console.error("Failed to fetch user bets from blockchain:", err);
        setError("Could not load bets from the blockchain.");
        setUserBets([]); // Clear bets on major error
      } finally {
        setLoading(false);
      }
    };

    fetchUserBets();
  }, [address, isConnected, markets]); // Re-run effect if address, connection status, or markets change

  if (!isConnected) {
    return (
      <div className="mt-8 text-center text-gray-500 dark:text-gray-400">
        Connect your wallet to view your bets.
      </div>
    );
  }

  return (
    <div className="mt-10 pt-6 border-t border-gray-200 dark:border-gray-700">
      <h2 className="text-2xl font-bold mb-4 text-gray-800 dark:text-white">Your Bets</h2>
      {loading ? (
        <div className="text-center py-5">
           <div className="inline-block h-6 w-6 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" role="status">
            <span className="sr-only">Loading...</span>
          </div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading your bets...</p>
        </div>
      ) : error ? (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded dark:bg-red-900 dark:border-red-700 dark:text-red-200">
          <p>Error loading bets: {error}</p>
        </div>
      ) : userBets.length === 0 ? (
        <p className="text-gray-500 dark:text-gray-400">You have not placed any bets yet.</p>
      ) : (
        <div className="space-y-4">
          {userBets.map((bet) => (
            <div key={`${bet.marketAddress}-${bet.betId}`} className="p-4 border rounded-lg shadow-sm bg-white dark:bg-gray-800 dark:border-gray-700">
              <div className="flex flex-col sm:flex-row justify-between sm:items-center mb-2">
                <p className="font-semibold text-lg text-gray-800 dark:text-white">
                  {bet.homeTeam} vs {bet.awayTeam}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 sm:mt-0">
                  Market: <code className="text-xs bg-gray-100 dark:bg-gray-700 p-1 rounded font-mono break-all">{bet.marketAddress}</code>
                </p>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-2 text-sm">
                 <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">Bet On:</span>
                    {/* For draw bets, betType 3 means draw regardless of isBettingOnHomeOrOver value */}
                    {bet.betType === 3 ? (
                      <span className="ml-1 font-semibold text-yellow-600 dark:text-yellow-400">
                        Draw
                      </span>
                    ) : (
                      <span className={`ml-1 font-semibold ${bet.isBettingOnHomeOrOver ? 'text-blue-600 dark:text-blue-400' : 'text-green-600 dark:text-green-400'}`}>
                        {bet.isBettingOnHomeOrOver ? bet.homeTeam : bet.awayTeam}
                      </span>
                    )}
                 </div>
                 <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">Amount:</span>
                    <span className="ml-1 text-gray-800 dark:text-white">{formatUnits(bet.amount, 6)} USDX</span>
                 </div>
                 <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">Potential Win:</span>
                    <span className="ml-1 text-gray-800 dark:text-white">{formatUnits(bet.potentialWinnings, 6)} USDX</span>
                 </div>
                  <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">Status:</span>
                    {bet.settled ? (
                       <span className={`ml-1 px-2 py-0.5 rounded-full text-xs font-medium ${bet.won ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}`}>
                         {bet.won ? 'Won' : 'Lost'}
                       </span>
                    ) : (
                      <span className="ml-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
                        Pending
                      </span>
                    )}
                  </div>
              </div>
              {/* <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">Bet ID: {bet.betId}</p> */}
            </div>
          ))}
        </div>
      )}
    </div>
  );
} 