import React from 'react';
import MarketCard from './MarketCard';
import { Market } from '../types/market';
import { CONTRACT_ADDRESSES } from '../config/contracts';

interface MarketsListProps {
  markets: Market[];
  usdxAddress: string;
}

const MarketsList: React.FC<MarketsListProps> = ({ markets, usdxAddress }) => {
  if (markets.length === 0) {
    return (
      <div className="bg-yellow-100 dark:bg-yellow-900 border border-yellow-400 dark:border-yellow-700 text-yellow-700 dark:text-yellow-200 px-4 py-3 rounded-lg">
        <p>No markets found. Try creating a market first.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      {markets.map((market) => (
        <MarketCard 
          key={market.address} 
          market={market} 
          usdxAddress={usdxAddress} 
          expectedChainId={CONTRACT_ADDRESSES.EXPECTED_CHAIN_ID}
        />
      ))}
    </div>
  );
};

export default MarketsList;
