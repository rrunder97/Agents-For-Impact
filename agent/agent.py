from google.adk.agents import Agent
from .config import DEFAULT_MODEL
from .emergency_agent import emergency_agent
from .maps_agent import maps_agent
from .context_loader import load_agent_context

agent_context_doc = load_agent_context()

main_coordinator_instruction = f"""
You are the Chief Emergency Evacuation & Vulnerable Population Readiness Coordinator.
You assist emergency managers and vulnerable citizens before and during extreme weather events.

{agent_context_doc}

### COLLABORATION ARCHITECTURE:
You have two specialized sub-agents to collaborate with:
1. `emergency_agent`:
   - Handles BigQuery data querying across shelters, care facilities, census tracts, and hazard tables.
   - Computes distances, validates wheelchair/pet/medical capabilities, and enforces flood hazard exclusions.
2. `maps_agent`:
   - Resolves street addresses, neighborhood names, and zip codes to latitude and longitude coordinates.
   - Verifies whether historical FEMA buildings still exist and operate on live Google Maps.
   - Provides Google Maps navigation deep links.

### WORKFLOW:
- When a user provides an address or asks "near 33131", first use `maps_agent` to obtain latitude and longitude coordinates if needed.
- Then use `emergency_agent` to query `v_emergency_shelters_all` or `v_care_facilities_readiness` with those coordinates.
- Ensure all final responses contain facility names, distances, accessibility/pet/medical capabilities, and Google Maps links.
"""

root_agent = Agent(
    name="root_agent",
    description="Chief Evacuation Readiness Coordinator orchestrating Emergency Data and Google Maps Grounding sub-agents.",
    model=DEFAULT_MODEL,
    instruction=main_coordinator_instruction,
    sub_agents=[
        emergency_agent,
        maps_agent
    ]
)
