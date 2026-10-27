import logging
from typing import Any, Dict, List, Optional
from google.cloud import bigquery
from ..config import (
    PROJECT_ID,
    TABLE_SHELTERS_ALL,
    TABLE_SHELTERS_ACTIVE,
    VIEW_CARE_FACILITIES,
    TABLE_HAZARD_TRACTS,
    TABLE_VULNERABILITY_MEDICAL,
    TABLE_MEDICAL_SHELTERS,
)

logger = logging.getLogger(__name__)

# Initialize client lazily to avoid startup crashes if credentials aren't yet active
_client: Optional[bigquery.Client] = None

def get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=PROJECT_ID)
    return _client

def query_emergency_shelters(
    user_lat: Optional[float] = None,
    user_lon: Optional[float] = None,
    wheelchair_accessible: Optional[bool] = None,
    pets_allowed: Optional[bool] = None,
    open_only: bool = True,
    avoid_flood: bool = True,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Queries emergency shelters from BigQuery (v_emergency_shelters_all).
    Calculates proximity in miles, ensures life-safety conditions, and returns Google Maps links.
    
    Args:
        user_lat: Latitude of user or disaster epicenter.
        user_lon: Longitude of user or disaster epicenter.
        wheelchair_accessible: If True, filters for ADA wheelchair accessible facilities.
        pets_allowed: If True, filters for pet accommodations.
        open_only: If True, ensures shelter status is OPEN and capacity > 0.
        avoid_flood: If True, excludes shelters in 100-year floodplains and storm surge slosh areas.
        limit: Maximum number of shelter records to return.
    """
    client = get_client()
    
    where_clauses = []
    params = []
    
    if open_only:
        where_clauses.append("LOWER(shelter_status_code) = 'open' AND evacuation_capacity > 0")
        
    if avoid_flood:
        where_clauses.append("COALESCE(in_100_yr_floodplain, FALSE) = FALSE AND COALESCE(in_surge_slosh_area, FALSE) = FALSE")
        
    if wheelchair_accessible is True:
        where_clauses.append("wheelchair_accessible = TRUE")
        
    if pets_allowed is True:
        where_clauses.append("LOWER(COALESCE(pet_accommodations_code, 'none')) NOT IN ('none', 'no', 'false')")
        
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    
    if user_lat is not None and user_lon is not None:
        distance_select = f"ROUND(ST_DISTANCE(geog_point, ST_GEOGPOINT(@lon, @lat)) / 1609.344, 1) AS distance_miles,"
        order_sql = "ORDER BY distance_miles ASC"
        params.extend([
            bigquery.ScalarQueryParameter("lat", "FLOAT64", user_lat),
            bigquery.ScalarQueryParameter("lon", "FLOAT64", user_lon),
        ])
    else:
        distance_select = "NULL AS distance_miles,"
        order_sql = "ORDER BY evacuation_capacity DESC"

    params.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))
    
    sql = f"""
    SELECT 
        shelter_id,
        shelter_name,
        address_1,
        city,
        zip,
        evacuation_capacity,
        shelter_status_code,
        wheelchair_accessible,
        pet_accommodations_code,
        generator_onsite,
        in_100_yr_floodplain,
        in_surge_slosh_area,
        {distance_select}
        maps_url
    FROM `{TABLE_SHELTERS_ALL}`
    {where_sql}
    {order_sql}
    LIMIT @limit
    """
    
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = client.query(sql, job_config=job_config).result()
    return [dict(row) for row in rows]

def query_care_facilities(
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    max_distance_miles: Optional[float] = None,
    min_beds: Optional[int] = None,
    ownership_type: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Queries nursing homes and long-term care facilities (v_care_facilities_readiness).
    
    Args:
        center_lat: Latitude of central point / disaster zone.
        center_lon: Longitude of central point / disaster zone.
        max_distance_miles: Radius limit in miles.
        min_beds: Minimum certified bed capacity.
        ownership_type: Filter by 'For profit', 'Non profit', 'Government', etc.
        limit: Max number of records to return.
    """
    client = get_client()
    where_clauses = []
    params = []

    if min_beds:
        where_clauses.append("bed_capacity >= @min_beds")
        params.append(bigquery.ScalarQueryParameter("min_beds", "INT64", min_beds))

    if ownership_type:
        where_clauses.append("LOWER(ownership_type) LIKE LOWER(@ownership)")
        params.append(bigquery.ScalarQueryParameter("ownership", "STRING", f"%{ownership_type}%"))

    if center_lat is not None and center_lon is not None:
        params.extend([
            bigquery.ScalarQueryParameter("lat", "FLOAT64", center_lat),
            bigquery.ScalarQueryParameter("lon", "FLOAT64", center_lon),
        ])
        distance_select = "ROUND(ST_DISTANCE(facility_location, ST_GEOGPOINT(@lon, @lat)) / 1609.344, 1) AS distance_miles,"
        order_sql = "ORDER BY distance_miles ASC"
        if max_distance_miles:
            meters = max_distance_miles * 1609.344
            where_clauses.append("ST_DWITHIN(facility_location, ST_GEOGPOINT(@lon, @lat), @max_meters)")
            params.append(bigquery.ScalarQueryParameter("max_meters", "FLOAT64", meters))
    else:
        distance_select = "NULL AS distance_miles,"
        order_sql = "ORDER BY bed_capacity DESC"

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    params.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))

    sql = f"""
    SELECT 
        certification_id,
        provider_name,
        provider_address,
        city,
        state,
        zip_code,
        bed_capacity,
        ownership_type,
        {distance_select}
        maps_url
    FROM `{VIEW_CARE_FACILITIES}`
    {where_sql}
    {order_sql}
    LIMIT @limit
    """

    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = client.query(sql, job_config=job_config).result()
    return [dict(row) for row in rows]

