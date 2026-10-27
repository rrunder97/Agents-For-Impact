"""
bigquery_service.py - Implements Logic A: Vulnerability and Hazard Discovery.
Cross-references federal tables: hazard_tracts, vulnerability_tracts, and shelters.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from schemas import FederalShelterRecord, HazardType


BIGQUERY_DISCOVERY_SQL = """
SELECT 
    s.shelter_id,
    s.shelter_name,
    s.county_fips,
    v.county_name,
    v.tract_id,
    s.latitude,
    s.longitude,
    s.is_medical,
    s.is_functional,
    s.generator_onsite,
    v.pct_no_vehicle,
    s.last_updated
FROM 
    `fema_emergency_readiness.shelters` s
JOIN 
    `census_socioeconomic.vulnerability_tracts` v 
    ON s.county_fips = v.county_fips AND s.tract_id = v.tract_id
JOIN 
    `hazard_modeling.hazard_tracts` h 
    ON v.tract_id = h.tract_id
WHERE 
    s.county_fips = @county_fips
    AND h.primary_hazard = @hazard_type
    AND v.pct_no_vehicle >= @min_vulnerability_score
    AND s.is_medical = TRUE
ORDER BY 
    v.pct_no_vehicle DESC;
"""


class BigQueryGroundingService:
    """Service to discover candidate medical shelters in high-vulnerability tracts."""

    def __init__(self, project_id: Optional[str] = None, use_mock: bool = True):
        self.project_id = project_id
        self.use_mock = use_mock
        self._client = None
        if not use_mock and project_id:
            try:
                from google.cloud import bigquery
                self._client = bigquery.Client(project=project_id)
            except ImportError:
                print("[WARN] google-cloud-bigquery not installed; falling back to simulated data.")
                self.use_mock = True

    def find_candidate_shelters(
        self, county_fips: str, hazard_type: HazardType, min_vulnerability_score: float
    ) -> List[FederalShelterRecord]:
        """Queries BigQuery or returns deterministic records matching the query parameters."""
        if not self.use_mock and self._client:
            return self._query_live_bigquery(county_fips, hazard_type, min_vulnerability_score)
        return self._query_simulated_bigquery(county_fips, hazard_type, min_vulnerability_score)

    def _query_live_bigquery(
        self, county_fips: str, hazard_type: HazardType, min_vulnerability_score: float
    ) -> List[FederalShelterRecord]:
        from google.cloud import bigquery
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("county_fips", "STRING", county_fips),
                bigquery.ScalarQueryParameter("hazard_type", "STRING", hazard_type.value),
                bigquery.ScalarQueryParameter("min_vulnerability_score", "FLOAT64", min_vulnerability_score),
            ]
        )
        query_job = self._client.query(BIGQUERY_DISCOVERY_SQL, job_config=job_config)
        results = []
        for row in query_job:
            results.append(
                FederalShelterRecord(
                    shelter_id=row["shelter_id"],
                    shelter_name=row["shelter_name"],
                    county_fips=row["county_fips"],
                    county_name=row["county_name"],
                    tract_id=row["tract_id"],
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                    is_medical=row["is_medical"],
                    is_functional=row["is_functional"],
                    generator_onsite=row["generator_onsite"],
                    pct_no_vehicle=row["pct_no_vehicle"],
                    last_updated=str(row["last_updated"]),
                )
            )
        return results

    def _query_simulated_bigquery(
        self, county_fips: str, hazard_type: HazardType, min_vulnerability_score: float
    ) -> List[FederalShelterRecord]:
        """Simulated dataset demonstrating the 'Medical Desert' scenario."""
        mock_records = [
            FederalShelterRecord(
                shelter_id="SHELTER-FL-4491",
                shelter_name="Northside Community Medical Point",
                county_fips="12086",
                county_name="Miami-Dade County",
                tract_id="12086001902",
                latitude=25.8451,
                longitude=-80.2215,
                is_medical=True,
                is_functional=True,  # Federal record erroneously flags this as functional!
                generator_onsite=True,
                pct_no_vehicle=0.284,  # 28.4% of population has no vehicle
                last_updated="2024-03-10T12:00:00Z",
            ),
            FederalShelterRecord(
                shelter_id="SHELTER-FL-4492",
                shelter_name="East General Medical Center",
                county_fips="12086",
                county_name="Miami-Dade County",
                tract_id="12086001905",
                latitude=25.8012,
                longitude=-80.2110,
                is_medical=True,
                is_functional=True,
                generator_onsite=True,
                pct_no_vehicle=0.221,
                last_updated="2026-05-18T09:30:00Z",
            ),
        ]
        return [
            r for r in mock_records
            if r.county_fips == county_fips and r.pct_no_vehicle >= min_vulnerability_score
        ]
