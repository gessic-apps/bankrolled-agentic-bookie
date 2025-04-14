import { NextResponse } from 'next/server';

// Example backend API base URL - Replace with your actual backend URL
// You might want to use an environment variable for this
const BACKEND_API_URL = 'http://localhost:3000'; // Make sure this is correct

export async function GET(
  request: Request,
  { params }: { params: { marketAddress: string } }
) {
  const marketAddress = params.marketAddress;

  if (!marketAddress) {
    return NextResponse.json({ error: 'Market address is required' }, { status: 400 });
  }

  try {
    const apiUrl = `${BACKEND_API_URL}/api/market/${marketAddress}/exposure-limits`;
    console.log(`Proxying request to: ${apiUrl}`); // Log the URL being called

    const res = await fetch(apiUrl);

    if (!res.ok) {
      // Log the error response from the backend
      const errorBody = await res.text(); // Read error as text first
      console.error(`Error fetching limits from backend (${res.status}): ${errorBody}`);
      // Try to parse as JSON, but handle cases where it's not JSON
      let errorJson = { error: `Backend error: ${res.status}`, details: errorBody };
      try {
        errorJson = JSON.parse(errorBody);
      } catch (e) {
        console.error('Error parsing error JSON:', e);
        // Ignore JSON parsing error, use the text body
      }
      return NextResponse.json(errorJson, { status: res.status });
    }

    const data = await res.json();
    console.log(`Successfully fetched limits for ${marketAddress}:`, data);
    return NextResponse.json(data);

  } catch (error: any) {
    console.error(`Error in limits API route for ${marketAddress}:`, error);
    return NextResponse.json({ error: 'Failed to fetch exposure limits', details: error.message }, { status: 500 });
  }
} 