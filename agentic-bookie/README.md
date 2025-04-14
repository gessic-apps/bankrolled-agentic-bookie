# Agentic Bookie System

A system of specialized agents for managing sports betting markets, including market creation, odds management, game status tracking, and risk management.

## Project Structure

The project has been refactored to follow clean code principles and DRY (Don't Repeat Yourself) practices:

```
agentic-bookie/
├── agents/             # Agent definitions
│   ├── __init__.py     # Agent imports
│   ├── agentGroup.py   # Triage agent and agent coordination
│   ├── market_creation_agent.py
│   ├── odds_manager_agent.py
│   ├── game_status_agent.py
│   ├── risk_triage_agent.py
│   ├── high_risk_handler_agent.py
│   └── risk_manager_agent.py
│
├── utils/              # Shared utility functions
│   ├── __init__.py     
│   ├── config.py       # Shared configuration
│   │
│   ├── api/            # API client functions
│   │   ├── __init__.py
│   │   ├── client.py   # General API client
│   │   └── sports_api.py  # Sports API client
│   │
│   ├── markets/        # Market-related utilities
│   │   ├── __init__.py
│   │   ├── market_data.py        # Market data retrieval
│   │   ├── market_creation.py    # Market creation functions
│   │   ├── odds_management.py    # Odds management functions
│   │   └── odds_operations.py    # Combined odds operations
│   │
│   ├── sports/         # Sports data utilities
│   │   ├── __init__.py
│   │   ├── games_data.py   # Game data retrieval
│   │   └── game_status.py  # Game status functions
│   │
│   ├── monte_carlo/    # Monte Carlo simulation
│   │   ├── __init__.py
│   │   ├── models.py         # Data models for simulation
│   │   ├── simulator.py      # Monte Carlo simulator
│   │   └── analysis.py       # Risk analysis functions
│   │
│   ├── risk_management/  # Risk management functions
│   │   ├── __init__.py
│   │   ├── liquidity.py     # Liquidity management
│   │   └── exposure.py      # Exposure management
│   │
│   ├── predictions/    # Prediction tools
│   │   ├── __init__.py
│   │   └── market_predictions.py # Market prediction analysis
│   │
│   └── tests/          # Unit tests for utilities
│       ├── __init__.py
│       ├── test_sports_api.py
│       └── test_market_data.py
│
└── tools/              # Legacy tools directory
```

## Key Components

1. **Agents**: Each agent specializes in a specific function:
   - **Market Creation Agent**: Creates betting markets for upcoming games
   - **Odds Manager Agent**: Sets and updates odds for markets
   - **Game Status Agent**: Monitors game completion and settles results
   - **Risk Management Agents**: Handles market risk and liquidity

2. **Utilities**:
   - **API Clients**: Handles communication with platform API and sports data APIs
   - **Market Utilities**: Functions for working with markets (creation, data, odds)
   - **Sports Utilities**: Functions for fetching and processing sports game data
   - **Monte Carlo Simulation**: Risk assessment through simulation
   - **Risk Management**: Liquidity and exposure management functions
   - **Predictions**: Functions for analyzing user predictions
   - **Configuration**: Shared configuration like supported sports

## Single Responsibility Principle

Each module has been designed to have a single responsibility:

- `utils/api/client.py` - Handles general API interactions
- `utils/api/sports_api.py` - Specifically handles sports API requests
- `utils/markets/market_data.py` - Manages market data retrieval
- `utils/markets/market_creation.py` - Handles market creation
- `utils/markets/odds_management.py` - Manages market odds operations
- `utils/sports/games_data.py` - Retrieves game data
- `utils/sports/game_status.py` - Manages game status and settlement
- `utils/monte_carlo/simulator.py` - Performs Monte Carlo simulations
- `utils/monte_carlo/analysis.py` - Analyzes risk using simulation results
- `utils/risk_management/liquidity.py` - Handles liquidity operations
- `utils/risk_management/exposure.py` - Manages market exposure

## Testing

Each utility module includes a main function at the bottom that demonstrates how to use the functions in that module. For example:

```python
if __name__ == "__main__":
    # Example usage of functions in this module
    result = some_function(test_args)
    print(result)
```

## Usage

The system is controlled by the triage agent which routes requests to specialized agents:

```python
from agents import triage_agent, Runner
import asyncio

async def main():
    prompt = "Create betting markets for today's NBA games."
    result = await Runner.run(triage_agent, prompt)
    print(result.final_output)

asyncio.run(main())
```

## Development

To add new functionality:

1. Add implementation to the appropriate utility module
2. Create a test function in that module's `if __name__ == "__main__":` block
3. Update the corresponding agent to use the new utility function

## Running Tests

To test individual utility modules:

```bash
python -m utils.markets.market_data
python -m utils.monte_carlo.analysis
```

To run the full agent system:

```bash
python -m agents.agentGroup
```