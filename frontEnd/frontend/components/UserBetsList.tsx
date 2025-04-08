"use client";

import { useState, useEffect } from "react";
import { useAccount } from "wagmi";
import { Market } from "../types/market"; // Assuming Market type is defined here

// Define Bet type based on user provided example
type Bet = {
  betId: string;
  bettor: string;
  amount: string;
  potentialWinnings: string;
  onHomeTeam: boolean;
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

      // Fetch bets for each market concurrently
      const betPromises = markets.map(async (market) => {
        try {
          // Call the Next.js API route
          const response = await fetch(`/api/user-bets/${market.address}/${address}`);
          if (!response.ok) {
            // Log specific error but don't block other requests
            const errorData = await response.json();
            console.error(`Failed to fetch bets for market ${market.address}:`, response.status, errorData);
            return []; // Return empty array for this market on error
          }
          const bets: Bet[] = await response.json();
          // Add market info to each bet
          return bets.map(bet => ({
            ...bet,
            marketAddress: market.address,
            homeTeam: market.homeTeam,
            awayTeam: market.awayTeam,
          }));
        } catch (err: any) {
          console.error(`Error fetching bets for market ${market.address}:`, err);
          return []; // Return empty array on network or parsing error
        }
      });

      // Wait for all fetch requests to settle
      const results = await Promise.allSettled(betPromises);

      // Aggregate bets from successful fetches
      results.forEach(result => {
        if (result.status === 'fulfilled' && result.value) {
          allBets = allBets.concat(result.value);
        }
        // Optionally handle 'rejected' statuses if more granular error reporting is needed
      });

      // Sort bets perhaps by betId or market, if desired (optional)
      // allBets.sort((a, b) => /* sorting logic */);

      setUserBets(allBets);
      setLoading(false);
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
        <p className="text-gray-500 dark:text-gray-400">You haven't placed any bets yet.</p>
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
                    <span className={`ml-1 font-semibold ${bet.onHomeTeam ? 'text-blue-600 dark:text-blue-400' : 'text-green-600 dark:text-green-400'}`}>
                       {bet.onHomeTeam ? bet.homeTeam : bet.awayTeam}
                    </span>
                 </div>
                 <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">Amount:</span>
                    <span className="ml-1 text-gray-800 dark:text-white">{parseFloat(bet.amount).toFixed(2)} USDX</span>
                 </div>
                 <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">Potential Win:</span>
                    <span className="ml-1 text-gray-800 dark:text-white">{parseFloat(bet.potentialWinnings).toFixed(2)} USDX</span>
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