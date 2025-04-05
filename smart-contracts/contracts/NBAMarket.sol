// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title NBAMarket
 * @dev Smart contract for NBA betting markets
 */
contract NBAMarket {
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
    
    // Events
    event OddsUpdated(uint256 homeOdds, uint256 awayOdds);
    event ResultSet(Outcome outcome);
    
    /**
     * @dev Constructor initializes the market with game info and administrative addresses
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
        address _resultsProvider
    ) {
        homeTeam = _homeTeam;
        awayTeam = _awayTeam;
        gameTimestamp = _gameTimestamp;
        oddsApiId = _oddsApiId;
        homeOdds = _homeOdds;
        awayOdds = _awayOdds;
        
        admin = _admin;
        oddsProvider = _oddsProvider;
        resultsProvider = _resultsProvider;
        
        gameStarted = false;
        gameEnded = false;
        oddsSet = (_homeOdds >= 1000 && _awayOdds >= 1000);
        outcome = Outcome.UNDECIDED;
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
    
    /**
     * @dev Updates the odds for the market
     * @param _homeOdds New home team odds (as integers with 3 decimal precision, e.g., 1941 for 1.941)
     * @param _awayOdds New away team odds (as integers with 3 decimal precision, e.g., 1051 for 1.051)
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
     * @dev Sets the game result
     * @param _outcome The game outcome (1 for home win, 2 for away win)
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
    }
    
    /**
     * @dev Changes the odds provider address
     * @param _newOddsProvider The new odds provider address
     */
    function changeOddsProvider(address _newOddsProvider) 
        external 
        onlyAdmin 
    {
        oddsProvider = _newOddsProvider;
    }
    
    /**
     * @dev Changes the results provider address
     * @param _newResultsProvider The new results provider address
     */
    function changeResultsProvider(address _newResultsProvider) 
        external 
        onlyAdmin 
    {
        resultsProvider = _newResultsProvider;
    }
    
    /**
     * @dev Returns market information
     */
    function getMarketInfo() 
        external 
        view 
        returns (
            string memory, 
            string memory, 
            uint256, 
            string memory, 
            uint256, 
            uint256, 
            bool, 
            bool, 
            bool,
            Outcome
        ) 
    {
        return (
            homeTeam,
            awayTeam,
            gameTimestamp,
            oddsApiId,
            homeOdds,
            awayOdds,
            gameStarted,
            gameEnded,
            oddsSet,
            outcome
        );
    }
    
    /**
     * @dev Checks if the market is ready for betting (has odds set and game not started)
     * @return Boolean indicating if market is ready for betting
     */
    function isReadyForBetting() 
        external 
        view 
        returns (bool) 
    {
        return oddsSet && !gameStarted && !gameEnded;
    }
    
}