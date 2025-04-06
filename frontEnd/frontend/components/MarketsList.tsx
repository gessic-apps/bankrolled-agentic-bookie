import React from 'react';
import MarketCard from './MarketCard';
import { Market } from '../types/market';

interface MarketsListProps {
  markets: Market[];
  usdxAddress: string;
}

const MarketsList: React.FC<MarketsListProps> = ({ markets, usdxAddress }) => {
  if (markets.length === 0) {
    return (
      <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded">
        <p>No markets found. Try creating a market first.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {markets.map((market) => (
        <MarketCard 
          key={market.address} 
          market={market} 
          usdxAddress={usdxAddress} 
          expectedChainId={8453}
        />
      ))}
    </div>
  );
};

export default MarketsList;
