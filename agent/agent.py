"""
agent.py - Main Root Agent for Google ADK (Agent Development Kit).
Implements the Sentinel Evacuation Readiness Agent for Challenge 4 (A4I 2026).

Compatible with:
- `adk web agent`
- Google Cloud Agent Runtime / Vertex AI
- Standalone Python execution & test harnesses
"""

import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

# Google ADK imports
try:
    from google.adk.agents import Agent
    from google.adk.tools import google_maps_grounding
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    Agent = None
    google_maps_grounding = None
from .config import DEFAULT_MODEL
from .maps_agent import maps_agent
from .context_loader import load_agent_context
from .tools.bigquery_tools import (
    query_emergency_shelters,
    query_care_facilities,
    query_hazard_tracts,
    query_vulnerability_medical_shelters,
    query_medical_shelters_available,
    execute_custom_bigquery,
)

# Sentinel services and schemas for standalone/direct audit tools
from .schemas import (
    CheckShelterReadinessInput,
    HazardType,
    GroundingPriority,
    AuditReportItem,
    FederalShelterRecord
)
from .bigquery_service import BigQueryGroundingService
from .maps_service import GoogleMapsGroundingService
from .alert_service import EmergencyInterventionService
from .bigquery_nl_query import BigQueryNLQueryEngine, TARGET_VIEW

from .host_agent import host_instruction

agent_context_doc = load_agent_context()

main_coordinator_instruction = f"""
================================================================================
MAIN AGENT: EMERGENCY RESPONSE & EVACUATION COORDINATOR (emergency_agent)
================================================================================
You are the Emergency Response & Evacuation Coordinator (emergency_agent), the Master Agent for disaster evacuation planning, emergency shelter readiness, and vulnerable population protection.

Your mission is to directly analyze BigQuery emergency data, assess hazard risks, audit shelter availability, and orchestrate specialized domain sub-agents.

{host_instruction}

Target Database View:
{TARGET_VIEW}

Operating Protocol: The "Skeptic" Sentinel:
1. NEVER trust federal records alone. Just because a database row lists `is_functional = TRUE` or `generator_onsite = TRUE`
   does not mean the physical building exists, is open, or has working power today.
2. GROUND WITH GOOGLE MAPS:
   - For every candidate shelter, verify physical existence, operating hours, and business status.
   - If Google Maps reports CLOSED, CLOSED_PERMANENTLY, or CONSTRUCTION, OVERRIDE the federal record immediately.
   - If imagery is >12 months old, flag as [UNVERIFIED_STALE_DATA]. If imagery predates the last hurricane, flag HIGH_UNCERTAINTY.
3. LAST-MILE TRANSIT EQUITY:
   - Federal tables measure straight-line distance, but carless populations must walk or take transit.
   - If walking duration from a vulnerable tract centroid (pct_no_vehicle > 20%) exceeds 20 minutes, flag LAST-MILE FAILURE.
   - If the walking route intersects active floodplains or drainage canals, flag ROUTE HAZARD INTERSECTION.
4. EXTERNAL INTERVENTION:
   - If a critical medical shelter fails grounding, invoke `send_fips_alert` to notify the county Emergency Operations Center (EOC).
5. HONEST REPORTING:
   - If accessibility data is blank in federal records, explicitly state that it is UNRECORDED (not "no").
   - Structure final briefs starting with `[VULNERABILITY DETECTED]` if failures exist.

### SPECIALIZED SUB-AGENTS UNDER YOUR COORDINATION:
You can delegate to or collaborate with specialized domain sub-agents based on the user's operational persona:
1. `first_responder_agent`: Tactical field coordination, hazard overlays, and staging coordinates for Fire, Police, EMS, and Search & Rescue.
2. `public_govt_agent`: Civil infrastructure, county FIPS vulnerability, SVI metrics, and macro resource/generator allocation for emergency managers.
3. `medical_agent`: Healthcare logistics, CMS certified bed capacity (CCN), and medical-grade shelter triage for hospitals and care facilities.
4. `citizen_agent`: Individual citizen and evacuee guidance, open shelter discovery, flood avoidance, and Google Maps direct links.
5. `maps_agent`: Dedicated Google Maps geospatial grounding, address geocoding, and verification.

{agent_context_doc}
"""

bq_engine = BigQueryNLQueryEngine(use_mock=True)
maps_service = GoogleMapsGroundingService(use_mock=True)
alert_service = EmergencyInterventionService()
bq_discovery = BigQueryGroundingService(use_mock=True)


