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

# Gemini Model Selection
DEFAULT_MODEL = os.getenv("ADK_MODEL", "gemini-2.5-flash")

# Model Context Protocol (MCP) Endpoints
MCP_TOOLBOX_URL = os.getenv("MCP_TOOLBOX_URL", "http://localhost:5000")
MAPS_MCP_URL = os.getenv("MAPS_MCP_URL", "https://mapstools.googleapis.com/mcp")
MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
USE_MCP = os.getenv("USE_MCP", "true").lower() in ("true", "1", "yes")
