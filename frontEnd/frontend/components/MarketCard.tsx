import React, { useState, useEffect } from 'react';
import { Market, MarketStatus } from '../types/market';
// Imports for ethers v6 and wagmi v1/v2
import { ethers, Contract } from 'ethers'; // Use BrowserProvider, Contract from ethers v6
import { useAccount, useWalletClient, useChainId } from 'wagmi'; // Use useChainId instead of useNetwork
// import { type WalletClient } from 'viem';
import NBAMarketABI from '../abis/contracts/NBAMarket.sol/NBAMarket.json';
import USDXABI from '../abis/contracts/USDX.sol/USDX.json';
import { WAGMI_CONFIG } from '@/config/contracts';
import { useWallet } from '../contexts/WalletContext';
// Consider using a toast library for better UX than alerts
// import { toast } from 'react-toastify';

// Helper to convert WalletClient (viem) to Signer (ethers v6)
// https://ethers.org/docs/v6/getting-started/#starting-signing
// Note: This basic version might need adjustments based on specific WalletClient transport
// async function getEthersSigner(walletClient: WalletClient): Promise<ethers.Signer | null> { // Return type includes null
//   const { account, chain, transport } = walletClient;
//   // Add checks for required properties
//   if (!account || !chain || !transport) {
//       console.warn("WalletClient is missing required properties (account, chain, or transport).");
//       return null;
//   }
//   const network = {
//     chainId: chain.id,
//     name: chain.name,
//   };
//   const provider = new BrowserProvider(transport, network);
//   // Ensure account.address exists before getting signer
//   if (!account.address) {
//       console.warn("WalletClient account is missing address.");
//       return null;
//   }
//   try {
//     const signer = await provider.getSigner(account.address);
//     return signer;
//   } catch (error) {
//       console.error("Error getting signer from provider:", error);
//       return null;
//   }
// }

// Import contract addresses from central config
// import { CONTRACT_ADDRESSES } from '../config/contracts';

interface MarketCardProps {
  market: Market;
  usdxAddress: string; // Address of the USDX ERC20 token
  expectedChainId: number; // The chain ID the contracts are deployed on (default to value from config)
}

// BetType enum values from BettingEngine.sol
const MONEYLINE_BET_TYPE = 0; 
const SPREAD_BET_TYPE = 1;
const TOTAL_BET_TYPE = 2;
const DRAW_BET_TYPE = 3; // For soccer draw bets

// Define the structure for the odds tuple returned by getFullOdds (using bigint for v6)
interface FullOdds {
  homeOdds: bigint;
  awayOdds: bigint;
  drawOdds: bigint;
  homeSpreadPoints: bigint;
  homeSpreadOdds: bigint;
  awaySpreadOdds: bigint;
  totalPoints: bigint;
  overOdds: bigint;
  underOdds: bigint;
}

// Structure for individual exposure details
interface ExposureDetail {
  maxExposure: string; // Keep as string from API
  currentExposure: string;
}

// Structure for the exposure limits data fetched from the API
interface ExposureLimits {
  moneyline: {
    home: ExposureDetail;
    away: ExposureDetail;
    draw: ExposureDetail;
  };
  spread: {
    home: ExposureDetail;
    away: ExposureDetail;
  };
  total: {
    over: ExposureDetail;
    under: ExposureDetail;
  };
}

// Helper function to get provider/signer (adjust based on your setup)
const getProviderOrSigner = (signer?: ethers.Signer | null): ethers.Provider | ethers.Signer => {
  // Use signer if available (for transactions), otherwise use a provider for reads
  if (signer) return signer;
  // Fallback to a default provider (replace with your preferred setup)
  // Make sure this provider is connected to the correct network (e.g., Base Sepolia)
  // return new ethers.JsonRpcProvider(process.env.NEXT_PUBLIC_BASE_SEPOLIA_RPC_URL || 'https://sepolia.base.org');
  return new ethers.JsonRpcProvider(WAGMI_CONFIG.RPC_URL);
  // return new ethers.JsonRpcProvider('https://base-sepolia.g.alchemy.com/v2/eU1jQGAZyansfxyaBRIHQrBQh1Y0bIQi');
  // return new ethers.JsonRpcProvider('http://127.0.0.1:8545');
};

