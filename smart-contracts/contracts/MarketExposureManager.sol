// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./LiquidityPool.sol";

/**
 * @title MarketExposureManager
 * @dev Manages market-specific exposure limits for betting markets
 */
abstract contract MarketExposureManager {
    // Bet Type Enum - must match BettingEngine.BetType
    enum BetType { MONEYLINE, SPREAD, TOTAL, DRAW }
    
    // Address of parent market - will be set by BettingEngine
    address public marketAddress;
    
    // Global exposure limits
    uint256 public maxExposure;
    uint256 public currentExposure;
    
    // Market-specific exposure limits
    // Home/Away moneyline exposure limits
    uint256 public homeMoneylineMaxExposure;
    uint256 public awayMoneylineMaxExposure;
    uint256 public drawMaxExposure;
    
    // Spread exposure limits
    uint256 public homeSpreadMaxExposure;
    uint256 public awaySpreadMaxExposure;
    
    // Total points exposure limits
    uint256 public overMaxExposure;
    uint256 public underMaxExposure;
    
    // Current market-specific exposures
    uint256 public homeMoneylineCurrentExposure;
    uint256 public awayMoneylineCurrentExposure;
    uint256 public drawCurrentExposure;
    uint256 public homeSpreadCurrentExposure;
    uint256 public awaySpreadCurrentExposure;
    uint256 public overCurrentExposure;
    uint256 public underCurrentExposure;
    
    // Events
    event MarketExposureLimitSet(
        BetType betType,
        bool isBettingOnHomeOrOver,
        uint256 newLimit
    );
    
    // Modifiers
    modifier onlyMarket() {
        require(msg.sender == marketAddress, "Only the market contract can call this function");
        _;
    }
    
    /**
     * @dev Increases the maximum exposure allowed for this market.
     * Should only be callable by the associated LiquidityPool contract when funding.
     */
    function increaseMaxExposure(uint256 _addedAmount) external virtual {
        require(msg.sender == address(liquidityPool()), "Only LiquidityPool can increase exposure");
        maxExposure += _addedAmount;
    }

    /**
     * @dev Decreases the maximum exposure allowed for this market.
     * Represents the Liquidity Pool reducing its backing for this market.
     * Should only be callable by the associated LiquidityPool contract.
     * Note: This only adjusts the accounting limit; actual fund withdrawal happens separately.
     */
    function decreaseMaxExposure(uint256 _removedAmount) external virtual {
        require(msg.sender == address(liquidityPool()), "Only LiquidityPool can decrease exposure");
        uint256 newMaxExposure = maxExposure - _removedAmount; // Relies on Solidity >=0.8 checks for underflow
        require(newMaxExposure >= currentExposure, "Decrease would leave market underfunded");
        maxExposure = newMaxExposure;
    }
    
    /**
     * @dev Sets the maximum exposure for a specific market type and side
     * @param _betType Type of bet (MONEYLINE, SPREAD, TOTAL, DRAW)
     * @param _isBettingOnHomeOrOver True for Home team (ML/Spread) or Over (Total), False for Away or Under
     * @param _newLimit The new exposure limit for this market type/side
     */
    function setMarketExposureLimit(
        BetType _betType,
        bool _isBettingOnHomeOrOver,
        uint256 _newLimit
    )
        external
        onlyMarket
    {
        // Set the appropriate limit based on bet type and side
        if (_betType == BetType.MONEYLINE) {
            if (_isBettingOnHomeOrOver) {
                homeMoneylineMaxExposure = _newLimit;
            } else {
                awayMoneylineMaxExposure = _newLimit;
            }
        } else if (_betType == BetType.DRAW) {
            drawMaxExposure = _newLimit;
        } else if (_betType == BetType.SPREAD) {
            if (_isBettingOnHomeOrOver) {
                homeSpreadMaxExposure = _newLimit;
            } else {
                awaySpreadMaxExposure = _newLimit;
            }
        } else if (_betType == BetType.TOTAL) {
            if (_isBettingOnHomeOrOver) {
                overMaxExposure = _newLimit;
            } else {
                underMaxExposure = _newLimit;
            }
        }
        
        emit MarketExposureLimitSet(_betType, _isBettingOnHomeOrOver, _newLimit);
    }
    
    /**
     * @dev Sets multiple market exposure limits at once
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
    )
        external
        onlyMarket
    {
        homeMoneylineMaxExposure = _homeMoneylineLimit;
        awayMoneylineMaxExposure = _awayMoneylineLimit;
        drawMaxExposure = _drawLimit;
        homeSpreadMaxExposure = _homeSpreadLimit;
        awaySpreadMaxExposure = _awaySpreadLimit;
        overMaxExposure = _overLimit;
        underMaxExposure = _underLimit;
        
        emit MarketExposureLimitSet(BetType.MONEYLINE, true, _homeMoneylineLimit);
        emit MarketExposureLimitSet(BetType.MONEYLINE, false, _awayMoneylineLimit);
        emit MarketExposureLimitSet(BetType.DRAW, false, _drawLimit);
        emit MarketExposureLimitSet(BetType.SPREAD, true, _homeSpreadLimit);
        emit MarketExposureLimitSet(BetType.SPREAD, false, _awaySpreadLimit);
        emit MarketExposureLimitSet(BetType.TOTAL, true, _overLimit);
        emit MarketExposureLimitSet(BetType.TOTAL, false, _underLimit);
    }
    
    /**
     * @dev Admin function to update max exposure (can be called via Market contract)
     */
    function updateMaxExposure(uint256 _newMaxExposure)
        external
        onlyMarket
    {
        require(_newMaxExposure >= currentExposure, "New max exposure cannot be less than current exposure");
        maxExposure = _newMaxExposure;
    }
    
    /**
     * @dev Check if a bet can be placed given the market-specific exposure limits
     */
    function _checkMarketExposureLimits(
        BetType _betType,
        bool _isBettingOnHomeOrOver,
        uint256 _potentialWinnings
    ) internal view returns (bool) {
        // Check global exposure limit
        if (currentExposure + _potentialWinnings > maxExposure) {
            return false;
        }
        
        // Check market-specific exposure limit
        if (_betType == BetType.MONEYLINE) {
            if (_isBettingOnHomeOrOver) {
                return homeMoneylineMaxExposure == 0 || // 0 means no specific limit
                       homeMoneylineCurrentExposure + _potentialWinnings <= homeMoneylineMaxExposure;
            } else {
                return awayMoneylineMaxExposure == 0 || // 0 means no specific limit
                       awayMoneylineCurrentExposure + _potentialWinnings <= awayMoneylineMaxExposure;
            }
        } else if (_betType == BetType.DRAW) {
            return drawMaxExposure == 0 || // 0 means no specific limit
                   drawCurrentExposure + _potentialWinnings <= drawMaxExposure;
        } else if (_betType == BetType.SPREAD) {
            if (_isBettingOnHomeOrOver) {
                return homeSpreadMaxExposure == 0 || // 0 means no specific limit
                       homeSpreadCurrentExposure + _potentialWinnings <= homeSpreadMaxExposure;
            } else {
                return awaySpreadMaxExposure == 0 || // 0 means no specific limit
                       awaySpreadCurrentExposure + _potentialWinnings <= awaySpreadMaxExposure;
            }
        } else if (_betType == BetType.TOTAL) {
            if (_isBettingOnHomeOrOver) {
                return overMaxExposure == 0 || // 0 means no specific limit
                       overCurrentExposure + _potentialWinnings <= overMaxExposure;
            } else {
                return underMaxExposure == 0 || // 0 means no specific limit
                       underCurrentExposure + _potentialWinnings <= underMaxExposure;
            }
        }
        
        return false; // Should never get here
    }
    
    /**
     * @dev Update market-specific exposure when a bet is placed
     */
    function _updateMarketExposureForBet(
        BetType _betType,
        bool _isBettingOnHomeOrOver,
        uint256 _potentialWinnings
    ) internal {
        // Update global exposure
        currentExposure += _potentialWinnings;
        
        // Update market-specific exposure
        if (_betType == BetType.MONEYLINE) {
            if (_isBettingOnHomeOrOver) {
                homeMoneylineCurrentExposure += _potentialWinnings;
            } else {
                awayMoneylineCurrentExposure += _potentialWinnings;
            }
        } else if (_betType == BetType.DRAW) {
            drawCurrentExposure += _potentialWinnings;
        } else if (_betType == BetType.SPREAD) {
            if (_isBettingOnHomeOrOver) {
                homeSpreadCurrentExposure += _potentialWinnings;
            } else {
                awaySpreadCurrentExposure += _potentialWinnings;
            }
        } else if (_betType == BetType.TOTAL) {
            if (_isBettingOnHomeOrOver) {
                overCurrentExposure += _potentialWinnings;
            } else {
                underCurrentExposure += _potentialWinnings;
            }
        }
    }
    
    /**
     * @dev Update market-specific exposure when a bet is lost/settled
     */
    function _reduceMarketExposureForLostBet(
        BetType _betType,
        bool _isBettingOnHomeOrOver,
        uint256 _potentialWinnings
    ) internal {
        // Reduce global exposure
        currentExposure -= _potentialWinnings;
        
        // Reduce market-specific exposure
        if (_betType == BetType.MONEYLINE) {
            if (_isBettingOnHomeOrOver) {
                homeMoneylineCurrentExposure -= _potentialWinnings;
            } else {
                awayMoneylineCurrentExposure -= _potentialWinnings;
            }
        } else if (_betType == BetType.DRAW) {
            drawCurrentExposure -= _potentialWinnings;
        } else if (_betType == BetType.SPREAD) {
            if (_isBettingOnHomeOrOver) {
                homeSpreadCurrentExposure -= _potentialWinnings;
            } else {
                awaySpreadCurrentExposure -= _potentialWinnings;
            }
        } else if (_betType == BetType.TOTAL) {
            if (_isBettingOnHomeOrOver) {
                overCurrentExposure -= _potentialWinnings;
            } else {
                underCurrentExposure -= _potentialWinnings;
            }
        }
    }
    
    /**
     * @dev Reset all market-specific exposures
     */
    function _resetAllMarketExposures() internal {
        // Reset all market-specific current exposures
        homeMoneylineCurrentExposure = 0;
        awayMoneylineCurrentExposure = 0; 
        drawCurrentExposure = 0;
        homeSpreadCurrentExposure = 0;
        awaySpreadCurrentExposure = 0;
        overCurrentExposure = 0;
        underCurrentExposure = 0;
        
        // Reset global exposure
        currentExposure = 0;
    }
    
    /**
     * @dev Returns moneyline market exposure limits and current exposures
     */
    function getMoneylineExposure() 
        external 
        view 
        returns (
            uint256 homeMaxExposure, 
            uint256 homeCurrentExposure,
            uint256 awayMaxExposure, 
            uint256 awayCurrentExposure,
            uint256 drawMax,
            uint256 drawCurrent
        ) 
    {
        return (
            homeMoneylineMaxExposure,
            homeMoneylineCurrentExposure,
            awayMoneylineMaxExposure,
            awayMoneylineCurrentExposure,
            drawMaxExposure,
            drawCurrentExposure
        );
    }
    
    /**
     * @dev Returns spread market exposure limits and current exposures
     */
    function getSpreadExposure() 
        external 
        view 
        returns (
            uint256 homeMaxExposure, 
            uint256 homeCurrentExposure,
            uint256 awayMaxExposure, 
            uint256 awayCurrentExposure
        ) 
    {
        return (
            homeSpreadMaxExposure,
            homeSpreadCurrentExposure,
            awaySpreadMaxExposure,
            awaySpreadCurrentExposure
        );
    }
    
    /**
     * @dev Returns total points market exposure limits and current exposures
     */
    function getTotalExposure() 
        external 
        view 
        returns (
            uint256 overMax, 
            uint256 overCurrent,
            uint256 underMax, 
            uint256 underCurrent
        ) 
    {
        return (
            overMaxExposure,
            overCurrentExposure,
            underMaxExposure,
            underCurrentExposure
        );
    }
    
    /**
     * @dev Returns market exposure for a specific market type and side
     */
    function getMarketExposure(
        BetType _betType,
        bool _isBettingOnHomeOrOver
    ) 
        external 
        view 
        returns (uint256 maxLimit, uint256 currentAmount) 
    {
        if (_betType == BetType.MONEYLINE) {
            if (_isBettingOnHomeOrOver) {
                return (homeMoneylineMaxExposure, homeMoneylineCurrentExposure);
            } else {
                return (awayMoneylineMaxExposure, awayMoneylineCurrentExposure);
            }
        } else if (_betType == BetType.DRAW) {
            return (drawMaxExposure, drawCurrentExposure);
        } else if (_betType == BetType.SPREAD) {
            if (_isBettingOnHomeOrOver) {
                return (homeSpreadMaxExposure, homeSpreadCurrentExposure);
            } else {
                return (awaySpreadMaxExposure, awaySpreadCurrentExposure);
            }
        } else if (_betType == BetType.TOTAL) {
            if (_isBettingOnHomeOrOver) {
                return (overMaxExposure, overCurrentExposure);
            } else {
                return (underMaxExposure, underCurrentExposure);
            }
        }
        
        // Default fallback - should never be reached
        return (0, 0);
    }
    
    // Abstract function to get liquidity pool reference
    function liquidityPool() internal view virtual returns (LiquidityPool);
}