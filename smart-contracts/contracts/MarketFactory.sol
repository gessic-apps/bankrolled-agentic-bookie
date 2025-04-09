// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./NBAMarket.sol";
import "./MarketOdds.sol";
import "./LiquidityPool.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title MarketFactory
 * @dev Factory contract for deploying NBA betting markets
 */
contract MarketFactory {
    address public admin;
    address public defaultOddsProvider;
    address public defaultResultsProvider;
    
    // Token and liquidity
    IERC20 public usdx;
    LiquidityPool public liquidityPool;
    uint256 public defaultMarketFunding = 1000 * 10**6; // 100k USDX by default (assuming 6 decimals)
    
    // Track all markets created
    NBAMarket[] public deployedMarkets;
    
    // Events
    event MarketCreated(address marketAddress, address oddsContractAddress, string homeTeam, string awayTeam, uint256 gameTimestamp, string oddsApiId, uint256 funding);
    
    // Additional events for easier tracking
    event DefaultOddsProviderChanged(address newOddsProvider);
    event DefaultResultsProviderChanged(address newResultsProvider);
    event DefaultMarketFundingChanged(uint256 newDefaultFunding);
    event AdminTransferred(address newAdmin);
    
    /**
     * @dev Constructor sets the administrator, default service providers, and financial settings
     */
    constructor(
        address _defaultOddsProvider, 
        address _defaultResultsProvider,
        address _usdx,
        address _liquidityPool
    ) {
        admin = msg.sender;
        defaultOddsProvider = _defaultOddsProvider;
        defaultResultsProvider = _defaultResultsProvider;
        usdx = IERC20(_usdx);
        liquidityPool = LiquidityPool(_liquidityPool);
    }
    
    // Modifiers
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can call this function");
        _;
    }
    
    /**
     * @dev Creates a new NBA market with funding from the liquidity pool
     * @param homeTeam The home team name
     * @param awayTeam The away team name
     * @param gameTimestamp The timestamp when the game starts
     * @param oddsApiId Unique identifier for the game/market
     * @param homeOdds Initial home team moneyline odds (3 decimals, e.g., 1910)
     * @param awayOdds Initial away team moneyline odds (3 decimals, e.g., 2050)
     * @param homeSpreadPoints Home team spread points (1 decimal, e.g., -75 for -7.5)
     * @param homeSpreadOdds Odds for home team covering spread (3 decimals)
     * @param awaySpreadOdds Odds for away team covering spread (3 decimals)
     * @param totalPoints Total points line (1 decimal, e.g., 2105 for 210.5)
     * @param overOdds Odds for score going over totalPoints (3 decimals)
     * @param underOdds Odds for score going under totalPoints (3 decimals)
     * @param marketFunding Amount of USDX to fund the market with (max exposure)
     * @return marketAddress The address of the newly created NBAMarket contract.
     * @return oddsContractAddress The address of the associated MarketOdds contract.
     */
    function createMarket(
        string memory homeTeam,
        string memory awayTeam,
        uint256 gameTimestamp,
        string memory oddsApiId,
        uint256 homeOdds,
        uint256 awayOdds,
        int256 homeSpreadPoints,
        uint256 homeSpreadOdds,
        uint256 awaySpreadOdds,
        uint256 totalPoints,
        uint256 overOdds,
        uint256 underOdds,
        uint256 marketFunding
    ) 
        public 
        onlyAdmin 
        returns (address marketAddress, address oddsContractAddress)
    {
        // Use default funding if not specified
        if (marketFunding == 0) {
            marketFunding = defaultMarketFunding;
        }
        
        // 1. Deploy MarketOdds contract
        // Pass 0x0 temporarily for controllingMarket, will be updated later if needed (or pass factory?)
        // Using defaultOddsProvider for the MarketOdds contract
        MarketOdds newOddsContract = new MarketOdds(
            address(this), // Pass factory address instead of zero address
            defaultOddsProvider,
            homeOdds,
            awayOdds,
            homeSpreadPoints,
            homeSpreadOdds,
            awaySpreadOdds,
            totalPoints,
            overOdds,
            underOdds
        );
        oddsContractAddress = address(newOddsContract);

        // 2. Deploy NBAMarket contract, linking the MarketOdds contract
        NBAMarket newMarket = new NBAMarket(
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
            // Roles & Finance
            admin,
            defaultOddsProvider,
            defaultResultsProvider,
            address(usdx),
            address(liquidityPool),
            oddsContractAddress, // Pass the address of the deployed odds contract
            marketFunding
        );
        marketAddress = address(newMarket);
        
        // Set the controlling market in the MarketOdds contract
        newOddsContract.setControllingMarket(marketAddress);
        
        deployedMarkets.push(newMarket);
        
        // Authorize market in liquidity pool and fund it
        address bettingEngineAddress = address(newMarket.bettingEngine());
        liquidityPool.authorizeMarket(bettingEngineAddress);
        liquidityPool.fundMarket(bettingEngineAddress, marketFunding);
        
        emit MarketCreated(marketAddress, oddsContractAddress, homeTeam, awayTeam, gameTimestamp, oddsApiId, marketFunding);
        
        // Return both addresses
        return (marketAddress, oddsContractAddress);
    }
    
    /**
     * @dev Creates a new NBA market with custom providers
     * @param homeTeam The home team name
     * @param awayTeam The away team name
     * @param gameTimestamp The timestamp when the game starts
     * @param oddsApiId Unique identifier for the game/market
     * @param homeOdds Initial home team moneyline odds (3 decimals)
     * @param awayOdds Initial away team moneyline odds (3 decimals)
     * @param homeSpreadPoints Home team spread points (1 decimal)
     * @param homeSpreadOdds Odds for home team covering spread (3 decimals)
     * @param awaySpreadOdds Odds for away team covering spread (3 decimals)
     * @param totalPoints Total points line (1 decimal)
     * @param overOdds Odds for score going over totalPoints (3 decimals)
     * @param underOdds Odds for score going under totalPoints (3 decimals)
     * @param oddsProvider Custom odds provider address
     * @param resultsProvider Custom results provider address
     * @param marketFunding Amount of USDX to fund the market with (max exposure)
     * @return marketAddress The address of the newly created NBAMarket contract.
     * @return oddsContractAddress The address of the associated MarketOdds contract.
     */
    function createMarketWithCustomProviders(
        string memory homeTeam,
        string memory awayTeam,
        uint256 gameTimestamp,
        string memory oddsApiId,
        uint256 homeOdds,
        uint256 awayOdds,
        int256 homeSpreadPoints,
        uint256 homeSpreadOdds,
        uint256 awaySpreadOdds,
        uint256 totalPoints,
        uint256 overOdds,
        uint256 underOdds,
        address oddsProvider,
        address resultsProvider,
        uint256 marketFunding
    ) 
        external 
        onlyAdmin 
        returns (address marketAddress, address oddsContractAddress)
    {
        // Use default funding if not specified
        if (marketFunding == 0) {
            marketFunding = defaultMarketFunding;
        }
        
        // 1. Deploy MarketOdds contract with custom provider
        MarketOdds newOddsContract = new MarketOdds(
            address(this), // Pass factory address instead of zero address
            oddsProvider, // Use the custom provider
            homeOdds,
            awayOdds,
            homeSpreadPoints,
            homeSpreadOdds,
            awaySpreadOdds,
            totalPoints,
            overOdds,
            underOdds
        );
         oddsContractAddress = address(newOddsContract);

        // 2. Deploy NBAMarket contract with custom providers
        NBAMarket newMarket = new NBAMarket(
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
            // Roles & Finance (using custom providers)
            admin,
            oddsProvider,
            resultsProvider,
            address(usdx),
            address(liquidityPool),
            oddsContractAddress, // Pass the address of the deployed odds contract
            marketFunding
        );
        marketAddress = address(newMarket);
        
        // Set the controlling market in the MarketOdds contract
        newOddsContract.setControllingMarket(marketAddress);
        
        deployedMarkets.push(newMarket);
        
        // Authorize market in liquidity pool and fund it
        address bettingEngineAddress = address(newMarket.bettingEngine());
        liquidityPool.authorizeMarket(bettingEngineAddress);
        liquidityPool.fundMarket(bettingEngineAddress, marketFunding);
        
        emit MarketCreated(marketAddress, oddsContractAddress, homeTeam, awayTeam, gameTimestamp, oddsApiId, marketFunding);
        
        // Return both addresses
        return (marketAddress, oddsContractAddress);
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
        emit DefaultOddsProviderChanged(_newDefaultOddsProvider);
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
        emit DefaultResultsProviderChanged(_newDefaultResultsProvider);
    }
    
    /**
     * @dev Updates the default market funding amount
     * @param _newDefaultFunding The new default funding amount
     */
    function setDefaultMarketFunding(uint256 _newDefaultFunding) 
        external 
        onlyAdmin 
    {
        defaultMarketFunding = _newDefaultFunding;
        emit DefaultMarketFundingChanged(_newDefaultFunding);
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
        emit AdminTransferred(_newAdmin);
    }
    
    /**
     * @dev Creates a market with no initial odds
     * @param homeTeam The home team name
     * @param awayTeam The away team name
     * @param gameTimestamp The timestamp when the game starts
     * @param oddsApiId Unique identifier for the game/market
     * @param marketFunding Amount of USDX to fund the market with (max exposure)
     * @return marketAddress The address of the newly created NBAMarket contract.
     * @return oddsContractAddress The address of the associated MarketOdds contract.
     */
    function createMarketWithoutOdds(
        string memory homeTeam,
        string memory awayTeam,
        uint256 gameTimestamp,
        string memory oddsApiId,
        uint256 marketFunding
    ) 
        external 
        onlyAdmin 
        returns (address marketAddress, address oddsContractAddress)
    {
        return createMarket(
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            marketFunding
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

    /**
     * @dev Gets the list of all deployed market addresses
     */
    function getDeployedMarkets() external view returns (NBAMarket[] memory) {
        return deployedMarkets;
    }
}