// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "./LiquidityPool.sol";

/**
 * @title BettingEngine
 * @dev Handles betting operations for NBAMarket contracts
 */
contract BettingEngine is ReentrancyGuard {
    // Token
    IERC20 public usdx;
    LiquidityPool public liquidityPool;
    
    // Parent market
    address public marketAddress;
    
    // Bet tracking
    struct Bet {
        address bettor;
        uint256 amount;
        uint256 potentialWinnings;
        bool onHomeTeam;
        bool settled;
        bool won;
    }
    
    Bet[] public bets;
    mapping(address => uint256[]) public bettorToBets;
    
    // Current financial status
    uint256 public maxExposure;
    uint256 public currentExposure;
    
    // Events
    event BetPlaced(uint256 betId, address bettor, uint256 amount, bool onHomeTeam, uint256 potentialWinnings);
    event BetSettled(uint256 betId, address bettor, bool won, uint256 payout);
    event MarketSettled(uint256 returnedToPool);
    
    // Modifiers
    modifier onlyMarket() {
        require(msg.sender == marketAddress, "Only the market contract can call this function");
        _;
    }
    
    /**
     * @dev Constructor sets up the betting engine
     */
    constructor(
        address _marketAddress,
        address _usdx,
        address _liquidityPool,
        uint256 _maxExposure
    ) {
        marketAddress = _marketAddress;
        usdx = IERC20(_usdx);
        liquidityPool = LiquidityPool(_liquidityPool);
        maxExposure = _maxExposure;
        currentExposure = 0;
    }
    
    /**
     * @dev Places a bet
     */
    function placeBet(address _bettor, uint256 _amount, bool _onHomeTeam, uint256 _odds) 
        external
        onlyMarket
        nonReentrant
        returns (uint256)
    {
        require(_amount > 0, "Bet amount must be greater than 0");
        
        // Calculate potential winnings
        uint256 potentialWinnings = _calculateWinnings(_amount, _odds);
        
        // Check exposure and transfer tokens
        _handleExposureAndTransfer(_bettor, _amount, potentialWinnings);
        
        // Record the bet and return the ID
        return _recordBet(_bettor, _amount, _onHomeTeam, potentialWinnings);
    }
    
    /**
     * @dev Calculate potential winnings based on bet amount and odds
     */
    function _calculateWinnings(uint256 _amount, uint256 _odds) internal pure returns (uint256) {
        return (_amount * _odds) / 1000 - _amount;
    }
    
    /**
     * @dev Handle exposure check and token transfer
     */
    function _handleExposureAndTransfer(address _bettor, uint256 _amount, uint256 _potentialWinnings) internal {
        // Check if the market can cover these potential winnings
        require(currentExposure + _potentialWinnings <= maxExposure, 
                "Market cannot accept this bet size with current exposure");
        
        // Transfer tokens from user to this contract
        require(usdx.transferFrom(_bettor, address(this), _amount), 
                "Token transfer failed");
        
        // Update exposure
        currentExposure += _potentialWinnings;
    }
    
    /**
     * @dev Record the bet in storage and emit event
     */
    function _recordBet(address _bettor, uint256 _amount, bool _onHomeTeam, uint256 _potentialWinnings) internal returns (uint256) {
        // Record the bet
        uint256 betId = bets.length;
        bets.push(Bet({
            bettor: _bettor,
            amount: _amount,
            potentialWinnings: _potentialWinnings,
            onHomeTeam: _onHomeTeam,
            settled: false,
            won: false
        }));
        
        // Track bettor's bets
        bettorToBets[_bettor].push(betId);
        
        emit BetPlaced(betId, _bettor, _amount, _onHomeTeam, _potentialWinnings);
        
        return betId;
    }
    
    /**
     * @dev Settles all bets based on the outcome
     */
    function settleBets(uint8 outcome) 
        external
        onlyMarket
        returns (uint256)
    {
        _settleBetsInternal(outcome);
        
        return _returnRemainingFunds();
    }
    
    /**
     * @dev Internal function to settle individual bets
     */
    function _settleBetsInternal(uint8 outcome) internal {
        for (uint256 i = 0; i < bets.length; i++) {
            _settleBet(i, outcome);
        }
    }
    
    /**
     * @dev Settle a single bet
     */
    function _settleBet(uint256 betId, uint8 outcome) internal {
        Bet storage bet = bets[betId];
        
        if (!bet.settled) {
            bool won = _determineBetOutcome(bet, outcome);
            
            bet.settled = true;
            bet.won = won;
            
            if (won) {
                _processWinningBet(betId, bet);
            } else {
                // Just mark as settled, funds stay with contract
                emit BetSettled(betId, bet.bettor, false, 0);
            }
        }
    }
    
    /**
     * @dev Process a winning bet payout
     */
    function _processWinningBet(uint256 betId, Bet storage bet) internal {
        uint256 payout = bet.amount + bet.potentialWinnings;
        
        // Transfer winnings to bettor
        usdx.transfer(bet.bettor, payout);
        
        emit BetSettled(betId, bet.bettor, true, payout);
    }
    
    /**
     * @dev Return remaining funds to the liquidity pool
     */
    function _returnRemainingFunds() internal returns (uint256) {
        uint256 remainingBalance = usdx.balanceOf(address(this));
        
        if (remainingBalance > 0) {
            usdx.approve(address(liquidityPool), remainingBalance);
            liquidityPool.returnFunds(remainingBalance);
            
            emit MarketSettled(remainingBalance);
        }
        
        return remainingBalance;
    }
    
    /**
     * @dev Determine if a bet has won based on the outcome
     * outcome: 1 = HOME_WIN, 2 = AWAY_WIN
     */
    function _determineBetOutcome(Bet storage bet, uint8 outcome) internal view returns (bool) {
        return (outcome == 1 && bet.onHomeTeam) || 
               (outcome == 2 && !bet.onHomeTeam);
    }
    
    /**
     * @dev Returns a user's bets
     */
    function getBettorBets(address _bettor) 
        external 
        view 
        returns (uint256[] memory) 
    {
        return bettorToBets[_bettor];
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
        require(_betId < bets.length, "Invalid bet ID");
        Bet storage bet = bets[_betId];
        
        return (
            bet.bettor,
            bet.amount,
            bet.potentialWinnings,
            bet.onHomeTeam,
            bet.settled,
            bet.won
        );
    }
    
    /**
     * @dev Update max exposure if needed
     */
    function updateMaxExposure(uint256 _newMaxExposure)
        external
        onlyMarket
    {
        require(_newMaxExposure >= currentExposure, "New max exposure must be >= current exposure");
        maxExposure = _newMaxExposure;
    }
}