import logging
from google.adk.agents import Agent
from .config import DEFAULT_MODEL
from .tools.maps_tools import (
    geocode_address,
    verify_shelter_on_google_maps
)

logger = logging.getLogger(__name__)

# Attempt to include built-in Google Maps Grounding tool
maps_tools = [geocode_address, verify_shelter_on_google_maps]
try:
    from google.adk.tools import google_maps_grounding
    maps_tools.append(google_maps_grounding)
    logger.info("Loaded ADK google_maps_grounding tool successfully.")
except Exception as e:
    logger.warning("Could not load google_maps_grounding: %s. Using standard geocoding tools.", e)

maps_instruction = """
You are the Maps & Geospatial Grounding Agent.
Your role is to handle location resolution, coordinate lookups (latitude and longitude), live Google Maps verification, and routing for emergency operations.

### YOUR CAPABILITIES:
1. Address & Zip Resolution: When a user or coordinator mentions an address or zip code, resolve it to latitude and longitude coordinates.
2. Live Facility Verification: The emergency shelters database contains historical FEMA registrations. Use Google Maps to verify whether the facility still exists, is open, or has been renamed/demolished.
3. Driving Directions & Deep Links: Generate Google Maps navigation URLs for safe routing.
4. Attribution: When displaying Google Maps information, retain 'Google Maps' unmodified with translate="no".
"""

maps_agent = Agent(
    name="maps_agent",
    description="Resolves addresses to coordinates (lat/lon), verifies whether facilities still exist via Google Maps, and provides navigation links.",
    model=DEFAULT_MODEL,
    instruction=maps_instruction,
    tools=maps_tools,
)
