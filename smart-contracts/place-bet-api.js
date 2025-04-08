// Place bet (USER DIRECT METHOD)
app.post('/api/market/:address/place-bet', async (req, res) => {
  try {
    const { address } = req.params;
    const { amount, onHomeTeam, bettor } = req.body;
    
    if (!amount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0) {
      return res.status(400).json({ error: 'Valid amount is required (must be a positive number)' });
    }
    
    if (onHomeTeam === undefined) {
      return res.status(400).json({ error: 'onHomeTeam (true/false) parameter is required' });
    }
    
    if (!bettor) {
      return res.status(400).json({ error: 'bettor address is required' });
    }
    
    console.log("=== STARTING USER BET PLACEMENT ===");
    console.log("Market address:", address);
    console.log("Bettor:", bettor);
    console.log("Amount:", amount);
    console.log("On home team:", onHomeTeam);
    
    const provider = setupProvider();
    
    // Find the correct wallet for this address
    let wallet;
    
    // MUST MATCH EXACTLY - use checksum addresses for comparison
    const checkSummedBettor = ethers.utils.getAddress(bettor);
    console.log("Checksummed bettor address:", checkSummedBettor);
    
    if (checkSummedBettor === '0x70997970C51812dc3A010C7d01b50e0d17dc79C8') {
      wallet = getRoleSigner('oddsProvider', provider);
      console.log("Using oddsProvider wallet (account 1)");
    } else if (checkSummedBettor === '0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC') {
      wallet = getRoleSigner('resultsProvider', provider);
      console.log("Using resultsProvider wallet (account 2)");
    } else if (checkSummedBettor === '0x90F79bf6EB2c4f870365E785982E1f101E93b906') {
      wallet = getRoleSigner('user1', provider);
      console.log("Using user1 wallet (account 3)");
    } else if (checkSummedBettor === '0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65') {
      wallet = getRoleSigner('user2', provider);
      console.log("Using user2 wallet (account 4)");
    } else {
      console.error(`No wallet available for address ${bettor}`);
      return res.status(400).json({
        error: "Unknown bettor address",
        details: `No wallet available for ${bettor}. Please use one of the test wallets.`
      });
    }
    
    // Confirm wallet address matches bettor
    if (wallet.address.toLowerCase() !== bettor.toLowerCase()) {
      console.error(`Wallet address ${wallet.address} doesn't match bettor ${bettor}`);
      return res.status(400).json({
        error: "Wallet mismatch",
        details: `The wallet address (${wallet.address}) doesn't match the bettor address (${bettor}).`
      });
    }
    
    console.log(`Using wallet with address ${wallet.address}`);
    
    // Convert amount to tokens
    const amountInTokens = ethers.utils.parseUnits(amount.toString(), 6);
    
    // Connect to the market contract with the correct wallet
    const market = new ethers.Contract(address, NBAMarketJson.abi, wallet);
    
    // First validate betting conditions
    try {
      const isReadyForBetting = await market.isReadyForBetting();
      if (\!isReadyForBetting) {
        return res.status(400).json({
          error: "Market not ready for betting",
          details: "The market may not have odds set or the game might have already started or ended."
        });
      }
      
      // Get USDX details
      const usdxAddress = await market.usdx();
      console.log("USDX token address:", usdxAddress);
      
      // Connect to USDX contract with user wallet
      const usdx = new ethers.Contract(usdxAddress, USDXJson.abi, wallet);
      
      // Check user's balance
      const balance = await usdx.balanceOf(wallet.address);
      console.log("User USDX balance:", ethers.utils.formatUnits(balance, 6));
      
      if (balance.lt(amountInTokens)) {
        console.log("Insufficient balance, trying to top up...");
        
        // Try to mint or transfer tokens to user
        try {
          // Get admin wallet
          const adminWallet = getDefaultWallet(provider);
          const usdxAdmin = usdx.connect(adminWallet);
          
          // Try minting first
          try {
            console.log("Attempting to mint tokens to user...");
            const mintTx = await usdxAdmin.mint(wallet.address, amountInTokens.mul(10));
            await mintTx.wait();
            console.log("Successfully minted tokens to user");
          } catch (mintError) {
            console.log("Minting failed, trying transfer instead:", mintError.message);
            
            // Check admin balance
            const adminBalance = await usdx.balanceOf(adminWallet.address);
            
            if (adminBalance.lt(amountInTokens)) {
              return res.status(400).json({
                error: "Insufficient tokens",
                details: "Neither user nor admin has enough tokens for this bet."
              });
            }
            
            // Transfer tokens to user
            const transferTx = await usdxAdmin.transfer(wallet.address, amountInTokens.mul(10));
            await transferTx.wait();
            console.log("Successfully transferred tokens to user");
          }
          
          // Recheck balance
          const newBalance = await usdx.balanceOf(wallet.address);
          console.log("New user balance:", ethers.utils.formatUnits(newBalance, 6));
          
          if (newBalance.lt(amountInTokens)) {
            return res.status(400).json({
              error: "Insufficient balance",
              details: "Failed to provide enough tokens to the user."
            });
          }
        } catch (topUpError) {
          console.error("Error topping up user balance:", topUpError);
          return res.status(500).json({
            error: "Token transfer failed",
            details: topUpError.message
          });
        }
      }
      
      // Check allowance
      const allowance = await usdx.allowance(wallet.address, address);
      console.log("Current allowance:", ethers.utils.formatUnits(allowance, 6));
      
      // If allowance is too low, approve market to spend tokens
      if (allowance.lt(amountInTokens)) {
        console.log("Insufficient allowance, approving market...");
        
        try {
          // Set unlimited approval for simplicity in testing
          const approveTx = await usdx.approve(address, ethers.constants.MaxUint256);
          await approveTx.wait();
          console.log("Approved market to spend tokens");
        } catch (approveError) {
          console.error("Error approving market:", approveError);
          return res.status(500).json({
            error: "Approval failed",
            details: approveError.message
          });
        }
      }
      
      // Now place the bet
      console.log("Placing bet with parameters:", {
        amount: amountInTokens.toString(),
        onHomeTeam: onHomeTeam
      });
      
      let receipt;
      try {
        const tx = await market.placeBet(amountInTokens, onHomeTeam, {
          gasLimit: 1000000 // Explicit gas limit to avoid estimation issues
        });
        console.log("Transaction submitted:", tx.hash);
        
        receipt = await tx.wait();
        console.log("Transaction confirmed in block:", receipt.blockNumber);
      } catch (betError) {
        console.error("Error placing bet:", betError);
        return res.status(500).json({
          error: "Bet placement failed",
          details: betError.message
        });
      }
      
      // Successfully placed bet, get the bet ID
      const bettingEngineAddress = await market.bettingEngine();
      const betIds = await market.getBettorBets(wallet.address);
      
      let betId, potentialWinnings;
      
      if (betIds && betIds.length > 0) {
        // Get the most recent bet
        betId = betIds[betIds.length - 1].toString();
        
        // Get bet details to include in response
        const betDetails = await market.getBetDetails(betId);
        potentialWinnings = ethers.utils.formatUnits(betDetails[2], 6);
      }
      
      return res.json({
        success: true,
        bettor: wallet.address,
        betId,
        amount,
        potentialWinnings,
        side: onHomeTeam ? 'home' : 'away',
        transaction: receipt.transactionHash
      });
      
    } catch (error) {
      console.error("Error during bet operations:", error);
      return res.status(500).json({
        error: "Error during bet operations",
        details: error.message
      });
    }
  } catch (error) {
    console.error('Error placing bet:', error);
    res.status(500).json({ 
      error: error.message,
      details: error.toString() 
    });
  }
});
