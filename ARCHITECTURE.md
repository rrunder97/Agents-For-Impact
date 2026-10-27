# Multi-Agent Emergency Evacuation & Readiness Architecture

This document describes the high-level system architecture, multi-agent coordination protocol, and end-to-end data flow of the **Google ADK Emergency Evacuation Framework**.

---

## 1. High-Level System Architecture Diagram

```mermaid
graph TD
    classDef userLayer fill:#E1F5FE,stroke:#0288D1,stroke-width:2px,color:#01579B;
    classDef routerLayer fill:#FFF8E1,stroke:#FFA000,stroke-width:2px,color:#E65100;
    classDef agentLayer fill:#E8F5E9,stroke:#388E3C,stroke-width:2px,color:#1B5E20;
    classDef toolLayer fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px,color:#4A148C;
    classDef dataLayer fill:#ECEFF1,stroke:#455A64,stroke-width:2px,color:#263238;

    subgraph UserLayer ["1. Incoming User Ingestion & Personas"]
        U1["First Responders<br/>(Police, Fire, EMS, Search & Rescue)"]:::userLayer
        U2["Public Government<br/>(County EOC, Emergency Planners)"]:::userLayer
        U3["Medical Personnel<br/>(Hospitals, Doctors, Care Homes)"]:::userLayer
        U4["Individual Citizens<br/>(Evacuees, Families, Special Needs)"]:::userLayer
    end

    subgraph IntakeRouter ["2. Master Intake & Router (host_agent / root_agent)"]
        H1["Heuristic Persona Classifier"]:::routerLayer
        H2["1-Step Disambiguation Selector"]:::routerLayer
        H3["UserProfileState Session Builder<br/>(Role, Urgency, FIPS/Loc, CCN)"]:::routerLayer
        H4["ADK Agent-to-Agent (A2A) Dispatcher"]:::routerLayer
        H1 --> H3
        H2 --> H3
        H3 --> H4
    end

    subgraph DomainAgents ["3. Specialized Domain Sub-Agents"]
        A1["first_responder_agent<br/>Tactical Dispatch & Staging"]:::agentLayer
        A2["public_govt_agent<br/>SVI & Macro Allocations"]:::agentLayer
        A3["medical_agent<br/>CMS Bed Capacity & Triage"]:::agentLayer
        A4["citizen_agent<br/>Shelters & Life Safety"]:::agentLayer
        A5["emergency_agent<br/>BigQuery Analytics"]:::agentLayer
        A6["maps_agent<br/>Live Maps Grounding"]:::agentLayer
    end

    subgraph ToolsServices ["4. Operational Tool Execution Layer"]
        T1["search_hazard_overlay<br/>get_staging_coordinates"]:::toolLayer
        T2["query_vulnerability_tracts<br/>query_hazard_tracts"]:::toolLayer
        T3["query_care_facilities<br/>query_medical_shelters"]:::toolLayer
        T4["query_emergency_shelters<br/>geocode_address"]:::toolLayer
        T5["audit_shelter_ground_truth<br/>send_fips_alert"]:::toolLayer
        T6["Google Maps Places & Routes<br/>Live Grounding Tool"]:::toolLayer
    end

    subgraph DataFoundation ["5. Data & Cloud Foundation"]
        BQ1[("BigQuery Views & Tables<br/>• v_emergency_shelters_all<br/>• v_care_facilities_readiness<br/>• hazard_tracts<br/>• vulnerability_tract_medical_shelters<br/>• medical_shelters_available")]:::dataLayer
        MAPS[("Google Maps Platform<br/>• Places API (Operating Status)<br/>• Routes API (Walk Times)<br/>• Satellite Recency Checks")]:::dataLayer
        VERTEX[("Google Vertex AI<br/>• gemini-2.5-flash<br/>• Session State Persistence")]:::dataLayer
        EOC[("County EOC Alert Dispatch<br/>• Automated Sentinel Notifications")]:::dataLayer
    end

    U1 --> H1
    U2 --> H1
    U3 --> H1
    U4 --> H1
    U1 -.->|Ambiguous| H2
    U2 -.->|Ambiguous| H2
    U3 -.->|Ambiguous| H2
    U4 -.->|Ambiguous| H2

    H4 -->|FIRST_RESPONDER| A1
    H4 -->|PUBLIC_GOVERNMENT| A2
    H4 -->|MEDICAL_PERSONNEL| A3
    H4 -->|INDIVIDUAL_CITIZEN| A4
    H4 -->|Data Deep Dive| A5
    H4 -->|Geospatial Grounding| A6

    A1 --> T1
    A2 --> T2
    A3 --> T3
    A4 --> T4
    A5 --> T5
    A6 --> T6

    T1 --> BQ1
    T1 --> MAPS
    T2 --> BQ1
    T3 --> BQ1
    T4 --> BQ1
    T4 --> MAPS
    T5 --> BQ1
    T5 --> EOC
    T6 --> MAPS

    DomainAgents -.-> VERTEX
```

---

