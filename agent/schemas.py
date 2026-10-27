"""
schemas.py - Data schemas for Evacuation Readiness Grounding Skill.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class HazardType(str, Enum):
    HURRICANE = "hurricane"
    FLOOD = "flood"


class GroundingPriority(str, Enum):
    CRITICAL_FIX_REQUIRED = "CRITICAL_FIX_REQUIRED"
    HIGH_UNCERTAINTY = "HIGH_UNCERTAINTY"
    ADVISORY = "ADVISORY"


class CheckShelterReadinessInput(BaseModel):
    county_fips: str = Field(..., description="5-digit FIPS code of the target county (e.g., '12086').")
    hazard_type: HazardType = Field(..., description="Primary disaster risk: 'hurricane' or 'flood'.")
    min_vulnerability_score: float = Field(
        default=0.20,
        description="Threshold for proportion of population without vehicles (e.g. 0.20 = 20%)."
    )


class FederalShelterRecord(BaseModel):
    shelter_id: str
    shelter_name: str
    county_fips: str
    county_name: str
    tract_id: str
    latitude: float
    longitude: float
    is_medical: bool = True
    is_functional: bool = True
    generator_onsite: bool = True
    pct_no_vehicle: float
    last_updated: str


class GoogleMapsGroundingResult(BaseModel):
    place_id: str
    business_status: str  # OPERATIONAL, CLOSED_TEMPORARILY, CLOSED_PERMANENTLY, CONSTRUCTION
    primary_type: str
    imagery_last_crawled: str
    is_stale: bool = False
    is_disaster_stale: bool = False
    functional_override: bool = False  # True if Maps overrides federal is_functional
    flags: List[str] = Field(default_factory=list)


class PedestrianRouteResult(BaseModel):
    walking_duration_minutes: float
    distance_meters: float
    crosses_flood_risk_area: bool = False
    hazard_feature_name: Optional[str] = None
    is_last_mile_failure: bool = False
    flags: List[str] = Field(default_factory=list)


class FipsAlertPayload(BaseModel):
    county_fips: str
    county_name: str
    emergency_manager_email: str
    shelter_name: str
    grounding_priority: GroundingPriority
    failure_reasons: List[str]
    suggested_redirect: Optional[str] = None
    timestamp: str


class AuditReportItem(BaseModel):
    shelter_name: str
    county_fips: str
    tract_id: str
    physical_status: str
    last_mile_status: str
    urgency_level: GroundingPriority
    population_at_risk_count: int
    population_no_vehicle_pct: float
    failure_diagnostics: List[str]
    alert_dispatched: bool
    redirect_facility: Optional[str]
    brief_markdown: str
