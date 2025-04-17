"use client";

import { useWallet } from '../contexts/WalletContext';

export default function TokenBalance() {
  const { 
    formattedBalance, 
    isLoading, 
    isError, 
    balance, 
    refreshBalance 
  } = useWallet();

  // Format the number with commas for readability
  const formatNumberWithCommas = (num: string) => {
    return num.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  };

  // Get display text based on state
  const getDisplayText = () => {
    if (isLoading) return 'Loading...';
    if (isError) return 'Error loading balance';
    if (balance === undefined || balance === null) return 'No balance';
    
    // Format with commas for better readability
    const [whole, fraction] = formattedBalance.split('.');
    return `${formatNumberWithCommas(whole)}.${fraction} USDX`;
  };
  
  return (
    <div className={`group flex items-center px-3 py-1.5 rounded-md ${
      balance && Number(balance) > 0 ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600'
    }`}>
      <svg 
        xmlns="http://www.w3.org/2000/svg" 
        className="h-4 w-4 mr-1.5" 
        viewBox="0 0 20 20" 
        fill="currentColor"
      >
        <path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z" />
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z" clipRule="evenodd" />
      </svg>
      <span className="text-sm font-medium">
        {getDisplayText()}
      </span>
      
      {/* Refresh button - only visible on hover */}
      <button 
        onClick={refreshBalance}
        className="ml-2 p-1 rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-200 dark:hover:bg-gray-700"
        title="Refresh balance"
      >
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          className="h-3 w-3" 
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={2} 
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" 
          />
        </svg>
      </button>
    </div>
  );
}