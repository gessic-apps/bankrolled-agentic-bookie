/**
 * Market Exposure API Test Script
 * Tests the market-specific exposure limit API endpoints
 * 
 * Usage:
 *   node market-exposure-api.js get <market-address>
 *   node market-exposure-api.js set <market-address> <exposure-type> <value>
 *   node market-exposure-api.js set-all <market-address> <home-ml> <away-ml> <draw> <home-spread> <away-spread> <over> <under>
 */

const axios = require('axios');
const { ethers } = require('ethers');

const API_URL = 'http://localhost:3002';

// Parse command-line arguments
const command = process.argv[2];
const marketAddress = process.argv[3];

async function getExposureLimits(marketAddress) {
  try {
    console.log(`Fetching exposure limits for market ${marketAddress}...`);
    const response = await axios.get(`${API_URL}/api/market/${marketAddress}/exposure-limits`);
    
    console.log(JSON.stringify(response.data, null, 2));
    return response.data;
  } catch (error) {
    console.error('Error fetching exposure limits:', error.response?.data || error.message);
  }
}

async function setExposureLimit(marketAddress, type, value) {
  try {
    console.log(`Setting ${type} exposure limit to ${value} for market ${marketAddress}...`);
    
    // Map the type string to the appropriate parameter name
    const typeMap = {
      'homeMoneyline': 'homeMoneylineLimit',
      'awayMoneyline': 'awayMoneylineLimit',
      'draw': 'drawLimit',
      'homeSpread': 'homeSpreadLimit',
      'awaySpread': 'awaySpreadLimit',
      'over': 'overLimit',
      'under': 'underLimit'
    };
    
    const paramName = typeMap[type];
    if (!paramName) {
      throw new Error(`Invalid exposure type: ${type}. Valid types are: ${Object.keys(typeMap).join(', ')}`);
    }
    
    // Create request body with just the specified parameter
    const body = {
      [paramName]: value
    };
    
    const response = await axios.post(`${API_URL}/api/market/${marketAddress}/exposure-limits`, body);
    
    console.log(JSON.stringify(response.data, null, 2));
    return response.data;
  } catch (error) {
    console.error('Error setting exposure limit:', error.response?.data || error.message);
  }
}

async function setAllExposureLimits(marketAddress, homeMl, awayMl, draw, homeSpread, awaySpread, over, under) {
  try {
    console.log(`Setting all exposure limits for market ${marketAddress}...`);
    
    const body = {
      homeMoneylineLimit: homeMl,
      awayMoneylineLimit: awayMl,
      drawLimit: draw,
      homeSpreadLimit: homeSpread,
      awaySpreadLimit: awaySpread,
      overLimit: over,
      underLimit: under
    };
    
    const response = await axios.post(`${API_URL}/api/market/${marketAddress}/exposure-limits`, body);
    
    console.log(JSON.stringify(response.data, null, 2));
    return response.data;
  } catch (error) {
    console.error('Error setting all exposure limits:', error.response?.data || error.message);
  }
}

// Execute the requested command
async function main() {
  if (!command || !marketAddress) {
    console.log('Usage:');
    console.log('  node market-exposure-api.js get <market-address>');
    console.log('  node market-exposure-api.js set <market-address> <exposure-type> <value>');
    console.log('  node market-exposure-api.js set-all <market-address> <home-ml> <away-ml> <draw> <home-spread> <away-spread> <over> <under>');
    return;
  }
  
  // Check if market address is a valid Ethereum address
  if (!ethers.utils.isAddress(marketAddress)) {
    console.error('Invalid Ethereum address:', marketAddress);
    return;
  }
  
  switch (command.toLowerCase()) {
    case 'get':
      await getExposureLimits(marketAddress);
      break;
    
    case 'set':
      const type = process.argv[4];
      const value = process.argv[5];
      
      if (!type || value === undefined) {
        console.error('Missing required parameters for "set" command');
        console.log('Usage: node market-exposure-api.js set <market-address> <exposure-type> <value>');
        console.log('Valid exposure types: homeMoneyline, awayMoneyline, draw, homeSpread, awaySpread, over, under');
        return;
      }
      
      await setExposureLimit(marketAddress, type, value);
      break;
    
    case 'set-all':
      const homeMl = process.argv[4];
      const awayMl = process.argv[5];
      const draw = process.argv[6];
      const homeSpread = process.argv[7];
      const awaySpread = process.argv[8];
      const over = process.argv[9];
      const under = process.argv[10];
      
      if (!homeMl || !awayMl || !draw || !homeSpread || !awaySpread || !over || !under) {
        console.error('Missing required parameters for "set-all" command');
        console.log('Usage: node market-exposure-api.js set-all <market-address> <home-ml> <away-ml> <draw> <home-spread> <away-spread> <over> <under>');
        return;
      }
      
      await setAllExposureLimits(marketAddress, homeMl, awayMl, draw, homeSpread, awaySpread, over, under);
      break;
    
    default:
      console.error('Unknown command:', command);
      console.log('Valid commands: get, set, set-all');
  }
}

main().catch(console.error);