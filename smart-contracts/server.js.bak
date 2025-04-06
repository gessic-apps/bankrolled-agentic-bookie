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
app.use(cors());
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
    const wallet = getDefaultWallet(provider);
    
    const MarketFactory = new ethers.ContractFactory(
      MarketFactoryJson.abi, 
      MarketFactoryJson.bytecode, 
      wallet
    );
    
    console.log('Deploying MarketFactory...');
    const marketFactory = await MarketFactory.deploy(
      oddsProviderAddress, 
      resultsProviderAddress,
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
    const { homeTeam, awayTeam, gameTimestamp, oddsApiId, homeOdds, awayOdds, marketFunding } = req.body;
    
    console.log("DeployedContracts:", deployedContracts);
    
    if (!deployedContracts.marketFactory) {
      return res.status(400).json({ error: 'MarketFactory not deployed yet' });
    }
    
    if (!homeTeam || !awayTeam || !gameTimestamp || !oddsApiId) {
      return res.status(400).json({ error: 'homeTeam, awayTeam, gameTimestamp, and oddsApiId are required' });
    }
    
    const provider = setupProvider();
    
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
    
    // Make sure odds are numbers, and properly handle when they're not provided
    const parsedHomeOdds = homeOdds !== undefined ? parseInt(homeOdds) : 0;
    const parsedAwayOdds = awayOdds !== undefined ? parseInt(awayOdds) : 0;
    
    console.log("Processed parameters:", {
      homeTeam, 
      awayTeam, 
      gameTimestamp: parseInt(gameTimestamp), 
      oddsApiId,
      homeOdds: parsedHomeOdds,
      awayOdds: parsedAwayOdds,
      fundingAmount: fundingAmount.toString()
    });
    
    if (parsedHomeOdds > 0 && parsedAwayOdds > 0) {
      // Create market with odds
      result = await signAndSendTransaction({
        contractAddress: factoryAddress,
        contractAbi: MarketFactoryJson.abi,
        method: 'createMarket',
        params: [
          homeTeam, 
          awayTeam, 
          parseInt(gameTimestamp), 
          oddsApiId, 
          parsedHomeOdds, 
          parsedAwayOdds, 
          fundingAmount
        ],
        role: 'admin'
      }, provider);
    } else {
      // Create market without odds
      result = await signAndSendTransaction({
        contractAddress: factoryAddress,
        contractAbi: MarketFactoryJson.abi,
        method: 'createMarketWithoutOdds',
        params: [
          homeTeam, 
          awayTeam, 
          parseInt(gameTimestamp), 
          oddsApiId, 
          fundingAmount
        ],
        role: 'admin'
      }, provider);
    }
    
    if (!result.success) {
      throw new Error(result.error);
    }
    
    // Get the receipt directly from the transaction result
    const receipt = await provider.getTransactionReceipt(result.transaction);
    
    // Parse logs to get the market address
    const marketFactory = new ethers.Contract(factoryAddress, MarketFactoryJson.abi, provider);
    const eventTopic = marketFactory.interface.getEventTopic('MarketCreated');
    
    // Find the MarketCreated event
    const marketEvent = receipt.logs.find(log => 
      log.topics[0] === eventTopic
    );
    
    if (!marketEvent) {
      throw new Error('Could not find MarketCreated event in transaction logs');
    }
    
    // Decode event data
    const eventData = marketFactory.interface.parseLog(marketEvent);
    const marketAddress = eventData.args[0];
    
    // Store market details
    const marketInfo = {
      address: marketAddress,
      homeTeam,
      awayTeam,
      gameTimestamp,
      oddsApiId,
      homeOdds: homeOdds || 0,
      awayOdds: awayOdds || 0,
      oddsSet: !!(homeOdds && awayOdds && homeOdds >= 1000 && awayOdds >= 1000),
      createdAt: new Date().toISOString(),
      funding: marketFunding || "Default"
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
    const { homeOdds, awayOdds } = req.body;
    
    if (!homeOdds || !awayOdds) {
      return res.status(400).json({ error: 'homeOdds and awayOdds are required' });
    }
    
    if (homeOdds < 1000 || awayOdds < 1000) {
      return res.status(400).json({ error: 'Odds must be at least 1.000 (1000)' });
    }
    
    const provider = setupProvider();
    
    console.log(`Updating odds for market ${address}...`);
    
    // Use the odds provider role to update odds
    const result = await signAndSendTransaction({
      contractAddress: address,
      contractAbi: NBAMarketJson.abi,
      method: 'updateOdds',
      params: [homeOdds, awayOdds],
      role: 'oddsProvider'  // This will use the odds provider's private key
    }, provider);
    
    if (!result.success) {
      throw new Error(result.error);
    }
    
    // Update stored market info
    const marketIndex = deployedContracts.markets.findIndex(m => m.address === address);
    if (marketIndex >= 0) {
      deployedContracts.markets[marketIndex].homeOdds = homeOdds;
      deployedContracts.markets[marketIndex].awayOdds = awayOdds;
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
      transaction: result.transaction
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
    
    // Get all market info using the individual getter functions
    const homeTeam = await market.getHomeTeam();
    const awayTeam = await market.getAwayTeam();
    const gameTimestamp = await market.getGameTimestamp();
    const oddsApiId = await market.getOddsApiId();
    const odds = await market.getOdds();
    const status = await market.getGameStatus();
    const exposure = await market.getExposureInfo();
    const isReadyForBetting = await market.isReadyForBetting();
    
    // Format the response
    const marketInfo = {
      address,
      homeTeam,
      awayTeam,
      gameTimestamp: gameTimestamp.toString(),
      oddsApiId,
      homeOdds: odds[0].toString(),
      awayOdds: odds[1].toString(),
      gameStarted: status[0],
      gameEnded: status[1],
      oddsSet: status[2],
      outcome: status[3],
      maxExposure: ethers.utils.formatUnits(exposure[0], 6),
      currentExposure: ethers.utils.formatUnits(exposure[1], 6),
      isReadyForBetting
    };
    
    res.json(marketInfo);
  } catch (error) {
    console.error('Error getting market info:', error);
    res.status(500).json({ error: error.message });
  }
});

