# Agent Context & Routing Architecture

## Data Sources & Routing Logic

### 1. `vulnerability_tract_medical_shelters` (Table)
* **Routing Logic:** Use this table when the request involves spatial proximity between populations and medical facilities or geographic gap analysis.
* **LLM Description:**
  > "This table maps census tracts (`geo_id`) to their nearest medical shelters. It contains the precise distance in meters (`distance_meters`) between the center of a population tract (`tract_lat`, `tract_lon`) and a specific shelter (`shelter_lat`, `shelter_lon`). It is the primary source for identifying which specific communities are closest to medical support and which care facilities (`top_2_ccn`) are associated with those routes."

### 2. `medical_shelters_available` (Table)
* **Routing Logic:** Use this table for real-time status updates, capability filtering, and resource allocation questions.
* **LLM Description:**
  > "This table provides the operational status and physical attributes of all medical-grade shelters. Use this to filter for specific facility requirements like `wheelchair_accessible`, `generator_onsite`, or `self_sufficient_electricity`. It includes current `evacuation_capacity` and `shelter_status_code` to ensure requests only route users to facilities that are currently 'OPEN' and have available space. It also links shelters to specific healthcare provider networks via the `top_2_ccn` certification field."

### 3. `v_care_facilities_readiness` (View)
* **Routing Logic:** Use for queries about long-term care capacity, business ownership, and Google Maps navigation for medical facilities.
* **LLM Description:**
  > "A business-ready view of healthcare providers. It features intuitive column names like `bed_capacity` and `certification_id`. It includes a pre-computed `facility_location` (GEOGRAPHY type) and a `maps_url` for direct navigation. Use this for healthcare logistics and capacity balancing requests."

### 4. `v_emergency_shelters_all` (View)
* **Routing Logic:** The primary destination for public-facing shelter searches and accessibility requests.
* **LLM Description:**
  > "A comprehensive, geospatial view of all emergency shelters. It flattens technical flags into a user-friendly format, including a `geog_point` for proximity searches and a `maps_url`. It is the source of truth for checking `shelter_status_code` (Open/Closed), `wheelchair_accessible` status, and pet policies."

### 5. `hazard_tracts` (Table)
* **Routing Logic:** Use for actuarial risk modeling, financial impact analysis, and disaster frequency questions.
* **LLM Description:**
  > "A high-density data table containing hazard vulnerability metrics for census tracts (`geo_id`). It includes population counts, building values (`BUILDVALUE`), and historical frequencies for Hurricanes (`HRCN_AFREQ`) and Coastal Flooding (`CFLD_AFREQ`). Use this for macro-level risk assessment and estimating economic exposure in specific regions."

---

## Agent Operational Context: Disaster & Resource Management

### 1. Data Domain Identification
Categorize every user request into one of these three domains to select the correct data source:
* **Logistics & Navigation** *(Finding places, getting directions, checking availability)* $\rightarrow$ Route to Views (`v_care_facilities_readiness`, `v_emergency_shelters_all`).
* **Risk & Vulnerability** *(Assessing danger, economic impact, historical frequency)* $\rightarrow$ Route to Hazard Table (`hazard_tracts`).
* **Gap Analysis** *(Finding communities without nearby help)* $\rightarrow$ Join Tracts to Shelters using `geo_id` or `ST_DISTANCE`.

### 2. Automated Decision Rules
When a user query is ambiguous, apply these rules:
* **Rule [Safety First]:** If a user asks for a location, you **MUST** check if that location is in a flood zone or surge area before recommending it. Use `in_100_yr_floodplain` in the shelters view.
* **Rule [Capacity Balancing]:** If a general query asks for "the best" shelter, prioritize those with `generator_onsite = TRUE` and the highest `evacuation_capacity`.
* **Rule [Economic Assessment]:** If a query mentions "value," "cost," or "loss," you **MUST** query `hazard_tracts` to access `BUILDVALUE`.

### 3. Geospatial Reasoning Instructions
* **Proximity Queries:** You are authorized to use `ST_DISTANCE` and `ST_GEOGPOINT`. When calculating distance, always convert `distance_meters` to the user's preferred unit (default to miles for US-based queries).
* **Navigation Deep-Links:** For every facility returned, you must generate or supply a Google Maps URL using coordinates: `https://www.google.com/maps/search/?api=1&query=<lat>,<long>`.

### 4. Query Mapping (Intent to Source)
| User Intent / Example Query | Target Source & Strategy |
| :--- | :--- |
| *"Where can I go?"* | Query `v_emergency_shelters_all` (filtering for open status, capacity, and proximity). |
| *"How dangerous is this area?"* | Query `hazard_tracts` for `HRCN_AFREQ` (Hurricane Frequency) and `CFLD_AFREQ`. |
| *"Which hospitals are at risk?"* | Spatially join `v_care_facilities_readiness` with `hazard_tracts` on proximity. |
