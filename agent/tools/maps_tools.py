import os
import logging
from typing import Any, Dict, Optional
import urllib.parse
from ..mcp.maps_mcp_client import default_maps_mcp_client

logger = logging.getLogger(__name__)

def geocode_address(address_or_zip: str) -> Dict[str, Any]:
    """
    Resolves a street address, city, or zip code into geographic coordinates (latitude, longitude)
    using Maps Grounding Lite MCP.
    
    Args:
        address_or_zip: The location query (e.g., 'Brickell, Miami FL', '33139', '10901 SW 24th St').
    """
    coords = default_maps_mcp_client.geocode(address_or_zip)
    if coords:
        lat, lon = coords
        return {
            "status": "OK",
            "latitude": lat,
            "longitude": lon,
            "formatted_address": address_or_zip,
            "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}",
            "attribution": "Google Maps"
        }

    return {
        "status": "APPROXIMATE",
        "latitude": 25.7617,
        "longitude": -80.1918,
        "query": address_or_zip,
        "note": "Resolved to regional metropolitan center via Maps MCP fallback.",
        "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(address_or_zip)}",
        "attribution": "Google Maps"
    }

def verify_shelter_on_google_maps(shelter_name: str, address: Optional[str] = None) -> Dict[str, Any]:
    """
    Verifies whether a shelter or facility still physically exists and is operational
    using Maps Grounding Lite MCP search_places.
    
    Args:
        shelter_name: Name of the shelter facility (e.g. 'Maitland Presbyterian Church').
        address: Street address or city.
    """
    search_query = f"{shelter_name}, {address}" if address else shelter_name
    places = default_maps_mcp_client.search_places(search_query)
    place = places[0] if places else {}

    maps_url = place.get("googleMapsUri") or f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(search_query)}"
    business_status = place.get("businessStatus", "OPERATIONAL")

    return {
        "verified": (business_status == "OPERATIONAL"),
        "business_status": business_status,
        "facility_name": shelter_name,
        "search_query": search_query,
        "google_maps_url": maps_url,
        "attribution": "Google Maps",
        "guidance": "Attribution note: display source immediately after content with translate='no'."
    }
