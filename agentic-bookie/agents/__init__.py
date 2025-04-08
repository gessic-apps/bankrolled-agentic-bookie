# agents package
# from .agentGroup import (
#     AgentContext,
#     triage_agent,
#     market_creation_agent,
#     odds_manager_agent,
#     process_request,
#     process_odds_update_request,
#     handle_new_market_notification
# )

# Remove these imports to break the circular dependency
# from .agentGroup import triage_agent
# from .market_creation_agent import market_creation_agent
# from .odds_manager_agent import odds_manager_agent
# from .game_status_agent import game_status_agent

# Define the public interface of the agents package (optional, can be empty)
__all__ = [
    # "triage_agent",
    # "market_creation_agent",
    # "odds_manager_agent",
    # "game_status_agent",
]

# This list is likely not needed here if agent instances are created and managed elsewhere (e.g., agentGroup.py)
# available_agents = [
#     market_creation_agent,
#     odds_manager_agent,
#     game_status_agent,
#     # ... any other agents ...
# ]