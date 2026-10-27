import os
from typing import List, Dict, Any, Optional
from google.cloud import bigquery

try:
    from google.adk.tools import FunctionTool
except ImportError:
    class FunctionTool:
        def __init__(self, func, **kwargs):
            self.func = func
            self.__doc__ = func.__doc__
        def __call__(self, *args, **kwargs):
            return self.func(*args, **kwargs)

PROJECT_ID = os.environ.get("GCP_PROJECT", "qwiklabs-gcp-03-82491e646971")
DATASET_TABLE = f"{PROJECT_ID}.evacuation_readiness.shelters"

bq_client = bigquery.Client()

def search_shelters_spatial(
    lat: float,
    lon: float,
    require_wheelchair: bool = False,
    require_medical: bool = False,
    require_generator: bool = False,
    include_closed: bool = False,
    limit: int = 3
) -> List[Dict[str, Any]]:
    """ADK Tool: Queries the BigQuery Evacuation Readiness dataset using spatial ST_DISTANCE geography functions.
    
    Args:
        lat: Latitude of user location.
        lon: Longitude of user location.
        require_wheelchair: If True, requires wheelchair accessibility.
        require_medical: If True, requires medical support readiness.
        require_generator: If True, requires backup generator power onsite.
        include_closed: If True, includes standby/closed shelters for preview/testing.
        limit: Maximum number of closest shelter records to return.
        
    Returns:
        List of matching shelter records ordered by distance, including real-time available capacity.
    """
    sql_query = f"""
    SELECT 
        shelter_id,
        shelter_name, 
        address_1, 
        city,
        latitude,
        longitude,
        shelter_status_code,
        evacuation_capacity,
        COALESCE(available_capacity, evacuation_capacity, 100.0) AS available_capacity,
        wheelchair_accessible,
        is_medical,
        generator_onsite,
        pet_accommodations_code,
        ROUND(ST_DISTANCE(ST_GEOGPOINT(longitude, latitude), ST_GEOGPOINT(@lon, @lat))) AS distance_meters
    FROM `{DATASET_TABLE}`
    WHERE (@include_closed = TRUE OR shelter_status_code = 'OPEN')
      AND (@req_wheelchair = FALSE OR wheelchair_accessible = TRUE)
      AND (@req_medical = FALSE OR is_medical = TRUE)
      AND (@req_generator = FALSE OR generator_onsite = TRUE)
    ORDER BY distance_meters ASC
    LIMIT @limit
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("lat", "FLOAT64", float(lat)),
            bigquery.ScalarQueryParameter("lon", "FLOAT64", float(lon)),
            bigquery.ScalarQueryParameter("include_closed", "BOOL", include_closed),
            bigquery.ScalarQueryParameter("req_wheelchair", "BOOL", require_wheelchair),
            bigquery.ScalarQueryParameter("req_medical", "BOOL", require_medical),
            bigquery.ScalarQueryParameter("req_generator", "BOOL", require_generator),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ]
    )

    query_job = bq_client.query(sql_query, job_config=job_config)
    return [dict(row) for row in query_job]

def book_shelter_capacity(shelter_id: int, count: int = 1) -> Dict[str, Any]:
    """ADK Tool: Atomically accepts an evacuee reservation for a shelter and decrements available capacity in BigQuery.
    
    Args:
        shelter_id: Integer shelter ID to book.
        count: Number of evacuee spots to reserve (default: 1).
        
    Returns:
        Dictionary with updated real-time capacity and reservation confirmation status.
    """
    count = max(1, int(count))
    update_dml = f"""
    UPDATE `{DATASET_TABLE}`
    SET available_capacity = GREATEST(0.0, available_capacity - @count)
    WHERE shelter_id = @shelter_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("shelter_id", "INT64", int(shelter_id)),
            bigquery.ScalarQueryParameter("count", "FLOAT64", float(count)),
        ]
    )
    job = bq_client.query(update_dml, job_config=job_config)
    job.result()

    # Fetch updated shelter details
    fetch_sql = f"""
    SELECT shelter_id, shelter_name, address_1, city, evacuation_capacity, available_capacity
    FROM `{DATASET_TABLE}`
    WHERE shelter_id = @shelter_id
    LIMIT 1
    """
    fetch_job = bq_client.query(fetch_sql, job_config=job_config)
    rows = list(fetch_job.result())
    if not rows:
        return {"success": False, "error": f"Shelter ID {shelter_id} not found"}

    row = rows[0]
    return {
        "success": True,
        "shelter_id": int(row.shelter_id),
        "shelter_name": row.shelter_name,
        "address": f"{row.address_1}, {row.city}",
        "spots_reserved": count,
        "total_capacity": int(row.evacuation_capacity or 0),
        "available_capacity": int(row.available_capacity or 0),
        "message": f"Successfully reserved {count} spot(s) at {row.shelter_name}."
    }

# ADK FunctionTool registrations
bigquery_shelter_tool = FunctionTool(search_shelters_spatial)
bigquery_book_shelter_tool = FunctionTool(book_shelter_capacity)