def audit_shelter_ground_truth(
    county_fips: str,
    hazard_type: str = "hurricane",
    min_vulnerability_score: float = 0.20
) -> Dict[str, Any]:
    """Cross-references federal BigQuery shelter records against live Google Maps signals and computes last-mile routing."""
    candidates = bq_discovery.find_candidate_shelters(
        county_fips=county_fips,
        hazard_type=HazardType(hazard_type.lower()),
        min_vulnerability_score=min_vulnerability_score
    )

    results = []
    for s in candidates:
        maps_res = maps_service.ground_shelter(s)
        route_res = maps_service.audit_pedestrian_route(
            origin_lat=s.latitude + 0.003,
            origin_lng=s.longitude - 0.0065,
            dest_lat=s.latitude,
            dest_lng=s.longitude,
            shelter_name=s.shelter_name
        )

        failures = []
        is_critical = False
        if maps_res.functional_override:
            failures.append(f"Physical existence failed: Maps status is '{maps_res.business_status}'")
            is_critical = True
        if route_res.is_last_mile_failure:
            failures.append(f"Last-mile walk time {route_res.walking_duration_minutes:.0f}m exceeds 20m threshold")
            is_critical = True
        if route_res.crosses_flood_risk_area:
            failures.append(f"Route crosses hazard feature: {route_res.hazard_feature_name}")

        results.append({
            "shelter_name": s.shelter_name,
            "tract_id": s.tract_id,
            "carless_population_pct": s.pct_no_vehicle,
            "maps_business_status": maps_res.business_status,
            "walking_duration_minutes": route_res.walking_duration_minutes,
            "failures": failures,
            "is_critical": is_critical
        })

    return {"county_fips": county_fips, "shelters_audited": len(results), "audit_details": results}


def send_fips_alert(
    county_fips: str,
    county_name: str,
    shelter_name: str,
    failure_reasons: List[str],
    suggested_redirect: Optional[str] = None
) -> Dict[str, Any]:
    """Dispatches a critical failure alert to the county emergency manager."""
    alert = alert_service.dispatch_fips_alert(
        county_fips=county_fips,
        county_name=county_name,
        shelter_name=shelter_name,
        grounding_priority=GroundingPriority.CRITICAL_FIX_REQUIRED,
        failure_reasons=failure_reasons,
        suggested_redirect=suggested_redirect
    )
    return {"status": "DISPATCHED", "recipient": alert.emergency_manager_email, "alert_id": alert.shelter_name}


from .tools.maps_tools import geocode_address, verify_shelter_on_google_maps
from .tools.profile_tools import build_user_profile
from .sub_agents import (
    first_responder_agent,
    public_govt_agent,
    medical_agent,
    citizen_agent
)

emergency_tools = [
    # Direct BigQuery Data Tools
    query_emergency_shelters,
    query_care_facilities,
    query_hazard_tracts,
    query_vulnerability_medical_shelters,
    query_medical_shelters_available,
    execute_custom_bigquery,
    # Sentinel Grounding & Alerting Tools
    audit_shelter_ground_truth,
    send_fips_alert,
    geocode_address,
    verify_shelter_on_google_maps,
    build_user_profile,
]

if ADK_AVAILABLE and Agent is not None:
    emergency_agent = Agent(
        name="emergency_agent",
        description="Main Emergency Response & Evacuation Coordinator analyzing BigQuery emergency data and orchestrating specialized sub-agents.",
        model=DEFAULT_MODEL,
        instruction=main_coordinator_instruction,
        tools=emergency_tools,
        sub_agents=[
            first_responder_agent,
            public_govt_agent,
            medical_agent,
            citizen_agent,
            maps_agent,
        ]
    )
    root_agent = emergency_agent
    agent = emergency_agent
else:
    emergency_agent = None
    root_agent = None
    agent = None


def run_standalone_audit(county_fips: str = "12086") -> str:
    """Convenience runner for offline or standalone CLI execution."""
    from .sentinel_agent import SentinelEvacuationAgent
    runner = SentinelEvacuationAgent(
        bigquery_service=bq_discovery,
        maps_service=maps_service,
        alert_service=alert_service
    )
    reports = runner.run_audit(
        CheckShelterReadinessInput(
            county_fips=county_fips,
            hazard_type=HazardType.HURRICANE,
            min_vulnerability_score=0.20
        )
    )
    return "\n\n".join([r.brief_markdown for r in reports])
