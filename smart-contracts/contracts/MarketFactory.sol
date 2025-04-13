// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./NBAMarket.sol";
import "./MarketOdds.sol";
import "./LiquidityPool.sol";
import "./MarketDeployer.sol";
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
    
    // Market deployer
    MarketDeployer public deployer;
    
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
        address _liquidityPool,
        address _deployer
    ) {
        admin = msg.sender;
        defaultOddsProvider = _defaultOddsProvider;
        defaultResultsProvider = _defaultResultsProvider;
        usdx = IERC20(_usdx);
        liquidityPool = LiquidityPool(_liquidityPool);
        
        // Initialize deployer - can be address(0) to deploy a new one
        if (_deployer == address(0)) {
            deployer = new MarketDeployer();
        } else {
            deployer = MarketDeployer(_deployer);
        }
    }
    
    // Modifiers
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can call this function");
        _;
    }
    
    /**
     * @dev Internal function to finalize market deployment and setup
     */
    function _finalizeMarketDeployment(
        address marketAddress, 
        address oddsContractAddress,
        string memory homeTeam,
        string memory awayTeam,
        uint256 gameTimestamp,
        string memory oddsApiId,
        uint256 marketFunding
    ) internal {
        // Add to deployed markets list
        NBAMarket newMarket = NBAMarket(marketAddress);
        deployedMarkets.push(newMarket);
        
        // Authorize market in liquidity pool and fund it
        address bettingEngineAddress = address(newMarket.bettingEngine());
        liquidityPool.authorizeMarket(bettingEngineAddress);
        liquidityPool.fundMarket(bettingEngineAddress, marketFunding);
        
        emit MarketCreated(marketAddress, oddsContractAddress, homeTeam, awayTeam, gameTimestamp, oddsApiId, marketFunding);
    }

    /**
     * @dev Creates a new NBA market with funding from the liquidity pool
     */
    function createMarket(
        string memory homeTeam,
        string memory awayTeam,
        uint256 gameTimestamp,
        string memory oddsApiId,
        uint256 homeOdds,
        uint256 awayOdds,
        uint256 drawOdds,
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
        
        // Deploy in two steps
        oddsContractAddress = deployer.deployOddsContract(
            address(this),
            defaultOddsProvider,
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
        
        marketAddress = deployer.deployMarketContract(
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
            admin,
            defaultOddsProvider,
            defaultResultsProvider,
            address(usdx),
            address(liquidityPool),
            oddsContractAddress,
            marketFunding
        );
        
        // Set the controlling market in the MarketOdds contract
        MarketOdds(oddsContractAddress).setControllingMarket(marketAddress);
        
        _finalizeMarketDeployment(
            marketAddress,
            oddsContractAddress,
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
            marketFunding
        );
        
        return (marketAddress, oddsContractAddress);
    }
    
    /**
     * @dev Creates a new NBA market with custom providers
     */
    function createMarketWithCustomProviders(
        string memory homeTeam,
        string memory awayTeam,
        uint256 gameTimestamp,
        string memory oddsApiId,
        uint256 homeOdds,
        uint256 awayOdds,
        uint256 drawOdds,
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
        
        // Deploy in two steps
        oddsContractAddress = deployer.deployOddsContract(
            address(this),
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
        
        marketAddress = deployer.deployMarketContract(
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
            admin,
            oddsProvider,
            resultsProvider,
            address(usdx),
            address(liquidityPool),
            oddsContractAddress,
            marketFunding
        );
        
        // Set the controlling market in the MarketOdds contract
        MarketOdds(oddsContractAddress).setControllingMarket(marketAddress);
        
        _finalizeMarketDeployment(
            marketAddress,
            oddsContractAddress,
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
            marketFunding
        );
        
        return (marketAddress, oddsContractAddress);
    }

    /**
     * @dev Creates a market with no initial odds
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
            0, 0, 0, // No moneyline or draw odds
            0, 0, 0, // No spread odds
            0, 0, 0, // No total odds
            marketFunding
        );
    }
    
    // --- Admin functions ---
    
    function setDefaultOddsProvider(address _newDefaultOddsProvider) external onlyAdmin {
        defaultOddsProvider = _newDefaultOddsProvider;
        emit DefaultOddsProviderChanged(_newDefaultOddsProvider);
    }
    
    function setDefaultResultsProvider(address _newDefaultResultsProvider) external onlyAdmin {
        defaultResultsProvider = _newDefaultResultsProvider;
        emit DefaultResultsProviderChanged(_newDefaultResultsProvider);
    }
    
    function setDefaultMarketFunding(uint256 _newDefaultFunding) external onlyAdmin {
        defaultMarketFunding = _newDefaultFunding;
        emit DefaultMarketFundingChanged(_newDefaultFunding);
    }
    
    function transferAdmin(address _newAdmin) external onlyAdmin {
        require(_newAdmin != address(0), "New admin cannot be zero address");
        admin = _newAdmin;
        emit AdminTransferred(_newAdmin);
    }
    
    // --- View functions ---
    
    function getDeployedMarketsCount() external view returns (uint256) {
        return deployedMarkets.length;
    }

    function getDeployedMarkets() external view returns (NBAMarket[] memory) {
        return deployedMarkets;
    }
}