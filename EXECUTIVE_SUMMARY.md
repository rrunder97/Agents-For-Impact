# Executive Summary for Judges: Agents for Impact 2026
## Adaptive Evacuation Readiness & Vulnerable Community Planning (Challenge 4)

---

## 1. Executive Summary & Real-World Impact

During extreme weather events such as hurricanes, conventional emergency evacuation plans quietly assume that residents possess private vehicles, intact physical mobility, inland family networks, and stable power. In disaster after disaster—such as Hurricane Ian, where the median age of the deceased was in the seventies—the fatalities are disproportionately concentrated among citizens who lack these advantages:
- **Transit-dependent households** without private automobiles.
- **Medically vulnerable individuals** dependent on electricity-powered life-support devices (e.g., oxygen concentrators, dialysis).
- **Elderly and disabled residents** unable to walk long distances across flooded drainage basins or storm surge slosh zones.

### Why This Matters: Turning Data into Pre-Landfall Intervention
This application transforms fragmented public data into **pre-season, life-saving operational interventions**. Rather than attempting real-time rescues at 3:00 AM during power grid failure, this system empowers county emergency managers in **August**—weeks before storm landfall—to:
1. **Uncover "Phantom Shelters" & Medical Deserts**: Cross-reference federal emergency shelter registries against live Google Maps ground truth. Federal records frequently mark facilities as `is_functional = True` when the physical location has been permanently closed, demolished, or repurposed into a non-medical facility.
2. **Audit Last-Mile Pedestrian Transit Equity**: While traditional models measure straight-line geometric distance, transit-dependent populations must walk. The system computes genuine walking routes and times; if a pedestrian route exceeds 20 minutes or crosses active floodplains/drainage canals, it flags a **Last-Mile Failure**.
3. **Automate EOC Alerts & Resource Rebalancing**: Dispatches automated alerts to county Emergency Operations Centers (EOC) with actionable rerouting directives to operational backup hospitals or community shelters equipped with backup generators.
4. **Enforce Honest Accounting of Unrecorded Data**: Recognizes that blank accessibility fields in government records mean *unrecorded*—not "inaccessible"—preventing false negative reports.

---

## 2. End-to-End System Architecture

```mermaid
graph TB
    subgraph User Personas & Entrypoints
        EOC[County Emergency Manager / Planner]
        Cit[Vulnerable Citizen / Evacuee]
        Med[Hospital & Care Facility Administrator]
        Tac[First Responder / Tactical Incident Command]
    end

    subgraph Google ADK Multi-Agent Orchestration
        Root[Master Coordinator / Chief Sentinel Agent]
        Skeptic[Skeptic Sentinel Grounding Protocol]
        CitizenAgent[citizen_agent]
        MedicalAgent[medical_agent]
        GovAgent[public_govt_agent]
        TacticalAgent[first_responder_agent]
        EmergencyAgent[emergency_agent]
        MapsAgent[maps_agent]
    end

    subgraph MCP Integration Tier
        ToolboxClient[MCPToolboxClient<br/>agent/mcp/toolbox_client.py]
        MapsMCPClient[MapsGroundingMCPClient<br/>agent/mcp/maps_mcp_client.py]
    end

    subgraph Google Model Context Protocol Servers
        MCP_Toolbox[Google MCP Toolbox for Databases<br/>Port 5000 | mcp-toolbox/tools.yaml]
        Maps_MCP[Google Maps Grounding Lite MCP<br/>mapstools.googleapis.com/mcp]
    end

    subgraph Ground-Truth Data & Cloud Infrastructure
        subgraph Google BigQuery Datasets
            BQ_Shelters[(fema_emergency_readiness.shelters)]
            BQ_Vulnerability[(census_socioeconomic.vulnerability_tracts)]
            BQ_Hazard[(hazard_modeling.hazard_tracts)]
            BQ_Care[(care_facilities_readiness)]
            BQ_VulnerMed[(vulnerability_tract_medical_shelters)]
        end
        subgraph Google Maps Platform APIs
            GMaps_Places[Google Places API: Business Status, Category, Imagery]
            GMaps_Routes[Google Routes API: Drive Time, Walk Time, Hazards]
            GMaps_Weather[Google Weather API: Real-time Ambient Conditions]
        end
        CloudRun[Cloud Run / HTTP Backend: shelter-agent-backend]
        EOC_Alerts[Emergency Operations Dispatch: send_fips_alert]
    end

    %% User Connections
    EOC --> Root
    Cit --> CitizenAgent
    Med --> MedicalAgent
    Tac --> TacticalAgent

    %% ADK Routing
    Root --> Skeptic
    Root --> CitizenAgent
    Root --> MedicalAgent
    Root --> GovAgent
    Root --> TacticalAgent
    Root --> EmergencyAgent
    Root --> MapsAgent

    %% MCP Dispatch
    Skeptic --> ToolboxClient
    Skeptic --> MapsMCPClient
    EmergencyAgent --> ToolboxClient
    GovAgent --> ToolboxClient
    MedicalAgent --> ToolboxClient
    CitizenAgent --> ToolboxClient
    CitizenAgent --> MapsMCPClient
    MapsAgent --> MapsMCPClient

    %% MCP Server Connections
    ToolboxClient -->|JSON-RPC 2.0 tools/call| MCP_Toolbox
    MapsMCPClient -->|JSON-RPC 2.0 tools/call| Maps_MCP

    %% Backend Service
    CloudRun --> ToolboxClient
    CloudRun --> MapsMCPClient

    %% Data Connections
    MCP_Toolbox --> BQ_Shelters
    MCP_Toolbox --> BQ_Vulnerability
    MCP_Toolbox --> BQ_Hazard
    MCP_Toolbox --> BQ_Care
    MCP_Toolbox --> BQ_VulnerMed

    Maps_MCP --> GMaps_Places
    Maps_MCP --> GMaps_Routes
    Maps_MCP --> GMaps_Weather

    %% Intervention Output
    Skeptic -->|Priority: CRITICAL_FIX_REQUIRED| EOC_Alerts
```

