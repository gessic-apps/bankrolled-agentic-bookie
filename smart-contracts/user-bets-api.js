// Get user bets
app.get('/api/market/:address/bets/:bettor', async (req, res) => {
  try {
    const { address, bettor } = req.params;
    
    const provider = setupProvider();
    const market = new ethers.Contract(address, NBAMarketJson.abi, provider);
    
    console.log(`Getting bets for user ${bettor} in market ${address}...`);
    
    // Get the betting engine
    const bettingEngineAddress = await market.bettingEngine();
    const bettingEngine = new ethers.Contract(bettingEngineAddress, BettingEngineJson.abi, provider);
    
    // Get user's bet IDs
    const betIds = await market.getBettorBets(bettor);
    
    // Get details for each bet
    const betDetails = [];
    for (const betId of betIds) {
      const details = await market.getBetDetails(betId);
      betDetails.push({
        betId: betId.toString(),
        bettor: details[0],
        amount: ethers.utils.formatUnits(details[1], 6),
        potentialWinnings: ethers.utils.formatUnits(details[2], 6),
        onHomeTeam: details[3],
        settled: details[4],
        won: details[5]
      });
    }
    
    res.json(betDetails);
  } catch (error) {
    console.error('Error getting user bets:', error);
    res.status(500).json({ error: error.message });
  }
});