// Start or handle game results
app.post('/api/market/:address/game-status', async (req, res) => {
  try {
    const { address } = req.params;
    const { action, outcome } = req.body;
    
    if (!action || !['start', 'set-result'].includes(action)) {
      return res.status(400).json({ error: 'Valid action is required (start or set-result)' });
    }
    
    if (action === 'set-result' && ![1, 2].includes(outcome)) {
      return res.status(400).json({ error: 'Valid outcome is required (1 for home win, 2 for away win)' });
    }
    
    const provider = setupProvider();
    
    let result;
    if (action === 'start') {
      console.log(`Starting game for market ${address}...`);
      result = await signAndSendTransaction({
        contractAddress: address,
        contractAbi: NBAMarketJson.abi,
        method: 'startGame',
        params: [],
        role: 'admin'  // This will use the admin's private key
      }, provider);
    } else {
      console.log(`Setting result for market ${address}...`);
      result = await signAndSendTransaction({
        contractAddress: address,
        contractAbi: NBAMarketJson.abi,
        method: 'setResult',
        params: [outcome],
        role: 'resultsProvider'  // This will use the results provider's private key
      }, provider);
    }
    
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
  try {
    if (!deployedContracts.marketFactory) {
      return res.status(400).json({ error: 'MarketFactory not deployed yet' });
    }
    
    const provider = setupProvider();
    const marketFactory = new ethers.Contract(
      deployedContracts.marketFactory.address, 
      MarketFactoryJson.abi, 
      provider
    );
    
    console.log('Getting all markets...');
    const count = await marketFactory.getDeployedMarketsCount();
    
    const markets = [];
    for (let i = 0; i < count; i++) {
      const marketAddress = await marketFactory.deployedMarkets(i);
      const market = new ethers.Contract(marketAddress, NBAMarketJson.abi, provider);
      
      // Get all market info using the individual getter functions
      const homeTeam = await market.getHomeTeam();
      const awayTeam = await market.getAwayTeam();
      const gameTimestamp = await market.getGameTimestamp();
      const oddsApiId = await market.getOddsApiId();
      const odds = await market.getOdds();
      const status = await market.getGameStatus();
      const exposure = await market.getExposureInfo();
      const isReadyForBetting = await market.isReadyForBetting();
      
      markets.push({
        address: marketAddress,
        homeTeam,
        awayTeam,
        gameTimestamp: gameTimestamp.toString(),
        oddsApiId,
        homeOdds: odds[0].toString(),
        awayOdds: odds[1].toString(),
        gameStarted: status[0],
        gameEnded: status[1],
        oddsSet: status[2],
        outcome: status[3],
        maxExposure: ethers.utils.formatUnits(exposure[0], 6),
        currentExposure: ethers.utils.formatUnits(exposure[1], 6),
        isReadyForBetting
      });
    }
    
    res.json(markets);
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