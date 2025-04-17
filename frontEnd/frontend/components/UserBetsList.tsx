"use client";

import { useState, useEffect } from "react";
import { useAccount, useConfig } from "wagmi";
import { readContract } from 'wagmi/actions';
import { type Address, zeroAddress, formatUnits, BaseError } from 'viem';
import { Market } from "../types/market";
import NBAMarketABI from '../abis/contracts/NBAMarket.sol/NBAMarket.json';
import BettingEngineABI from '../abis/contracts/BettingEngine.sol/BettingEngine.json';
import { useWallet } from "../contexts/WalletContext";

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

// Helper function to get bet type string
const getBetTypeString = (betType: number): string => {
  switch (betType) {
    case 0: return 'Moneyline';
    case 1: return 'Spread';
    case 2: return 'Total (O/U)';
    case 3: return 'Draw'; // Already handled specially below, but good for completeness
    default: return 'Unknown';
  }
};

// Helper function to format the line based on bet type
const formatLine = (line: bigint, betType: number): string => {
  const lineValue = Number(line) / 10; // Assuming line is stored * 10 in contract

  if (betType === 1) { // Spread
    return lineValue > 0 ? `+${lineValue}` : `${lineValue}`;
  }
  if (betType === 2) { // Total
    return `${lineValue}`;
  }
  return ''; // No line for Moneyline or Draw
};

export default function UserBetsList({ markets }: UserBetsListProps) {
  const {  isConnected } = useAccount();
  const config = useConfig();
  const { displayAddress, isManagedWallet } = useWallet();
  const [userBets, setUserBets] = useState<BetWithMarketInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Determine if a user is connected (with either regular wallet or managed wallet)
  const isUserConnected = isConnected || isManagedWallet;
  // Use the appropriate address
  const userAddress = displayAddress as Address | undefined;

  useEffect(() => {
    const fetchUserBets = async () => {
      if (!isUserConnected || !userAddress || markets.length === 0) {
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
                args: [userAddress],
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
  }, [userAddress, isUserConnected, markets, config]); // Re-run effect if address, connection status, or markets change

  if (!isUserConnected) {
    return (
      <div className="mt-8 text-center text-gray-500 dark:text-gray-400">
        Connect your wallet to view your bets.
      </div>
    );
  }

  return (
    <div className="mt-10 pt-6 border-t border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-2 mb-6">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6 text-primary">
          <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
          <polyline points="17 21 17 13 7 13 7 21" />
          <polyline points="7 3 7 8 15 8" />
        </svg>
        <h2 className="text-2xl font-bold text-gray-800 dark:text-white">Your Bets</h2>
      </div>
      
      {loading ? (
        <div className="flex justify-center items-center py-10">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      ) : error ? (
        <div className="bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-200 px-5 py-4 rounded-lg">
          <p>Error loading bets: {error}</p>
        </div>
      ) : userBets.length === 0 ? (
        <div className="p-6 border rounded-lg border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 text-center">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto mb-3 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-gray-500 dark:text-gray-400 text-lg">You have not placed any bets yet.</p>
          <p className="text-gray-400 dark:text-gray-500 mt-1">When you place bets, they will appear here.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-4">
          {userBets.map((bet) => (
            <div key={`${bet.marketAddress}-${bet.betId}`} className="card overflow-hidden">
              <div className="bg-gray-100 dark:bg-gray-700 px-4 py-3 border-b border-gray-200 dark:border-gray-600">
                <div className="flex justify-between items-center">
                  <h3 className="font-bold text-gray-800 dark:text-white">
                    {bet.homeTeam} vs {bet.awayTeam}
                  </h3>
                  {bet.settled ? (
                    <span className={`status-badge ${bet.won ? 'bg-green-500' : 'bg-red-500'}`}>
                      {bet.won ? 'Won' : 'Lost'}
                    </span>
                  ) : (
                    <span className="status-badge bg-yellow-500">
                      Pending
                    </span>
                  )}
                </div>
              </div>
              
              <div className="p-4">
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Bet Type</p>
                    <p className="font-medium text-gray-800 dark:text-white">{getBetTypeString(bet.betType)}</p>
                  </div>
                  
                  <div className="bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Bet On</p>
                    {bet.betType === 3 ? (
                      <p className="font-medium text-yellow-600 dark:text-yellow-400">Draw</p>
                    ) : (
                      <p className={`font-medium ${bet.isBettingOnHomeOrOver ? 'text-blue-600 dark:text-blue-400' : 'text-green-600 dark:text-green-400'}`}>
                        {bet.betType === 0 && (bet.isBettingOnHomeOrOver ? bet.homeTeam : bet.awayTeam)}
                        {bet.betType === 1 && `${bet.isBettingOnHomeOrOver ? bet.homeTeam : bet.awayTeam} ${formatLine(bet.line, bet.betType)}`}
                        {bet.betType === 2 && `${bet.isBettingOnHomeOrOver ? 'Over' : 'Under'} ${formatLine(bet.line, bet.betType)}`}
                      </p>
                    )}
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Amount</p>
                    <p className="font-medium text-gray-800 dark:text-white">{formatUnits(bet.amount, 6)} USDX</p>
                  </div>
                  
                  <div className="bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Potential Win</p>
                    <p className="font-medium text-gray-800 dark:text-white">{formatUnits(bet.potentialWinnings, 6)} USDX</p>
                  </div>
                </div>
                
                <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                    Market: {bet.marketAddress}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
} 