const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const { ethers } = require('ethers');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

// Import wallet helpers
const { 
  getDefaultWallet, 
  getRoleSigner, 
  signAndSendTransaction, 
  setupProvider 
} = require('./utils/wallet-helper');

// Initialize express app
const app = express();
const PORT = process.env.PORT || 3002;

// Middleware
app.use(cors({ origin: '*' }));
app.use(bodyParser.json());
app.use(express.static('public'));

// Store deployed contract addresses
let deployedContracts = {
  marketFactory: null,
  usdx: null,
  liquidityPool: null,
  markets: []
};

// Load contract artifacts
const MarketFactoryJson = require('./artifacts/contracts/MarketFactory.sol/MarketFactory.json');
const NBAMarketJson = require('./artifacts/contracts/NBAMarket.sol/NBAMarket.json');
const LiquidityPoolJson = require('./artifacts/contracts/LiquidityPool.sol/LiquidityPool.json');
const USDXJson = require('./artifacts/contracts/USDX.sol/USDX.json');
const BettingEngineJson = require('./artifacts/contracts/BettingEngine.sol/BettingEngine.json');
const MarketOddsJson = require('./artifacts/contracts/MarketOdds.sol/MarketOdds.json');

// Note: setupProvider and wallet management functions are now imported from wallet-helper.js

// Save deployed contracts to a file for persistence
const saveDeployedContracts = () => {
  const dataPath = path.join(__dirname, 'deployed-contracts.json');
  fs.writeFileSync(dataPath, JSON.stringify(deployedContracts, null, 2));
};

// Load previously deployed contracts
const loadDeployedContracts = () => {
  const dataPath = path.join(__dirname, 'deployed-contracts.json');
  if (fs.existsSync(dataPath)) {
    try {
      deployedContracts = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
      // Ensure the markets array exists
      if (!deployedContracts.markets) {
        deployedContracts.markets = [];
      }
      console.log('Loaded previously deployed contracts');
    } catch (error) {
      console.error('Error loading deployed contracts:', error);
    }
  }
};

// API Routes

// Get all deployed contracts
app.get('/api/contracts', (req, res) => {
  res.json(deployedContracts);
});

// Deploy MarketFactory
app.post('/api/deploy/factory', async (req, res) => {
  try {
    const { oddsProviderAddress, resultsProviderAddress, usdxAddress, liquidityPoolAddress } = req.body;
    
    if (!oddsProviderAddress || !resultsProviderAddress) {
      return res.status(400).json({ error: 'oddsProviderAddress and resultsProviderAddress are required' });
    }
    
    if (!usdxAddress || !liquidityPoolAddress) {
      return res.status(400).json({ error: 'usdxAddress and liquidityPoolAddress are required' });
    }
    
    const provider = setupProvider();
    const wallet = await getDefaultWallet(provider);
    
    const MarketFactory = new ethers.ContractFactory(
      MarketFactoryJson.abi, 
      MarketFactoryJson.bytecode, 
      wallet
    );
    
    console.log('Deploying MarketFactory...', wallet);
    const marketFactory = await MarketFactory.deploy(
      "0xdc63788Ada727255db07819632488d2629139CE8", 
      "0xdc63788Ada727255db07819632488d2629139CE8",
      usdxAddress,
      liquidityPoolAddress
    );
    await marketFactory.deployed();
    
    deployedContracts.marketFactory = {
      address: marketFactory.address,
      oddsProvider: oddsProviderAddress,
      resultsProvider: resultsProviderAddress,
      usdx: usdxAddress,
      liquidityPool: liquidityPoolAddress,
      deployedAt: new Date().toISOString()
    };
    
    // Set the market factory in the liquidity pool
    console.log("Setting MarketFactory in LiquidityPool...");
    const LiquidityPool = new ethers.Contract(
      liquidityPoolAddress, 
      LiquidityPoolJson.abi, 
      wallet
    );
    
    const tx = await LiquidityPool.setMarketFactory(marketFactory.address);
    await tx.wait();
    console.log("LiquidityPool updated with MarketFactory address");
    
    saveDeployedContracts();
    
    console.log(`MarketFactory deployed to: ${marketFactory.address}`);
    res.json({ 
      success: true, 
      address: marketFactory.address,
      transaction: marketFactory.deployTransaction.hash
    });
  } catch (error) {
    console.error('Error deploying MarketFactory:', error);
    res.status(500).json({ error: error.message });
  }
});