---

## 3. Google MCP Toolbox for Databases Integration

The application uses Google's official **MCP Toolbox for Databases** (`googleapis/mcp-toolbox`) packaged as a standalone microservice in `mcp-toolbox/Dockerfile` and orchestrated via `docker-compose.yml`.

### Configured MCP Tools (`mcp-toolbox/tools.yaml`)

| MCP Tool Name | Target BigQuery Source | Parameters | Description & Operational Value |
|---|---|---|---|
| `search_shelters_spatial` | `fema_emergency_readiness.shelters` | `lat`, `lon`, `require_wheelchair`, `require_medical`, `require_generator`, `include_closed`, `limit` | Computes spherical geospatial distances (`ST_DISTANCE`) between user coordinates and candidate shelters; filters by life-safety requirements. |
| `book_shelter_capacity` | `fema_emergency_readiness.shelters` | `shelter_id`, `count` | Executes atomic BigQuery DML `UPDATE` to decrement `available_capacity`, preventing shelter overbooking. |
| `query_candidate_medical_shelters` | Join: `shelters` + `vulnerability_tracts` + `hazard_tracts` | `county_fips`, `hazard_type`, `min_vulnerability_score` | Cross-references federal medical shelters against high-vulnerability tracts (high carless %) in primary hazard corridors. |
| `query_care_facilities` | `care_facilities_readiness` | `min_beds`, `ownership_type`, `limit` | Queries certified nursing homes and long-term care facilities to prevent acute-care hospital bed congestion. |
| `query_vulnerability_tracts` | `census_socioeconomic.vulnerability_tracts` | `fips_pattern` | Pulls Social Vulnerability Index (SVI), transit dependency (carless households), and building valuation exposure. |
| `query_hazard_tracts` | `hazard_modeling.hazard_tracts` | `limit` | Extracts FEMA National Risk Index metrics, hurricane frequency (`HRCN_AFREQ`), and coastal flood frequency (`CFLD_AFREQ`). |

---

## 4. Google Maps Grounding Lite MCP Integration

Physical grounding is managed via the **Google Maps Grounding Lite MCP Server** (`https://mapstools.googleapis.com/mcp`).

### Grounding Tools & Capabilities