def query_hazard_tracts(
    geo_id: Optional[str] = None,
    min_building_value: Optional[float] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Queries FEMA National Risk Index metrics from hazard_tracts.
    Useful for actuarial risk modeling, building value exposure, and hurricane/flood frequencies.
    """
    client = get_client()
    where_clauses = []
    params = []

    if geo_id:
        where_clauses.append("CAST(geo_id AS STRING) = @geo_id")
        params.append(bigquery.ScalarQueryParameter("geo_id", "STRING", str(geo_id)))

    if min_building_value:
        where_clauses.append("BUILDVALUE >= @min_val")
        params.append(bigquery.ScalarQueryParameter("min_val", "FLOAT64", min_building_value))

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    params.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))

    sql = f"""
    SELECT 
        geo_id,
        BUILDVALUE,
        HRCN_AFREQ,
        CFLD_AFREQ,
        HRCN_EALB,
        CFLD_EALB
    FROM `{TABLE_HAZARD_TRACTS}`
    {where_sql}
    ORDER BY BUILDVALUE DESC
    LIMIT @limit
    """

    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = client.query(sql, job_config=job_config).result()
    return [dict(row) for row in rows]

def query_vulnerability_medical_shelters(
    geo_id: Optional[str] = None,
    max_distance_meters: Optional[float] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Queries spatial proximity between census tracts and their nearest medical shelters
    from vulnerability_tract_medical_shelters.
    """
    client = get_client()
    where_clauses = []
    params = []

    if geo_id:
        where_clauses.append("CAST(geo_id AS STRING) = @geo_id")
        params.append(bigquery.ScalarQueryParameter("geo_id", "STRING", str(geo_id)))

    if max_distance_meters:
        where_clauses.append("distance_meters <= @max_dist")
        params.append(bigquery.ScalarQueryParameter("max_dist", "FLOAT64", max_distance_meters))

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    params.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))

    sql = f"""
    SELECT 
        geo_id,
        distance_meters,
        ROUND(distance_meters / 1609.344, 2) AS distance_miles,
        tract_lat,
        tract_lon,
        shelter_lat,
        shelter_lon,
        top_2_ccn
    FROM `{TABLE_VULNERABILITY_MEDICAL}`
    {where_sql}
    ORDER BY distance_meters ASC
    LIMIT @limit
    """

    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = client.query(sql, job_config=job_config).result()
    return [dict(row) for row in rows]

def query_medical_shelters_available(
    wheelchair_accessible: Optional[bool] = None,
    generator_onsite: Optional[bool] = None,
    open_only: bool = True,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Queries operational status and physical attributes of all medical-grade shelters
    from medical_shelters_available.
    """
    client = get_client()
    where_clauses = []
    params = []

    if open_only:
        where_clauses.append("LOWER(shelter_status_code) = 'open' AND evacuation_capacity > 0")

    if wheelchair_accessible is True:
        where_clauses.append("wheelchair_accessible = TRUE")

    if generator_onsite is True:
        where_clauses.append("(generator_onsite = TRUE OR self_sufficient_electricity = TRUE)")

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    params.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))

    sql = f"""
    SELECT 
        shelter_id,
        shelter_name,
        evacuation_capacity,
        shelter_status_code,
        wheelchair_accessible,
        generator_onsite,
        self_sufficient_electricity,
        top_2_ccn
    FROM `{TABLE_MEDICAL_SHELTERS}`
    {where_sql}
    ORDER BY evacuation_capacity DESC
    LIMIT @limit
    """

    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = client.query(sql, job_config=job_config).result()
    return [dict(row) for row in rows]

def execute_custom_bigquery(query_sql: str) -> List[Dict[str, Any]]:
    """
    Executes a read-only custom SQL query against the evacuation_readiness dataset.
    Use for aggregations, business intelligence, or multi-table joins.
    """
    client = get_client()
    # Guard against accidental write statements
    lower_sql = query_sql.strip().lower()
    if any(keyword in lower_sql for keyword in ["drop", "delete", "truncate", "insert", "update", "alter"]):
        raise ValueError("Only read-only SELECT queries are allowed.")

    rows = client.query(query_sql).result()
    return [dict(row) for row in rows]
