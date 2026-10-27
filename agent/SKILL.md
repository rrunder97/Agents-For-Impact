---
name: evac_readiness_grounding
description: Translates natural language requests into BigQuery Standard SQL and audits emergency shelter readiness using live geospatial signals and the comprehensive v_emergency_shelters_all view.
---

# Evacuation Readiness & BigQuery Grounding Skill

This skill equips the agent to translate natural language user questions into high-performance, read-only BigQuery Standard SQL against the enterprise emergency shelters view:
`qwiklabs-gcp-03-82491e646971.evacuation_readiness.v_emergency_shelters_all`

---

## 1. Table/View Catalog & Schema

**Fully Qualified View:** `qwiklabs-gcp-03-82491e646971.evacuation_readiness.v_emergency_shelters_all`

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `shelter_id` | `INT64` | Unique identifier for the shelter. |
| `shelter_name` | `STRING` | The name of the facility. |
| `address_1` | `STRING` | Street address. |
| `city` | `STRING` | City location. |
| `zip` | `STRING` | Zip code. |
| `latitude` / `longitude` | `FLOAT64` | Decimal coordinates. |
| `geog_point` | `GEOGRAPHY` | Native BigQuery Geography object for spatial analysis. |
| `maps_url` | `STRING` | URL for Google Maps navigation. |
| `evacuation_capacity` | `FLOAT64` | The maximum number of individuals the shelter can hold. |
| `shelter_status_code` | `STRING` | Current status (e.g., `Open`, `Full`, `Closed`). |
| `wheelchair_accessible` | `BOOL` | Indicates if the facility is ADA/wheelchair accessible. |
| `is_medical` | `BOOL` | Indicates if the shelter is equipped for medical needs. |
| `is_functional` | `BOOL` | Indicates if the facility is currently operational. |
| `pet_accommodations_code` | `STRING` | Details regarding pet allowance. |
| `generator_onsite` | `BOOL` | True if the facility has a backup power generator. |
| `self_sufficient_electricity` | `BOOL` | Indicates if the facility can operate off-grid for power. |
| `in_surge_slosh_area` | `BOOL` | Risk flag: Facility is located in a hurricane storm surge zone. |
| `in_100_yr_floodplain` | `BOOL` | Risk flag: Facility is located in a 1% annual chance flood zone. |

---

## 2. SQL Generation Guidelines & Constraints

1. **Read-Only Safety:** Only `SELECT` statements are permitted. Never emit DDL/DML.
2. **Spatial Proximity:**
   - Always use `geog_point` with `ST_DWITHIN` or `ST_DISTANCE`.
   - Remember BigQuery geography coordinate order: `ST_GEOGPOINT(longitude, latitude)`.
   - Distance calculations: 1 mile = 1609.34 meters.
   - Example radius filter (within 5 miles of target coordinate):
     ```sql
     ST_DWITHIN(geog_point, ST_GEOGPOINT(-80.2215, 25.8451), 5 * 1609.34)
     ```
3. **Hazard Risk Filters:**
   - Safe from hurricane storm surge: `in_surge_slosh_area = FALSE`
   - Safe from 100-year floodplain: `in_100_yr_floodplain = FALSE`
4. **Capacity & Regional Aggregation:**
   - Compute available capacity with `SUM(COALESCE(evacuation_capacity, 0))`.
   - Group by `city` or filter by operational status (`is_functional = TRUE`).

---

## 3. High-Value Few-Shot SQL Examples

### Example A: Safe Medical Shelters with Backup Power
*User Prompt:* "Find all open medical shelters with backup power that are NOT in a flood zone or storm surge area."
```sql
SELECT 
    shelter_id,
    shelter_name,
    city,
    address_1,
    evacuation_capacity,
    generator_onsite,
    self_sufficient_electricity,
    maps_url
FROM `qwiklabs-gcp-03-82491e646971.evacuation_readiness.v_emergency_shelters_all`
WHERE is_functional = TRUE
  AND is_medical = TRUE
  AND generator_onsite = TRUE
  AND in_100_yr_floodplain = FALSE
  AND in_surge_slosh_area = FALSE
ORDER BY evacuation_capacity DESC
LIMIT 50;
```

### Example B: Spatial Proximity & Accessibility
*User Prompt:* "List wheelchair accessible shelters within 10 miles of lat 25.7617, lng -80.1918 sorted by proximity."
```sql
SELECT 
    shelter_id,
    shelter_name,
    address_1,
    city,
    evacuation_capacity,
    wheelchair_accessible,
    ROUND(ST_DISTANCE(geog_point, ST_GEOGPOINT(-80.1918, 25.7617)) / 1609.34, 2) AS distance_miles,
    maps_url
FROM `qwiklabs-gcp-03-82491e646971.evacuation_readiness.v_emergency_shelters_all`
WHERE is_functional = TRUE
  AND wheelchair_accessible = TRUE
  AND ST_DWITHIN(geog_point, ST_GEOGPOINT(-80.1918, 25.7617), 10 * 1609.34)
ORDER BY distance_miles ASC
LIMIT 50;
```

### Example C: Regional Capacity Breakdown
*User Prompt:* "What is the total shelter capacity by city for pet-friendly shelters?"
```sql
SELECT 
    city,
    COUNT(*) AS total_shelters,
    SUM(COALESCE(evacuation_capacity, 0)) AS total_evacuation_capacity
FROM `qwiklabs-gcp-03-82491e646971.evacuation_readiness.v_emergency_shelters_all`
WHERE is_functional = TRUE
  AND pet_accommodations_code IS NOT NULL
  AND pet_accommodations_code != 'None'
GROUP BY city
ORDER BY total_evacuation_capacity DESC;
```
