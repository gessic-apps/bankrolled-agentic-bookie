#!/usr/bin/env python3
import os
import sys
import asyncio
from dotenv import load_dotenv
from agents.risk_manager_agent import risk_manager_agent
from agents import Runner

# Load environment variables from .env file
load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:3000")

# Check if API_URL is set
if not API_URL:
    print(f"Warning: API_URL not found, defaulting to {API_URL}", file=sys.stderr)

async def test_risk_manager():
    """
    Test the Risk Manager Agent directly
    """
    prompt = "Analyze current markets and add liquidity where needed based on risk assessment."
    print(f"--- Running Risk Manager Agent with prompt: '{prompt}' ---")
    
    # Run the Risk Manager Agent
    result = await Runner.run(risk_manager_agent, prompt)
    
    # Display the result
    print("\n=== Risk Manager Agent Result ===")
    print(result.final_output)
    print("================================\n")

if __name__ == "__main__":
    print("=== Testing the Risk Manager Agent ===\n")
    asyncio.run(test_risk_manager())