import React from 'react';
import { Market } from '../types/market';

interface MarketCardProps {
  market: Market;
}

const MarketCard: React.FC<MarketCardProps> = ({ market }) => {
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
        
        <div className="mt-4 pt-3 border-t text-xs text-gray-500">
          <p className="truncate">Market Address: {market.address}</p>
        </div>
      </div>
    </div>
  );
};

export default MarketCard;
