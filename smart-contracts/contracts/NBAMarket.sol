// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "./LiquidityPool.sol";
import "./BettingEngine.sol";
import "./MarketOdds.sol";
import "./MarketExposureManager.sol";

/**
 * @title NBAMarket
 * @dev Smart contract for NBA betting markets with moneyline, spread, and total points betting.
 */
contract NBAMarket is ReentrancyGuard {
    // --- Game Information ---
    string public homeTeam;
    string public awayTeam;
    uint256 public gameTimestamp;
    string public oddsApiId;

    // --- Odds (3 decimal precision, e.g., 1.941 -> 1941) ---
    // Spread (Points stored with 1 decimal precision, e.g., -7.5 -> -75)
    // homeSpreadPoints represents the points for the home team (e.g., -75 for -7.5)
    // awaySpreadPoints is implicitly -homeSpreadPoints
    int256 public homeSpreadPoints; 
    uint256 public homeSpreadOdds; // Odds for betting on the home team to cover the spread
    uint256 public awaySpreadOdds; // Odds for betting on the away team to cover the spread
    // Total Points (Points stored with 1 decimal precision, e.g., 210.5 -> 2105)
    uint256 public totalPoints; 
    uint256 public overOdds;    // Odds for betting on the total score going OVER totalPoints
    uint256 public underOdds;   // Odds for betting on the total score going UNDER totalPoints
    
    // --- Status Variables ---
    bool public gameStarted;
    bool public gameEnded;
    enum MarketStatus { PENDING, OPEN, STARTED, SETTLED, CANCELLED } // Refined status
    MarketStatus public marketStatus;
    
    // --- Result Variables ---
    uint256 public homeScore;
    uint256 public awayScore;
    bool public resultSettled;

    // --- Roles ---
    address public admin;
    address public oddsProvider;
    address public resultsProvider;
    
    // --- Betting and Finance ---
    address public marketOddsContract;
    IERC20 public usdx;
    LiquidityPool public liquidityPool;
    BettingEngine public bettingEngine;
    
    // --- Events ---
    event MarketResultSet(uint256 homeScore, uint256 awayScore);
    event GameStarted();
    event MarketStatusChanged(MarketStatus newStatus);

    /**
     * @dev Constructor initializes the market with basic info and potentially initial odds/lines
     */
    constructor(
        string memory _homeTeam,
        string memory _awayTeam,
        uint256 _gameTimestamp,
        string memory _oddsApiId,
        // Roles & Finance
        address _admin,
        address _oddsProvider,
        address _resultsProvider,
        address _usdx,
        address _liquidityPool,
        address _marketOddsContract,
        uint256 _maxExposure
    ) {
        // Set team and game info
        homeTeam = _homeTeam;
        awayTeam = _awayTeam;
        gameTimestamp = _gameTimestamp;
        oddsApiId = _oddsApiId;
        
        // Set roles
        admin = _admin;
        oddsProvider = _oddsProvider;
        resultsProvider = _resultsProvider;
        
        // Set finance
        marketOddsContract = _marketOddsContract;
        usdx = IERC20(_usdx);
        liquidityPool = LiquidityPool(_liquidityPool);
        
        // Initialize game state
        bool initialOddsAreSet = MarketOdds(_marketOddsContract).initialOddsSet();
        marketStatus = MarketStatus.PENDING; // Starts as pending
        if (initialOddsAreSet) {
            marketStatus = MarketStatus.OPEN; // Open if odds were provided
        }
        gameStarted = false; // Explicitly false
        gameEnded = false; // Explicitly false
        resultSettled = false; // Explicitly false
        
        // Create the betting engine
        bettingEngine = new BettingEngine(
            address(this),
            _usdx,
            _liquidityPool,
            _maxExposure
        );
        emit MarketStatusChanged(marketStatus);
    }
    
    // --- Modifiers ---
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can call this function");
        _;
    }
    
    // modifier onlyOddsProvider() {
    //     require(msg.sender == oddsProvider, "Only odds provider can call this function");
    //     _;
    // }
    
    // modifier onlyResultsProvider() {
    //     require(msg.sender == resultsProvider, "Only results provider can call this function");
    //     _;
    // }
    
    modifier marketIsOpen() {
        require(marketStatus == MarketStatus.OPEN, "Market not open for betting");
        _;
    }

    modifier marketNotSettled() {
        require(marketStatus != MarketStatus.SETTLED && marketStatus != MarketStatus.CANCELLED, "Market already settled or cancelled");
        _;
    }
    
    modifier marketNotStarted() {
        require(marketStatus == MarketStatus.PENDING || marketStatus == MarketStatus.OPEN, "Market already started");
         _;
    }

    // --- Getters ---

    function getMarketDetails() 
        external 
        view 
        returns (
            string memory _homeTeam,
            string memory _awayTeam,
            uint256 _gameTimestamp,
            string memory _oddsApiId,
            MarketStatus _marketStatus,
            bool _resultSettled,
            uint256 _homeScore,
            uint256 _awayScore
        ) 
    {
        return (
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
            marketStatus,
            resultSettled,
            homeScore,
            awayScore
        );
    }

    function getSpreadDetails() external view returns (int256 _homeSpreadPoints, uint256 _homeSpreadOdds, uint256 _awaySpreadOdds) {
        return (homeSpreadPoints, homeSpreadOdds, awaySpreadOdds);
    }

    function getTotalPointsDetails() external view returns (uint256 _totalPoints, uint256 _overOdds, uint256 _underOdds) {
        return (totalPoints, overOdds, underOdds);
    }
    
    /** @dev Fetches and returns all current odds/lines from the MarketOdds contract */
    function getFullOdds() 
        external 
        view 
        returns (
            uint256 _homeOdds,
            uint256 _awayOdds,
            uint256 _drawOdds, // Added draw odds
            int256 _homeSpreadPoints, 
            uint256 _homeSpreadOdds, 
            uint256 _awaySpreadOdds, 
            uint256 _totalPoints, 
            uint256 _overOdds, 
            uint256 _underOdds
        ) 
    {
        require(marketOddsContract != address(0), "Odds contract not set");
        // Call the view function on the associated MarketOdds contract
        return MarketOdds(marketOddsContract).getFullOdds();
    }

    function getStatus() external view returns (MarketStatus) {
        return marketStatus;
    }

    function getExposureInfo() external view returns (uint256, uint256) {
        return (bettingEngine.maxExposure(), bettingEngine.currentExposure());
    }
    
    /**
     * @dev Returns moneyline market exposure limits and current exposures
     */
    function getMoneylineExposure() external view returns (
        uint256 homeMaxExposure, 
        uint256 homeCurrentExposure,
        uint256 awayMaxExposure, 
        uint256 awayCurrentExposure,
        uint256 drawMax,
        uint256 drawCurrent
    ) {
        return bettingEngine.getMoneylineExposure();
    }
    
    /**
     * @dev Returns spread market exposure limits and current exposures
     */
    function getSpreadExposure() external view returns (
        uint256 homeMaxExposure, 
        uint256 homeCurrentExposure,
        uint256 awayMaxExposure, 
        uint256 awayCurrentExposure
    ) {
        return bettingEngine.getSpreadExposure();
    }
    
    /**
     * @dev Returns total points market exposure limits and current exposures
     */
    function getTotalExposure() external view returns (
        uint256 overMaxExposure, 
        uint256 overCurrentExposure,
        uint256 underMaxExposure, 
        uint256 underCurrentExposure
    ) {
        return bettingEngine.getTotalExposure();
    }
    
    /**
     * @dev Returns market exposure for a specific market type and side
     */
    function getMarketExposure(
        MarketExposureManager.BetType _betType,
        bool _isBettingOnHomeOrOver
    ) external view returns (uint256 maxExposure, uint256 currentExposure) {
        return bettingEngine.getMarketExposure(_betType, _isBettingOnHomeOrOver);
    }
    
    /** @dev Returns the address of the associated MarketOdds contract */
    function getMarketOddsContract() external view returns (address) {
        return marketOddsContract;
    }

    // --- Setters / Actions ---

    /**
     * @dev Marks the game as started, changes status to STARTED
     */
    function startGame() 
        external 
        // onlyResultsProvider 
        marketNotStarted
    {
        // Check if odds are set in the associated MarketOdds contract
        require(marketOddsContract != address(0), "Odds contract not set");
        require(MarketOdds(marketOddsContract).initialOddsSet(), "Cannot start game before odds are set");

        gameStarted = true; // Keep this flag for compatibility/quick checks if needed
        marketStatus = MarketStatus.STARTED;
        
        // Notify the MarketOdds contract that the market has started
        try MarketOdds(marketOddsContract).setMarketStarted() {} catch {}
        
        emit GameStarted();
        emit MarketStatusChanged(marketStatus);
    }
    
    /**
     * @dev Sets the final game scores and triggers settlement
     */
    function setResult(uint256 _homeScore, uint256 _awayScore) 
        external 
        // onlyResultsProvider 
        marketNotSettled 
    {
        require(marketStatus == MarketStatus.STARTED, "NBAMarket: Market must be in STARTED status to set result");
        require(!resultSettled, "NBAMarket: Result already settled");

        homeScore = _homeScore;
        awayScore = _awayScore;
        resultSettled = true;
        gameEnded = true; // Keep this flag too

        emit MarketResultSet(_homeScore, _awayScore);
        
        // Settle bets through the betting engine
        // Pass both scores for spread and total calculations
        bettingEngine.settleBets(_homeScore, _awayScore); 

        // Mark market as settled
        marketStatus = MarketStatus.SETTLED;
        emit MarketStatusChanged(marketStatus);
    }
    
    /**
     * @dev Places a bet based on type
     */
    function placeBet(
        MarketExposureManager.BetType _betType, 
        uint256 _amount, 
        bool _isBettingOnHomeOrOver // True for Home (ML/Spread), True for Over (Total), Not used for DRAW
    ) 
        external 
        nonReentrant
        marketIsOpen // Use the market status check
    {
        require(_amount > 0, "Bet amount must be > 0");
        
        require(marketOddsContract != address(0), "Odds contract not set");
        MarketOdds oddsContract = MarketOdds(marketOddsContract);

        uint256 odds;
        int256 line = 0; // For spread/total points

        if (_betType == MarketExposureManager.BetType.MONEYLINE) {
            (uint256 _homeOdds, uint256 _awayOdds, ) = oddsContract.getMoneylineOdds();
            require(_homeOdds > 0 && _awayOdds > 0, "Moneyline odds not set in MarketOdds");
            odds = _isBettingOnHomeOrOver ? _homeOdds : _awayOdds;
        } else if (_betType == MarketExposureManager.BetType.DRAW) {
            (,,uint256 _drawOdds) = oddsContract.getMoneylineOdds();
            require(_drawOdds > 0, "Draw odds not set in MarketOdds");
            odds = _drawOdds;
            // For DRAW bet, _isBettingOnHomeOrOver is ignored
        } else if (_betType == MarketExposureManager.BetType.SPREAD) {
            (int256 _homeSpreadPoints, uint256 _homeSpreadOdds, uint256 _awaySpreadOdds) = oddsContract.getSpreadDetails();
            require(_homeSpreadOdds > 0 && _awaySpreadOdds > 0, "Spread odds not set in MarketOdds");
            odds = _isBettingOnHomeOrOver ? _homeSpreadOdds : _awaySpreadOdds;
            line = _homeSpreadPoints;
        } else if (_betType == MarketExposureManager.BetType.TOTAL) {
            (uint256 _totalPoints, uint256 _overOdds, uint256 _underOdds) = oddsContract.getTotalPointsDetails();
            require(_overOdds > 0 && _underOdds > 0, "Total odds not set in MarketOdds");
            odds = _isBettingOnHomeOrOver ? _overOdds : _underOdds;
            line = int256(_totalPoints);
        } else {
            revert("Invalid bet type");
        }

        require(odds >= 1000, "Selected odds not valid"); // Check specific odds chosen
        
        // Place bet through the betting engine
        bettingEngine.placeBet(
            msg.sender, 
            _amount, 
            _betType, 
            _isBettingOnHomeOrOver, 
            odds,
            line // Pass the line (spread or total points)
        );
    }
    
    // --- Admin Functions ---

    function changeOddsProvider(address _newOddsProvider) external onlyAdmin {
        oddsProvider = _newOddsProvider;
    }
    
    function changeResultsProvider(address _newResultsProvider) external onlyAdmin {
        resultsProvider = _newResultsProvider;
    }
    
    function updateMaxExposure(uint256 _newMaxExposure) external onlyAdmin {
        bettingEngine.updateMaxExposure(_newMaxExposure);
    }
    
    /**
     * @dev Sets the maximum exposure for a specific market type and side
     * @param _betType Type of bet (MONEYLINE, SPREAD, TOTAL, DRAW)
     * @param _isBettingOnHomeOrOver True for Home team (ML/Spread) or Over (Total), False for Away or Under
     * @param _newLimit The new exposure limit for this market type/side
     */
    function setMarketExposureLimit(
        MarketExposureManager.BetType _betType,
        bool _isBettingOnHomeOrOver,
        uint256 _newLimit
    ) external onlyAdmin {
        bettingEngine.setMarketExposureLimit(_betType, _isBettingOnHomeOrOver, _newLimit);
    }
    
    /**
     * @dev Sets all market-specific exposure limits at once
     * @param _homeMoneylineLimit Home moneyline exposure limit
     * @param _awayMoneylineLimit Away moneyline exposure limit
     * @param _drawLimit Draw exposure limit
     * @param _homeSpreadLimit Home spread exposure limit
     * @param _awaySpreadLimit Away spread exposure limit
     * @param _overLimit Over exposure limit
     * @param _underLimit Under exposure limit
     */
    function setAllMarketExposureLimits(
        uint256 _homeMoneylineLimit,
        uint256 _awayMoneylineLimit,
        uint256 _drawLimit,
        uint256 _homeSpreadLimit,
        uint256 _awaySpreadLimit,
        uint256 _overLimit,
        uint256 _underLimit
    ) external onlyAdmin {
        bettingEngine.setAllMarketExposureLimits(
            _homeMoneylineLimit,
            _awayMoneylineLimit,
            _drawLimit,
            _homeSpreadLimit,
            _awaySpreadLimit,
            _overLimit,
            _underLimit
        );
    }

    /**
     * @dev Allows admin to cancel a market before settlement (e.g., game cancelled)
     * This should trigger a refund mechanism in the BettingEngine.
     */
    function cancelMarket() external onlyAdmin marketNotSettled {
         require(marketStatus != MarketStatus.STARTED, "Cannot cancel after game started unless emergency"); // Or allow cancellation after start? TBD.
         marketStatus = MarketStatus.CANCELLED;
         gameEnded = true; // Mark as ended
         // TODO: Trigger refund in BettingEngine
         bettingEngine.cancelBetsAndRefund(); 
         emit MarketStatusChanged(marketStatus);
    }
    
    /**
     * @dev Emergency settlement if normal process fails AFTER results are known.
     * Requires scores to be manually set first if not already done.
     */
    function emergencySettle() external onlyAdmin {
        require(resultSettled, "Scores must be set for emergency settlement");
        require(marketStatus != MarketStatus.SETTLED && marketStatus != MarketStatus.CANCELLED, "Market already settled or cancelled");
        
        bettingEngine.settleBets(homeScore, awayScore); // Use stored scores

        marketStatus = MarketStatus.SETTLED;
        emit MarketStatusChanged(marketStatus);
    }

    /**
     * @dev Allows the admin to attempt to transition the market from PENDING to OPEN.
     * This should be called after odds have been successfully set in the MarketOdds contract
     * if the market didn't open automatically during creation.
     */
    // function tryOpenMarket() external onlyAdmin onlyOddsProvider {
    function tryOpenMarket() external {
        require(marketStatus == MarketStatus.PENDING, "NBAMarket: Market not in PENDING status");
        require(marketOddsContract != address(0), "NBAMarket: Odds contract not set");
        require(MarketOdds(marketOddsContract).initialOddsSet(), "NBAMarket: Odds not yet set in MarketOdds contract");
        // require(block.timestamp < gameTimestamp, "NBAMarket: Game has already started based on timestamp");
        
        // If all conditions met, open the market
        marketStatus = MarketStatus.OPEN;
        emit MarketStatusChanged(marketStatus);
    }

    // --- View Functions ---

    function getBettorBets(address _bettor) 
        external 
        view 
        returns (uint256[] memory) 
    {
        return bettingEngine.getBettorBets(_bettor);
    }
    
    /** @dev Gets details for a specific bet directly from the BettingEngine */
    function getBetDetails(uint256 _betId) 
        external 
        view 
        returns (
            address _bettor, 
            uint256 _amount, 
            uint256 _potentialWinnings, 
            MarketExposureManager.BetType _betType, 
            bool _isBettingOnHomeOrOver, 
            int256 _line, 
            uint256 _odds,
            bool _settled, 
            bool _won 
        ) 
    {
        // Direct pass-through to BettingEngine
        return bettingEngine.getBetDetails(_betId);
    }
    
    function isMarketOpenForBetting() external view returns (bool) {
        return marketStatus == MarketStatus.OPEN;
    }
}