1. **`search_places`**:
   - Validates live business status (`OPERATIONAL`, `CLOSED_PERMANENTLY`, `CLOSED_TEMPORARILY`, `CONSTRUCTION`).
   - Confirms facility category (e.g., verifying that a registered shelter is still a functioning clinic or school, rather than a commercial storefront).
   - Audits imagery crawl dates; flags data older than 12 months as `[UNVERIFIED_STALE_DATA]` and data predating the last hurricane as `HIGH_UNCERTAINTY`.
2. **`compute_routes`**:
   - **`travelMode: DRIVE`**: Calculates realistic road travel times and traffic-aware transit durations for evacuation staging.
   - **`travelMode: WALK`**: Audits pedestrian accessibility for carless populations. Flags `LAST-MILE FAILURE` if walk duration exceeds 20 minutes, or `ROUTE HAZARD INTERSECTION` if walking path traverses active floodplains or canals.
3. **`lookup_weather`**:
   - Retrieves real-time meteorological conditions (temperature, precipitation, wind speed) at origin and destination coordinates.
4. **Strict Attribution & Compliance**:
   - Complies with Google Maps Platform display guidelines: preserves the label `"Google Maps"` with `translate="no"`, and attaches direct Google Maps deep-links (`googleMapsUri`).

---

## 5. Datasets & Provenance

| Dataset | Scope / Authority | Role in Evacuation Readiness |
|---|---|---|
| **`fema_emergency_readiness.shelters`** | FEMA / National Shelter System | Primary registry containing 1,326+ shelters, physical addresses, capacity, wheelchair flags, and generator status. |
| **`census_socioeconomic.vulnerability_tracts`** | U.S. Census Bureau ACS (2020) | Census tract-level demographics: % households with no vehicle (`pct_no_vehicle`), elderly living alone, disability %. |
| **`hazard_modeling.hazard_tracts`** | FEMA National Risk Index (NRI) | Annual hurricane frequency (`HRCN_AFREQ`), coastal flood frequency (`CFLD_AFREQ`), and building asset value exposure (`BUILDVALUE`). |
| **`care_facilities_readiness`** | CMS (Centers for Medicare & Medicaid Services) | Long-term care facilities, nursing homes, bed counts, and CMS Certification Numbers (CCN). |
| **`vulnerability_tract_medical_shelters`** | Spatial Precomputations | Precomputed proximity matrices between vulnerable tract centroids and nearest medical shelters. |
| **Google Maps Live Ground Truth** | Google Maps Platform | Real-time ground truth for physical building existence, operating status, street navigation, and satellite imagery recency. |

---

## 6. Demonstrated Test Scenarios & Validation

The application features full end-to-end automated test suites verified on Linux:

1. **`agent/test_mcp_integration.py` (7/7 Unit Tests Passed)**:
   - Validates `tools.yaml` structure, schema definitions, and parameter mapping.
   - Validates MCP Toolbox execution for spatial queries, atomic booking, and healthcare queries.
   - Validates Maps MCP `search_places`, multi-modal `compute_routes` (`DRIVE` & `WALK`), and `lookup_weather`.
2. **`agent/test_medical_desert.py` (The 'Medical Desert' Scenario - Passed)**:
   - Audits County FIPS `12086` (Miami-Dade).
   - Detects that federal record for *Northside Community Medical Point* (`is_functional = True`) is invalid because Google Maps reports `CLOSED_PERMANENTLY`.
   - Flags last-mile pedestrian transit failure (27 mins walk > 20 min threshold) crossing Little River Canal flood zone.
   - Dispatches emergency alert to `eoc-ops@miamidade.gov` and redirects transit to *East General Medical Center*.
3. **`agent/test_bigquery_nl.py` (Natural Language to BigQuery SQL - Passed)**:
   - Validates NL-to-SQL generation and parameterized execution for spatial bounding queries, flood avoidance, and capacity aggregations.
4. **`shelter-agent-backend/main.py` (Cloud Function Endpoints - Passed)**:
   - HTTP endpoint tested with address geocoding (`33139`) -> HTTP 200 with verified shelters and driving directions.
   - Atomic reservation endpoint tested (`action: "book"`) -> HTTP 200 decrements available capacity.
