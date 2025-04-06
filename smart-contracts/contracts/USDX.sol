// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title USDX Token
 * @dev ERC20 Token for the autonomous sportsbook with 1M initial supply
 */
contract USDX is ERC20, Ownable {
    uint8 private constant _decimals = 6;
    uint256 private constant _initialSupply = 1_000_000 * 10**6; // 1M tokens with 6 decimals

    constructor() ERC20("USD Stable Token X", "USDX") {
        _transferOwnership(msg.sender);
        _mint(msg.sender, _initialSupply);
    }

    function decimals() public pure override returns (uint8) {
        return _decimals;
    }
    
    /**
     * @dev Mints new tokens and assigns them to the specified account
     * @param to The account to receive the minted tokens
     * @param amount The amount of tokens to mint
     */
    function mint(address to, uint256 amount) public onlyOwner {
        _mint(to, amount);
    }
}