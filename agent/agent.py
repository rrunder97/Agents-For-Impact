"""
agent.py - Main Root Agent for Google ADK (Agent Development Kit).
Implements the Sentinel Evacuation Readiness Agent for Challenge 4 (A4I 2026).

Compatible with:
- `adk web`
- Google Cloud Agent Runtime / Vertex AI
- Standalone Python execution & test harnesses
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Google ADK imports
try:
    from google.adk.agents import Agent
    from google.adk.tools import google_maps_grounding
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    Agent = None
    google_maps_grounding = None

from schemas import (
    CheckShelterReadinessInput,
    HazardType,
    GroundingPriority,
    AuditReportItem,
    FederalShelterRecord
)
from bigquery_service import BigQueryGroundingService
from maps_service import GoogleMapsGroundingService
from alert_service import EmergencyInterventionService
from bigquery_nl_query import BigQueryNLQueryEngine, TARGET_VIEW


# ==============================================================================
# SKEPTIC SENTINEL SYSTEM INSTRUCTIONS
# ==============================================================================
MAIN_AGENT_INSTRUCTIONS = f"""
You are the Sentinel Evacuation Readiness & Vulnerable Community Planning Agent.
Your mission is to audit designated emergency shelters in Florida/target counties for an upcoming storm,
focusing on transit-dependent and medically vulnerable populations who cannot easily evacuate.

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
"""


# ==============================================================================
# CUSTOM ADK TOOLS (Python Function Tools)
# ==============================================================================
bq_engine = BigQueryNLQueryEngine(use_mock=True)
maps_service = GoogleMapsGroundingService(use_mock=True)
alert_service = EmergencyInterventionService()
bq_discovery = BigQueryGroundingService(use_mock=True)


def query_emergency_shelters(natural_language_query: str) -> Dict[str, Any]:
    """Translates a natural language question into BigQuery Standard SQL and queries the emergency shelters view."""
    sql = bq_engine.generate_sql(natural_language_query)
    result = bq_engine.execute_query(sql)
    return result


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


# ==============================================================================
# MAIN ADK AGENT DECLARATION
# ==============================================================================
tools_list = [
    query_emergency_shelters,
    audit_shelter_ground_truth,
    send_fips_alert
]

if google_maps_grounding is not None:
    # Add Google Maps Grounding as required by the challenge
    tools_list.append(google_maps_grounding)

if ADK_AVAILABLE and Agent is not None:
    # Primary Google ADK Agent instance
    root_agent = Agent(
        name="evac_readiness_sentinel",
        description="Sentinel Evacuation Readiness & Vulnerable Community Planning Agent for Challenge 4.",
        model="gemini-3.6-flash",
        instruction=MAIN_AGENT_INSTRUCTIONS,
        tools=tools_list
    )
    # Alias for adk web discovery
    agent = root_agent
else:
    root_agent = None
    agent = None


def run_standalone_audit(county_fips: str = "12086") -> str:
    """Convenience runner for offline or standalone CLI execution."""
    from sentinel_agent import SentinelEvacuationAgent
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
