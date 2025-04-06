// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "./LiquidityPool.sol";
import "./BettingEngine.sol";

/**
 * @title NBAMarket
 * @dev Smart contract for NBA betting markets with betting functionality
 */
contract NBAMarket is ReentrancyGuard {
    // Game information
    string public homeTeam;
    string public awayTeam;
    uint256 public gameTimestamp;
    string public oddsApiId;
    
    // Odds stored as integers with 3 decimal precision (multiply by 1000)
    // Example: 1.941 is stored as 1941, 10.51 is stored as 10510
    uint256 public homeOdds;
    uint256 public awayOdds;
    
    // Status variables
    bool public gameStarted;
    bool public gameEnded;
    bool public oddsSet;
    enum Outcome { UNDECIDED, HOME_WIN, AWAY_WIN }
    Outcome public outcome;
    
    // Roles
    address public admin;
    address public oddsProvider;
    address public resultsProvider;
    
    // Betting and finance
    IERC20 public usdx;
    LiquidityPool public liquidityPool;
    BettingEngine public bettingEngine;
    
    // Events
    event OddsUpdated(uint256 homeOdds, uint256 awayOdds);
    event ResultSet(Outcome outcome);
    
    /**
     * @dev Constructor initializes the market with basic info
     */
    constructor(
        string memory _homeTeam,
        string memory _awayTeam,
        uint256 _gameTimestamp,
        string memory _oddsApiId,
        uint256 _homeOdds,
        uint256 _awayOdds,
        address _admin,
        address _oddsProvider,
        address _resultsProvider,
        address _usdx,
        address _liquidityPool,
        uint256 _maxExposure
    ) {
        // Set team and game info
        homeTeam = _homeTeam;
        awayTeam = _awayTeam;
        gameTimestamp = _gameTimestamp;
        oddsApiId = _oddsApiId;
        
        // Set odds
        homeOdds = _homeOdds;
        awayOdds = _awayOdds;
        
        // Set roles
        admin = _admin;
        oddsProvider = _oddsProvider;
        resultsProvider = _resultsProvider;
        
        // Set finance
        usdx = IERC20(_usdx);
        liquidityPool = LiquidityPool(_liquidityPool);
        
        // Initialize game state
        gameStarted = false;
        gameEnded = false;
        oddsSet = (_homeOdds >= 1000 && _awayOdds >= 1000);
        outcome = Outcome.UNDECIDED;
        
        // Create the betting engine
        bettingEngine = new BettingEngine(
            address(this),
            _usdx,
            _liquidityPool,
            _maxExposure
        );
    }
    
    // Modifiers
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can call this function");
        _;
    }
    
    modifier onlyOddsProvider() {
        require(msg.sender == oddsProvider, "Only odds provider can call this function");
        _;
    }
    
    modifier onlyResultsProvider() {
        require(msg.sender == resultsProvider, "Only results provider can call this function");
        _;
    }
    
    modifier gameNotStarted() {
        require(!gameStarted, "Game already started");
        _;
    }
    
    modifier gameNotEnded() {
        require(!gameEnded, "Game already ended");
        _;
    }
    
    modifier readyForBetting() {
        require(oddsSet && !gameStarted && !gameEnded, "Market not open for betting");
        _;
    }
    
    /**
     * @dev Returns basic game information
     */
    function getHomeTeam() external view returns (string memory) {
        return homeTeam;
    }
    
    function getAwayTeam() external view returns (string memory) {
        return awayTeam;
    }
    
    function getGameTimestamp() external view returns (uint256) {
        return gameTimestamp;
    }
    
    function getOddsApiId() external view returns (string memory) {
        return oddsApiId;
    }
    
    function getOdds() external view returns (uint256, uint256) {
        return (homeOdds, awayOdds);
    }
    
    function getGameStatus() external view returns (bool, bool, bool, Outcome) {
        return (gameStarted, gameEnded, oddsSet, outcome);
    }
    
    function getExposureInfo() external view returns (uint256, uint256) {
        return (bettingEngine.maxExposure(), bettingEngine.currentExposure());
    }
    
    /**
     * @dev Updates the odds for the market
     */
    function updateOdds(uint256 _homeOdds, uint256 _awayOdds) 
        external 
        onlyOddsProvider 
        gameNotStarted 
    {
        require(_homeOdds >= 1000 && _awayOdds >= 1000, "Odds must be at least 1.000 (1000)");
        
        homeOdds = _homeOdds;
        awayOdds = _awayOdds;
        oddsSet = true;
        
        emit OddsUpdated(_homeOdds, _awayOdds);
    }
    
    /**
     * @dev Marks the game as started
     */
    function startGame() 
        external 
        onlyAdmin 
        gameNotStarted 
    {
        gameStarted = true;
    }
    
    /**
     * @dev Sets the game result and triggers settlement
     */
    function setResult(uint8 _outcome) 
        external 
        onlyResultsProvider 
        gameNotEnded 
    {
        require(_outcome == 1 || _outcome == 2, "Invalid outcome");
        
        if (_outcome == 1) {
            outcome = Outcome.HOME_WIN;
        } else {
            outcome = Outcome.AWAY_WIN;
        }

        gameEnded = true;
        
        emit ResultSet(outcome);
        
        // Settle bets through the betting engine
        bettingEngine.settleBets(_outcome);
    }
    
    /**
     * @dev Places a bet on the market
     */
    function placeBet(uint256 _amount, bool _onHomeTeam) 
        external 
        nonReentrant
        readyForBetting
    {
        require(_amount > 0, "Bet amount must be greater than 0");
        
        // Get the appropriate odds
        uint256 odds = _onHomeTeam ? homeOdds : awayOdds;
        
        // Place bet through the betting engine
        bettingEngine.placeBet(msg.sender, _amount, _onHomeTeam, odds);
    }
    
    /**
     * @dev Changes the odds provider address
     */
    function changeOddsProvider(address _newOddsProvider) 
        external 
        onlyAdmin 
    {
        oddsProvider = _newOddsProvider;
    }
    
    /**
     * @dev Changes the results provider address
     */
    function changeResultsProvider(address _newResultsProvider) 
        external 
        onlyAdmin 
    {
        resultsProvider = _newResultsProvider;
    }
    
    /**
     * @dev Returns a user's bets
     */
    function getBettorBets(address _bettor) 
        external 
        view 
        returns (uint256[] memory) 
    {
        return bettingEngine.getBettorBets(_bettor);
    }
    
    /**
     * @dev Returns bet details
     */
    function getBetDetails(uint256 _betId) 
        external 
        view 
        returns (
            address, 
            uint256, 
            uint256, 
            bool, 
            bool, 
            bool
        ) 
    {
        return bettingEngine.getBetDetails(_betId);
    }
    
    /**
     * @dev Checks if the market is ready for betting
     */
    function isReadyForBetting() 
        external 
        view 
        returns (bool) 
    {
        return oddsSet && !gameStarted && !gameEnded;
    }
    
    /**
     * @dev Admin can update max exposure if needed
     */
    function updateMaxExposure(uint256 _newMaxExposure)
        external
        onlyAdmin
    {
        bettingEngine.updateMaxExposure(_newMaxExposure);
    }
    
    /**
     * @dev Admin can execute emergency settlement in case of issues
     */
    function emergencySettle() 
        external 
        onlyAdmin 
    {
        require(gameStarted, "Game must be started for emergency settlement");
        require(outcome != Outcome.UNDECIDED, "Outcome must be set before settlement");
        
        bettingEngine.settleBets(uint8(outcome));
    }
}