const MarketCard: React.FC<MarketCardProps> = ({ market, usdxAddress, expectedChainId }) => {
  const [betAmount, setBetAmount] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false); // For loading state
  const [signer, setSigner] = useState<ethers.Signer | null>(null); // State for ethers signer
  const [isFetchingData, setIsFetchingData] = useState(true); // For initial odds/status fetch
  const [isFetchingLimits, setIsFetchingLimits] = useState(true); // Separate state for limits fetch
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [limitsError, setLimitsError] = useState<string | null>(null); // Separate state for limits error

  // State for selected bet type and betting on draw option
  const [selectedBetType, setSelectedBetType] = useState<number>(MONEYLINE_BET_TYPE);
  const [isBettingOnDraw, setIsBettingOnDraw] = useState<boolean>(false);
  console.log("signer", isBettingOnDraw);
  // --- Wallet Hooks ---
  const {  isConnected, chainId } = useAccount();
  const currentChainId = useChainId(); // Get current chain ID
  const { data: walletClient } = useWalletClient({ chainId: currentChainId }); // Get WalletClient for the expected chain
  // --- Wallet Context ---
  const { displayAddress, isManagedWallet, getManagedSigner, getEthersSigner, refreshBalance } = useWallet();
  // --- End Wallet Hooks ---
  
  // --- Effect to get Signer when WalletClient is available or when using managed wallet ---
  useEffect(() => {
    const fetchSigner = async () => {
      try {
        let signerToUse = null;
        
        if (isManagedWallet) {
          // If using managed wallet, get managed signer
          signerToUse = await getManagedSigner();
        } else if (walletClient) {
          // If using connected wallet client, get signer from wallet client
          signerToUse = await getEthersSigner();
        }
        
        setSigner(signerToUse);
      } catch (error) {
        console.error("Error getting signer:", error);
        setSigner(null);
      }
    };
    
    fetchSigner();
  }, [walletClient, isManagedWallet, getManagedSigner, getEthersSigner]);
  // --- End Effect ---

  // State for blockchain-fetched data
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null);
  const [liveOdds, setLiveOdds] = useState<FullOdds | null>(null);
  // Add state for scores
  const [homeScore, setHomeScore] = useState<number | null>(null);
  const [awayScore, setAwayScore] = useState<number | null>(null);
  // State for overall market exposure limit
  const [overallMarketLimit, setOverallMarketLimit] = useState<string | null>(null);
  // State for overall current exposure
  const [overallCurrentExposure, setOverallCurrentExposure] = useState<string | null>(null);
  // State for detailed exposure limits
  const [exposureLimits, setExposureLimits] = useState<ExposureLimits | null>(null);

  // Fetch Market Status, Odds, and Overall Limit from Blockchain
  useEffect(() => {
    const fetchMarketData = async () => {
      setIsFetchingData(true);
      setFetchError(null);
      setOverallMarketLimit(null); // Reset market limit on fetch
      setOverallCurrentExposure(null); // Reset current exposure on fetch
      try {
        const provider = getProviderOrSigner(); // Use read-only provider
        const marketContract = new ethers.Contract(market.address, NBAMarketABI.abi, provider);

        // Fetch details (includes status, scores, overall exposure) and odds concurrently
        const [details, oddsResult, exposureInfo] = await Promise.all([
          marketContract.getMarketDetails(),
          marketContract.getFullOdds(),
          marketContract.getExposureInfo() // Fetch overall exposure info
        ]);

        console.log(`Market ${market.address} - Raw Details Result:`, details);
        console.log(`Market ${market.address} - Raw Odds Result:`, oddsResult);
        console.log(`Market ${market.address} - Raw Exposure Info:`, exposureInfo);

        // Extract and set status, home score, and away score from details
        // Indices based on user feedback: 0: homeTeam, 1: awayTeam, 2: timestamp, 3: oddsApiId, 4: status, 5: settled, 6: homeScore, 7: awayScore
        const numericStatus = Number(details[4]); // Status is at index 4
        setMarketStatus(numericStatus as MarketStatus);
        setHomeScore(Number(details[6])); // Home score is at index 6
        setAwayScore(Number(details[7])); // Away score is at index 7

        // Extract and set overall market limit (max exposure) from exposureInfo
        // Assuming exposureInfo returns [maxExposure, currentExposure]
        if (exposureInfo && exposureInfo[0]) {
          setOverallMarketLimit(ethers.formatUnits(exposureInfo[0], 6)); // Assuming 6 decimals
        }
        if (exposureInfo && exposureInfo[1]) {
          setOverallCurrentExposure(ethers.formatUnits(exposureInfo[1], 6)); // Assuming 6 decimals
        }

        // Map the tuple to the FullOdds interface (updated to include drawOdds)
        setLiveOdds({
          homeOdds: oddsResult[0],
          awayOdds: oddsResult[1],
          drawOdds: oddsResult[2],
          homeSpreadPoints: oddsResult[3],
          homeSpreadOdds: oddsResult[4],
          awaySpreadOdds: oddsResult[5],
          totalPoints: oddsResult[6],
          overOdds: oddsResult[7],
          underOdds: oddsResult[8],
        });

      } catch (error: any) {
        console.error(`Error fetching data for market ${market.address}:`, error);
        setFetchError(`Failed to load market data: ${error.message || 'Unknown error'}`);
        setMarketStatus(null); // Reset on error
        setLiveOdds(null);
        setHomeScore(null); // Reset scores on error
        setAwayScore(null); // Reset scores on error
        setOverallMarketLimit(null); // Reset market limit on error
        setOverallCurrentExposure(null); // Reset current exposure on error
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

   // Fetch Detailed Exposure Limits from API Route
   useEffect(() => {
    const fetchLimits = async () => {
      if (!market.address) return; // Don't fetch if no address

      setIsFetchingLimits(true);
      setLimitsError(null);
      setExposureLimits(null); // Reset limits on fetch

      try {
        const response = await fetch(`/api/limits/${market.address}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        const data: ExposureLimits = await response.json();
        setExposureLimits(data);
        console.log(`Fetched limits for ${market.address}:`, data);
      } catch (error: any) {
        console.error(`Error fetching limits for market ${market.address}:`, error);
        setLimitsError(`Failed to load limits: ${error.message || 'Unknown error'}`);
        setExposureLimits(null); // Reset on error
      } finally {
        setIsFetchingLimits(false);
      }
    };

    fetchLimits();

    // Optional: Fetch limits periodically if they might change often
    // const intervalId = setInterval(fetchLimits, 60000); // e.g., every 60 seconds
    // return () => clearInterval(intervalId);

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

  // Helper function to get the **actual** Bet Limit for a specific option, considering odds and current exposure
  const getBetLimit = (type: 'moneyline' | 'spread' | 'total', side: 'home' | 'away' | 'draw' | 'over' | 'under'): string => {
    if (isFetchingLimits || isFetchingData) return 'Loading...'; // Need both limits and odds
    if (limitsError || fetchError) return 'Error';
    if (!exposureLimits || overallMarketLimit === null || !liveOdds) return 'N/A'; // Need odds now

    let specificMaxExposureString: string | undefined = '0.0';
    let specificCurrentExposureString: string | undefined = '0.0';
    let relevantOddsBigInt: bigint | undefined | null = 0n;

    try {
        // 1. Determine the relevant Max and Current Exposure limit strings
        let limitsDetail: ExposureDetail | undefined;
        switch (type) {
            case 'moneyline':
                if (side === 'home') limitsDetail = exposureLimits.moneyline.home;
                else if (side === 'away') limitsDetail = exposureLimits.moneyline.away;
                else if (side === 'draw') limitsDetail = exposureLimits.moneyline.draw;
                break;
            case 'spread':
                if (side === 'home') limitsDetail = exposureLimits.spread.home;
                else if (side === 'away') limitsDetail = exposureLimits.spread.away;
                break;
            case 'total':
                if (side === 'over') limitsDetail = exposureLimits.total.over;
                else if (side === 'under') limitsDetail = exposureLimits.total.under;
                break;
        }
        if (limitsDetail) {
            specificMaxExposureString = limitsDetail.maxExposure;
            specificCurrentExposureString = limitsDetail.currentExposure;
        }


        // 2. Determine the relevant Odds BigInt
        switch (type) {
            case 'moneyline':
                if (side === 'home') relevantOddsBigInt = liveOdds.homeOdds;
                else if (side === 'away') relevantOddsBigInt = liveOdds.awayOdds;
                else if (side === 'draw') relevantOddsBigInt = liveOdds.drawOdds;
                break;
            case 'spread':
                 if (side === 'home') relevantOddsBigInt = liveOdds.homeSpreadOdds;
                 else if (side === 'away') relevantOddsBigInt = liveOdds.awaySpreadOdds;
                 break;
            case 'total':
                 if (side === 'over') relevantOddsBigInt = liveOdds.overOdds;
                 else if (side === 'under') relevantOddsBigInt = liveOdds.underOdds;
                 break;
        }
    } catch (e) {
        console.error("Error accessing exposure limits or odds structure:", e, exposureLimits, liveOdds);
        return 'Error'; // Return error if structure is invalid
    }

    // 3. Use overall market limit if specific limit is "0.0"
    //    This logic might need revisiting: if specific limit is 0, does it mean use overall or truly 0?
    //    Assuming for now it means use the overall market limit's remaining capacity.
    //    HOWEVER, the *current* exposure should still be the specific one if available.
    const effectiveMaxExposureString = (specificMaxExposureString === '0.0' || specificMaxExposureString === undefined) ? overallMarketLimit : specificMaxExposureString;
    // Note: We will use the specificCurrentExposureString regardless of whether max exposure was specific or overall.

    // 4. Validate and convert limit strings to numbers
    let maxExposureValue: number;
    let currentExposureValue: number;
    try {
        maxExposureValue = parseFloat(effectiveMaxExposureString);
        if (isNaN(maxExposureValue) || maxExposureValue < 0) throw new Error("Invalid max exposure value");

        // Use specific current exposure if available, otherwise default to 0? Needs clarification.
        // For now, assume if we couldn't get specific limits, current exposure is also unknown relative to max.
        currentExposureValue = parseFloat(specificCurrentExposureString || '0');
         if (isNaN(currentExposureValue) || currentExposureValue < 0) throw new Error("Invalid current exposure value");

    } catch (e: any) {
        console.warn("Could not parse exposure values:", effectiveMaxExposureString, specificCurrentExposureString, e?.message);
        return 'Invalid Limit Data';
    }

    // 5. Calculate Available Exposure
    const availableExposure = Math.max(0, maxExposureValue - currentExposureValue); // Ensure it's not negative

     if (availableExposure <= 0) {
        return '$0.00'; // No room left for more exposure
    }

    // 6. Validate and convert odds BigInt to multiplier
    if (relevantOddsBigInt === undefined || relevantOddsBigInt === null || relevantOddsBigInt <= 0n) {
        return 'N/A (Odds)';
    }

    let oddsMultiplier: number;
    try {
        oddsMultiplier = parseFloat(ethers.formatUnits(relevantOddsBigInt, 3));
        if (isNaN(oddsMultiplier) || oddsMultiplier <= 0) throw new Error("Invalid odds multiplier derived");
        if (oddsMultiplier < 1) {
             console.warn("Odds multiplier < 1:", oddsMultiplier);
             // If multiplier is < 1, the bet amount itself might exceed exposure.
             // Example: Limit $10, Odds 0.5 (-200). Bet $20 -> Payout $10. Max bet is $10.
             // If limit $10, Odds 0.8. Bet $12.5 -> Payout $10. Max bet is $12.5.
             // Hmm, the formula Max Bet = Available / Multiplier still holds, but interpretation is tricky.
             // Let's assume odds >= 1 (>= +100) for simplicity, typical for payouts.
             // If odds represent the *profit* multiplier, the formula changes slightly.
             // Assuming odds *represent total return multiplier* (stake + profit).
        }
    } catch(e) {
        console.error("Error converting odds to multiplier:", relevantOddsBigInt, e);
        return 'Invalid Odds';
    }

    // 7. Calculate the actual maximum bet amount based on available exposure
    // Max Bet = Available Exposure / Odds Multiplier
    const actualMaxBet = availableExposure / oddsMultiplier;

    // 8. Format the result
    try {
        if (isNaN(actualMaxBet)) return 'Calculation Error';
        // Return $0.00 if calculated max bet is negligible or negative
        return `$${Math.max(0, actualMaxBet).toFixed(2)}`;
    } catch {
        return 'Format Error';
    }
  };

  // Game status display logic using fetched marketStatus
  const getStatusBadge = () => {
    // Handle loading and initial null state first
    if (isFetchingData || marketStatus === null) { 
      return <span className="status-badge text-white bg-gray-500">Loading...</span>;
    }
    if (fetchError) {
      return <span className="status-badge status-cancelled">Error</span>;
    }

    switch (marketStatus) {
      case MarketStatus.PENDING:
        return <span className="status-badge status-pending">Pending</span>;
      case MarketStatus.OPEN:
        // Check game time vs current time
        const now = Date.now() / 1000; // Current time in seconds
        if (parseInt(market.gameTimestamp, 10) > now) {
            return <span className="status-badge status-open">Open</span>;
        } else {
            // If time has passed but status is still OPEN, maybe there's a delay? Treat as Started for UI.
            return <span className="status-badge status-live">Live</span>;
        }
      case MarketStatus.STARTED:
        return <span className="status-badge status-live">Live</span>;
      case MarketStatus.SETTLED:
        return <span className="status-badge status-settled">Settled</span>;
      case MarketStatus.CANCELLED:
        return <span className="status-badge status-cancelled">Cancelled</span>;
      default:
        return <span className="status-badge text-white bg-gray-500">Unknown</span>;
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
      <div className="mt-4 text-center font-semibold text-gray-800 dark:text-gray-100">
        {outcomeText}
      </div>
    );
  };

  // New function to handle different types of bets without state dependency
  const placeBet = async (betOption: "home" | "away" | "draw" | "over" | "under", displayName: string) => {
    console.log("placeBet", betOption, displayName);
    
    // --- Input Validations ---
    if (!betAmount || isNaN(parseFloat(betAmount)) || parseFloat(betAmount) <= 0) {
      alert('Please enter a valid positive bet amount.');
      return;
    }
    
    // Validate wallet connection - allow either connected wallet or managed wallet
    if ((!isConnected && !isManagedWallet) || !displayAddress) { 
      alert('Please connect your wallet or create an account first.');
      return;
    }
    
    if (!signer) { 
      // If this is a managed wallet, try to get the signer again
      if (isManagedWallet) {
        const managedSigner = await getManagedSigner();
        if (!managedSigner) {
          alert('Unable to create wallet signer. Please try again.');
          return;
        }
        setSigner(managedSigner);
      } else {
        alert('Wallet signer not available. Ensure your wallet is connected and on the correct network.');
        return;
      }
    }
    
    // For connected wallets, check chainId. For managed wallets this is handled internally.
    if (!isManagedWallet && chainId !== expectedChainId) {
      alert(`Please switch to the correct network (Expected: ${expectedChainId}, Connected: ${chainId}).`);
      return;
    }
    // --- End Validations ---

    setIsLoading(true);
    
    // Only show a single "Processing" message for managed wallets
    if (isManagedWallet) {
      console.log(`Processing bet of ${betAmount} USDX on ${displayName} with managed wallet...`);
    } else {
      console.log(`Attempting to bet ${betAmount} USDX on ${displayName}`);
    }

    try {
      // --- Contract Setup (Ethers v6) ---
      const marketContract = new Contract(market.address, NBAMarketABI.abi, signer);
      const usdxContract = new Contract(usdxAddress, USDXABI.abi, signer);
      const bettingEngineAddress = await marketContract.bettingEngine();
      const decimals = 6;
      const amountInWei = ethers.parseUnits(betAmount, decimals);
      // --- End Contract Setup ---

      // --- Allowance Check ---
      console.log(`Checking USDX allowance for Betting Engine: ${bettingEngineAddress}`);
      
      // Get the address to check allowance for (either connected wallet or managed wallet)
      const addressToCheck = displayAddress;
      if (!addressToCheck) throw new Error("Wallet address not found after connection check.");
      
      const currentAllowance = await usdxContract.allowance(addressToCheck, bettingEngineAddress);

      if (currentAllowance < amountInWei) {
        console.log(`Allowance (${ethers.formatUnits(currentAllowance, decimals)}) is less than bet amount (${betAmount}). Requesting approval...`);
        
        // Only show alert for regular wallets, not for managed wallets
        if (!isManagedWallet) {
          alert(`Approval Needed: The betting contract needs permission to spend ${betAmount} USDX on your behalf. Please confirm the approval transaction in your wallet.`);
        }

        const approveTx = await usdxContract.approve(bettingEngineAddress, ethers.MaxUint256);
        console.log('Approval transaction sent:', approveTx.hash);
        
        // Only show approval alert for regular wallets
        if (!isManagedWallet) {
          alert('Approval transaction sent. Waiting for confirmation...');
        }

        const receipt = await approveTx.wait();
        if (!receipt || receipt.status !== 1) {
          throw new Error(`Approval transaction failed or was reverted. Hash: ${approveTx.hash}`);
        }

        // Only show success alert for regular wallets
        if (!isManagedWallet) {
          alert('Approval successful! You can now confirm the bet.');
        }
        console.log('Approval confirmed.');
      } else {
        console.log(`Sufficient allowance found: ${ethers.formatUnits(currentAllowance, decimals)} USDX`);
      }
      // --- End Allowance Check ---

      // --- Place Bet ---
      console.log(`Calling placeBet on market ${market.address} for ${displayName} with amount ${betAmount} USDX (${amountInWei.toString()} wei)`);
      
      // Only show transaction confirmation alert for regular wallets
      if (!isManagedWallet) {
        alert(`Placing Bet: Please confirm the transaction in your wallet to bet ${betAmount} USDX on ${displayName}.`);
      }

      // Determine bet parameters based on bet option
      let betType: number;
      let isBettingOnHomeOrOver: boolean;
      let oddsForBet: bigint;
        
      // Set parameters based on bet option
      switch(betOption) {
        case "home":
          betType = selectedBetType; // MONEYLINE or SPREAD
          isBettingOnHomeOrOver = true;
          oddsForBet = selectedBetType === MONEYLINE_BET_TYPE ? liveOdds!.homeOdds : liveOdds!.homeSpreadOdds;
          break;
        case "away":
          betType = selectedBetType; // MONEYLINE or SPREAD
          isBettingOnHomeOrOver = false;
          oddsForBet = selectedBetType === MONEYLINE_BET_TYPE ? liveOdds!.awayOdds : liveOdds!.awaySpreadOdds;
          break;
        case "draw":
          betType = DRAW_BET_TYPE; // Special bet type for draws
          isBettingOnHomeOrOver = false; // This value doesn't matter for draws but we set it to false for consistency
          oddsForBet = liveOdds!.drawOdds;
          break;
        case "over":
          betType = TOTAL_BET_TYPE;
          isBettingOnHomeOrOver = true;
          oddsForBet = liveOdds!.overOdds;
          break;
        case "under":
          betType = TOTAL_BET_TYPE;
          isBettingOnHomeOrOver = false;
          oddsForBet = liveOdds!.underOdds;
          break;
        default:
          throw new Error("Invalid bet option");
      }
      
      if (oddsForBet === 0n || oddsForBet < 1000n) {
        throw new Error("Selected odds are not available or invalid.");
      }
      
      console.log(`Placing bet: type=${betType}, option=${betOption}, isHomeOrOver=${isBettingOnHomeOrOver}, odds=${formatOdds(oddsForBet)}`);
      
      const placeBetTx = await marketContract.placeBet(
        betType,
        amountInWei,
        isBettingOnHomeOrOver
      );
      
      console.log('Bet transaction sent:', placeBetTx.hash);
      
      // Only show waiting alert for regular wallets
      if (!isManagedWallet) {
        alert('Bet transaction sent. Waiting for confirmation...');
      }

      const betReceipt = await placeBetTx.wait();
      if (!betReceipt || betReceipt.status !== 1) {
        throw new Error(`Bet transaction failed or was reverted. Hash: ${placeBetTx.hash}`);
      }

      // Show success message
      alert(`Success! Bet of ${betAmount} USDX placed on ${displayName}.`);
      console.log('Bet transaction confirmed:', placeBetTx.hash);
      setBetAmount('');
      
      // Refresh balance after successful bet
      refreshBalance();
      // --- End Place Bet ---

    } catch (error: any) {
      console.error('Betting transaction failed:', error);
      let errorMessage = 'Betting failed. Please check the console for details.';
      
      if (error.code === 'ACTION_REJECTED') {
        errorMessage = 'Transaction rejected in wallet.';
      } else if (error.reason) {
        errorMessage = `Betting failed: ${error.reason}`;
      } else if (error.message) {
        errorMessage = `Betting failed: ${error.message}`;
      }
      
      // Check for insufficient ETH error (for managed wallets)
      const errorStr = JSON.stringify(error);
      if (isManagedWallet && (
          errorStr.includes("doesn't have enough funds") || 
          errorStr.includes("insufficient funds") ||
          errorStr.includes("sender's balance is: 0")
      )) {
        // For managed wallets with insufficient ETH, automatically try to fund and retry
        try {
          // Don't show error message yet - try to recover automatically
          console.log('Managed wallet needs ETH for gas. Attempting to fund wallet...');
          
          // Attempt to fund the wallet
          const fundResponse = await fetch('/api/fund-wallet', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ address: displayAddress }),
          });
          
          const fundData = await fundResponse.json();
          console.log('Wallet funding result:', fundData);
          
          if (fundData.success) {
            // If funding was successful, wait a moment for the transaction to be mined
            // then try the bet again automatically
            alert("Your wallet is being funded with ETH for gas fees. Your bet will process automatically in a moment.");
            
            // Wait for the funding transaction to be mined (5 seconds)
            await new Promise(resolve => setTimeout(resolve, 5000));
            
            // Try the bet again recursively
            // Reset loading state before recursive call
            setIsLoading(false);
            return placeBet(betOption, displayName);
          } else {
            // If funding failed, show the error
            errorMessage = "Unable to fund your wallet with ETH for gas fees. Please try again later.";
          }
        } catch (fundError) {
          console.error('Error funding wallet:', fundError);
          errorMessage = "Error funding your wallet with ETH for gas fees. Please try again later.";
        }
      }
      
      alert(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Convert Unix timestamp to readable date
  const gameDate = new Date(parseInt(market.gameTimestamp, 10) * 1000).toLocaleString();
  
  // Log state values before render
  console.log(`Market ${market.address} - Rendering State:`, 
    { isLoading, isFetchingData, marketStatus, fetchError, isFetchingLimits, limitsError, overallMarketLimit, overallCurrentExposure, exposureLimits }
  );

  return (
    <div className="card dark:bg-gray-800 hover:shadow-lg">
      <div className="bg-gray-100 dark:bg-gray-700 px-4 py-3 border-b border-gray-200 dark:border-gray-600 flex justify-between items-center">
        <h3 className="font-bold truncate text-gray-800 dark:text-white">{market.homeTeam} vs {market.awayTeam}</h3>
        {getStatusBadge()}
      </div>
      
      <div className="p-5">
        <div className="mb-4 flex justify-between items-center">
            <div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Game Time:</p>
                <p className="font-medium text-gray-800 dark:text-white">{gameDate}</p>
            </div>
            {/* Display Overall Market Limit */}
            <div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1 text-right">Market Limit:</p>
                <p className="font-medium text-gray-800 dark:text-white text-right">
                    {isFetchingData ? 'Loading...' : overallMarketLimit !== null ? `$${parseFloat(overallMarketLimit).toFixed(2)}` : fetchError ? 'Error' : 'N/A'}
                </p>
                {/* Display Overall Current Exposure */} 
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1 text-right">Current Exposure:</p>
                <p className="font-medium text-gray-800 dark:text-white text-right">
                    {isFetchingData ? 'Loading...' : overallCurrentExposure !== null ? `$${parseFloat(overallCurrentExposure).toFixed(2)}` : fetchError ? 'Error' : 'N/A'}
                </p>
            </div>
        </div>
        
        <div className="mb-5 bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2 font-semibold border-b border-gray-200 dark:border-gray-700 pb-1">Moneyline:</p>
          <div className={`grid ${liveOdds?.drawOdds && liveOdds.drawOdds > 0n ? 'grid-cols-3' : 'grid-cols-2'} gap-4`}>
            <div className="text-center p-2 bg-blue-50 dark:bg-blue-900/30 rounded">
              <p className="text-xs text-blue-600 dark:text-blue-400 mb-1">{market.homeTeam}</p>
              <p className="font-medium text-blue-700 dark:text-blue-300 text-lg">{isFetchingData ? 'Loading...' : formatOdds(liveOdds?.homeOdds)}</p>
            </div>
            {(liveOdds?.drawOdds && liveOdds.drawOdds > 0n ) ? (
              <div className="text-center p-2 bg-yellow-50 dark:bg-yellow-900/30 rounded">
                <p className="text-xs text-yellow-600 dark:text-yellow-400 mb-1">Draw</p>
                <p className="font-medium text-yellow-700 dark:text-yellow-300 text-lg">{isFetchingData ? 'Loading...' : formatOdds(liveOdds?.drawOdds)}</p>
              </div>
            ) : null}
            <div className="text-center p-2 bg-green-50 dark:bg-green-900/30 rounded">
              <p className="text-xs text-green-600 dark:text-green-400 mb-1">{market.awayTeam}</p>
              <p className="font-medium text-green-700 dark:text-green-300 text-lg">{isFetchingData ? 'Loading...' : formatOdds(liveOdds?.awayOdds)}</p>
            </div>
          </div>
        </div>
        
        {/* Spread Odds */}
        {!isFetchingData && liveOdds && liveOdds.homeSpreadOdds > 0n && (
          <div className="mb-5 bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2 font-semibold border-b border-gray-200 dark:border-gray-700 pb-1">Spread:</p>
            <div className="grid grid-cols-2 gap-4 text-center">
              <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded">
                <p className="text-xs text-blue-600 dark:text-blue-400 mb-1">{market.homeTeam}</p>
                <p className="font-medium text-blue-700 dark:text-blue-300">
                  <span className="block text-lg">{formatPoints(liveOdds?.homeSpreadPoints)}</span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">({formatOdds(liveOdds?.homeSpreadOdds)})</span>
                </p>
              </div>
              <div className="p-2 bg-green-50 dark:bg-green-900/30 rounded">
                <p className="text-xs text-green-600 dark:text-green-400 mb-1">{market.awayTeam}</p>
                <p className="font-medium text-green-700 dark:text-green-300">
                  <span className="block text-lg">{formatPoints(liveOdds && liveOdds.homeSpreadPoints ? -liveOdds.homeSpreadPoints : null)}</span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">({formatOdds(liveOdds?.awaySpreadOdds)})</span>
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Total Odds */}
        {!isFetchingData && liveOdds && liveOdds.overOdds > 0n && (
          <div className="mb-5 bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2 font-semibold border-b border-gray-200 dark:border-gray-700 pb-1">Total:</p>
            <div className="grid grid-cols-2 gap-4 text-center">
              <div className="p-2 bg-indigo-50 dark:bg-indigo-900/30 rounded">
                <p className="text-xs text-indigo-600 dark:text-indigo-400 mb-1">Over</p>
                <p className="font-medium text-indigo-700 dark:text-indigo-300">
                  <span className="block text-lg">{formatPoints(liveOdds?.totalPoints)}</span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">({formatOdds(liveOdds?.overOdds)})</span>
                </p>
              </div>
              <div className="p-2 bg-purple-50 dark:bg-purple-900/30 rounded">
                <p className="text-xs text-purple-600 dark:text-purple-400 mb-1">Under</p>
                <p className="font-medium text-purple-700 dark:text-purple-300">
                  <span className="block text-lg">{formatPoints(liveOdds?.totalPoints)}</span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">({formatOdds(liveOdds?.underOdds)})</span>
                </p>
              </div>
            </div>
          </div>
        )}

        {getOutcome()}
        
        {/* Betting Section - Show only if market status is OPEN */}
        {/* Ensure both data and limits are loaded before showing betting section */}
        {!isFetchingData && !isFetchingLimits && marketStatus === MarketStatus.OPEN && !fetchError && !limitsError && (
          <div className="mt-5 pt-4 border-t border-gray-200 dark:border-gray-700">
            {/* Bet Type Selection Tabs */}
            <div className="mb-4 flex border-b border-gray-200 dark:border-gray-700">
              <button
                className={`flex-1 py-2 px-4 text-center text-sm font-medium ${                  selectedBetType === MONEYLINE_BET_TYPE
                    ? 'border-b-2 border-primary text-primary dark:text-primary-light'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
                onClick={() => {
                  setSelectedBetType(MONEYLINE_BET_TYPE);
                  setIsBettingOnDraw(false); // Reset draw selection when switching bet types
                }}
                disabled={!liveOdds || liveOdds.homeOdds <= 0n} // Disable if ML odds not available
              >
                Moneyline
              </button>
              <button 
                className={`flex-1 py-2 px-4 text-center text-sm font-medium ${
                  selectedBetType === SPREAD_BET_TYPE 
                    ? 'border-b-2 border-primary text-primary dark:text-primary-light' 
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
                onClick={() => {
                  setSelectedBetType(SPREAD_BET_TYPE);
                  setIsBettingOnDraw(false); // Reset draw selection when switching bet types
                }}
                disabled={!liveOdds || liveOdds.homeSpreadOdds <= 0n} // Disable if spread odds not available
              >
                Spread
              </button>
              <button 
                className={`flex-1 py-2 px-4 text-center text-sm font-medium ${
                  selectedBetType === TOTAL_BET_TYPE 
                    ? 'border-b-2 border-primary text-primary dark:text-primary-light' 
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
                onClick={() => {
                  setSelectedBetType(TOTAL_BET_TYPE);
                  setIsBettingOnDraw(false); // Reset draw selection when switching bet types
                }}
                disabled={!liveOdds || liveOdds.overOdds <= 0n} // Disable if total odds not available
              >
                Total
              </button>
            </div>

            <div className="mb-4">
              <label htmlFor={`bet-amount-${market.address}`} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Bet Amount (USDX)
              </label>
              <input
                type="number"
                id={`bet-amount-${market.address}`}
                name={`bet-amount-${market.address}`}
                className="shadow-sm focus:ring-primary focus:border-primary block w-full text-sm border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg p-3"
                placeholder="0.0"
                value={betAmount}
                onChange={(e) => setBetAmount(e.target.value)}
                min="0"
                step="any" // Allow decimals
                disabled={isLoading || isFetchingData || isFetchingLimits || marketStatus !== MarketStatus.OPEN}
              />
            </div>
            {/* Betting Buttons with Limits */}
            <div className={`grid ${selectedBetType === MONEYLINE_BET_TYPE && liveOdds?.drawOdds && liveOdds.drawOdds > 0n ? 'grid-cols-3' : 'grid-cols-2'} gap-3 items-start`}>
              {/* Home / Over Button */}
              <div className="flex flex-col items-center">
                <button
                  type="button"
                  onClick={() => {
                    if (selectedBetType === MONEYLINE_BET_TYPE || selectedBetType === SPREAD_BET_TYPE) {
                      placeBet("home", market.homeTeam);
                    } else {
                      placeBet("over", "Over");
                    }
                  }}
                  disabled={isLoading || !betAmount || parseFloat(betAmount) <= 0}
                  className={`btn-home w-full inline-flex justify-center items-center px-4 py-3 border border-transparent text-sm font-medium rounded-lg shadow-sm text-white ${                    isLoading || !betAmount || parseFloat(betAmount) <= 0
                      ? 'bg-gray-400 dark:bg-gray-600 cursor-not-allowed'
                      : 'bet-button-home hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
                  }`}
                >
                  {isLoading ? 'Processing...' :
                   (selectedBetType === MONEYLINE_BET_TYPE || selectedBetType === SPREAD_BET_TYPE) ? `Bet ${market.homeTeam}` : 'Bet Over'}
                </button>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Bet Limit: {
                        (selectedBetType === MONEYLINE_BET_TYPE) ? getBetLimit('moneyline', 'home') :
                        (selectedBetType === SPREAD_BET_TYPE) ? getBetLimit('spread', 'home') :
                        getBetLimit('total', 'over')
                    }
                </p>
              </div>

              {/* Draw Button (Conditional) */}
              {((selectedBetType === MONEYLINE_BET_TYPE && liveOdds?.drawOdds && liveOdds.drawOdds > 0n)) ? (
                <div className="flex flex-col items-center">
                  <button
                    type="button"
                    onClick={() => placeBet("draw", "Draw")}
                    disabled={isLoading || !betAmount || parseFloat(betAmount) <= 0}
                    className={`btn-draw w-full inline-flex justify-center items-center px-4 py-3 border border-transparent text-sm font-medium rounded-lg shadow-sm text-white ${                      isLoading || !betAmount || parseFloat(betAmount) <= 0
                        ? 'bg-gray-400 dark:bg-gray-600 cursor-not-allowed'
                        : 'bet-button-draw hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500'
                    }`}
                  >
                    {isLoading ? 'Processing...' : 'Bet Draw'}
                  </button>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Bet Limit: {getBetLimit('moneyline', 'draw')}
                  </p>
                </div>
              ) : null}

              {/* Away / Under Button */}
              <div className="flex flex-col items-center">
                <button
                  type="button"
                  onClick={() => {
                    if (selectedBetType === MONEYLINE_BET_TYPE || selectedBetType === SPREAD_BET_TYPE) {
                      placeBet("away", market.awayTeam);
                    } else {
                      placeBet("under", "Under");
                    }
                  }}
                  disabled={isLoading || !betAmount || parseFloat(betAmount) <= 0}
                  className={`btn-away w-full inline-flex justify-center items-center px-4 py-3 border border-transparent text-sm font-medium rounded-lg shadow-sm text-white ${                    isLoading || !betAmount || parseFloat(betAmount) <= 0
                      ? 'bg-gray-400 dark:bg-gray-600 cursor-not-allowed'
                      : 'bet-button-away hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500'
                  }`}
                >
                  {isLoading ? 'Processing...' :
                   (selectedBetType === MONEYLINE_BET_TYPE || selectedBetType === SPREAD_BET_TYPE) ? `Bet ${market.awayTeam}` : 'Bet Under'}
                </button>
                 <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Bet Limit: {
                        (selectedBetType === MONEYLINE_BET_TYPE) ? getBetLimit('moneyline', 'away') :
                        (selectedBetType === SPREAD_BET_TYPE) ? getBetLimit('spread', 'away') :
                        getBetLimit('total', 'under')
                    }
                </p>
              </div>
            </div>
             {/* Display Limits Error */}
             {limitsError && (
                <p className="text-xs text-red-500 dark:text-red-400 mt-2 text-center">
                    Could not load bet limits: {limitsError}
                </p>
            )}
          </div>
        )}
        
        {/* Display Fetching/Error States for Betting Section */}
        {(isFetchingData || isFetchingLimits) && marketStatus === MarketStatus.OPEN && (
           <p className="text-sm text-gray-500 dark:text-gray-400 mt-4 text-center">Loading betting options...</p>
        )}
        {(fetchError || limitsError) && marketStatus === MarketStatus.OPEN && (
            <p className="text-sm text-red-500 dark:text-red-400 mt-4 text-center">
                Error loading market data or limits. Betting unavailable.
            </p>
        )}
         {marketStatus !== MarketStatus.OPEN && marketStatus !== null && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-4 text-center">
               Betting is closed for this market.
            </p>
         )}

        <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
          <p className="truncate">Market Address: {market.address}</p>
        </div>
      </div>
    </div>
  );
};

export default MarketCard;
