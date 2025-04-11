import React, { useState, useEffect } from 'react';
import { Market, MarketStatus } from '../types/market';
// Imports for ethers v6 and wagmi v1/v2
import { ethers, BrowserProvider, Contract } from 'ethers'; // Use BrowserProvider, Contract from ethers v6
import { useAccount, useWalletClient, useChainId } from 'wagmi'; // Use useChainId instead of useNetwork
import { type WalletClient } from 'viem';
import NBAMarketABI from '../abis/contracts/NBAMarket.sol/NBAMarket.json';
import USDXABI from '../abis/contracts/USDX.sol/USDX.json';
// Consider using a toast library for better UX than alerts
// import { toast } from 'react-toastify';

// Helper to convert WalletClient (viem) to Signer (ethers v6)
// https://ethers.org/docs/v6/getting-started/#starting-signing
// Note: This basic version might need adjustments based on specific WalletClient transport
async function getEthersSigner(walletClient: WalletClient): Promise<ethers.Signer | null> { // Return type includes null
  const { account, chain, transport } = walletClient;
  // Add checks for required properties
  if (!account || !chain || !transport) {
      console.warn("WalletClient is missing required properties (account, chain, or transport).");
      return null;
  }
  const network = {
    chainId: chain.id,
    name: chain.name,
  };
  const provider = new BrowserProvider(transport, network);
  // Ensure account.address exists before getting signer
  if (!account.address) {
      console.warn("WalletClient account is missing address.");
      return null;
  }
  try {
    const signer = await provider.getSigner(account.address);
    return signer;
  } catch (error) {
      console.error("Error getting signer from provider:", error);
      return null;
  }
}

interface MarketCardProps {
  market: Market;
  usdxAddress: string; // Address of the USDX ERC20 token
  expectedChainId: number; // The chain ID the contracts are deployed on
}

// TODO: Confirm the actual enum value for Moneyline from BettingEngine.sol
const MONEYLINE_BET_TYPE = 0; 
const SPREAD_BET_TYPE = 1;
const TOTAL_BET_TYPE = 2;

// Define the structure for the odds tuple returned by getFullOdds (using bigint for v6)
interface FullOdds {
  homeOdds: bigint;
  awayOdds: bigint;
  homeSpreadPoints: bigint;
  homeSpreadOdds: bigint;
  awaySpreadOdds: bigint;
  totalPoints: bigint;
  overOdds: bigint;
  underOdds: bigint;
}

// Helper function to get provider/signer (adjust based on your setup)
const getProviderOrSigner = (signer?: ethers.Signer | null): ethers.Provider | ethers.Signer => {
  // Use signer if available (for transactions), otherwise use a provider for reads
  if (signer) return signer;
  // Fallback to a default provider (replace with your preferred setup)
  // Make sure this provider is connected to the correct network (e.g., Base Sepolia)
  // return new ethers.JsonRpcProvider(process.env.NEXT_PUBLIC_BASE_SEPOLIA_RPC_URL || 'https://sepolia.base.org');
  return new ethers.JsonRpcProvider('https://base-sepolia.g.alchemy.com/v2/eU1jQGAZyansfxyaBRIHQrBQh1Y0bIQi');
};

