import os
import urllib.parse
import urllib.request
import json
from typing import List, Dict, Any, Optional, Tuple

try:
    import googlemaps
except ImportError:
    googlemaps = None

try:
    from google.adk.tools import FunctionTool
except ImportError:
    class FunctionTool:
        def __init__(self, func, **kwargs):
            self.func = func
            self.__doc__ = func.__doc__
        def __call__(self, *args, **kwargs):
            return self.func(*args, **kwargs)

MAPS_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "AIzaSyCL992WDJJTY99Cx-QJDDg_bj6Go1x2RD0")
maps_client = None
if googlemaps:
    try:
        maps_client = googlemaps.Client(key=MAPS_KEY)
    except Exception as e:
        print(f"[MAPS_INIT_WARNING] {e}")

def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """ADK Tool: Geocodes a natural language street address, city, or postal code into (latitude, longitude).
    
    Args:
        address: Natural language street address or location string.
        
    Returns:
        Tuple of (latitude, longitude) or None if address could not be resolved.
    """
    if not address:
        return None

    if maps_client:
        try:
            results = maps_client.geocode(address)
            if results and len(results) > 0:
                loc = results[0]["geometry"]["location"]
                return (loc["lat"], loc["lng"])
        except Exception as e:
            print(f"[MAPS_CLIENT_GEOCODE_ERROR] {e}")

    # Robust direct HTTP fallback
    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={MAPS_KEY}"
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            if data.get("results"):
                loc = data["results"][0]["geometry"]["location"]
                return (loc["lat"], loc["lng"])
    except Exception as e:
        print(f"[MAPS_HTTP_GEOCODE_ERROR] {e}")

    return None

def calculate_driving_routes(
    origin_lat: float,
    origin_lon: float,
    destinations: List[Tuple[float, float]]
) -> List[Dict[str, Any]]:
    """ADK Tool: Computes real-time driving times and distances using Google Maps Distance Matrix API.
    
    Args:
        origin_lat: User starting latitude.
        origin_lon: User starting longitude.
        destinations: List of (latitude, longitude) destinations.
        
    Returns:
        List of dictionaries with estimated driving duration and distance.
    """
    if not destinations:
        return []

    if maps_client:
        try:
            res = maps_client.distance_matrix(
                origins=[(origin_lat, origin_lon)],
                destinations=destinations,
                mode="driving",
                departure_time="now"
            )
            metrics = []
            if res and "rows" in res and len(res["rows"]) > 0:
                elements = res["rows"][0].get("elements", [])
                for elem in elements:
                    if elem.get("status") == "OK":
                        duration = elem.get("duration_in_traffic", elem.get("duration", {}))
                        distance = elem.get("distance", {})
                        metrics.append({
                            "duration_text": duration.get("text", "Unavailable"),
                            "duration_value_sec": duration.get("value", 0),
                            "distance_text": distance.get("text", "Unavailable"),
                            "distance_value_m": distance.get("value", 0)
                        })
                    else:
                        metrics.append({"duration_text": "Unavailable", "distance_text": "Unavailable"})
                return metrics
        except Exception as e:
            print(f"[MAPS_CLIENT_DISTANCE_ERROR] {e}")

    # Robust direct HTTP fallback
    try:
        dest_str = "|".join([f"{d[0]},{d[1]}" for d in destinations])
        url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origin_lat},{origin_lon}&destinations={urllib.parse.quote(dest_str)}&mode=driving&key={MAPS_KEY}"
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            metrics = []
            if "rows" in data and len(data["rows"]) > 0:
                for elem in data["rows"][0].get("elements", []):
                    if elem.get("status") == "OK":
                        dur = elem.get("duration", {}).get("text", "Unavailable")
                        dist = elem.get("distance", {}).get("text", "Unavailable")
                        metrics.append({"duration_text": dur, "distance_text": dist})
                    else:
                        metrics.append({"duration_text": "Unavailable", "distance_text": "Unavailable"})
                return metrics
    except Exception as e:
        print(f"[MAPS_HTTP_DISTANCE_ERROR] {e}")

    return [{"duration_text": "Unavailable", "distance_text": "Unavailable"} for _ in destinations]

def build_google_maps_directions_link(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    dest_name_or_address: str
) -> str:
    """ADK Tool: Generates universal Google Maps Turn-by-Turn Navigation URL."""
    base_url = "https://www.google.com/maps/dir/?api=1"
    origin_param = f"{origin_lat},{origin_lon}"
    dest_param = dest_name_or_address if dest_name_or_address else f"{dest_lat},{dest_lon}"
    query = urllib.parse.urlencode({
        "origin": origin_param,
        "destination": dest_param,
        "travelmode": "driving"
    })
    return f"{base_url}&{query}"

# ADK FunctionTool registrations
maps_geocode_tool = FunctionTool(geocode_address)
maps_routing_tool = FunctionTool(calculate_driving_routes)
maps_directions_link_tool = FunctionTool(build_google_maps_directions_link)
