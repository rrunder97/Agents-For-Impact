from enum import Enum
from typing import Optional, Literal
from pydantic import BaseModel, Field
import uuid

class UserRole(str, Enum):
    FIRST_RESPONDER = "FIRST_RESPONDER"
    PUBLIC_GOVERNMENT_SYSTEMS = "PUBLIC_GOVERNMENT_SYSTEMS"
    MEDICAL_PERSONNEL = "MEDICAL_PERSONNEL"
    INDIVIDUAL_CITIZEN = "INDIVIDUAL_CITIZEN"

class UrgencyLevel(str, Enum):
    EMERGENCY = "EMERGENCY"
    URGENT = "URGENT"
    ROUTINE = "ROUTINE"

class UserProfileState(BaseModel):
    """
    Standard user profile session state across all ADK agents.
    """
    session_id: str = Field(default_factory=lambda: f"ADK-SESS-{uuid.uuid4().hex[:8]}")
    user_id: str = Field(default_factory=lambda: f"USR-{uuid.uuid4().hex[:8]}")
    role: Literal[
        "FIRST_RESPONDER",
        "PUBLIC_GOVERNMENT_SYSTEMS",
        "MEDICAL_PERSONNEL",
        "INDIVIDUAL_CITIZEN"
    ]
    full_name: str = "Anonymous User"
    organization: str = "General Public"
    badge_or_id_number: Optional[str] = None
    location_or_fips: str = Field(description="Address, City, ZIP, or Parish/County FIPS")
    urgency: Literal["EMERGENCY", "URGENT", "ROUTINE"] = "ROUTINE"
    primary_request: str