## 2. End-to-End Request Flow (Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Field Operator
    participant Root as root_agent (Intake Router)
    participant Profile as UserProfileState
    participant SubAgent as Domain Subagent (e.g. medical_agent)
    participant Tools as Tool Execution Layer
    participant BQ as Google BigQuery
    participant Maps as Google Maps Platform

    User->>Root: "We have 15 ventilator patients needing medical shelter triage..."
    Note over Root: 1. Parse keywords: 'patients', 'ventilator', 'medical shelter'
    Root->>Profile: build_user_profile(role='MEDICAL_PERSONNEL', urgency='URGENT')
    Profile-->>Root: UserProfileState registered (ADK-SESS-UUID)
    
    Root->>SubAgent: A2A Transfer to medical_agent with UserProfileState
    Note over SubAgent: 2. Analyze bed requirements & generator dependencies
    
    SubAgent->>Tools: query_care_facilities(min_beds=15, ownership_type=None)
    Tools->>BQ: SELECT * FROM v_care_facilities_readiness WHERE bed_capacity >= 15
    BQ-->>Tools: Returns facilities (CCN: 105030, 105728, coordinates)
    Tools-->>SubAgent: Certified Care Facility Records
    
    SubAgent->>Tools: query_medical_shelters_available(requires_generator=True)
    Tools->>BQ: SELECT * FROM medical_shelters_available WHERE generator_onsite=TRUE
    BQ-->>Tools: Shelter capacity & generator status
    Tools-->>SubAgent: Medical Shelter Records
    
    SubAgent->>Tools: geocode & generate Maps URLs for facilities
    Tools->>Maps: Verify facility existence & generate deep link
    Maps-->>Tools: Verified Google Maps URLs
    Tools-->>SubAgent: Location URLs
    
    SubAgent-->>User: [MEDICAL & HEALTHCARE LOGISTICS DISPATCH]<br/>• CCN 105030 Miami Jewish Health (393 Beds)<br/>• Verified Google Maps Direct Routing<br/>• Generator & Oxygen Triage Directives
```

---

## 3. Persona Routing & Operational Capabilities

| Persona Role | Target Audience | Trigger Heuristics | Assigned Sub-Agent | Primary Tools | Structured Output Contract |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`FIRST_RESPONDER`** | Firefighters, Police, EMS, Search & Rescue | *"fire"*, *"EMS"*, *"rescue"*, *"unit"*, *"staging"*, *"tactical"* | `first_responder_agent` | `search_hazard_overlay`<br>`get_staging_coordinates` | `[FIRST RESPONDER TACTICAL DISPATCH]`<br>• Hazard overlay<br>• Staging coords & radio channel<br>• Action items |
| **`PUBLIC_GOVERNMENT_SYSTEMS`** | County EOC, Emergency Managers, Public Safety Admins | *"county"*, *"parish"*, *"FIPS"*, *"SVI"*, *"census tract"*, *"macro"* | `public_govt_agent` | `query_vulnerability_tracts`<br>`query_hazard_tracts` | `[CIVIL INFRASTRUCTURE & VULNERABILITY REPORT]`<br>• County SVI Score<br>• Carless household %<br>• Power dependency count<br>• Generator directives |
| **`MEDICAL_PERSONNEL`** | Hospital Incident Command, Doctors, Triage Nurses, Care Directors | *"CCN"*, *"hospital"*, *"patient"*, *"nurse"*, *"certified bed"*, *"triage"* | `medical_agent` | `query_care_facilities`<br>`query_medical_shelters_available`<br>`query_vulnerability_medical_shelters` | `[MEDICAL & HEALTHCARE LOGISTICS DISPATCH]`<br>• Provider CCN & Beds<br>• Generator & Oxygen status<br>• Safe transfer routing |
| **`INDIVIDUAL_CITIZEN`** | General Public, Evacuees, Families, Pet owners, Mobility impaired | *"shelter"*, *"evacuate"*, *"family"*, *"pet"*, *"wheelchair"*, *"where to go"* | `citizen_agent` | `query_emergency_shelters`<br>`geocode_address`<br>`verify_shelter_on_google_maps` | `[CITIZEN EVACUATION ASSISTANCE]`<br>• Open shelters outside flood zones<br>• ADA & Pet policies<br>• Direct Google Maps links |
| **`CORE_DATA_ANALYTICS`** | Deep spatial queries & cross-table SQL operations | *"BigQuery"*, *"custom SQL"*, *"vulnerability distance"* | `emergency_agent` | `execute_custom_bigquery`<br>`query_emergency_shelters` | Structured Table Data & Spatial Calculations |
| **`CORE_GEOSPATIAL`** | Live ground truth & place verification | *"grounding"*, *"is building open"*, *"Google Maps status"* | `maps_agent` | `google_maps_grounding`<br>`verify_shelter_on_google_maps` | Real-time Places & Routes Verification |

---

## 4. Safety & Grounding Guardrails

1. **Life Safety First (Floodplain & Storm Surge Exclusion):**
   * Before recommending any shelter to citizens or first responders, the system inspects `in_100_yr_floodplain` and `in_surge_slosh_area`.
   * Shelters located in active flood zones are disqualified and flagged as hazardous.

2. **The "Skeptic" Sentinel Protocol (Ground-Truth Auditing):**
   * Federal records (e.g., FEMA historical entries) indicating `is_functional = TRUE` are never accepted blindly.
   * Facilities are cross-referenced with live Google Maps signals. If Google Maps reports `CLOSED_PERMANENTLY` or demolished, the federal record is immediately overridden.

3. **Last-Mile Transit Equity:**
   * Distances for carless populations (where `pct_no_vehicle > 20%`) are evaluated using pedestrian walking durations rather than straight-line Euclidean vectors.
   * Walks exceeding 20 minutes or traversing flood barriers trigger critical transit warnings.

4. **External Intervention Dispatches:**
   * When a critical medical shelter fails ground truth verification, the system invokes `send_fips_alert` to notify the designated county Emergency Operations Center (EOC).
