import React, { useState, useEffect } from 'react';
import { Market } from '../types/market';
// Imports for ethers v6 and wagmi v1/v2
import { ethers, BrowserProvider, Contract } from 'ethers'; // Use BrowserProvider, Contract from ethers v6
import { useAccount, useWalletClient, useChainId } from 'wagmi'; // Use useChainId instead of useNetwork
import { type WalletClient } from 'viem';
import { abi as NBAMarketABI } from '../abis/contracts/NBAMarket.sol/NBAMarket.json';
import { abi as USDXABI } from '../abis/contracts/USDX.sol/USDX.json';
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

const MarketCard: React.FC<MarketCardProps> = ({ market, usdxAddress, expectedChainId }) => {
  const [betAmount, setBetAmount] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false); // For loading state
  const [signer, setSigner] = useState<ethers.Signer | null>(null); // State for ethers signer

  // --- Wallet Hooks ---
  const { address: userAddress, isConnected } = useAccount();
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

  // Convert Unix timestamp to readable date
  const gameDate = new Date(parseInt(market.gameTimestamp) * 1000).toLocaleString();
  
  // Helper function to display odds in decimal format (e.g., 1850 -> 1.85)
  const formatOdds = (odds: string) => {
    const oddsNumber = parseInt(odds);
    return oddsNumber ? (oddsNumber / 1000).toFixed(3) : 'Not set';
  };

  // Helper function to display market status
  const getStatusBadge = () => {
    if (market.gameEnded) {
      return <span className="px-2 py-1 text-xs rounded bg-gray-500 text-white">Game Ended</span>;
    }
    if (market.gameStarted) {
      return <span className="px-2 py-1 text-xs rounded bg-blue-500 text-white">In Progress</span>;
    }
    if (market.isReadyForBetting) {
      return <span className="px-2 py-1 text-xs rounded bg-green-500 text-white">Ready for Betting</span>;
    }
    return <span className="px-2 py-1 text-xs rounded bg-yellow-500 text-white">Not Ready</span>;
  };

  // Helper function to display outcome
  const getOutcome = () => {
    if (!market.gameEnded) return null;
    
    if (market.outcome === 1) {
      return <div className="mt-2 text-green-600 font-semibold">{market.homeTeam} Won</div>;
    }
    if (market.outcome === 2) {
      return <div className="mt-2 text-green-600 font-semibold">{market.awayTeam} Won</div>;
    }
    return <div className="mt-2 text-gray-600">No result yet</div>;
  };

  // Function to handle placing a bet
  const handleBet = async (onHomeTeam: boolean) => {
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
    // if (currentChainId !== expectedChainId) { 
    //    alert(`Incorrect Network: Please switch to the network with Chain ID ${expectedChainId}. You are currently connected to Chain ID ${currentChainId}.`);
    //    return;
    // }
    // --- End Validations ---

    setIsLoading(true);
    const teamName = onHomeTeam ? market.homeTeam : market.awayTeam;
    console.log(`Attempting to bet ${betAmount} USDX on ${teamName}`);
    // toast.info(`Processing bet for ${teamName}...`);

    try {
      // --- Contract Setup (Ethers v6) ---
      // Pass signer directly to Contract constructor
      const marketContract = new Contract(market.address, NBAMarketABI, signer);
      const usdxContract = new Contract(usdxAddress, USDXABI, signer);
      const bettingEngineAddress = await marketContract.bettingEngine(); // Fetch the engine address
      const amountInWei = ethers.parseUnits(betAmount, 6); // Ethers v6 syntax
      // --- End Contract Setup ---

      // --- Allowance Check ---
      console.log(`Checking USDX allowance for Betting Engine: ${bettingEngineAddress}`);
      // toast.info('Checking token allowance...');
      // Ensure userAddress is not null/undefined before calling allowance
      if (!userAddress) throw new Error("User address not found after connection check.");
      const currentAllowance = await usdxContract.allowance(userAddress, bettingEngineAddress);

      if (currentAllowance < amountInWei) { // Use standard comparison for BigInts
        console.log(`Allowance (${ethers.formatUnits(currentAllowance, 18)}) is less than bet amount (${betAmount}). Requesting approval...`); // Ethers v6 syntax
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
        console.log(`Sufficient allowance found: ${ethers.formatUnits(currentAllowance, 18)} USDX`); // Ethers v6 syntax
        // toast.success('Allowance sufficient.');
      }
      // --- End Allowance Check ---

      // --- Place Bet ---
      console.log(`Calling placeBet on market ${market.address} for ${teamName} with amount ${betAmount} USDX (${amountInWei.toString()} wei)`);
      alert(`Placing Bet: Please confirm the transaction in your wallet to bet ${betAmount} USDX on ${teamName}.`);
      // toast.info('Placing bet. Please confirm in your wallet.');

      const placeBetTx = await marketContract.placeBet(amountInWei, onHomeTeam);
      // toast.loading('Waiting for betting transaction...');
      console.log('Bet transaction sent:', placeBetTx.hash);
      alert('Bet transaction sent. Waiting for confirmation...');

      const betReceipt = await placeBetTx.wait(); // Wait for confirmation
      if (!betReceipt || betReceipt.status !== 1) { // Check receipt status for success
         throw new Error(`Bet transaction failed or was reverted. Hash: ${placeBetTx.hash}`);
      }

      // toast.dismiss();
      // toast.success(`Successfully placed bet of ${betAmount} USDX on ${teamName}!`);
      alert(`Success! Bet of ${betAmount} USDX placed on ${teamName}.`);
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
            <p className="font-medium">{formatOdds(market.homeOdds)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 mb-1">{market.awayTeam} Odds:</p>
            <p className="font-medium">{formatOdds(market.awayOdds)}</p>
          </div>
        </div>
        
        {getOutcome()}
        
        {/* Betting Section - Show only if market is ready */}
        {market.isReadyForBetting && !market.gameStarted && !market.gameEnded && (
          <div className="mt-4 pt-4 border-t">
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
                disabled={isLoading} // Only disable input while loading
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => handleBet(true)}
                disabled={isLoading || !betAmount || parseFloat(betAmount) <= 0}
                className={`inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white ${
                  isLoading || !betAmount || parseFloat(betAmount) <= 0 ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
                }`}
              >
                {isLoading ? 'Processing...' : `Bet ${market.homeTeam}`}
              </button>
              <button
                type="button"
                onClick={() => handleBet(false)}
                disabled={isLoading || !betAmount || parseFloat(betAmount) <= 0}
                className={`inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white ${
                  isLoading || !betAmount || parseFloat(betAmount) <= 0 ? 'bg-gray-400 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500'
                }`}
              >
                {isLoading ? 'Processing...' : `Bet ${market.awayTeam}`}
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