const MarketCard: React.FC<MarketCardProps> = ({ market, usdxAddress, expectedChainId }) => {
  const [betAmount, setBetAmount] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false); // For loading state
  const [signer, setSigner] = useState<ethers.Signer | null>(null); // State for ethers signer
  const [isFetchingData, setIsFetchingData] = useState(true); // For initial odds/status fetch
  const [fetchError, setFetchError] = useState<string | null>(null);

  // State for selected bet type
  const [selectedBetType, setSelectedBetType] = useState<number>(MONEYLINE_BET_TYPE);

  // --- Wallet Hooks ---
  const { address: userAddress, isConnected, chainId } = useAccount();
  const currentChainId = useChainId(); // Get current chain ID
  const { data: walletClient } = useWalletClient({ chainId: currentChainId }); // Get WalletClient for the expected chain
  // --- End Wallet Hooks ---
  console.log("signer", signer, "userAddress", userAddress, "isConnected", isConnected, "currentChainId", currentChainId, "expectedChainId", expectedChainId, "walletClient", walletClient);
  // --- Effect to get Signer when WalletClient is available ---
   useEffect(() => {
     const fetchSigner = async () => {
        if (walletClient) {
            try {
                const ethersSigner = await getEthersSigner(walletClient);
                setSigner(ethersSigner);
            } catch (error) {
                console.error("Error getting ethers signer:", error);
                setSigner(null);
            }
        } else {
            setSigner(null); // Reset signer if walletClient becomes unavailable
        }
     };
     fetchSigner();
  }, [walletClient]);
  // --- End Effect ---

  // State for blockchain-fetched data
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null);
  const [liveOdds, setLiveOdds] = useState<FullOdds | null>(null);
  // Add state for scores
  const [homeScore, setHomeScore] = useState<number | null>(null);
  const [awayScore, setAwayScore] = useState<number | null>(null);

  // Fetch Market Status and Odds from Blockchain
  useEffect(() => {
    const fetchMarketData = async () => {
      setIsFetchingData(true);
      setFetchError(null);
      try {
        const provider = getProviderOrSigner(); // Use read-only provider
        const marketContract = new ethers.Contract(market.address, NBAMarketABI.abi, provider);

        // Fetch details (includes status and scores) and odds concurrently
        const [details, oddsResult] = await Promise.all([
          marketContract.getMarketDetails(),
          marketContract.getFullOdds()
        ]);

        console.log(`Market ${market.address} - Raw Details Result:`, details);
        console.log(`Market ${market.address} - Raw Odds Result:`, oddsResult);

        // Extract and set status, home score, and away score from details
        // Indices based on user feedback: 0: homeTeam, 1: awayTeam, 2: timestamp, 3: oddsApiId, 4: status, 5: settled, 6: homeScore, 7: awayScore
        const numericStatus = Number(details[4]); // Status is at index 4
        setMarketStatus(numericStatus as MarketStatus);
        setHomeScore(Number(details[6])); // Home score is at index 6
        setAwayScore(Number(details[7])); // Away score is at index 7

        // Map the tuple to the FullOdds interface (remains the same)
        setLiveOdds({
          homeOdds: oddsResult[0],
          awayOdds: oddsResult[1],
          homeSpreadPoints: oddsResult[2],
          homeSpreadOdds: oddsResult[3],
          awaySpreadOdds: oddsResult[4],
          totalPoints: oddsResult[5],
          overOdds: oddsResult[6],
          underOdds: oddsResult[7],
        });

      } catch (error: any) {
        console.error(`Error fetching data for market ${market.address}:`, error);
        setFetchError(`Failed to load market data: ${error.message || 'Unknown error'}`);
        setMarketStatus(null); // Reset on error
        setLiveOdds(null);
        setHomeScore(null); // Reset scores on error
        setAwayScore(null); // Reset scores on error
      } finally {
        setIsFetchingData(false);
      }
    };

    if (market.address) {
      fetchMarketData();
    } else {
        setIsFetchingData(false); // No address, nothing to fetch
        setFetchError("Market address is missing.");
    }

    // Optional: Setup interval polling or event listeners for updates
    // const intervalId = setInterval(fetchMarketData, 30000); // Re-fetch every 30s
    // return () => clearInterval(intervalId); // Cleanup interval

  }, [market.address]); // Re-fetch if market address changes

  // Format odds (adjust divisor based on decimals used in contract)
  // Assuming 3 decimal places (multiply by 1000 in contract)
  const formatOdds = (oddsBigInt: bigint | undefined | null): string => {
    if (oddsBigInt === undefined || oddsBigInt === null || oddsBigInt === 0n) return 'N/A';
    try {
      // Convert bigint to a fixed-point string using ethers v6
      const formatted = ethers.formatUnits(oddsBigInt, 3); // 3 decimal places
      // Ensure it shows at least 3 decimal places
      const decimalPart = formatted.split('.')[1] || '';
      return parseFloat(formatted).toFixed(Math.max(3, decimalPart.length));
    } catch (e) {
      console.error("Error formatting odds:", oddsBigInt, e);
      return 'Error';
    }
  };

  // Format points (adjust divisor based on decimals used in contract)
  // Assuming 1 decimal place (multiply by 10 in contract)
  const formatPoints = (pointsBigInt: bigint | undefined | null): string => {
    if (pointsBigInt === undefined || pointsBigInt === null) return 'N/A'; // No need to check for 0n, 0 points is valid
    try {
      // Convert bigint to a fixed-point string using ethers v6
      const formatted = ethers.formatUnits(pointsBigInt, 1); // 1 decimal place
      // Add sign for non-zero values
      const num = parseFloat(formatted);
      return num > 0 ? `+${num.toFixed(1)}` : num.toFixed(1);
    } catch (e) {
      console.error("Error formatting points:", pointsBigInt, e);
      return 'Error';
    }
  };

  // Game status display logic using fetched marketStatus
  const getStatusBadge = () => {
    // Handle loading and initial null state first
    if (isFetchingData || marketStatus === null) { 
      return <span className="px-2 py-1 text-xs font-semibold text-gray-700 bg-gray-200 rounded-full">Loading...</span>;
    }
    if (fetchError) {
      return <span className="px-2 py-1 text-xs font-semibold text-red-700 bg-red-200 rounded-full">Error</span>;
    }

    switch (marketStatus) {
      case MarketStatus.PENDING:
        return <span className="px-2 py-1 text-xs font-semibold text-gray-700 bg-gray-200 rounded-full">Pending</span>;
      case MarketStatus.OPEN:
        // Check game time vs current time
         const now = Date.now() / 1000; // Current time in seconds
        if (parseInt(market.gameTimestamp, 10) > now) {
            return <span className="px-2 py-1 text-xs font-semibold text-green-700 bg-green-200 rounded-full">Open</span>;
        } else {
            // If time has passed but status is still OPEN, maybe there's a delay? Treat as Started for UI.
            return <span className="px-2 py-1 text-xs font-semibold text-yellow-700 bg-yellow-200 rounded-full">Live</span>;
        }
      case MarketStatus.STARTED:
         return <span className="px-2 py-1 text-xs font-semibold text-yellow-700 bg-yellow-200 rounded-full">Live</span>;
      case MarketStatus.SETTLED:
        return <span className="px-2 py-1 text-xs font-semibold text-blue-700 bg-blue-200 rounded-full">Settled</span>;
      case MarketStatus.CANCELLED:
        return <span className="px-2 py-1 text-xs font-semibold text-red-700 bg-red-200 rounded-full">Cancelled</span>;
      default:
        return <span className="px-2 py-1 text-xs font-semibold text-gray-700 bg-gray-200 rounded-full">Unknown</span>;
    }
  };

  // Game outcome display logic (reads from state now)
  const getOutcome = () => {
     // Only show outcome if settled and scores are available
     if (marketStatus !== MarketStatus.SETTLED || homeScore === null || awayScore === null) return null;

    let outcomeText = "Result: Scores Pending"; // Default for SETTLED status

     // Use scores from state
     if (typeof homeScore === 'number' && typeof awayScore === 'number') {
         // Format changed to: homeTeamName homeScore - awayScore awayTeamName
         outcomeText = `${market.homeTeam} ${homeScore} - ${awayScore} ${market.awayTeam}`;
     }

    return (
      <div className="mt-4 text-center font-semibold text-gray-800">
        {outcomeText}
      </div>
    );
  };

  // Function to handle placing a bet
  const handleBet = async (isBettingOnHomeOrOver: boolean) => {
    // --- Input Validations ---
    if (!betAmount || isNaN(parseFloat(betAmount)) || parseFloat(betAmount) <= 0) {
      alert('Please enter a valid positive bet amount.');
      return;
    }
    // Use currentChainId obtained from the hook
    if (!isConnected || !userAddress) { 
      alert('Please connect your wallet first.');
      return;
    }
    // Use derived signer state
    if (!signer) { 
       alert('Wallet signer not available. Ensure your wallet is connected and on the correct network.');
       return;
    }
    // Check chain ID using the dedicated hook
    if (chainId !== expectedChainId) {
        alert(`Please switch to the correct network (Expected: ${expectedChainId}, Connected: ${chainId}).`);
        return;
    }
    // --- End Validations ---

    setIsLoading(true);
    // Determine team/option name based on bet type
    let betOnName: string;
    if (selectedBetType === MONEYLINE_BET_TYPE || selectedBetType === SPREAD_BET_TYPE) {
       betOnName = isBettingOnHomeOrOver ? market.homeTeam : market.awayTeam;
    } else { // TOTAL_BET_TYPE
       betOnName = isBettingOnHomeOrOver ? 'Over' : 'Under';
    }
    console.log(`Attempting to bet ${betAmount} USDX on ${betOnName}`);
    // toast.info(`Processing bet for ${teamName}...`);

    try {
      // --- Contract Setup (Ethers v6) ---
      // Pass signer directly to Contract constructor
      const marketContract = new Contract(market.address, NBAMarketABI.abi, signer);
      const usdxContract = new Contract(usdxAddress, USDXABI.abi, signer);
      const bettingEngineAddress = await marketContract.bettingEngine(); // Fetch the engine address
      // TODO: Confirm USDX decimals
       const decimals = 6; // await usdxContract.decimals(); // Fetch dynamically if needed
       // Use ethers.parseUnits for v6
       const amountInWei = ethers.parseUnits(betAmount, decimals);
      // --- End Contract Setup ---

      // --- Allowance Check ---
      console.log(`Checking USDX allowance for Betting Engine: ${bettingEngineAddress}`);
      // toast.info('Checking token allowance...');
      // Ensure userAddress is not null/undefined before calling allowance
      if (!userAddress) throw new Error("User address not found after connection check.");
      const currentAllowance = await usdxContract.allowance(userAddress, bettingEngineAddress);

      if (currentAllowance < amountInWei) { // Use standard comparison for BigInts
        console.log(`Allowance (${ethers.formatUnits(currentAllowance, decimals)}) is less than bet amount (${betAmount}). Requesting approval...`); // Ethers v6 syntax
        alert(`Approval Needed: The betting contract needs permission to spend ${betAmount} USDX on your behalf. Please confirm the approval transaction in your wallet.`);
        // toast.info('Approval required. Please confirm in your wallet.');

        // Request maximum approval using ethers v6 constant
        const approveTx = await usdxContract.approve(bettingEngineAddress, ethers.MaxUint256); // Ethers v6 syntax
        // toast.loading('Waiting for approval transaction...');
        console.log('Approval transaction sent:', approveTx.hash);
        alert('Approval transaction sent. Waiting for confirmation...');

        const receipt = await approveTx.wait(); // Wait for confirmation
        if (!receipt || receipt.status !== 1) { // Check receipt status for success
           throw new Error(`Approval transaction failed or was reverted. Hash: ${approveTx.hash}`);
        }

        // toast.dismiss();
        // toast.success('Approval successful!');
        alert('Approval successful! You can now confirm the bet.');
        console.log('Approval confirmed.');
      } else {
        console.log(`Sufficient allowance found: ${ethers.formatUnits(currentAllowance, decimals)} USDX`); // Ethers v6 syntax
        // toast.success('Allowance sufficient.');
      }
      // --- End Allowance Check ---

      // --- Place Bet ---
      console.log(`Calling placeBet on market ${market.address} for ${betOnName} with amount ${betAmount} USDX (${amountInWei.toString()} wei)`);
      alert(`Placing Bet: Please confirm the transaction in your wallet to bet ${betAmount} USDX on ${betOnName}.`);
      // toast.info('Placing bet. Please confirm in your wallet.');

      // Get the correct odds from liveOdds state (use non-null assertion)
       const oddsForBet = isBettingOnHomeOrOver ? liveOdds!.homeOdds : liveOdds!.awayOdds;
      // Use bigint comparison for v6
      if (oddsForBet === 0n || oddsForBet < 1000n) { // Simplified check since liveOdds is guaranteed non-null here
          throw new Error("Selected odds are not available or invalid.");
      }

      // Updated placeBet call in NBAMarket contract
      // placeBet(BettingEngine.BetType _betType, uint256 _amount, bool _isBettingOnHomeOrOver)
      const placeBetTx = await marketContract.placeBet(
        selectedBetType,      // _betType
        amountInWei,          // _amount
        isBettingOnHomeOrOver // _isBettingOnHomeOrOver
       );
      // toast.loading('Waiting for betting transaction...');
      console.log('Bet transaction sent:', placeBetTx.hash);
      alert('Bet transaction sent. Waiting for confirmation...');

      const betReceipt = await placeBetTx.wait(); // Wait for confirmation
      if (!betReceipt || betReceipt.status !== 1) { // Check receipt status for success
         throw new Error(`Bet transaction failed or was reverted. Hash: ${placeBetTx.hash}`);
      }

      // toast.dismiss();
      // toast.success(`Successfully placed bet of ${betAmount} USDX on ${teamName}!`);
      alert(`Success! Bet of ${betAmount} USDX placed on ${betOnName}.`);
      console.log('Bet transaction confirmed:', placeBetTx.hash);
      setBetAmount(''); // Reset input after successful bet
      // Consider triggering a refresh of market data or user balances here
      // --- End Place Bet ---

    } catch (error: any) {
      console.error('Betting transaction failed:', error);
      // toast.dismiss(); // Dismiss any loading toasts
      let errorMessage = 'Betting failed. Please check the console for details.';
      if (error.code === 'ACTION_REJECTED') {
          errorMessage = 'Transaction rejected in wallet.';
      } else if (error.reason) {
          // Ethers.js often includes a 'reason' for contract reverts
          errorMessage = `Betting failed: ${error.reason}`;
      } else if (error.message) {
          errorMessage = `Betting failed: ${error.message}`;
      }
      // toast.error(errorMessage);
      alert(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Convert Unix timestamp to readable date
  const gameDate = new Date(parseInt(market.gameTimestamp, 10) * 1000).toLocaleString();
  
  // Log state values before render
  console.log(`Market ${market.address} - Rendering State:`, 
    { isLoading, isFetchingData, marketStatus, fetchError }
  );

  return (
    <div className="border rounded-lg overflow-hidden shadow-md bg-white">
      <div className="bg-gray-100 px-4 py-2 border-b flex justify-between items-center">
        <h3 className="font-bold truncate">{market.homeTeam} vs {market.awayTeam}</h3>
        {getStatusBadge()}
      </div>
      
      <div className="p-4">
        <div className="mb-4">
          <p className="text-sm text-gray-600 mb-1">Game Time:</p>
          <p className="font-medium">{gameDate}</p>
        </div>
        
        <div className="mb-4 grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">{market.homeTeam} Odds:</p>
            <p className="font-medium">{isFetchingData ? 'Loading...' : formatOdds(liveOdds?.homeOdds)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 mb-1">{market.awayTeam} Odds:</p>
            <p className="font-medium">{isFetchingData ? 'Loading...' : formatOdds(liveOdds?.awayOdds)}</p>
          </div>
        </div>
        
        {/* Spread Odds */}
        {!isFetchingData && liveOdds && liveOdds.homeSpreadOdds > 0n && (
          <div className="mb-4">
            <p className="text-sm text-gray-600 mb-1 font-semibold">Spread:</p>
            <div className="grid grid-cols-2 gap-4 text-center">
              <div>
                <p className="text-xs text-gray-500">{market.homeTeam}</p>
                <p className="font-medium">{formatPoints(liveOdds?.homeSpreadPoints)} ({formatOdds(liveOdds?.homeSpreadOdds)})</p>
              </div>
              <div>
                 <p className="text-xs text-gray-500">{market.awayTeam}</p>
                 {/* Away spread points are the negative of home spread points */}
                 <p className="font-medium">{formatPoints(liveOdds && liveOdds.homeSpreadPoints ? -liveOdds.homeSpreadPoints : null)} ({formatOdds(liveOdds?.awaySpreadOdds)})</p>
              </div>
            </div>
          </div>
        )}

        {/* Total Odds */}
        {!isFetchingData && liveOdds && liveOdds.overOdds > 0n && (
          <div className="mb-4">
            <p className="text-sm text-gray-600 mb-1 font-semibold">Total:</p>
             <div className="grid grid-cols-2 gap-4 text-center">
               <div>
                 <p className="text-xs text-gray-500">Over</p>
                 <p className="font-medium">{formatPoints(liveOdds?.totalPoints)} ({formatOdds(liveOdds?.overOdds)})</p>
               </div>
               <div>
                 <p className="text-xs text-gray-500">Under</p>
                 <p className="font-medium">{formatPoints(liveOdds?.totalPoints)} ({formatOdds(liveOdds?.underOdds)})</p>
               </div>
             </div>
          </div>
        )}

        {getOutcome()}
        
        {/* Betting Section - Show only if market status is OPEN */}
        {!isFetchingData && marketStatus === MarketStatus.OPEN && (
          <div className="mt-4 pt-4 border-t">
            {/* Bet Type Selection Tabs */}
            <div className="mb-4 flex border-b">
              <button 
                className={`flex-1 py-2 px-4 text-center text-sm font-medium ${selectedBetType === MONEYLINE_BET_TYPE ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
                onClick={() => setSelectedBetType(MONEYLINE_BET_TYPE)}
                disabled={!liveOdds || liveOdds.homeOdds <= 0n} // Disable if ML odds not available
              >
                Moneyline
              </button>
              <button 
                 className={`flex-1 py-2 px-4 text-center text-sm font-medium ${selectedBetType === SPREAD_BET_TYPE ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
                 onClick={() => setSelectedBetType(SPREAD_BET_TYPE)}
                 disabled={!liveOdds || liveOdds.homeSpreadOdds <= 0n} // Disable if spread odds not available
              >
                Spread
              </button>
              <button 
                 className={`flex-1 py-2 px-4 text-center text-sm font-medium ${selectedBetType === TOTAL_BET_TYPE ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
                 onClick={() => setSelectedBetType(TOTAL_BET_TYPE)}
                 disabled={!liveOdds || liveOdds.overOdds <= 0n} // Disable if total odds not available
              >
                Total
              </button>
            </div>

            <div className="mb-3">
              <label htmlFor={`bet-amount-${market.address}`} className="block text-sm font-medium text-gray-700 mb-1">
                Bet Amount (USDX)
              </label>
              <input
                type="number"
                id={`bet-amount-${market.address}`}
                name={`bet-amount-${market.address}`}
                className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md p-2"
                placeholder="0.0"
                value={betAmount}
                onChange={(e) => setBetAmount(e.target.value)}
                min="0"
                step="any" // Allow decimals
                disabled={isLoading || isFetchingData || marketStatus !== MarketStatus.OPEN}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => handleBet(true)}
                disabled={isLoading || isFetchingData || marketStatus !== MarketStatus.OPEN || !betAmount || parseFloat(betAmount) <= 0}
                className={`inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white ${
                  isLoading || isFetchingData || marketStatus !== MarketStatus.OPEN || !betAmount || parseFloat(betAmount) <= 0 ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
                }`}
              >
                {isLoading ? 'Processing...' : 
                 (selectedBetType === MONEYLINE_BET_TYPE || selectedBetType === SPREAD_BET_TYPE) ? `Bet ${market.homeTeam}` : 'Bet Over'}
              </button>
              <button
                type="button"
                onClick={() => handleBet(false)}
                disabled={isLoading || isFetchingData || marketStatus !== MarketStatus.OPEN || !betAmount || parseFloat(betAmount) <= 0}
                className={`inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white ${
                  isLoading || isFetchingData || marketStatus !== MarketStatus.OPEN || !betAmount || parseFloat(betAmount) <= 0 ? 'bg-gray-400 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500'
                }`}
              >
                {isLoading ? 'Processing...' : 
                 (selectedBetType === MONEYLINE_BET_TYPE || selectedBetType === SPREAD_BET_TYPE) ? `Bet ${market.awayTeam}` : 'Bet Under'}
              </button>
            </div>
          </div>
        )}
        
        <div className="mt-4 pt-3 border-t text-xs text-gray-500">
          <p className="truncate">Market Address: {market.address}</p>
        </div>
      </div>
    </div>
  );
};

export default MarketCard;
