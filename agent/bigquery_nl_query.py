"""
bigquery_nl_query.py - Text-to-SQL Query Service for Emergency Shelters View.
Target View: qwiklabs-gcp-03-82491e646971.evacuation_readiness.v_emergency_shelters_all
"""

import json
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

TARGET_VIEW = "`qwiklabs-gcp-03-82491e646971.evacuation_readiness.v_emergency_shelters_all`"

VIEW_METADATA_PROMPT = f"""
You are a specialized BigQuery SQL Engineer for Disaster Preparedness and Emergency Response.
Your objective is to translate natural language questions into valid, optimized, read-only BigQuery Standard SQL for the following view:

Table/View: {TARGET_VIEW}
Description: Comprehensive metadata for emergency shelters including spatial coordinates, capacity, accessibility, and environmental hazard risks.

Columns & Types:
- shelter_id (INT64): Unique shelter identifier.
- shelter_name (STRING): Facility name.
- address_1 (STRING): Street address.
- city (STRING): City name.
- zip (STRING): Postal code.
- latitude (FLOAT64): Decimal latitude.
- longitude (FLOAT64): Decimal longitude.
- geog_point (GEOGRAPHY): Native BigQuery Geography object for spatial calculations.
- maps_url (STRING): Google Maps navigation link.
- evacuation_capacity (FLOAT64): Maximum individual capacity.
- shelter_status_code (STRING): Current status (e.g. 'Open', 'Full', 'Closed').
- wheelchair_accessible (BOOL): ADA wheelchair accessibility flag.
- is_medical (BOOL): Equipped for medical needs.
- is_functional (BOOL): Facility is currently operational.
- pet_accommodations_code (STRING): Details regarding pets allowed.
- generator_onsite (BOOL): On-site backup power generator available.
- self_sufficient_electricity (BOOL): Able to operate off-grid for power.
- in_surge_slosh_area (BOOL): TRUE if in a hurricane storm surge inundation zone.
- in_100_yr_floodplain (BOOL): TRUE if in a 1% annual chance (100-year) flood zone.

SQL Rules & Spatial Guidelines:
1. SELECT queries ONLY. Never generate INSERT, UPDATE, DELETE, DROP, or ALTER.
2. For spatial radius/proximity searches, ALWAYS use `ST_DWITHIN(geog_point, ST_GEOGPOINT(longitude, latitude), distance_meters)`.
   Notice: ST_GEOGPOINT expects (longitude, latitude) in that order!
   To calculate distance, use `ST_DISTANCE(geog_point, ST_GEOGPOINT(longitude, latitude))`.
   1 mile ≈ 1609.34 meters.
3. For hazard risk queries:
   - Safe from flood: `in_100_yr_floodplain = FALSE`
   - Safe from storm surge: `in_surge_slosh_area = FALSE`
4. For capacity calculations:
   - Use `SUM(evacuation_capacity)` or `AVG(evacuation_capacity)`. Use `COALESCE(evacuation_capacity, 0)`.
5. For active/open facilities:
   - Use `is_functional = TRUE` and/or `LOWER(shelter_status_code) = 'open'`.
6. Always include a sensible `LIMIT` (default 50) unless doing a high-level aggregation with `GROUP BY`.
7. Return ONLY the raw SQL statement or structured JSON. Do NOT wrap in markdown quotes if returning raw string.
"""


class QuerySheltersNLInput(BaseModel):
    query: str = Field(..., description="Natural language request about emergency shelters (e.g., 'Find all medical shelters with generators outside flood zones in Tampa').")
    limit: Optional[int] = Field(default=50, description="Maximum rows to return.")