// Create a new market
app.post('/api/market/create', async (req, res) => {
  try {
    console.log("Request body:", req.body);
    const {
      homeTeam, awayTeam, gameTimestamp, oddsApiId, 
      homeOdds, awayOdds, 
      homeSpreadPoints, homeSpreadOdds, awaySpreadOdds,
      totalPoints, overOdds, underOdds,
      marketFunding 
    } = req.body;
    
    console.log("DeployedContracts:", deployedContracts);
    
    if (!deployedContracts.marketFactory) {
      return res.status(400).json({ error: 'MarketFactory not deployed yet' });
    }
    
    if (!homeTeam || !awayTeam || !gameTimestamp || !oddsApiId) {
      return res.status(400).json({ error: 'homeTeam, awayTeam, gameTimestamp, and oddsApiId are required' });
    }
    
    const provider = setupProvider();
    const adminSigner = await getRoleSigner('admin', provider); // Get signer explicitly

    // Get the factory address - handle both string and object formats
    let factoryAddress;
    if (typeof deployedContracts.marketFactory === 'string') {
      factoryAddress = deployedContracts.marketFactory;
    } else if (deployedContracts.marketFactory && deployedContracts.marketFactory.address) {
      factoryAddress = deployedContracts.marketFactory.address;
    } else {
      console.error("Invalid marketFactory structure:", deployedContracts.marketFactory);
    }
    
    if (!factoryAddress) {
      return res.status(400).json({ error: 'Invalid MarketFactory address' });
    }
    
    console.log('Creating market with factory at:', factoryAddress);
    let result;
    
    // Convert funding to wei representation if provided
    const fundingAmount = marketFunding ? ethers.utils.parseUnits(marketFunding.toString(), 6) : 0;
    
    // Make sure odds/lines are numbers, defaulting to 0
    const params = [
      homeTeam, 
      awayTeam, 
      parseInt(gameTimestamp), 
      oddsApiId, 
      homeOdds !== undefined ? parseInt(homeOdds) : 0,
      awayOdds !== undefined ? parseInt(awayOdds) : 0,
      homeSpreadPoints !== undefined ? parseInt(homeSpreadPoints) : 0,
      homeSpreadOdds !== undefined ? parseInt(homeSpreadOdds) : 0,
      awaySpreadOdds !== undefined ? parseInt(awaySpreadOdds) : 0,
      totalPoints !== undefined ? parseInt(totalPoints) : 0,
      overOdds !== undefined ? parseInt(overOdds) : 0,
      underOdds !== undefined ? parseInt(underOdds) : 0,
      fundingAmount
    ];

    console.log("Processed parameters for createMarket:", params);
    
    // Always use createMarket, passing 0 for unspecified odds/lines
    result = await signAndSendTransaction({
      contractAddress: factoryAddress,
      contractAbi: MarketFactoryJson.abi,
      method: 'createMarket',
      params: params,
      signer: adminSigner // Pass the explicit signer
    }, provider);

    if (!result.success) {
      // If signAndSendTransaction failed (error during estimation, sending, or waiting), throw the error
      console.error("signAndSendTransaction failed:", result.error);
      throw new Error(result.error);
    }

    // At this point, signAndSendTransaction succeeded in sending AND waiting for the tx.
    // However, the transaction might have *reverted* (status 0).
    // Let's fetch the full receipt again now to get the logs, handling potential null.
    
    console.log(`Fetching full receipt for confirmed tx: ${result.transaction}...`);
    const receipt = await provider.getTransactionReceipt(result.transaction);

    // --- Check if the receipt was found and if the transaction reverted ---
    if (!receipt) {
        // This case is less likely if tx.wait() succeeded, but possible with node issues
        console.error(`Failed to fetch receipt for transaction: ${result.transaction}. Transaction might not be mined or node is out of sync.`);
        throw new Error(`Failed to fetch receipt for transaction ${result.transaction}.`);
    }

    if (receipt.status === 0) {
      console.error(`Transaction reverted (status 0): ${result.transaction}`);
      // Optional: Try to get revert reason (might not always work)
      try {
          const tx = await provider.getTransaction(result.transaction);
          if (tx) { // Ensure tx exists before calling provider.call
             await provider.call(tx, tx.blockNumber); // This might throw with the reason
          } else {
             console.error("Could not fetch transaction details to check revert reason.");
          }
      } catch (err) {
          // This error often contains the revert reason
          console.error("Revert reason check error:", err);
          throw new Error(`Transaction reverted. Reason: ${err.reason || err.message || 'Unknown'}`);
      }
      // Fallback error if provider.call didn't throw a useful reason
      throw new Error('Transaction reverted. Check contract logic, parameters, and potential revert reasons.');
    }
    // --- End revert check ---

    // Transaction was successful (status 1), now parse the logs from the fetched receipt
    console.log("Transaction successful (status 1), parsing logs...");
    const marketFactoryInterface = new ethers.utils.Interface(MarketFactoryJson.abi);
    // Corrected event signature: address, address, string, string, uint256, string, uint256
    const correctEventSignature = "MarketCreated(address,address,string,string,uint256,string,uint256)";
    const marketCreatedEventTopic = ethers.utils.id(correctEventSignature);
    
    // ---- START ADDED DEBUG LOGGING ----
    console.log("DEBUG: Searching for MarketCreated event in receipt for tx:", result.transaction);
    console.log("DEBUG: Expected Factory Address:", factoryAddress.toLowerCase());
    console.log("DEBUG: Expected Event Topic:", marketCreatedEventTopic);
    console.log("DEBUG: Full Receipt Logs:", JSON.stringify(receipt.logs, (key, value) => 
        typeof value === 'bigint' ? value.toString() : // Convert BigInts to strings for JSON
        value, 2)); // Pretty print JSON
    // ---- END ADDED DEBUG LOGGING ----

    // Find the MarketCreated event using the correct topic
    const marketEventLog = receipt.logs.find(log => 
      log.topics[0] === marketCreatedEventTopic && log.address.toLowerCase() === factoryAddress.toLowerCase()
    );
    
    if (!marketEventLog) {
      console.warn("Could not find MarketCreated event in transaction logs for factory", factoryAddress, "Topic:", marketCreatedEventTopic);
      // Attempt to fallback by checking the deployedMarkets array length change if needed, but error is safer
      throw new Error('Could not reliably find MarketCreated event');
    }
    
    // Decode event data
    const eventData = marketFactoryInterface.parseLog(marketEventLog);
    const marketAddress = eventData.args.marketAddress;
    
    // Store market details
    const marketInfo = {
      address: marketAddress,
      homeTeam: eventData.args.homeTeam,
      awayTeam: eventData.args.awayTeam,
      gameTimestamp: eventData.args.gameTimestamp.toNumber(),
      oddsApiId: eventData.args.oddsApiId,
      funding: ethers.utils.formatUnits(eventData.args.funding, 6),
      transaction: result.transaction,
      createdAt: new Date().toISOString()
    };
    
    deployedContracts.markets.push(marketInfo);
    saveDeployedContracts();
    
    console.log(`Market created at: ${marketAddress}`);
    res.json({ 
      success: true, 
      market: marketInfo,
      transaction: result.transaction
    });
  } catch (error) {
    console.error('Error creating market:', error);
    res.status(500).json({ error: error.message });
  }
});

