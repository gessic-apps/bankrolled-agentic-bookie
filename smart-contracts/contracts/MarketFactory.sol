// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./NBAMarket.sol";

/**
 * @title MarketFactory
 * @dev Factory contract for deploying NBA betting markets
 */
contract MarketFactory {
    address public admin;
    address public defaultOddsProvider;
    address public defaultResultsProvider;
    
    // Track all markets created
    NBAMarket[] public deployedMarkets;
    
    // Events
    event MarketCreated(address marketAddress, string homeTeam, string awayTeam, uint256 gameTimestamp, string oddsApiId);
    
    /**
     * @dev Constructor sets the administrator and default service providers
     */
    constructor(address _defaultOddsProvider, address _defaultResultsProvider) {
        admin = msg.sender;
        defaultOddsProvider = _defaultOddsProvider;
        defaultResultsProvider = _defaultResultsProvider;
    }
    
    // Modifiers
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can call this function");
        _;
    }
    
    /**
     * @dev Creates a new NBA market
     * @param homeTeam The home team name
     * @param awayTeam The away team name
     * @param gameTimestamp The timestamp when the game starts
     * @param homeOdds Initial home team odds (in basis points, can be 0)
     * @param awayOdds Initial away team odds (in basis points, can be 0)
     * @return The address of the newly created market
     */
    function createMarket(
        string memory homeTeam,
        string memory awayTeam,
        uint256 gameTimestamp,
        string memory oddsApiId,
        uint256 homeOdds,
        uint256 awayOdds
    ) 
        public 
        onlyAdmin 
        returns (address) 
    {
        NBAMarket newMarket = new NBAMarket(
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
            homeOdds,
            awayOdds,
            admin,
            defaultOddsProvider,
            defaultResultsProvider
        );
        
        deployedMarkets.push(newMarket);
        
        emit MarketCreated(address(newMarket), homeTeam, awayTeam, gameTimestamp, oddsApiId);
        
        return address(newMarket);
    }
    
    /**
     * @dev Creates a new NBA market with custom providers
     * @param homeTeam The home team name
     * @param awayTeam The away team name
     * @param gameTimestamp The timestamp when the game starts
     * @param homeOdds Initial home team odds (in basis points, can be 0)
     * @param awayOdds Initial away team odds (in basis points, can be 0)
     * @param oddsProvider Custom odds provider address
     * @param resultsProvider Custom results provider address
     * @return The address of the newly created market
     */
    function createMarketWithCustomProviders(
        string memory homeTeam,
        string memory awayTeam,
        uint256 gameTimestamp,
        string memory oddsApiId,
        uint256 homeOdds,
        uint256 awayOdds,
        address oddsProvider,
        address resultsProvider
    ) 
        external 
        onlyAdmin 
        returns (address) 
    {
        NBAMarket newMarket = new NBAMarket(
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
            homeOdds,
            awayOdds,
            admin,
            oddsProvider,
            resultsProvider
        );
        
        deployedMarkets.push(newMarket);
        
        emit MarketCreated(address(newMarket), homeTeam, awayTeam, gameTimestamp, oddsApiId);
        
        return address(newMarket);
    }

    /**
     * @dev Updates the default odds provider
     * @param _newDefaultOddsProvider The new default odds provider address
     */
    function setDefaultOddsProvider(address _newDefaultOddsProvider) 
        external 
        onlyAdmin 
    {
        defaultOddsProvider = _newDefaultOddsProvider;
    }
    
    /**
     * @dev Updates the default results provider
     * @param _newDefaultResultsProvider The new default results provider address
     */
    function setDefaultResultsProvider(address _newDefaultResultsProvider) 
        external 
        onlyAdmin 
    {
        defaultResultsProvider = _newDefaultResultsProvider;
    }
    
    /**
     * @dev Transfers admin role to a new address
     * @param _newAdmin The new admin address
     */
    function transferAdmin(address _newAdmin) 
        external 
        onlyAdmin 
    {
        require(_newAdmin != address(0), "New admin cannot be zero address");
        admin = _newAdmin;
    }
    
    /**
     * @dev Creates a market with no initial odds
     * @param homeTeam The home team name
     * @param awayTeam The away team name
     * @param gameTimestamp The timestamp when the game starts
     * @return The address of the newly created market
     */
    function createMarketWithoutOdds(
        string memory homeTeam,
        string memory awayTeam,
        uint256 gameTimestamp,
        string memory oddsApiId
    ) 
        external 
        onlyAdmin 
        returns (address) 
    {
        return createMarket(
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
            0,
            0
        );
    }
    
    /**
     * @dev Gets the total number of deployed markets
     * @return The number of deployed markets
     */
    function getDeployedMarketsCount() 
        external 
        view 
        returns (uint256) 
    {
        return deployedMarkets.length;
    }
}