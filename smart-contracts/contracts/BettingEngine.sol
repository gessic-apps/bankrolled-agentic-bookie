// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "./LiquidityPool.sol";
import "./MarketExposureManager.sol";

/**
 * @title BettingEngine
 * @dev Handles betting operations for NBAMarket contracts
 */
contract BettingEngine is ReentrancyGuard, MarketExposureManager {
    // Token
    IERC20 public usdx;
    LiquidityPool public _liquidityPool;
    
    // Bet tracking
    struct Bet {
        address bettor;
        uint256 amount;         // Amount staked
        uint256 potentialWinnings; // Winnings excluding stake
        BetType betType;        // Type of bet
        bool isBettingOnHomeOrOver; // True for Home (ML/Spread), True for Over (Total)
        int256 line;            // Spread points (e.g., -75 for -7.5) or Total points (e.g., 2105 for 210.5) at time of bet
        uint256 odds;           // Odds (e.g., 1910 for 1.91) at time of bet
        bool settled;
        bool won;
    }
    
    Bet[] public bets;
    mapping(address => uint256[]) public bettorToBets;
    
    // Events
    event BetPlaced(
        uint256 indexed betId, 
        address indexed bettor, 
        uint256 amount, 
        BetType betType, 
        bool isBettingOnHomeOrOver, 
        int256 line, 
        uint256 odds, 
        uint256 potentialWinnings
    );
    event BetSettled(uint256 indexed betId, address indexed bettor, bool won, uint256 payout);
    event MarketSettled(uint256 returnedToPool);
    event BetsRefunded(uint256 totalRefunded);
    
    // Modifiers - implemented via MarketExposureManager
    
    /**
     * @dev Constructor sets up the betting engine
     */
    constructor(
        address _marketAddress,
        address _usdx,
        address _liquidityPoolAddress,
        uint256 _maxExposure
    ) {
        require(_marketAddress != address(0), "Invalid market address");
        require(_usdx != address(0), "Invalid USDX address");
        require(_liquidityPoolAddress != address(0), "Invalid LiquidityPool address");
        marketAddress = _marketAddress;
        usdx = IERC20(_usdx);
        _liquidityPool = LiquidityPool(_liquidityPoolAddress);
        maxExposure = _maxExposure;
        currentExposure = 0;
    }
    
    /**
     * @dev Implementation of the abstract function from MarketExposureManager
     */
    function liquidityPool() internal view override returns (LiquidityPool) {
        return _liquidityPool;
    }
    
    /**
     * @dev Places a bet - called by NBAMarket
     */
    function placeBet(
        address _bettor, 
        uint256 _amount, 
        BetType _betType, 
        bool _isBettingOnHomeOrOver, 
        uint256 _odds,
        int256 _line
    ) 
        external
        onlyMarket
        nonReentrant
        returns (uint256)
    {
        require(_amount > 0, "Bet amount must be > 0");
        require(_odds >= 1000, "Odds must be >= 1.000"); // Odds passed from market
        
        // Calculate potential winnings (excluding stake)
        uint256 potentialWinnings = _calculateWinnings(_amount, _odds);
        
        // Check exposure limits
        require(_checkMarketExposureLimits(_betType, _isBettingOnHomeOrOver, potentialWinnings),
                "BettingEngine: Market exposure limit exceeded");
        
        // Transfer tokens from bettor
        require(usdx.transferFrom(_bettor, address(this), _amount), 
                "BettingEngine: Token transfer failed. Ensure sufficient balance and allowance.");
        
        // Update market-specific exposure
        _updateMarketExposureForBet(_betType, _isBettingOnHomeOrOver, potentialWinnings);
        
        // Record the bet and return the ID
        return _recordBet(_bettor, _amount, _betType, _isBettingOnHomeOrOver, _line, _odds, potentialWinnings);
    }
    
    /**
     * @dev Calculate potential winnings based on bet amount and odds (winnings = stake * (odds/1000 - 1))
     */
    function _calculateWinnings(uint256 _amount, uint256 _odds) internal pure returns (uint256) {
        // Ensure odds are at least 1000 (1.0) to avoid underflow
        require(_odds >= 1000, "Odds cannot be less than 1.0");
        // Calculate winnings: amount * (odds / 1000) - amount
        // Use intermediate variable to prevent overflow/underflow issues during calculation
        uint256 totalReturn = (_amount * _odds) / 1000;
        return totalReturn - _amount;
    }
    
    
    /**
     * @dev Record the bet in storage and emit event
     */
    function _recordBet(
        address _bettor, 
        uint256 _amount, 
        BetType _betType, 
        bool _isBettingOnHomeOrOver, 
        int256 _line, 
        uint256 _odds, 
        uint256 _potentialWinnings
    ) internal returns (uint256) {
        uint256 betId = bets.length;
        bets.push(Bet({
            bettor: _bettor,
            amount: _amount,
            potentialWinnings: _potentialWinnings,
            betType: _betType,
            isBettingOnHomeOrOver: _isBettingOnHomeOrOver,
            line: _line,
            odds: _odds,
            settled: false,
            won: false
        }));
        
        // Track bettor's bets
        bettorToBets[_bettor].push(betId);
        
        emit BetPlaced(
            betId, 
            _bettor, 
            _amount, 
            _betType, 
            _isBettingOnHomeOrOver, 
            _line, 
            _odds, 
            _potentialWinnings
        );
        
        return betId;
    }
    
    /**
     * @dev Settles all bets based on the final scores - called by NBAMarket
     */
    function settleBets(uint256 homeScore, uint256 awayScore) 
        external
        onlyMarket
        returns (uint256) // Returns amount returned to pool
    {
        _settleBetsInternal(homeScore, awayScore);
        return _returnRemainingFunds();
    }

     /**
     * @dev Cancels all unsettled bets and refunds stakes - called by NBAMarket
     */
    function cancelBetsAndRefund() external onlyMarket returns (uint256) {
        uint256 totalRefunded = 0;
        for (uint256 i = 0; i < bets.length; i++) {
            Bet storage bet = bets[i];
            if (!bet.settled) {
                bet.settled = true; // Mark as settled (cancelled)
                bet.won = false; // Not won
                uint256 refundAmount = bet.amount;
                if (refundAmount > 0) {
                    // Refund the original stake
                    usdx.transfer(bet.bettor, refundAmount); 
                    totalRefunded += refundAmount;
                    
                    // Reduce market-specific exposure
                    _reduceMarketExposureForLostBet(
                        bet.betType,
                        bet.isBettingOnHomeOrOver,
                        bet.potentialWinnings
                    );

                    // Emit settlement event indicating a loss (payout 0) or a new Cancelled event?
                    // Using BetSettled for consistency, payout 0 indicates loss/cancellation refund
                    emit BetSettled(i, bet.bettor, false, 0); 
                }
            }
        }
        emit BetsRefunded(totalRefunded);
        // Any remaining balance should ideally be 0 if all bets were refunded
        // but return any dust to the pool just in case.
        return _returnRemainingFunds(); 
    }


    /**
     * @dev Internal function to settle individual bets based on scores
     */
    function _settleBetsInternal(uint256 homeScore, uint256 awayScore) internal {
        for (uint256 i = 0; i < bets.length; i++) {
            _settleBet(i, homeScore, awayScore);
        }
    }
    
    /**
     * @dev Settle a single bet based on scores
     */
    function _settleBet(uint256 betId, uint256 homeScore, uint256 awayScore) internal {
         // Ensure betId is valid (although loop prevents out-of-bounds)
        require(betId < bets.length, "Invalid bet ID"); 
        Bet storage bet = bets[betId];
        
        if (!bet.settled) {
            bool won = _determineBetOutcome(bet, homeScore, awayScore);
            
            bet.settled = true;
            bet.won = won;
            
            uint256 payout = 0;
            if (won) {
                payout = bet.amount + bet.potentialWinnings;
                // Transfer winnings to bettor
                usdx.transfer(bet.bettor, payout);
                // Exposure was already accounted for; it remains until settlement completes.
                // It represents the max potential payout, which is now realized or lost.
            } else {
                // Bet lost, stake remains with the contract (will be returned to pool).
                // Reduce exposures as this potential payout is no longer needed
                _reduceMarketExposureForLostBet(
                    bet.betType,
                    bet.isBettingOnHomeOrOver,
                    bet.potentialWinnings
                );
            }

             emit BetSettled(betId, bet.bettor, won, payout);
        }
    }

    
    /**
     * @dev Return remaining funds to the liquidity pool after settlement
     */
    function _returnRemainingFunds() internal returns (uint256) {
        uint256 remainingBalance = usdx.balanceOf(address(this));
        
        // After settlement, currentExposure should reflect the total potential payout 
        // for *unsettled* bets. Since all bets are now settled (either paid out or lost), 
        // the remaining balance represents the net profit/loss for the market. 
        // We reset exposure here. Ideally, remainingBalance should cover the final payouts.
        
        // Reset all exposures
        _resetAllMarketExposures();

        if (remainingBalance > 0) {
            // No need to approve if LP pulls, but safer to approve if LP needs it
            // Check LiquidityPool implementation - assuming it needs approval or uses transferFrom
             usdx.approve(address(_liquidityPool), remainingBalance); 
             _liquidityPool.returnFunds(remainingBalance); // LP pulls approved funds

            emit MarketSettled(remainingBalance);
        } else {
             emit MarketSettled(0);
        }
        
        return remainingBalance;
    }
    
    // Exposure management functions now handled by MarketExposureManager

    /**
     * @dev Determine if a bet has won based on the type and outcome scores
     */
    function _determineBetOutcome(Bet storage bet, uint256 homeScore, uint256 awayScore) internal view returns (bool) {
        if (bet.betType == BetType.MONEYLINE) {
            // Home win and bet on home OR Away win and bet on away
            return (homeScore > awayScore && bet.isBettingOnHomeOrOver) || 
                   (awayScore > homeScore && !bet.isBettingOnHomeOrOver);
            // Ties are losses for moneyline bets
        } else if (bet.betType == BetType.DRAW) {
            // Draw bet wins if scores are equal
            return homeScore == awayScore;
        } else if (bet.betType == BetType.SPREAD) {
             // Spread calculation: Score + Spread Points (adjusting for 1 decimal precision)
             // Example: Home -7.5 (line = -75), Score 100-90. Home Bet: 1000 + (-75) = 925. Away score 900. 925 > 900 -> Home Wins.
             // Example: Away +7.5 (line = 75 => bet.line is -75 if betting home, 75 if betting away), Score 100-95. Away Bet: 950 + 75 = 1025. Home score 1000. 1025 > 1000 -> Away Wins.
            
            // Alternate logic: Compare score difference to spread line
            int256 actualSpread = int256(homeScore) - int256(awayScore); // Positive if home wins, negative if away wins
             
            // We stored the line relative to the team bet on. 
            // Let's redefine: bet.line will *always* be the home team's spread (e.g., -75).
            // bet.isBettingOnHomeOrOver determines which side the bettor took.
             
             // Let's re-calculate based on a consistent definition: bet.line is always home spread.
             // We need to pass the *actual* home spread points from the market when placing the bet.
             // Let's assume bet.line IS the home team spread (e.g. -75 for -7.5)
             
             if (bet.isBettingOnHomeOrOver) { // Betting on Home Team (e.g., Home -7.5)
                 // Home wins if (Home Score + Home Spread) > Away Score
                 // Or (Home Score - Away Score) > -Home Spread
                 // Use 1 decimal precision: (Home Score - Away Score) * 10 > -Home Spread Line (bet.line)
                  return (actualSpread * 10) > (-bet.line); // e.g. (100-90)*10 = 100. -bet.line = -(-75) = 75. 100 > 75 -> WIN
             } else { // Betting on Away Team (e.g., Away +7.5, means home spread is -7.5)
                 // Away wins if (Away Score + Away Spread) > Home Score
                 // Where Away Spread = -Home Spread (bet.line)
                 // Or (Home Score - Away Score) < -Home Spread (bet.line)
                  return (actualSpread * 10) < (-bet.line); // e.g. (100-95)*10 = 50. -bet.line = -(-75)=75. 50 < 75 -> WIN
             }
            // Note: A push (tie on the spread) results in a loss for the bettor here. Need PUSH handling? For now, push is loss.

        } else if (bet.betType == BetType.TOTAL) {
            uint256 totalScore = homeScore + awayScore;
            uint256 totalLine = uint256(bet.line); // Total line stored with 1 decimal (e.g., 2105 for 210.5)

            if (bet.isBettingOnHomeOrOver) { // Betting on Over
                return totalScore * 10 > totalLine;
            } else { // Betting on Under
                return totalScore * 10 < totalLine;
            }
             // Note: A push (score equals total line) results in a loss for the bettor here. Need PUSH handling? For now, push is loss.
        }
        return false; // Should not happen with valid BetType
    }
    
    // --- View Functions ---

    function getBettorBets(address _bettor) 
        external 
        view 
        returns (uint256[] memory) 
    {
        return bettorToBets[_bettor];
    }
    
    /**
     * @dev Returns bet details including type and line
     */
    function getBetDetails(uint256 _betId) 
        external 
        view 
        returns (
            address bettor, 
            uint256 amount, 
            uint256 potentialWinnings, 
            BetType betType,
            bool isBettingOnHomeOrOver,
            int256 line, // Spread or Total points line for the bet
            uint256 odds,
            bool settled, 
            bool won
        ) 
    {
        require(_betId < bets.length, "Invalid bet ID");
        Bet storage bet = bets[_betId];
        
        return (
            bet.bettor,
            bet.amount,
            bet.potentialWinnings,
            bet.betType,
            bet.isBettingOnHomeOrOver,
            bet.line,
            bet.odds,
            bet.settled,
            bet.won
        );
    }
    
    // Exposure getters now handled by MarketExposureManager

    // Exposure management functions now handled by MarketExposureManager
}