import logging
from typing import Any, Dict, Optional
from ..models import UserProfileState, UserRole, UrgencyLevel

logger = logging.getLogger(__name__)

def build_user_profile(
    role: str,
    primary_request: str,
    location_or_fips: str,
    full_name: str = "Anonymous User",
    organization: str = "Civilian",
    urgency: str = "ROUTINE",
    badge_or_id_number: Optional[str] = None
) -> Dict[str, Any]:
    """
    Constructs and registers the immutable UserProfileState for the active session.
    
    Args:
        role: ONE OF 'FIRST_RESPONDER', 'PUBLIC_GOVERNMENT_SYSTEMS', 'MEDICAL_PERSONNEL', 'INDIVIDUAL_CITIZEN'.
        primary_request: The user's core operational goal or question.
        location_or_fips: Target location, address, zip code, or county FIPS code.
        full_name: Full name of the user or unit (default: 'Anonymous User').
        organization: Organization affiliation (e.g. 'Miami Fire Rescue', 'County EOC', 'Mercy Hospital').
        urgency: ONE OF 'EMERGENCY', 'URGENT', 'ROUTINE'.
        badge_or_id_number: Optional badge number, CCN, or professional identifier.
    """
    normalized_role = role.upper().replace(" ", "_")
    if normalized_role not in [r.value for r in UserRole]:
        if "RESPONDER" in normalized_role or "FIRE" in normalized_role or "POLICE" in normalized_role or "RESCUE" in normalized_role:
            normalized_role = UserRole.FIRST_RESPONDER.value
        elif "GOV" in normalized_role or "COUNTY" in normalized_role or "FIPS" in normalized_role:
            normalized_role = UserRole.PUBLIC_GOVERNMENT_SYSTEMS.value
        elif "MED" in normalized_role or "HOSPITAL" in normalized_role or "NURSE" in normalized_role or "CCN" in normalized_role:
            normalized_role = UserRole.MEDICAL_PERSONNEL.value
        else:
            normalized_role = UserRole.INDIVIDUAL_CITIZEN.value

    normalized_urgency = urgency.upper()
    if normalized_urgency not in [u.value for u in UrgencyLevel]:
        normalized_urgency = UrgencyLevel.ROUTINE.value

    profile = UserProfileState(
        role=normalized_role,
        full_name=full_name,
        organization=organization,
        badge_or_id_number=badge_or_id_number,
        location_or_fips=location_or_fips,
        urgency=normalized_urgency,
        primary_request=primary_request
    )
    
    logger.info("Created UserProfileState: %s (Role: %s, Urgency: %s)", profile.session_id, profile.role, profile.urgency)
    return profile.model_dump()
