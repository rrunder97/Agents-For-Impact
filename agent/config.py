import os

# Google Cloud Configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-82491e646971")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
DATASET_ID = os.getenv("BIGQUERY_DATASET", "evacuation_readiness")

# BigQuery Objects
TABLE_SHELTERS_ALL = f"{PROJECT_ID}.{DATASET_ID}.v_emergency_shelters_all"
TABLE_SHELTERS_ACTIVE = f"{PROJECT_ID}.{DATASET_ID}.v_emergency_shelters"
VIEW_CARE_FACILITIES = f"{PROJECT_ID}.{DATASET_ID}.v_care_facilities_readiness"
TABLE_HAZARD_TRACTS = f"{PROJECT_ID}.{DATASET_ID}.hazard_tracts"
TABLE_VULNERABILITY_MEDICAL = f"{PROJECT_ID}.{DATASET_ID}.vulnerability_tract_medical_shelters"
TABLE_MEDICAL_SHELTERS = f"{PROJECT_ID}.{DATASET_ID}.medical_shelters_available"

# Gemini Model Selection (gemini-2.5-flash is active in Vertex AI for this project)
DEFAULT_MODEL = os.getenv("ADK_MODEL", "gemini-2.5-flash")

# Google Maps Grounding & MCP Endpoint
MAPS_MCP_URL = os.getenv("MAPS_MCP_URL", "https://mapstools.googleapis.com/mcp")
