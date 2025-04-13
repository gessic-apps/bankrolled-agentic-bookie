// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "./NBAMarket.sol";
import "./BettingEngine.sol";
import "hardhat/console.sol";

/**
 * @title LiquidityPool
 * @dev Manages funds for the sportsbook markets
 */
contract LiquidityPool is Ownable, ReentrancyGuard {
    IERC20 public usdx;
    address public marketFactory;
    
    // Maps market address to whether it's authorized
    mapping(address => bool) public authorizedMarkets;
    
    // Events
    event MarketFunded(address indexed market, uint256 amount);
    event FundsReturned(address indexed market, uint256 amount);
    event MarketAuthorized(address indexed market);
    event MarketDeauthorized(address indexed market);
    
    constructor(address _usdx) {
        _transferOwnership(msg.sender);
        usdx = IERC20(_usdx);
    }
    
    /**
     * @dev Sets the market factory address
     */
    function setMarketFactory(address _marketFactory) external onlyOwner {
        marketFactory = _marketFactory;
    }
    
    /**
     * @dev Authorizes a market to receive funds
     */
    function authorizeMarket(address _market) external {
        // Only owner or market factory can authorize markets
        require(msg.sender == owner() || msg.sender == marketFactory, 
                "Only owner or market factory can authorize");
        authorizedMarkets[_market] = true;
        emit MarketAuthorized(_market);
    }
    
    /**
     * @dev Deauthorizes a market
     */
    function deauthorizeMarket(address _market) external onlyOwner {
        authorizedMarkets[_market] = false;
        emit MarketDeauthorized(_market);
    }
    
    /**
     * @dev Funds a market with USDX tokens
     */
    function fundMarket(address _market, uint256 _amount) external nonReentrant {
        // Only owner or market factory can fund markets
        require(msg.sender == owner() || msg.sender == marketFactory, 
                "Only owner or market factory can fund markets");
        require(authorizedMarkets[_market], "Market not authorized");
        
        // Transfer tokens to the market
        require(usdx.transfer(_market, _amount), "Token transfer failed");
        
        // Notify the Betting Engine (assuming _market is the BettingEngine address)
        try BettingEngine(_market).increaseMaxExposure(_amount) {
            // Success
        } catch (bytes memory reason) {
            // Handle potential error if the target contract isn't a BettingEngine or call fails
            // For now, we just proceed, but logging or reverting might be needed in production
            console.log("Failed to call increaseMaxExposure on BettingEngine:");
            // Revert? Or just log? Depends on requirements.
            // revert("Failed to update BettingEngine exposure");
        }

        emit MarketFunded(_market, _amount);
    }
    
    /**
     * @dev Reduces the maximum exposure limit for a market in its BettingEngine.
     * This only adjusts the accounting limit within the BettingEngine; it does not
     * directly withdraw funds from the BettingEngine back to the pool.
     * Can only be called by the owner.
     * @param _bettingEngineAddress The address of the BettingEngine contract for the market.
     * @param _amount The amount by which to decrease the maximum exposure.
     */
    function reduceMarketFunding(address _bettingEngineAddress, uint256 _amount) external onlyOwner nonReentrant {
        require(authorizedMarkets[_bettingEngineAddress], "LiquidityPool: Market (BettingEngine) not authorized");
        
        try BettingEngine(_bettingEngineAddress).decreaseMaxExposure(_amount) {
            // Success - emit event maybe? Event MarketExposureReduced?
        } catch (bytes memory reason) {
            // Log or revert based on requirements if the call fails 
            // (e.g., tried to reduce below current exposure)
            console.log("Failed to call decreaseMaxExposure on BettingEngine:");
            // Reverting might be safer to signal the operation failed clearly.
            revert("LiquidityPool: Failed to decrease BettingEngine exposure");
        }
        
        // Emit an event if needed
        // emit MarketExposureReduced(_bettingEngineAddress, _amount);
    }
    
    /**
     * @dev Returns funds from a market to the liquidity pool
     * Can only be called by the market itself (when settling)
     */
    function returnFunds(uint256 _amount) external nonReentrant {
        require(authorizedMarkets[msg.sender], "Only authorized markets can return funds");
        
        // Transfer tokens from the market back to the pool
        require(usdx.transferFrom(msg.sender, address(this), _amount), 
                "Token transfer from market failed");
        
        emit FundsReturned(msg.sender, _amount);
    }
    
    /**
     * @dev Returns the current balance of USDX in the liquidity pool
     */
    function getBalance() external view returns (uint256) {
        return usdx.balanceOf(address(this));
    }
    
    /**
     * @dev Allows the owner to withdraw tokens in case of emergency
     */
    function emergencyWithdraw(uint256 _amount) external onlyOwner {
        require(usdx.transfer(owner(), _amount), "Token transfer failed");
    }
}