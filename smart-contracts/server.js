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
  markets: []
};

// Load contract artifacts
const MarketFactoryJson = require('./artifacts/contracts/MarketFactory.sol/MarketFactory.json');
const NBAMarketJson = require('./artifacts/contracts/NBAMarket.sol/NBAMarket.json');

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
    const { oddsProviderAddress, resultsProviderAddress } = req.body;
    
    if (!oddsProviderAddress || !resultsProviderAddress) {
      return res.status(400).json({ error: 'oddsProviderAddress and resultsProviderAddress are required' });
    }
    
    const provider = setupProvider();
    const wallet = getDefaultWallet(provider);
    
    const MarketFactory = new ethers.ContractFactory(
      MarketFactoryJson.abi, 
      MarketFactoryJson.bytecode, 
      wallet
    );
    
    console.log('Deploying MarketFactory...');
    const marketFactory = await MarketFactory.deploy(oddsProviderAddress, resultsProviderAddress);
    await marketFactory.deployed();
    
    deployedContracts.marketFactory = {
      address: marketFactory.address,
      oddsProvider: oddsProviderAddress,
      resultsProvider: resultsProviderAddress,
      deployedAt: new Date().toISOString()
    };
    
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
    const { homeTeam, awayTeam, gameTimestamp, homeOdds, awayOdds } = req.body;
    
    if (!deployedContracts.marketFactory) {
      return res.status(400).json({ error: 'MarketFactory not deployed yet' });
    }
    
    if (!homeTeam || !awayTeam || !gameTimestamp) {
      return res.status(400).json({ error: 'homeTeam, awayTeam, and gameTimestamp are required' });
    }
    
    const provider = setupProvider();
    const factoryAddress = deployedContracts.marketFactory.address;
    
    console.log('Creating market...');
    let result;
    
    if (homeOdds && awayOdds) {
      // Create market with odds
      result = await signAndSendTransaction({
        contractAddress: factoryAddress,
        contractAbi: MarketFactoryJson.abi,
        method: 'createMarket',
        params: [homeTeam, awayTeam, gameTimestamp, homeOdds, awayOdds],
        role: 'admin'
      }, provider);
    } else {
      // Create market without odds
      result = await signAndSendTransaction({
        contractAddress: factoryAddress,
        contractAbi: MarketFactoryJson.abi,
        method: 'createMarketWithoutOdds',
        params: [homeTeam, awayTeam, gameTimestamp],
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
      homeOdds: homeOdds || 0,
      awayOdds: awayOdds || 0,
      oddsSet: !!(homeOdds && awayOdds && homeOdds >= 1000 && awayOdds >= 1000),
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

// Get market info
app.get('/api/market/:address', async (req, res) => {
  try {
    const { address } = req.params;
    
    const provider = setupProvider();
    
    const market = new ethers.Contract(
      address, 
      NBAMarketJson.abi, 
      provider
    );
    
    console.log(`Getting info for market ${address}...`);
    const info = await market.getMarketInfo();
    const isReadyForBetting = await market.isReadyForBetting();
    
    const marketInfo = {
      address,
      homeTeam: info[0],
      awayTeam: info[1],
      gameTimestamp: info[2].toString(),
      homeOdds: info[3].toString(),
      awayOdds: info[4].toString(),
      gameStarted: info[5],
      gameEnded: info[6],
      oddsSet: info[7],
      outcome: info[8],
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
      const market = new ethers.Contract(
        marketAddress, 
        NBAMarketJson.abi, 
        provider
      );
      
      const info = await market.getMarketInfo();
      const isReadyForBetting = await market.isReadyForBetting();
      
      markets.push({
        address: marketAddress,
        homeTeam: info[0],
        awayTeam: info[1],
        gameTimestamp: info[2].toString(),
        homeOdds: info[3].toString(),
        awayOdds: info[4].toString(),
        gameStarted: info[5],
        gameEnded: info[6],
        oddsSet: info[7],
        outcome: info[8],
        isReadyForBetting
      });
    }
    
    res.json(markets);
  } catch (error) {
    console.error('Error getting markets:', error);
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
          
          // Try to match with MarketFactory events
          const marketFactoryInterface = new ethers.utils.Interface(MarketFactoryJson.abi);
          try {
            const decoded = marketFactoryInterface.parseLog(log);
            eventName = decoded.name;
            decodedData = decoded.args;
          } catch (e) {
            // Try NBAMarket if MarketFactory fails
            try {
              const nbaMarketInterface = new ethers.utils.Interface(NBAMarketJson.abi);
              const decoded = nbaMarketInterface.parseLog(log);
              eventName = decoded.name;
              decodedData = decoded.args;
            } catch (e) {
              // Unable to decode with available ABIs
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