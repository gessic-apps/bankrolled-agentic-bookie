import { NextResponse } from 'next/server';

// Define the actual backend API URL (replace if different)
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:3000'; // Or your backend port

type RouteParams = {
  params: {
    marketAddress: string;
    bettorAddress: string;
  };
};

export async function GET(request: Request, { params }: RouteParams) {
  const { marketAddress, bettorAddress } = params;

  if (!marketAddress || !bettorAddress) {
    return NextResponse.json({ error: 'Market address and bettor address are required' }, { status: 400 });
  }

  // Basic address validation (optional, but recommended)
  if (!/^0x[a-fA-F0-9]{40}$/.test(marketAddress) || !/^0x[a-fA-F0-9]{40}$/.test(bettorAddress)) {
     return NextResponse.json({ error: 'Invalid address format' }, { status: 400 });
  }

  try {
    const backendResponse = await fetch(`${BACKEND_API_URL}/api/market/${marketAddress}/bets/${bettorAddress}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      // Add caching strategy if desired, e.g., revalidate frequently
      cache: 'no-store', 
    });

    const data = await backendResponse.json();

    if (!backendResponse.ok) {
      // Forward the error from the backend
      // Handle cases where the backend might return non-JSON error messages or specific statuses
      console.error(`Backend error fetching bets for market ${marketAddress}, user ${bettorAddress}:`, backendResponse.status, data);
      return NextResponse.json({ error: data.error || data.message || `Failed to fetch bets (Status: ${backendResponse.status})` }, { status: backendResponse.status });
    }

    // Forward the success response (which should be an array of bets)
    return NextResponse.json(data, { status: 200 });

  } catch (error: any) {
    console.error('User Bets API route error:', error);
    return NextResponse.json({ error: 'Internal Server Error', details: error.message }, { status: 500 });
  }
} 