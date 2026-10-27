"""
bigquery_service.py - Implements Logic A: Vulnerability and Hazard Discovery.
Cross-references federal tables via Google MCP Toolbox for Databases.
"""

from typing import List, Dict, Any, Optional
try:
    from .schemas import FederalShelterRecord, HazardType
    from .mcp.toolbox_client import default_toolbox_client, MCPToolboxClient
except ImportError:
    from schemas import FederalShelterRecord, HazardType
    from mcp.toolbox_client import default_toolbox_client, MCPToolboxClient


class BigQueryGroundingService:
    """Service to discover candidate medical shelters via MCP Toolbox for Databases."""

    def __init__(self, project_id: Optional[str] = None, use_mock: bool = False, toolbox_client: Optional[MCPToolboxClient] = None):
        self.project_id = project_id
        self.use_mock = use_mock
        self.toolbox = toolbox_client or default_toolbox_client

    def find_candidate_shelters(
        self, county_fips: str, hazard_type: HazardType, min_vulnerability_score: float
    ) -> List[FederalShelterRecord]:
        """Queries BigQuery through MCP Toolbox tool 'query_candidate_medical_shelters'."""
        raw_shelters = self.toolbox.call_tool(
            "query_candidate_medical_shelters",
            {
                "county_fips": county_fips,
                "hazard_type": hazard_type.value,
                "min_vulnerability_score": min_vulnerability_score
            }
        )

        results: List[FederalShelterRecord] = []
        if isinstance(raw_shelters, list):
            for row in raw_shelters:
                if row.get("county_fips") == county_fips and float(row.get("pct_no_vehicle", 0)) >= min_vulnerability_score:
                    results.append(
                        FederalShelterRecord(
                            shelter_id=row["shelter_id"],
                            shelter_name=row["shelter_name"],
                            county_fips=row["county_fips"],
                            county_name=row.get("county_name", "County"),
                            tract_id=row["tract_id"],
                            latitude=float(row["latitude"]),
                            longitude=float(row["longitude"]),
                            is_medical=bool(row.get("is_medical", True)),
                            is_functional=bool(row.get("is_functional", True)),
                            generator_onsite=bool(row.get("generator_onsite", True)),
                            pct_no_vehicle=float(row.get("pct_no_vehicle", 0.0)),
                            last_updated=str(row.get("last_updated", "")),
                        )
                    )
        return results
