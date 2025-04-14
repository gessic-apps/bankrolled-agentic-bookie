import { NextResponse } from 'next/server';

// TODO: Make the backend URL configurable via environment variables
const BACKEND_URL = 'http://localhost:3000';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/getAgentOutput`, {
        cache: 'no-store', // Ensure fresh data is fetched every time
        headers: {
            'Content-Type': 'application/json',
        },
    });

    if (!response.ok) {
        console.error(`Error fetching agent output: ${response.status} ${response.statusText}`);
        const errorBody = await response.text();
        console.error("Error body:", errorBody);
        throw new Error(`Failed to fetch agent reports from backend. Status: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error: unknown) {
    console.error("Error in agent-reports API route:", error);
    const message = error instanceof Error ? error.message : 'An unknown error occurred';
    // Return a proper JSON error response
    return NextResponse.json(
        { error: 'Failed to fetch agent reports', details: message },
        { status: 500 }
    );
  }
} 