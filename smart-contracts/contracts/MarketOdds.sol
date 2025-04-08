// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./NBAMarket.sol"; // Import NBAMarket to access its status

/**
 * @title MarketOdds
 * @dev Stores and manages odds/lines for a specific NBAMarket.
 * Typically deployed by MarketFactory and linked to an NBAMarket instance.
 */
contract MarketOdds {
    // --- State Variables ---
    address public controllingMarket; // Address of the NBAMarket this belongs to (for reference/verification)
    address public oddsProvider;      // Address allowed to update odds
    bool public marketStarted = false; // Track if the associated NBAMarket has started

    // Moneyline Odds (3 decimal precision, e.g., 1910)
    uint256 public homeOdds;
    uint256 public awayOdds;

    // Spread (Points: 1 decimal precision, e.g., -75 for -7.5; Odds: 3 decimal precision)
    int256 public homeSpreadPoints; 
    uint256 public homeSpreadOdds; 
    uint256 public awaySpreadOdds; 

    // Total Points (Points: 1 decimal precision, e.g., 2105 for 210.5; Odds: 3 decimal precision)
    uint256 public totalPoints; 
    uint256 public overOdds;    
    uint256 public underOdds;   

    bool public initialOddsSet = false;

    // --- Events ---
     event OddsUpdated(
        address indexed marketAddress, // Include market address for easier off-chain tracking
        uint256 homeOdds, 
        uint256 awayOdds, 
        int256 homeSpreadPoints, 
        uint256 homeSpreadOdds, 
        uint256 awaySpreadOdds, 
        uint256 totalPoints, 
        uint256 overOdds, 
        uint256 underOdds
    );

    // --- Modifier ---
    modifier onlyOddsProvider() {
        require(msg.sender == oddsProvider, "MarketOdds: Only odds provider can call this");
        _;
    }

    // --- Constructor ---
    /**
     * @dev Sets the controlling market, odds provider, and optionally initial odds.
     * @param _controllingMarket The address of the associated NBAMarket contract.
     * @param _oddsProvider The address designated as the odds provider for this market.
     * @param _initialHomeOdds Initial moneyline home odds (0 if not set).
     * @param _initialAwayOdds Initial moneyline away odds (0 if not set).
     * @param _initialHomeSpreadPoints Initial home spread points (0 if not set).
     * @param _initialHomeSpreadOdds Initial home spread odds (0 if not set).
     * @param _initialAwaySpreadOdds Initial away spread odds (0 if not set).
     * @param _initialTotalPoints Initial total points line (0 if not set).
     * @param _initialOverOdds Initial over odds (0 if not set).
     * @param _initialUnderOdds Initial under odds (0 if not set).
     */
    constructor(
        address _controllingMarket,
        address _oddsProvider,
        uint256 _initialHomeOdds,
        uint256 _initialAwayOdds,
        int256 _initialHomeSpreadPoints,
        uint256 _initialHomeSpreadOdds,
        uint256 _initialAwaySpreadOdds,
        uint256 _initialTotalPoints,
        uint256 _initialOverOdds,
        uint256 _initialUnderOdds
    ) {
        require(_controllingMarket != address(0), "MarketOdds: Invalid controlling market");
        require(_oddsProvider != address(0), "MarketOdds: Invalid odds provider");
        
        controllingMarket = _controllingMarket;
        oddsProvider = _oddsProvider;

        // Set initial values if provided (validation happens in updateOdds if called later)
        homeOdds = _initialHomeOdds;
        awayOdds = _initialAwayOdds;
        homeSpreadPoints = _initialHomeSpreadPoints;
        homeSpreadOdds = _initialHomeSpreadOdds;
        awaySpreadOdds = _initialAwaySpreadOdds;
        totalPoints = _initialTotalPoints;
        overOdds = _initialOverOdds;
        underOdds = _initialUnderOdds;

        // Mark if initial odds were set based on moneyline
        if (_initialHomeOdds >= 1000 && _initialAwayOdds >= 1000) {
             initialOddsSet = true;
        }

        // Emit event if initial odds were set
        if (initialOddsSet) {
             emit OddsUpdated(
                _controllingMarket,
                _initialHomeOdds, 
                _initialAwayOdds, 
                _initialHomeSpreadPoints, 
                _initialHomeSpreadOdds, 
                _initialAwaySpreadOdds, 
                _initialTotalPoints, 
                _initialOverOdds, 
                _initialUnderOdds
            );
        }
    }

    // --- Functions ---

    /**
     * @dev Updates all odds and lines for the market. Only callable by the oddsProvider.
     */
    function updateOdds(
        uint256 _homeOdds, 
        uint256 _awayOdds,
        int256 _homeSpreadPoints, 
        uint256 _homeSpreadOdds, 
        uint256 _awaySpreadOdds, 
        uint256 _totalPoints, 
        uint256 _overOdds, 
        uint256 _underOdds
    ) 
        external 
        onlyOddsProvider 
    {
        // Require NBAMarket to check status, but this might prevent deployment before NBAMarket
        // We'll set marketStarted via a separate function called by NBAMarket.
        // require(NBAMarket(_controllingMarket).marketStatus() != NBAMarket.MarketStatus.STARTED, "MarketOdds: Cannot update odds after market started");
        require(!marketStarted, "MarketOdds: Cannot update odds after market started");

        // Basic validation (more can be added if needed)
        require(_homeOdds >= 1000 && _awayOdds >= 1000, "MarketOdds: ML odds must be >= 1.000");
        require((_homeSpreadOdds == 0 && _awaySpreadOdds == 0) || (_homeSpreadOdds >= 1000 && _awaySpreadOdds >= 1000), "MarketOdds: Spread odds must be >= 1.000 if set");
        require((_overOdds == 0 && _underOdds == 0) || (_overOdds >= 1000 && _underOdds >= 1000), "MarketOdds: Total odds must be >= 1.000 if set");

        homeOdds = _homeOdds;
        awayOdds = _awayOdds;
        homeSpreadPoints = _homeSpreadPoints;
        homeSpreadOdds = _homeSpreadOdds;
        awaySpreadOdds = _awaySpreadOdds;
        totalPoints = _totalPoints;
        overOdds = _overOdds;
        underOdds = _underOdds;

        initialOddsSet = true; // Mark as set once updated
        
        emit OddsUpdated(
            controllingMarket, // Use stored market address
            _homeOdds, 
            _awayOdds, 
            _homeSpreadPoints, 
            _homeSpreadOdds, 
            _awaySpreadOdds, 
            _totalPoints, 
            _overOdds, 
            _underOdds
        );
    }

    /**
     * @dev Sets the marketStarted flag. Only callable by the controlling NBAMarket contract.
     */
    function setMarketStarted() external {
        require(msg.sender == controllingMarket, "MarketOdds: Only the controlling market can call this");
        marketStarted = true;
    }

    /**
     * @dev Sets the controlling market address. Typically called once by the Factory or Market after deployment.
     * This is needed if the MarketOdds is deployed *before* the NBAMarket knows its address.
     */
    function setControllingMarket(address _marketAddress) external {
        // Allow setting only if not set, or if called by the current controlling market (or admin?)
        // For simplicity, let's assume it's called by the factory/deployer initially.
        // A more robust system might involve ownership transfer or roles.
        require(controllingMarket == address(0) || msg.sender == controllingMarket, "MarketOdds: Controlling market already set or unauthorized caller");
        require(_marketAddress != address(0), "MarketOdds: Invalid market address");
        controllingMarket = _marketAddress;
    }

    // --- View Functions ---

    /** @dev Returns Moneyline odds */
    function getMoneylineOdds() external view returns (uint256, uint256) {
        return (homeOdds, awayOdds);
    }

    /** @dev Returns Spread line and odds */
    function getSpreadDetails() external view returns (int256, uint256, uint256) {
        // Returns homeSpreadPoints, homeSpreadOdds, awaySpreadOdds
        return (homeSpreadPoints, homeSpreadOdds, awaySpreadOdds);
    }

    /** @dev Returns Total points line and odds */
    function getTotalPointsDetails() external view returns (uint256, uint256, uint256) {
        // Returns totalPoints, overOdds, underOdds
        return (totalPoints, overOdds, underOdds);
    }

     /** @dev Returns all odds and lines */
    function getFullOdds() 
        external 
        view 
        returns (
            uint256 _homeOdds,
            uint256 _awayOdds,
            int256 _homeSpreadPoints, 
            uint256 _homeSpreadOdds, 
            uint256 _awaySpreadOdds, 
            uint256 _totalPoints, 
            uint256 _overOdds, 
            uint256 _underOdds
        ) 
    {
        return (
            homeOdds, 
            awayOdds, 
            homeSpreadPoints, 
            homeSpreadOdds, 
            awaySpreadOdds, 
            totalPoints, 
            overOdds, 
            underOdds
        );
    }

    /** @dev Changes the designated odds provider address. Only callable by the current odds provider. */
    function changeOddsProvider(address _newOddsProvider) 
        external 
        onlyOddsProvider 
    {
         require(_newOddsProvider != address(0), "MarketOdds: New provider cannot be zero address");
        oddsProvider = _newOddsProvider;
        // Maybe emit an event here?
    }
} 