// Update odds for a market
app.post('/api/market/:address/update-odds', async (req, res) => {
  try {
    const { address } = req.params;
    const {
      homeOdds, awayOdds, 
      homeSpreadPoints, homeSpreadOdds, awaySpreadOdds,
      totalPoints, overOdds, underOdds
    } = req.body;

    // Validate required fields - all are needed for the contract function
    if (homeOdds === undefined || awayOdds === undefined || 
        homeSpreadPoints === undefined || homeSpreadOdds === undefined || awaySpreadOdds === undefined ||
        totalPoints === undefined || overOdds === undefined || underOdds === undefined) {
      return res.status(400).json({ error: 'Missing one or more required odds/line parameters for updateOdds' });
    }

    // Parse all parameters as integers
    const params = [
        parseInt(homeOdds),
        parseInt(awayOdds),
        parseInt(homeSpreadPoints),
        parseInt(homeSpreadOdds),
        parseInt(awaySpreadOdds),
        parseInt(totalPoints),
        parseInt(overOdds),
        parseInt(underOdds)
    ];

    // Basic NaN check after parsing
    if (params.some(isNaN)) {
         return res.status(400).json({ error: 'All odds/line parameters must be valid numbers' });
    }

    console.log(`Updating odds for ${address} with params:`, params);

    const provider = setupProvider();

    // 1. Get the MarketOdds contract address from the NBAMarket contract
    console.log("Fetching MarketOdds contract address...");
    const nbaMarketContract = new ethers.Contract(address, NBAMarketJson.abi, provider); 
    const marketOddsAddress = await nbaMarketContract.getMarketOddsContract();

    if (!marketOddsAddress || marketOddsAddress === ethers.constants.AddressZero) {
      return res.status(404).json({ error: `MarketOdds contract not found for NBAMarket ${address}` });
    }
    console.log(`Targeting MarketOdds contract: ${marketOddsAddress}`);

    // 2. Send transaction to the MarketOdds contract
    const resultOddsUpdate = await signAndSendTransaction({
      contractAddress: marketOddsAddress, // Target the odds contract
      contractAbi: MarketOddsJson.abi,   // Use its ABI
      method: 'updateOdds',
      params: params,
      role: 'oddsProvider' // Use odds provider signer
    }, provider);

    if (!resultOddsUpdate.success) {
      // Keep original error handling
      throw new Error(resultOddsUpdate.error);
    }
    
    console.log(`Odds values updated in MarketOdds contract: ${marketOddsAddress}`);

    // 3. After successful odds update, try to transition NBAMarket status to OPEN
    try {
      console.log(`Attempting to call tryOpenMarket on NBAMarket: ${address}`);
      // We need a signer to call a state-changing function like tryOpenMarket
      // Using 'admin' role signer as defined in NBAMarket.sol
      const adminSigner = await getRoleSigner('admin', provider); 
      const resultStatusUpdate = await signAndSendTransaction({
          contractAddress: address, // Target NBAMarket contract
          contractAbi: NBAMarketJson.abi, // Use NBAMarket ABI
          method: 'tryOpenMarket', // Call the new function
          params: [], // No parameters for tryOpenMarket
          signer: adminSigner // Use admin signer
      }, provider);

      if (resultStatusUpdate.success) {
          console.log(`Successfully called tryOpenMarket on NBAMarket: ${address}. Market might now be OPEN. Tx: ${resultStatusUpdate.transaction}`);
      } else {
          // Log a warning but don't fail the whole request. 
          // This might fail if market was already Open, game started, or odds weren't readable by the contract yet.
          console.warn(`Call to tryOpenMarket on NBAMarket ${address} did not succeed (it might have reverted). Odds were updated, but status might remain Pending. Error: ${resultStatusUpdate.error}`);
      }
    } catch (statusUpdateError) {
         // Log a warning but don't fail the whole request
         console.warn(`Error occurred while trying to call tryOpenMarket for ${address}:`, statusUpdateError);
    }

    // Update stored market info
    const marketIndex = deployedContracts.markets.findIndex(m => m.address === address);
    if (marketIndex >= 0) {
      deployedContracts.markets[marketIndex].homeOdds = homeOdds;
      deployedContracts.markets[marketIndex].awayOdds = awayOdds;
      deployedContracts.markets[marketIndex].homeSpreadPoints = homeSpreadPoints;
      deployedContracts.markets[marketIndex].homeSpreadOdds = homeSpreadOdds;
      deployedContracts.markets[marketIndex].awaySpreadOdds = awaySpreadOdds;
      deployedContracts.markets[marketIndex].totalPoints = totalPoints;
      deployedContracts.markets[marketIndex].overOdds = overOdds;
      deployedContracts.markets[marketIndex].underOdds = underOdds;
      deployedContracts.markets[marketIndex].oddsSet = true;
      deployedContracts.markets[marketIndex].updatedAt = new Date().toISOString();
      saveDeployedContracts();
    }
    
    console.log(`Odds updated for market ${address}`);
    res.json({ 
      success: true, 
      address,
      homeOdds,
      awayOdds,
      homeSpreadPoints,
      homeSpreadOdds,
      awaySpreadOdds,
      totalPoints,
      overOdds,
      underOdds,
      transaction: resultOddsUpdate.transaction // Report the odds update transaction hash
    });
  } catch (error) {
    console.error('Error updating odds:', error);
    res.status(500).json({ error: error.message });
  }
});

