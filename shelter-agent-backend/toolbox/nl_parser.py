"""
nl_parser.py - Disaster Evacuation Natural Language Query Parser.

Extracts structured life-safety constraints, party sizes, and geospatial preferences
from natural language evacuation queries for emergency shelter matching.
"""

import re
from typing import Dict, Any, Optional

# Word-to-number mapping for common party/family sizes
WORD_NUMS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "single": 1, "couple": 2, "myself": 1, "me": 1
}

# Known Louisiana cities in the FEMA NSS dataset
LOUISIANA_CITIES = [
    "baton rouge", "new orleans", "shreveport", "lafayette",
    "lake charles", "alexandria", "monroe", "houma", "bossier city",
    "kenner", "slidell", "hammond", "natchitoches", "new iberia"
]

def parse_shelter_intent(query: str) -> Dict[str, Any]:
    """
    Parses a citizen's or responder's natural language request into structured
    search parameters for the FEMA / BigQuery shelter database.
    
    Example queries:
    - 'I have a family of 4 with one person having wheelchair needs and hospital need'
    - 'Need a nearest shelter with generator'
    - 'Wheelchair accessible shelter in Baton Rouge with medical care for 3 people'
    """
    if not query:
        return {
            "raw_query": "",
            "party_size": 1,
            "wheelchair_accessible": False,
            "is_medical": False,
            "generator_onsite": False,
            "pets_allowed": False,
            "detected_location": None,
            "limit": 3,
            "badges": ["👥 Party of 1"],
            "summary": "Standard Search"
        }

    q_lower = query.lower().strip()
    
    # 1. Extract Party / Family Size
    party_size = 1
    # Check "family of X", "party of X", "group of X", "X people", "X persons", "X members"
    party_match = re.search(
        r'(?:family|party|group|household)\s+of\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)',
        q_lower
    )
    if not party_match:
        party_match = re.search(
            r'(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:people|persons|members|family\s+members|of\s+us)',
            q_lower
        )
    if not party_match:
        adult_kid_match = re.search(r'(\d+)\s+adults?(?:\s+and\s+(\d+)\s+(?:kids?|children))?', q_lower)
        if adult_kid_match:
            adults = int(adult_kid_match.group(1))
            kids = int(adult_kid_match.group(2)) if adult_kid_match.group(2) else 0
            party_size = max(1, adults + kids)
    
    if party_match:
        val = party_match.group(1)
        if val.isdigit():
            party_size = max(1, int(val))
        elif val in WORD_NUMS:
            party_size = WORD_NUMS[val]

    # 2. Extract Wheelchair / ADA Accessibility Needs
    wheelchair_accessible = bool(re.search(
        r'\b(wheelchair|wheelchairs|mobility|handicap|disabled|ada|special\s+mobility)\b',
        q_lower
    ))

    # 3. Extract Medical / Hospital / Clinical Care Needs
    is_medical = bool(re.search(
        r'\b(medical|hospital|hospitals|clinic|nursing|dialysis|oxygen|healthcare|special\s+medical|critical\s+care)\b',
        q_lower
    ))

    # 4. Extract Backup Generator / On-site Electricity Needs
    generator_onsite = bool(re.search(
        r'\b(generator|generators|power|backup\s+power|electricity|grid|power\s+onsite|backup\s+electric)\b',
        q_lower
    ))

    # 5. Extract Pet Accommodations
    pets_allowed = bool(re.search(
        r'\b(pet|pets|dog|dogs|cat|cats|animal|service\s+animal)\b',
        q_lower
    ))

    # 6. Extract Location / City
    detected_location = None
    for city in LOUISIANA_CITIES:
        if city in q_lower:
            detected_location = city.title() + ", LA"
            break
            
    # Also check zip codes (5 digits)
    zip_match = re.search(r'\b(7\d{4}|3\d{4})\b', q_lower)
    if zip_match and not detected_location:
        detected_location = zip_match.group(1)

    # 7. Extract Proximity / Limit
    limit = 3
    if re.search(r'\b(nearest|closest|top\s+1|single)\b', q_lower):
        limit = 3
    limit_match = re.search(r'top\s+(\d+)', q_lower)
    if limit_match:
        limit = max(1, min(10, int(limit_match.group(1))))

    # 8. Human-Readable Badges & Summary for UI
    badges = []
    badges.append(f"👥 Party of {party_size}")
    if wheelchair_accessible:
        badges.append("♿ Wheelchair Access Required")
    if is_medical:
        badges.append("🏥 Medical / Hospital Readiness Required")
    if generator_onsite:
        badges.append("⚡ Backup Generator Required")
    if pets_allowed:
        badges.append("🐾 Pet Accommodations")
    if detected_location:
        badges.append(f"📍 Location: {detected_location}")

    summary = " | ".join(badges)

    return {
        "raw_query": query,
        "party_size": party_size,
        "wheelchair_accessible": wheelchair_accessible,
        "is_medical": is_medical,
        "generator_onsite": generator_onsite,
        "pets_allowed": pets_allowed,
        "detected_location": detected_location,
        "limit": limit,
        "badges": badges,
        "summary": summary
    }
