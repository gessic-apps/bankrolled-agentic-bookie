// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./NBAMarket.sol";
import "./MarketOdds.sol";
import "./LiquidityPool.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title MarketDeployer
 * @dev Contract for deploying market contracts
 */
contract MarketDeployer {
    /**
     * @dev Deploys market odds contract
     */
    function deployOddsContract(
        address caller,
        address oddsProvider,
        uint256 homeOdds,
        uint256 awayOdds,
        uint256 drawOdds,
        int256 homeSpreadPoints,
        uint256 homeSpreadOdds,
        uint256 awaySpreadOdds,
        uint256 totalPoints,
        uint256 overOdds,
        uint256 underOdds
    ) 
        public
        returns (address)
    {
        // Deploy Market Odds contract
        MarketOdds newOddsContract = new MarketOdds(
            caller, // Pass caller address
            oddsProvider,
            homeOdds,
            awayOdds,
            drawOdds,
            homeSpreadPoints,
            homeSpreadOdds,
            awaySpreadOdds,
            totalPoints,
            overOdds,
            underOdds
        );
        
        return address(newOddsContract);
    }
    
    /**
     * @dev Deploys market contract
     */
    function deployMarketContract(
        string memory homeTeam,
        string memory awayTeam,
        uint256 gameTimestamp,
        string memory oddsApiId,
        address admin,
        address oddsProvider,
        address resultsProvider,
        address usdx,
        address liquidityPool,
        address oddsContractAddress,
        uint256 marketFunding
    )
        public
        returns (address)
    {
        // Deploy NBA Market contract
        NBAMarket newMarket = new NBAMarket(
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
            // Roles & Finance
            admin,
            oddsProvider,
            resultsProvider,
            usdx,
            liquidityPool,
            oddsContractAddress,
            marketFunding
        );
        
        return address(newMarket);
    }
}