class BigQueryNLQueryEngine:
    """Translates natural language to BigQuery SQL and executes against the emergency shelters view."""

    def __init__(self, project_id: str = "qwiklabs-gcp-03-82491e646971", use_mock: bool = True):
        self.project_id = project_id
        self.use_mock = use_mock
        self._client = None
        if not use_mock:
            try:
                from google.cloud import bigquery
                self._client = bigquery.Client(project=project_id)
            except Exception as e:
                print(f"[WARN] BigQuery client initialization failed: {e}. Using mock mode.")
                self.use_mock = True

    def generate_sql(self, natural_language_query: str, limit: int = 50) -> str:
        """Translates natural language into BigQuery Standard SQL using semantic pattern matching or LLM."""
        q = natural_language_query.lower()

        # Spatial Proximity: coordinates / distance
        coord_match = re.search(r'(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)', q)
        radius_match = re.search(r'(\d+)\s*(?:mile|mi|km|meter)', q)

        if "capacity" in q and "by city" in q:
            return (
                f"SELECT \n"
                f"    city,\n"
                f"    COUNT(*) AS total_shelters,\n"
                f"    SUM(CASE WHEN is_functional THEN 1 ELSE 0 END) AS functional_shelters,\n"
                f"    SUM(COALESCE(evacuation_capacity, 0)) AS total_evacuation_capacity\n"
                f"FROM {TARGET_VIEW}\n"
                f"WHERE is_functional = TRUE\n"
                f"GROUP BY city\n"
                f"ORDER BY total_evacuation_capacity DESC\n"
                f"LIMIT {limit};"
            )

        if "wheelchair" in q and ("medical" in q or "hospital" in q):
            return (
                f"SELECT \n"
                f"    shelter_id, shelter_name, address_1, city, evacuation_capacity,\n"
                f"    wheelchair_accessible, is_medical, generator_onsite, maps_url\n"
                f"FROM {TARGET_VIEW}\n"
                f"WHERE is_functional = TRUE\n"
                f"  AND wheelchair_accessible = TRUE\n"
                f"  AND is_medical = TRUE\n"
                f"ORDER BY evacuation_capacity DESC\n"
                f"LIMIT {limit};"
            )

        if "generator" in q and ("nearest" in q or "shelter" in q or "backup" in q):
            return (
                f"SELECT \n"
                f"    shelter_id, shelter_name, address_1, city, evacuation_capacity,\n"
                f"    wheelchair_accessible, is_medical, generator_onsite, maps_url\n"
                f"FROM {TARGET_VIEW}\n"
                f"WHERE is_functional = TRUE\n"
                f"  AND generator_onsite = TRUE\n"
                f"ORDER BY evacuation_capacity DESC\n"
                f"LIMIT {limit};"
            )

        if "medical" in q and ("generator" in q or "power" in q) and ("flood" in q or "surge" in q or "safe" in q):
            return (
                f"SELECT \n"
                f"    shelter_id, shelter_name, city, zip, evacuation_capacity, \n"
                f"    generator_onsite, in_surge_slosh_area, in_100_yr_floodplain, maps_url\n"
                f"FROM {TARGET_VIEW}\n"
                f"WHERE is_medical = TRUE \n"
                f"  AND is_functional = TRUE \n"
                f"  AND generator_onsite = TRUE\n"
                f"  AND in_100_yr_floodplain = FALSE\n"
                f"  AND in_surge_slosh_area = FALSE\n"
                f"ORDER BY evacuation_capacity DESC\n"
                f"LIMIT {limit};"
            )

        if coord_match and radius_match:
            lat = float(coord_match.group(1))
            lng = float(coord_match.group(2))
            # Swap if lat/lng were inverted (typical US lats are 24-49, lngs -125 to -66)
            if lat < 0 and lng > 0:
                lat, lng = lng, lat
            miles = float(radius_match.group(1))
            meters = miles * 1609.34

            return (
                f"SELECT \n"
                f"    shelter_id, shelter_name, address_1, city, evacuation_capacity,\n"
                f"    wheelchair_accessible, is_medical, generator_onsite, maps_url,\n"
                f"    ROUND(ST_DISTANCE(geog_point, ST_GEOGPOINT({lng}, {lat})) / 1609.34, 2) AS distance_miles\n"
                f"FROM {TARGET_VIEW}\n"
                f"WHERE is_functional = TRUE\n"
                f"  AND ST_DWITHIN(geog_point, ST_GEOGPOINT({lng}, {lat}), {meters:.1f})\n"
                f"ORDER BY distance_miles ASC\n"
                f"LIMIT {limit};"
            )

        # Default smart query: Operational shelters with safety flags
        return (
            f"SELECT \n"
            f"    shelter_id, shelter_name, city, evacuation_capacity,\n"
            f"    is_medical, wheelchair_accessible, generator_onsite,\n"
            f"    in_surge_slosh_area, in_100_yr_floodplain, maps_url\n"
            f"FROM {TARGET_VIEW}\n"
            f"WHERE is_functional = TRUE\n"
            f"ORDER BY evacuation_capacity DESC\n"
            f"LIMIT {limit};"
        )

    def execute_query(self, sql: str) -> Dict[str, Any]:
        """Executes query or validates dry-run."""
        if not self.use_mock and self._client:
            from google.cloud import bigquery
            # Dry-run validation first
            dry_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
            dry_job = self._client.query(sql, job_config=dry_config)
            bytes_processed = dry_job.total_bytes_processed

            # Actual execution
            query_job = self._client.query(sql)
            rows = [dict(row) for row in query_job.result()]
            return {
                "status": "SUCCESS",
                "sql": sql,
                "bytes_processed": bytes_processed,
                "row_count": len(rows),
                "data": rows
            }

        # Simulated response for testing
        return {
            "status": "SUCCESS",
            "sql": sql,
            "simulated": True,
            "row_count": 2,
            "data": [
                {
                    "shelter_id": 10491,
                    "shelter_name": "Metro Regional Care Facility",
                    "city": "Miami",
                    "evacuation_capacity": 450.0,
                    "generator_onsite": True,
                    "in_surge_slosh_area": False,
                    "in_100_yr_floodplain": False,
                    "maps_url": "https://maps.google.com/?q=25.8012,-80.2110"
                },
                {
                    "shelter_id": 10492,
                    "shelter_name": "Biscayne Community Center",
                    "city": "Miami",
                    "evacuation_capacity": 320.0,
                    "generator_onsite": True,
                    "in_surge_slosh_area": False,
                    "in_100_yr_floodplain": False,
                    "maps_url": "https://maps.google.com/?q=25.8122,-80.1980"
                }
            ]
        }
