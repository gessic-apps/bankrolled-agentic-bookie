// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./NBAMarket.sol";
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
    uint256 public defaultMarketFunding = 100000 * 10**6; // 100k USDX by default (assuming 6 decimals)
    
    // Track all markets created
    NBAMarket[] public deployedMarkets;
    
    // Events
    event MarketCreated(address marketAddress, string homeTeam, string awayTeam, uint256 gameTimestamp, string oddsApiId, uint256 funding);
    
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
     * @param homeOdds Initial home team odds (in basis points, can be 0)
     * @param awayOdds Initial away team odds (in basis points, can be 0)
     * @param marketFunding Amount of USDX to fund the market with (max exposure)
     * @return The address of the newly created market
     */
    function createMarket(
        string memory homeTeam,
        string memory awayTeam,
        uint256 gameTimestamp,
        string memory oddsApiId,
        uint256 homeOdds,
        uint256 awayOdds,
        uint256 marketFunding
    ) 
        public 
        onlyAdmin 
        returns (address) 
    {
        // Use default funding if not specified
        if (marketFunding == 0) {
            marketFunding = defaultMarketFunding;
        }
        
        NBAMarket newMarket = new NBAMarket(
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
            homeOdds,
            awayOdds,
            admin,
            defaultOddsProvider,
            defaultResultsProvider,
            address(usdx),
            address(liquidityPool),
            marketFunding
        );
        
        deployedMarkets.push(newMarket);
        
        // Authorize market in liquidity pool and fund it
        liquidityPool.authorizeMarket(address(newMarket));
        liquidityPool.fundMarket(address(newMarket), marketFunding);
        
        emit MarketCreated(address(newMarket), homeTeam, awayTeam, gameTimestamp, oddsApiId, marketFunding);
        
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
     * @param marketFunding Amount of USDX to fund the market with (max exposure)
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
        address resultsProvider,
        uint256 marketFunding
    ) 
        external 
        onlyAdmin 
        returns (address) 
    {
        // Use default funding if not specified
        if (marketFunding == 0) {
            marketFunding = defaultMarketFunding;
        }
        
        NBAMarket newMarket = new NBAMarket(
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
            homeOdds,
            awayOdds,
            admin,
            oddsProvider,
            resultsProvider,
            address(usdx),
            address(liquidityPool),
            marketFunding
        );
        
        deployedMarkets.push(newMarket);
        
        // Authorize market in liquidity pool and fund it
        liquidityPool.authorizeMarket(address(newMarket));
        liquidityPool.fundMarket(address(newMarket), marketFunding);
        
        emit MarketCreated(address(newMarket), homeTeam, awayTeam, gameTimestamp, oddsApiId, marketFunding);
        
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
     * @param marketFunding Amount of USDX to fund the market with (max exposure)
     * @return The address of the newly created market
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
        returns (address) 
    {
        return createMarket(
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
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
}