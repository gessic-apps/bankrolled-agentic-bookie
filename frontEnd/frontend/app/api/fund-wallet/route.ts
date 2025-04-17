import { NextResponse } from 'next/server';
import { ethers } from 'ethers';
import {  WAGMI_CONFIG } from '@/config/contracts';

// Use server admin wallet to fund managed wallets with a small amount of ETH for gas
// In production, this private key should be in env vars and properly secured
const ADMIN_PRIVATE_KEY = process.env.ADMIN_PRIVATE_KEY || '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'; // Hardhat default key

export async function POST(request: Request) {
  try {
    const { address } = await request.json();
    
    if (!address) {
      return NextResponse.json({ error: 'Address is required' }, { status: 400 });
    }
    
    // Create a provider
    const provider = new ethers.JsonRpcProvider(WAGMI_CONFIG.RPC_URL);
    
    // Create a wallet from the admin private key
    const adminWallet = new ethers.Wallet(ADMIN_PRIVATE_KEY, provider);
    
    // Amount of ETH to send (0.01 ETH should be enough for multiple transactions)
    const fundAmount = ethers.parseEther("0.0001");
    
    // Check if address already has ETH
    const currentBalance = await provider.getBalance(address);
    
    if (currentBalance > ethers.parseEther("0.0001")) {
      // Already has enough ETH, no need to send more
      return NextResponse.json({ 
        message: `Wallet already has ${ethers.formatEther(currentBalance)} ETH, no additional funds sent.`,
        transaction: null,
        success: true
      });
    }
    
    // Send ETH to the managed wallet
    const tx = await adminWallet.sendTransaction({
      to: address,
      value: fundAmount
    });
    
    // Wait for transaction to be mined
    await tx.wait();
    
    return NextResponse.json({ 
      message: `Successfully sent ${ethers.formatEther(fundAmount)} ETH to ${address}`,
      transaction: tx.hash,
      success: true
    });
    
  } catch (error: any) {
    console.error('Fund wallet API route error:', error);
    return NextResponse.json({ 
      error: 'Failed to fund wallet', 
      details: error.message,
      success: false
    }, { status: 500 });
  }
}