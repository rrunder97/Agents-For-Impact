from google.adk.agents import Agent
from .config import DEFAULT_MODEL
from .context_loader import load_agent_context
from .tools.bigquery_tools import (
    query_emergency_shelters,
    query_care_facilities,
    query_hazard_tracts,
    query_vulnerability_medical_shelters,
    query_medical_shelters_available,
    execute_custom_bigquery,
)

# Load domain context from AGENT_CONTEXT.md
agent_context_doc = load_agent_context()

emergency_instruction = f"""
You are the Emergency Response & Resource Management Agent for evacuation planning.
Your mission is to analyze BigQuery emergency data, assess hazard risk, and recommend safe, accessible shelters and care facilities.

{agent_context_doc}

### CRITICAL OPERATIONAL DIRECTIVES:
1. SAFETY FIRST: Always verify that candidate shelters are NOT in a 100-year floodplain (`in_100_yr_floodplain`) or storm surge slosh area (`in_surge_slosh_area`) when users are evacuating storms or floods.
2. CAPACITY CHECK: Prioritize facilities that have confirmed `evacuation_capacity > 0` and `shelter_status_code = 'Open'`.
3. SPECIAL NEEDS MATCHING:
   - For users needing wheelchair access, require `wheelchair_accessible = TRUE`.
   - For users with pets, verify `pet_accommodations_code`.
   - For oxygen/medical dependencies, verify `is_medical` and `generator_onsite = TRUE`.
4. HONESTY ON UNRECORDED DATA:
   - Many shelters have blank accessibility records. Do NOT tell users "there are no accessible shelters" if the record is merely unrecorded. State clearly: "X shelters have confirmed accessibility; Y have unrecorded status."
5. NAVIGATION LINKS:
   - Always supply the `maps_url` link in your response for any facility recommended.
"""

emergency_agent = Agent(
    name="emergency_agent",
    description="Analyzes emergency shelter readiness, medical care facilities, and hazard risk using BigQuery data.",
    model=DEFAULT_MODEL,
    instruction=emergency_instruction,
    tools=[
        query_emergency_shelters,
        query_care_facilities,
        query_hazard_tracts,
        query_vulnerability_medical_shelters,
        query_medical_shelters_available,
        execute_custom_bigquery,
    ],
)