// Add liquidity to a market
app.post('/api/market/:address/add-liquidity', async (req, res) => {
  try {
    const { address } = req.params;
    const { amount } = req.body;
    
    if (!amount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0) {
      return res.status(400).json({ error: 'Valid amount is required (must be a positive number)' });
    }
    
    if (!deployedContracts.liquidityPool) {
      return res.status(400).json({ error: 'Liquidity Pool not deployed yet' });
    }
    
    const provider = setupProvider();
    const liquidityPoolAddress = deployedContracts.liquidityPool;
    
    console.log(`Adding ${amount} USDX liquidity to market ${address}...`);
    
    // Convert amount to wei representation
    const amountInTokens = ethers.utils.parseUnits(amount.toString(), 6);
    
    // Get the betting engine address
    const market = new ethers.Contract(address, NBAMarketJson.abi, provider);
    const bettingEngineAddress = await market.bettingEngine();
    console.log(`Found betting engine at: ${bettingEngineAddress}`);
    
    // First authorize the betting engine if not already authorized
    const authResult = await signAndSendTransaction({
      contractAddress: liquidityPoolAddress,
      contractAbi: LiquidityPoolJson.abi,
      method: 'authorizeMarket',
      params: [bettingEngineAddress],
      role: 'admin'
    }, provider);
    
    if (!authResult.success) {
      console.warn('Warning authorizing betting engine:', authResult.error);
      // Continue anyway as the betting engine might already be authorized
    }
    
    // Fund the betting engine
    const result = await signAndSendTransaction({
      contractAddress: liquidityPoolAddress,
      contractAbi: LiquidityPoolJson.abi,
      method: 'fundMarket',
      params: [bettingEngineAddress, amountInTokens],
      role: 'admin'
    }, provider);
    
    if (!result.success) {
      throw new Error(result.error);
    }
    
    // Update stored market info to track funding
    const marketIndex = deployedContracts.markets.findIndex(m => m.address === address);
    if (marketIndex >= 0) {
      if (!deployedContracts.markets[marketIndex].additionalFunding) {
        deployedContracts.markets[marketIndex].additionalFunding = [];
      }
      
      deployedContracts.markets[marketIndex].additionalFunding.push({
        amount: amount,
        timestamp: new Date().toISOString(),
        transaction: result.transaction
      });
      
      saveDeployedContracts();
    }
    
    console.log(`Liquidity added to market ${address}`);
    res.json({ 
      success: true, 
      address,
      amount,
      transaction: result.transaction
    });
  } catch (error) {
    console.error('Error adding liquidity:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get market info
app.get('/api/market/:address', async (req, res) => {
  try {
    const { address } = req.params;
    
    const provider = setupProvider();
    const market = new ethers.Contract(address, NBAMarketJson.abi, provider);
    
    console.log(`Getting info for market ${address}...`);
    
    // Fetch all details concurrently
    const [details, fullOdds, exposure, bettingEngineAddress] = await Promise.all([
         market.getMarketDetails(),
         // Fetch odds from the associated MarketOdds contract
         (async () => {
            try {
                const marketOddsAddr = await market.getMarketOddsContract();
                if (!marketOddsAddr || marketOddsAddr === ethers.constants.AddressZero) return { error: "No MarketOdds contract linked" };
                const oddsContract = new ethers.Contract(marketOddsAddr, MarketOddsJson.abi, provider);
                const oddsData = await oddsContract.getFullOdds();
                return { address: marketOddsAddr, data: oddsData }; // Return address and data
            } catch (e) {
                 console.error("Error fetching odds data:", e);
                 return { error: e.message };
            }
         })(),
         market.getExposureInfo(),
         market.bettingEngine() // Get the associated betting engine
    ]);
    
    // Format the response
    const marketInfo = {
      address,
      homeTeam: details._homeTeam,
      awayTeam: details._awayTeam,
      gameTimestamp: details._gameTimestamp.toNumber(),
      oddsApiId: details._oddsApiId,
      homeScore: details._homeScore.toNumber(),
      awayScore: details._awayScore.toNumber(),
      marketOddsAddress: fullOdds.address || null, // Include the odds contract address
      ...(fullOdds.data ? { // Check if odds data was fetched successfully
          homeOdds: fullOdds.data._homeOdds.toNumber() / 1000,
          awayOdds: fullOdds.data._awayOdds.toNumber() / 1000,
          homeSpreadPoints: formatLine(1, fullOdds.data._homeSpreadPoints),
          homeSpreadOdds: fullOdds.data._homeSpreadOdds.toNumber() / 1000,
          awaySpreadOdds: fullOdds.data._awaySpreadOdds.toNumber() / 1000,
          totalPoints: formatLine(2, fullOdds.data._totalPoints),
          overOdds: fullOdds.data._overOdds.toNumber() / 1000,
          underOdds: fullOdds.data._underOdds.toNumber() / 1000,
          // Raw Odds (optional, for debugging/internal use)
          rawOdds: {
              homeOdds: fullOdds.data._homeOdds.toString(),
              awayOdds: fullOdds.data._awayOdds.toString(),
              homeSpreadPoints: fullOdds.data._homeSpreadPoints.toString(),
              homeSpreadOdds: fullOdds.data._homeSpreadOdds.toString(),
              awaySpreadOdds: fullOdds.data._awaySpreadOdds.toString(),
              totalPoints: fullOdds.data._totalPoints.toString(),
              overOdds: fullOdds.data._overOdds.toString(),
              underOdds: fullOdds.data._underOdds.toString(),
          }
      } : { oddsError: fullOdds.error || "Odds not loaded" }), // Include error if fetch failed
      gameStarted: details._marketStatus[0],
      gameEnded: details._marketStatus[1],
      oddsSet: details._marketStatus[2],
      outcome: details._marketStatus[3],
      maxExposure: ethers.utils.formatUnits(exposure[0], 6),
      currentExposure: ethers.utils.formatUnits(exposure[1], 6),
      bettingEngineAddress
    };
    
    res.json(marketInfo);
  } catch (error) {
    console.error('Error getting market info:', error);
    res.status(500).json({ error: error.message });
  }
});

// Control game status (start game, set result)
app.post('/api/market/:address/game-status', async (req, res) => {
  try {
    const { address } = req.params;
    const { action, outcome, homeScore, awayScore } = req.body; // outcome is deprecated, use scores

    let method;
    let params = [];
    let role;

    if (action === 'start') {
      method = 'startGame';
      role = 'resultsProvider';
    } else if (action === 'set-result') {
      // Validate scores for set-result
      if (homeScore === undefined || awayScore === undefined) {
        return res.status(400).json({ error: 'homeScore and awayScore are required for set-result' });
      }
      const parsedHomeScore = parseInt(homeScore);
      const parsedAwayScore = parseInt(awayScore);
      if (isNaN(parsedHomeScore) || isNaN(parsedAwayScore) || parsedHomeScore < 0 || parsedAwayScore < 0) {
         return res.status(400).json({ error: 'Scores must be non-negative integers.' });
      }

      method = 'setResult';
      params = [parsedHomeScore, parsedAwayScore]; // Pass scores
      role = 'resultsProvider';
    } else {
      return res.status(400).json({ error: 'Invalid action. Must be \"start\" or \"set-result\"' });
    }

    console.log(`Performing action '${action}' on market ${address} with role '${role}' and params:`, params);

    const provider = setupProvider();
    // Explicitly get the signer based on the required role
    const actionSigner = await getRoleSigner(role, provider);
    if (!actionSigner) {
        console.error(`Could not get signer for role: ${role}`);
        return res.status(500).json({ error: `Server configuration error: Could not load signer for role '${role}'.` });
    }
    console.log(`Using signer address: ${await actionSigner.getAddress()} for role ${role}`);

    const result = await signAndSendTransaction({
      contractAddress: address,
      contractAbi: NBAMarketJson.abi,
      method: method,
      params: params,
      // Pass the explicit signer object instead of the role string
      signer: actionSigner 
    }, provider);

    if (!result.success) {
      throw new Error(result.error);
    }
    
    // Update stored market info
    const marketIndex = deployedContracts.markets.findIndex(m => m.address === address);
    if (marketIndex >= 0) {
      if (action === 'start') {
        deployedContracts.markets[marketIndex].gameStarted = true;
      } else {
        deployedContracts.markets[marketIndex].gameEnded = true;
        deployedContracts.markets[marketIndex].outcome = outcome;
      }
      deployedContracts.markets[marketIndex].updatedAt = new Date().toISOString();
      saveDeployedContracts();
    }
    
    console.log(`Game status updated for market ${address}`);
    res.json({ 
      success: true, 
      address,
      action,
      outcome: action === 'set-result' ? outcome : undefined,
      transaction: result.transaction
    });
  } catch (error) {
    console.error('Error updating game status:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get all markets from factory
app.get('/api/markets', async (req, res) => {
  if (!deployedContracts.marketFactory) {
    return res.status(400).json({ error: 'MarketFactory not deployed yet' });
  }

  try {
    const provider = setupProvider();
    const factoryAddress = (typeof deployedContracts.marketFactory === 'string')
      ? deployedContracts.marketFactory
      : deployedContracts.marketFactory.address;

    const marketFactory = new ethers.Contract(factoryAddress, MarketFactoryJson.abi, provider);
    
    let marketAddresses = [];
    try {
        marketAddresses = await marketFactory.getDeployedMarkets();
    } catch (e) {
        // Handle case where getDeployedMarkets might not exist or fails
        console.warn("marketFactory.getDeployedMarkets() failed, trying stored markets:", e.message);
        // Fallback to locally stored markets if necessary
        if (deployedContracts.markets && deployedContracts.markets.length > 0) {
            marketAddresses = deployedContracts.markets.map(m => m.address);
            console.log(`Using ${marketAddresses.length} stored market addresses as fallback.`);
        } else {
            console.error("Failed to get markets from factory and no stored markets found.");
            return res.json([]); // Return empty array if no markets found
        }
    }
    
    if (!marketAddresses || marketAddresses.length === 0) {
        console.log("No market addresses found.");
        return res.json([]);
    }

    // Fetch basic details for each market concurrently
    const marketDetailsPromises = marketAddresses.map(async (address) => {
      try {
        const marketContract = new ethers.Contract(address, NBAMarketJson.abi, provider);
        const details = await marketContract.getMarketDetails(); // Using new getter
        const exposure = await marketContract.getExposureInfo();
        
        // Fetch odds from associated MarketOdds contract
        let oddsDetails = {};
        try {
            const marketOddsAddress = await marketContract.getMarketOddsContract();
            if (marketOddsAddress && marketOddsAddress !== ethers.constants.AddressZero) {
               const oddsContract = new ethers.Contract(marketOddsAddress, MarketOddsJson.abi, provider);
               const fullOddsData = await oddsContract.getFullOdds();
               oddsDetails = {
                  marketOddsAddress: marketOddsAddress,
                  homeOdds: fullOddsData._homeOdds.toNumber() / 1000,
                  awayOdds: fullOddsData._awayOdds.toNumber() / 1000,
                  homeSpreadPoints: formatLine(1, fullOddsData._homeSpreadPoints), // Use helper
                  homeSpreadOdds: fullOddsData._homeSpreadOdds.toNumber() / 1000,
                  awaySpreadOdds: fullOddsData._awaySpreadOdds.toNumber() / 1000,
                  totalPoints: formatLine(2, fullOddsData._totalPoints), // Use helper
                  overOdds: fullOddsData._overOdds.toNumber() / 1000,
                  underOdds: fullOddsData._underOdds.toNumber() / 1000,
              };
           } else {
              oddsDetails = { marketOddsAddress: 'Not Set or Zero', error: 'Odds contract missing' };
           }
        } catch (oddsError) {
             console.error(`Error fetching odds details for market ${address}:`, oddsError);
             oddsDetails = { error: 'Failed to fetch odds details' };
        }
        
        return {
          address: address,
          homeTeam: details._homeTeam,
          awayTeam: details._awayTeam,
          gameTimestamp: details._gameTimestamp.toNumber(),
          oddsApiId: details._oddsApiId,
          status: mapMarketStatusEnumToString(details._marketStatus), // Use helper
          resultSettled: details._resultSettled,
          homeScore: details._homeScore.toNumber(),
          awayScore: details._awayScore.toNumber(),
          // Include odds for quick view
          ...oddsDetails, // Spread odds details into the market object
          maxExposure: ethers.utils.formatUnits(exposure[0], 6), // Assuming 6 decimals for USDX
          currentExposure: ethers.utils.formatUnits(exposure[1], 6)
        };
      } catch (marketError) {
        console.error(`Error fetching details for market ${address}:`, marketError);
        return { address: address, error: 'Failed to fetch details' }; // Return partial info on error
      }
    });

    const markets = await Promise.all(marketDetailsPromises);
    res.json(markets.filter(m => !m.error)); // Filter out markets that failed to load

  } catch (error) {
    console.error('Error getting markets:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get liquidity pool info
app.get('/api/liquidity-pool', async (req, res) => {
  try {
    if (!deployedContracts.liquidityPool) {
      return res.status(400).json({ error: 'Liquidity Pool not deployed yet' });
    }
    
    const provider = setupProvider();
    const liquidityPoolAddress = deployedContracts.liquidityPool;
    
    const liquidityPool = new ethers.Contract(
      liquidityPoolAddress,
      LiquidityPoolJson.abi,
      provider
    );
    
    console.log('Getting liquidity pool info...');
    const balance = await liquidityPool.getBalance();
    const formattedBalance = ethers.utils.formatUnits(balance, 6);
    
    res.json({
      address: liquidityPoolAddress,
      balance: formattedBalance,
      balanceRaw: balance.toString()
    });
  } catch (error) {
    console.error('Error getting liquidity pool info:', error);
    res.status(500).json({ error: error.message });
  }
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Get transaction details
app.get('/api/tx/:txHash', async (req, res) => {
  try {
    const { txHash } = req.params;
    
    const provider = setupProvider();
    
    // Get transaction
    const tx = await provider.getTransaction(txHash);
    
    if (!tx) {
      return res.status(404).json({ error: 'Transaction not found' });
    }
    
    // Get transaction receipt for additional info
    const receipt = await provider.getTransactionReceipt(txHash);
    
    // Format event logs in a readable way
    const formattedLogs = [];
    if (receipt && receipt.logs) {
      // Try to decode logs based on contract ABIs
      for (const log of receipt.logs) {
        try {
          let eventName = "Unknown Event";
          let decodedData = {};
          
          // Try to match with different contract interfaces
          const interfaces = [
            new ethers.utils.Interface(MarketFactoryJson.abi),
            new ethers.utils.Interface(NBAMarketJson.abi),
            new ethers.utils.Interface(LiquidityPoolJson.abi),
            new ethers.utils.Interface(USDXJson.abi),
            new ethers.utils.Interface(BettingEngineJson.abi)
          ];
          
          let decoded = null;
          for (const iface of interfaces) {
            try {
              decoded = iface.parseLog(log);
              if (decoded) {
                eventName = decoded.name;
                decodedData = decoded.args;
                break;
              }
            } catch (e) {
              // Try next interface
            }
          }
          
          formattedLogs.push({
            address: log.address,
            eventName,
            topics: log.topics,
            data: log.data,
            decodedData: Object.keys(decodedData)
              .filter(key => isNaN(Number(key))) // Filter out numeric keys
              .reduce((obj, key) => {
                // Convert BigNumber to string
                if (decodedData[key] && decodedData[key]._isBigNumber) {
                  obj[key] = decodedData[key].toString();
                } else {
                  obj[key] = decodedData[key];
                }
                return obj;
              }, {})
          });
        } catch (error) {
          formattedLogs.push({
            address: log.address,
            topics: log.topics,
            data: log.data,
            error: "Could not decode log"
          });
        }
      }
    }
    
    // Return comprehensive transaction details
    const txDetails = {
      hash: tx.hash,
      from: tx.from,
      to: tx.to,
      value: tx.value.toString(),
      gasPrice: tx.gasPrice?.toString(),
      gasLimit: tx.gasLimit?.toString(),
      nonce: tx.nonce,
      data: tx.data,
      chainId: tx.chainId,
      
      // Receipt details
      blockNumber: receipt?.blockNumber,
      blockHash: receipt?.blockHash,
      transactionIndex: receipt?.transactionIndex,
      confirmations: receipt?.confirmations,
      status: receipt?.status === 1 ? 'success' : 'failed',
      gasUsed: receipt?.gasUsed?.toString(),
      cumulativeGasUsed: receipt?.cumulativeGasUsed?.toString(),
      effectiveGasPrice: receipt?.effectiveGasPrice?.toString(),
      contractAddress: receipt?.contractAddress,
      
      // Event logs
      logs: formattedLogs
    };
    
    res.json(txDetails);
  } catch (error) {
    console.error('Error getting transaction details:', error);
    res.status(500).json({ error: error.message });
  }
});

// Start the server
app.listen(PORT, () => {
  console.log(`API server running on port ${PORT}`);
  loadDeployedContracts();
});

// Export for PM2
module.exports = app;

// Place a bet on a market
app.post('/api/market/:address/place-bet', async (req, res) => {
  try {
    const { address } = req.params;
    const { amount, betType, betSide, bettor } = req.body; // betType: 'moneyline', 'spread', 'total'; betSide: 'home'/'away' or 'over'/'under'

    if (!amount || !betType || !betSide || !bettor) {
      return res.status(400).json({ error: 'amount, betType, betSide, and bettor are required' });
    }

    // Map betType string to enum index
    let betTypeEnum;
    if (betType.toLowerCase() === 'moneyline') betTypeEnum = 0;
    else if (betType.toLowerCase() === 'spread') betTypeEnum = 1;
    else if (betType.toLowerCase() === 'total') betTypeEnum = 2;
    else return res.status(400).json({ error: 'Invalid betType' });

    // Map betSide string to boolean (isBettingOnHomeOrOver)
    let isBettingOnHomeOrOver;
    const sideLower = betSide.toLowerCase();
    if (betTypeEnum === 0 || betTypeEnum === 1) { // ML or Spread
        if (sideLower === 'home') isBettingOnHomeOrOver = true;
        else if (sideLower === 'away') isBettingOnHomeOrOver = false;
        else return res.status(400).json({ error: 'Invalid betSide for moneyline/spread' });
    } else { // Total
        if (sideLower === 'over') isBettingOnHomeOrOver = true;
        else if (sideLower === 'under') isBettingOnHomeOrOver = false;
        else return res.status(400).json({ error: 'Invalid betSide for total' });
    }
    
    const provider = setupProvider();
    
    // --- Get the correct signer based on the 'bettor' address provided ---
    let actualBettorSigner;
    const hardhatAccounts = {
        // Map addresses to their known private keys for local dev
        '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266': '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80', // Account 0 (Admin/Deployer)
        '0x70997970c51812dc3a010c7d01b50e0d17dc79c8': '0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d', // Account 1 (Odds)
        '0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc': '0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a', // Account 2 (Results)
        '0x90f79bf6eb2c4f870365e785982e1f101e93b906': '0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6', // Account 3 (User 1)
        '0x15d34aaf54267db7d7c367839aaf71a00a2c6a65': '0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a', // Account 4 (User 2)
        '0xdc63788ada727255db07819632488d2629139ce8': '0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba'  // Account 5 (Added for UI) - Assuming Hardhat PK
        // Add other known bettor private keys if needed for testing
    };
    
    const lowerCaseBettor = bettor.toLowerCase();
    let foundPrivateKey = null;
    for (const addressKey in hardhatAccounts) {
        if (addressKey.toLowerCase() === lowerCaseBettor) {
            foundPrivateKey = hardhatAccounts[addressKey];
            break;
        }
    }

    if (foundPrivateKey) {
        actualBettorSigner = new ethers.Wallet(foundPrivateKey, provider);
        console.log(`Found signer for ${bettor} using pre-configured local keys.`);
    } else {
        // Fallback or error handling if the bettor address isn't known/configured
        // For now, we'll use the default wallet as a fallback, but this might not be desired
        console.warn(`Could not find pre-configured private key for bettor ${bettor}. Falling back to default wallet.`);
        // Using default wallet might lead to unexpected behavior if it doesnt have USDX or allowance
        // Consider throwing an error instead:
        return res.status(400).json({ error: `Signer for bettor address ${bettor} not configured on the server.` });
        // actualBettorSigner = await getDefaultWallet(provider); 
    }
    // --- End signer determination ---

    if (!actualBettorSigner) { // Basic check, though the logic above should handle it
      return res.status(500).json({ error: `Could not load the signer for address ${bettor}. Check server configuration.` });
    }

    console.log(`Placing bet using signer: ${await actualBettorSigner.getAddress()}`); // Use actualBettorSigner

    // Convert amount to token units
    const betAmountInTokens = ethers.utils.parseUnits(amount.toString(), 6);
    
    // --- Get Betting Engine Address (Needed for Approval) ---
    const marketContractReader = new ethers.Contract(address, NBAMarketJson.abi, provider); // Use provider for read-only call
    let bettingEngineAddress;
    try {
        bettingEngineAddress = await marketContractReader.bettingEngine();
        if (!bettingEngineAddress || bettingEngineAddress === ethers.constants.AddressZero) {
            return res.status(500).json({ error: 'Could not find a valid BettingEngine address linked to this market.' });
        }
        console.log(`Targeting BettingEngine for approval: ${bettingEngineAddress}`);
    } catch (fetchError) {
        console.error('Error fetching BettingEngine address for approval:', fetchError);
        return res.status(500).json({ error: `Failed to fetch BettingEngine address: ${fetchError.message}` });
    }
    // --- End Get Betting Engine ---

    // --- Approve USDX spending before placing bet ---
    // Note: Approval should be for the BettingEngine contract, as it will call transferFrom
    if (!deployedContracts.usdx) {
      return res.status(500).json({ error: 'USDX contract address not found in deployment data.' });
    }
    const usdxAddress = deployedContracts.usdx;
    const usdxContract = new ethers.Contract(usdxAddress, USDXJson.abi, actualBettorSigner); // Use actualBettorSigner

    console.log(`Approving BettingEngine (${bettingEngineAddress}) to spend ${amount} USDX (${betAmountInTokens}) for ${await actualBettorSigner.getAddress()}...`); // Use actualBettorSigner
    try {
      // Check current allowance first
      const currentAllowance = await usdxContract.allowance(await actualBettorSigner.getAddress(), bettingEngineAddress); // Check allowance for BettingEngine address
      if (currentAllowance.lt(betAmountInTokens)) {
           console.log(`Allowance (${currentAllowance}) is less than bet amount (${betAmountInTokens}). Approving...`);
           const approveTx = await usdxContract.approve(bettingEngineAddress, betAmountInTokens); // Approve the BettingEngine address
           console.log(`Approval transaction submitted: ${approveTx.hash}`);
           const approveReceipt = await approveTx.wait();
           if (approveReceipt.status !== 1) {
               console.error('USDX approval transaction failed:', approveReceipt);
               throw new Error('Failed to approve USDX spending for the BettingEngine contract.');
           }
           console.log('USDX spending approved.');
      } else {
          console.log(`Sufficient allowance (${currentAllowance}) already granted. Skipping approval.`);
      }
    } catch (approvalError) {
        console.error('Error during USDX approval:', approvalError);
        // Include more details from the error if possible
        const errorMessage = approvalError.reason || approvalError.message || 'Unknown approval error';
        return res.status(500).json({ 
            error: `Failed to approve USDX tokens: ${errorMessage}`,
            details: approvalError // Include the raw error for debugging
        });
    }
    // --- End USDX Approval ---

    // Prepare transaction parameters for NBAMarket.placeBet
    const params = [
      betTypeEnum,
      betAmountInTokens,
      isBettingOnHomeOrOver
      // No need to pass odds/line here, NBAMarket fetches them
    ];

    console.log(`Placing bet via NBAMarket ${address}: Type=${betTypeEnum}, Amount=${betAmountInTokens}, Side=${isBettingOnHomeOrOver} by ${bettor}`);

    // Send transaction using the bettor's signer to the NBAMarket contract
    const result = await signAndSendTransaction({
      contractAddress: address, // Target NBAMarket contract
      contractAbi: NBAMarketJson.abi, // Use NBAMarket ABI
      method: 'placeBet',
      params: params, // Pass the 3 parameters for NBAMarket.placeBet
      signer: actualBettorSigner // Pass the specific bettor's signer
    }, provider);

    if (!result.success) {
        // Attempt to provide a more specific error message if possible
        const errorDetails = result.error || 'Unknown error during transaction execution.';
        console.error('Bet placement transaction failed:', errorDetails);
        // Check for common revert reasons if available in the error string
        if (typeof errorDetails === 'string' && errorDetails.includes('reverted with reason string')) {
            const match = errorDetails.match(/reverted with reason string '([^']+)'/);
            if (match && match[1]) {
                throw new Error(`Bet placement failed: ${match[1]}`);
            }
        }
        throw new Error(`Bet placement transaction failed: ${errorDetails}`);
    }

    // Get the receipt directly from the transaction result
    const receipt = await provider.getTransactionReceipt(result.transaction);
    
    if (receipt.status === 0) {
        console.error(`Transaction reverted: ${result.transaction}`);
        // Add better revert reason fetching here if possible
        throw new Error('Bet placement transaction reverted. Check parameters and contract state.');
    }

    // --- Fetch bet details *after* confirmation --- 
    // The BetPlaced event is emitted by the BettingEngine, which is called by NBAMarket.
    // We need to find the BettingEngine address first to correctly parse the log.
    let betId = 'N/A';
    let potentialWinnings = 'N/A';
    try {
        // Get Betting Engine address associated with the market
        const marketContractReader = new ethers.Contract(address, NBAMarketJson.abi, provider); 
        const bettingEngineAddress = await marketContractReader.bettingEngine();

        if (!bettingEngineAddress || bettingEngineAddress === ethers.constants.AddressZero) {
            console.warn("Could not retrieve BettingEngine address for market", address, "Unable to parse BetPlaced event accurately.");
        } else {
            // Use BettingEngine ABI to parse BetPlaced event
            const bettingEngineInterface = new ethers.utils.Interface(BettingEngineJson.abi);
            // Corrected event signature matching BettingEngine.sol
            const betPlacedEventSignature = "BetPlaced(uint256,address,uint256,uint8,bool,int256,uint256,uint256)";
            const betPlacedEventTopic = ethers.utils.id(betPlacedEventSignature); // Use updated signature

            const betPlacedLog = receipt.logs.find(log => 
                log.address.toLowerCase() === bettingEngineAddress.toLowerCase() &&
                log.topics[0] === betPlacedEventTopic
            );

            if (betPlacedLog) {
                const decodedEvent = bettingEngineInterface.parseLog(betPlacedLog);
                betId = decodedEvent.args.betId.toString();
                // Potential winnings are part of the event in BettingEngine
                potentialWinnings = ethers.utils.formatUnits(decodedEvent.args.potentialWinnings, 6);
                console.log(`Successfully parsed BetPlaced event. Bet ID: ${betId}, Potential Winnings: ${potentialWinnings}`);
            } else {
                console.warn("Could not find BetPlaced event in transaction receipt logs. Attempting fallback...");
                // Fallback: Try fetching last bet ID from NBAMarket - less reliable
                const bettorAddress = await actualBettorSigner.getAddress();
                const betIds = await marketContractReader.getBettorBets(bettorAddress);
                if (betIds && betIds.length > 0) {
                  betId = betIds[betIds.length - 1].toString();
                  // Need to fetch details from NBAMarket again
                  const betDetails = await marketContractReader.getBetDetails(betId);
                  potentialWinnings = ethers.utils.formatUnits(betDetails.potentialWinnings, 6);
                  console.log(`Fallback: Fetched last Bet ID: ${betId}, Potential Winnings: ${potentialWinnings}`);
                } else {
                  console.warn("Fallback failed: No bets found for user.");
                }
            }
        }
    } catch(parseError) {
        console.error("Error parsing BetPlaced event or fetching bet details:", parseError);
    }
    // --- End Fetch Bet Details ---

    return res.json({
      success: true,
      bettor: await actualBettorSigner.getAddress(), // Address used for the bet
      betId: betId,
      amount: amount, // Original requested amount
      potentialWinnings: potentialWinnings,
      side: betSide, // Original requested side
      transaction: result.transaction // Use the hash from signAndSendTransaction
    });
  } catch (error) {
    console.error('Error placing bet:', error);
    res.status(500).json({ error: error.message });
  }
});

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
    console.log(betIds);
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

// Get user balances (Native and USDX)
app.get('/api/balance/:address', async (req, res) => {
  try {
    const { address } = req.params;

    if (!ethers.utils.isAddress(address)) {
      return res.status(400).json({ error: 'Invalid Ethereum address provided' });
    }

    const provider = setupProvider();
    let usdxBalanceFormatted = 'N/A (USDX not deployed)';
    let usdxBalanceRaw = '0';

    // Get native balance
    const nativeBalance = await provider.getBalance(address);
    const nativeBalanceFormatted = ethers.utils.formatEther(nativeBalance); // Native is usually 18 decimals

    // Get USDX balance if deployed
    if (deployedContracts.usdx) {
      try {
        const usdx = new ethers.Contract(deployedContracts.usdx, USDXJson.abi, provider);
        const usdxBalance = await usdx.balanceOf(address);
        // Assuming USDX uses 6 decimals as elsewhere in the code
        usdxBalanceFormatted = ethers.utils.formatUnits(usdxBalance, 6);
        usdxBalanceRaw = usdxBalance.toString();
      } catch (usdxError) {
        console.error(`Error fetching USDX balance for ${address}:`, usdxError);
        usdxBalanceFormatted = 'Error fetching USDX balance';
      }
    }

    res.json({
      address: address,
      nativeBalance: nativeBalanceFormatted,
      nativeBalanceRaw: nativeBalance.toString(),
      usdxBalance: usdxBalanceFormatted,
      usdxBalanceRaw: usdxBalanceRaw
    });

  } catch (error) {
    console.error('Error fetching balances:', error);
    res.status(500).json({ error: error.message });
  }
});

// Faucet endpoint to mint USDX tokens (using admin wallet)
app.post('/api/faucet', async (req, res) => {
  try {
    const { address, amount } = req.body;

    if (!ethers.utils.isAddress(address)) {
      return res.status(400).json({ error: 'Valid recipient address is required' });
    }
    if (!amount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0) {
      return res.status(400).json({ error: 'Valid positive amount is required' });
    }
    if (!deployedContracts.usdx) {
      return res.status(400).json({ error: 'USDX contract not deployed yet' });
    }

    const provider = setupProvider();
    const adminWallet = await getDefaultWallet(provider); // Wallet with minting privileges
    const usdxAddress = deployedContracts.usdx;

    console.log(`Faucet request: Minting ${amount} USDX to ${address}...`);

    const usdx = new ethers.Contract(usdxAddress, USDXJson.abi, adminWallet);
    const amountInTokens = ethers.utils.parseUnits(amount.toString(), 6); // Assuming 6 decimals for USDX

    let mintTx;
    try {
      mintTx = await usdx.mint(address, amountInTokens);
      console.log(`Mint transaction submitted with hash: ${mintTx.hash}`);
      await mintTx.wait();
      console.log("Mint transaction confirmed");
    } catch (error) {
      console.error("Error during mint transaction:", error);
      return res.status(500).json({ error: error.message });
    }

    res.json({
      success: true,
      address,
      amount,
      transaction: mintTx.hash
    });
  } catch (error) {
    console.error('Error during faucet request:', error);
    res.status(500).json({ error: error.message });
  }
});

// --- Helper Functions for Formatting ---

function mapMarketStatusEnumToString(enumIndex) {
    // Assuming MarketStatus { PENDING, OPEN, STARTED, SETTLED, CANCELLED }
    switch (enumIndex) {
        case 0: return 'Pending';
        case 1: return 'Open';
        case 2: return 'Started';
        case 3: return 'Settled';
        case 4: return 'Cancelled';
        default: return 'Unknown';
    }
}

function mapBetTypeEnumToString(enumIndex) {
    // Assuming BetType { MONEYLINE, SPREAD, TOTAL }
    switch (enumIndex) {
        case 0: return 'Moneyline';
        case 1: return 'Spread';
        case 2: return 'Total';
        default: return 'Unknown';
    }
}

function mapBetSideToString(betType, isHomeOrOver) {
    // BetType: 0=ML, 1=Spread, 2=Total
    if (betType === 0 || betType === 1) { // Moneyline or Spread
        return isHomeOrOver ? 'Home' : 'Away';
    } else if (betType === 2) { // Total
        return isHomeOrOver ? 'Over' : 'Under';
    } else {
        return 'N/A';
    }
}

function formatLine(betType, lineBigNumber) {
    // BetType: 0=ML, 1=Spread, 2=Total
    // line is int256 for spread, uint256 for total in contract, but likely treated as BigNumber here
    if (betType === 1 || betType === 2) { // Spread or Total
        try {
            const line = lineBigNumber.toNumber(); // Convert BigNumber to number
            // Format with one decimal place
            const formatted = (line / 10).toFixed(1);
            // Add '+' sign for positive spreads only
            if (betType === 1 && line > 0) {
                return `+${formatted}`;
            }
            return formatted;
        } catch (e) {
            console.warn("Could not format line:", lineBigNumber, e);
            return lineBigNumber.toString(); // Fallback to string representation
        }
    } else { // Moneyline has no line
        return 'N/A';
    }
}

// --- End Helper Functions ---