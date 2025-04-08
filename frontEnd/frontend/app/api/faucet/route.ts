import { NextResponse } from 'next/server';

// Define the actual backend API URL (replace if different)
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:3000'; // Or your backend port

export async function POST(request: Request) {
  try {
    const { address } = await request.json();
    console.log('address!', address);
    if (!address) {
      return NextResponse.json({ error: 'Address is required' }, { status: 400 });
    }
    console.log('continue!', address);
    // Amount to mint (can be fixed or passed from frontend if needed)
    const amount = 1000;

    const backendResponse = await fetch(`${BACKEND_API_URL}/api/faucet`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ address, amount }),
    });
    console.log('backendResponse', backendResponse);
    const data = await backendResponse.json();
    console.log('data', data);
    if (!backendResponse.ok) {
      // Forward the error from the backend
      return NextResponse.json(data, { status: backendResponse.status });
    }

    // Forward the success response from the backend
    return NextResponse.json(data, { status: 200 });

  } catch (error: any) {
    console.error('Faucet API route error:', error);
    return NextResponse.json({ error: 'Internal Server Error', details: error.message }, { status: 500 });
  }
} 