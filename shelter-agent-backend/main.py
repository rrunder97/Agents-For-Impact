import json

try:
    import functions_framework
    http_decorator = functions_framework.http
except ImportError:
    def http_decorator(func):
        return func

from toolbox import (
    search_shelters_spatial,
    book_shelter_capacity,
    geocode_address,
    calculate_driving_routes,
    build_google_maps_directions_link
)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "3600"
}

@http_decorator
def find_shelters(request):
    """ADK-Integrated HTTP Cloud Function for Emergency Shelter Spatial Routing & Real-Time Capacity."""
    if request.method == "OPTIONS":
        return ("", 204, CORS_HEADERS)

    response_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
    }

    request_json = request.get_json(silent=True) or {}

    # Action 1: Reserve / Accept Shelter Capacity
    action = request_json.get("action")
    if action == "book" or (request_json.get("shelter_id") and request_json.get("reserve")):
        shelter_id = request_json.get("shelter_id")
        party_size = int(request_json.get("party_size", 1))
        print(f"[BOOK_REQUEST] Reserving shelter_id={shelter_id}, party_size={party_size}")
        try:
            booking_res = book_shelter_capacity(shelter_id, party_size)
            return (json.dumps(booking_res), 200, response_headers)
        except Exception as e:
            print(f"[BOOK_ERROR] Error booking shelter {shelter_id}: {str(e)}")
            return (json.dumps({"success": False, "error": str(e)}), 500, response_headers)

    # Action 2: Spatial Search & Route Calculations
    user_lat = request_json.get("latitude")
    user_lon = request_json.get("longitude")
    address = request_json.get("address")
    require_wheelchair = bool(request_json.get("wheelchair_accessible", False))
    require_medical = bool(request_json.get("is_medical", False))
    require_generator = bool(request_json.get("generator_onsite", False))
    if "include_closed" in request_json:
        include_closed = bool(request_json["include_closed"])
    else:
        include_closed = True # Default to True so queries match standby facilities in FEMA database
    limit = int(request_json.get("limit", 3))

    print(f"[SEARCH_REQUEST] address='{address}', lat={user_lat}, lon={user_lon}, include_closed={include_closed}, limit={limit}")

    # Step 1: Use ADK Maps Tool for Geocoding if needed
    if (user_lat is None or user_lon is None) and address:
        coords = geocode_address(address)
        if coords:
            user_lat, user_lon = coords
            print(f"[ADK_TOOL] Geocoded '{address}' -> ({user_lat}, {user_lon})")
        else:
            return (json.dumps({"error": f"Address '{address}' could not be resolved."}), 400, response_headers)

    if user_lat is None or user_lon is None:
        return (json.dumps({"error": "Latitude/Longitude or a valid address is required."}), 400, response_headers)

    # Step 2: Use ADK BigQuery Tool for Spatial Search & Real-Time Capacity
    try:
        rows = search_shelters_spatial(
            lat=float(user_lat),
            lon=float(user_lon),
            require_wheelchair=require_wheelchair,
            require_medical=require_medical,
            require_generator=require_generator,
            include_closed=include_closed,
            limit=limit
        )
        print(f"[ADK_TOOL] BigQuery returned {len(rows)} matching shelters")
    except Exception as e:
        print(f"[ADK_TOOL_ERROR] BigQuery error: {str(e)}")
        return (json.dumps({"error": f"BigQuery error: {str(e)}"}), 500, response_headers)

    # Step 3: Use ADK Maps Routing Tool for Distance Matrix & Driving Directions
    destinations = [(float(r["latitude"]), float(r["longitude"])) for r in rows if r.get("latitude") and r.get("longitude")]
    driving_metrics = calculate_driving_routes(float(user_lat), float(user_lon), destinations)

    results = []
    for idx, row in enumerate(rows):
        drive_metric = driving_metrics[idx] if idx < len(driving_metrics) else {"duration_text": "Unavailable", "distance_text": "Unavailable"}
        
        dest_addr = f"{row.get('address_1', '')}, {row.get('city', '')}"
        maps_nav_link = build_google_maps_directions_link(
            origin_lat=float(user_lat),
            origin_lon=float(user_lon),
            dest_lat=float(row["latitude"]),
            dest_lon=float(row["longitude"]),
            dest_name_or_address=f"{row['shelter_name']}, {dest_addr}"
        )

        raw_cap = row.get("evacuation_capacity")
        raw_avail = row.get("available_capacity")
        total_cap = int(raw_cap if raw_cap is not None else (raw_avail if raw_avail is not None else 100))
        avail_cap = int(raw_avail if raw_avail is not None else total_cap)

        results.append({
            "shelter_id": row.get("shelter_id"),
            "shelter_name": row["shelter_name"],
            "address": dest_addr,
            "city": row.get("city"),
            "status": row.get("shelter_status_code", "UNKNOWN"),
            "total_capacity": total_cap,
            "available_capacity": avail_cap,
            "capacity": total_cap,
            "features": {
                "wheelchair_accessible": row.get("wheelchair_accessible"),
                "medical_ready": row.get("is_medical"),
                "backup_generator": row.get("generator_onsite"),
                "pets_allowed": row.get("pet_accommodations_code")
            },
            "straight_line_distance_km": round(row.get("distance_meters", 0) / 1000.0, 2),
            "estimated_driving_time": drive_metric.get("duration_text", "Unavailable"),
            "estimated_driving_distance": drive_metric.get("distance_text", "Unavailable"),
            "google_maps_url": maps_nav_link,
            "origin_coordinates": {"lat": user_lat, "lon": user_lon},
            "shelter_coordinates": {"lat": row["latitude"], "lon": row["longitude"]}
        })

    print(f"[SEARCH_RESPONSE] Returning {len(results)} matches")
    return (json.dumps({"matches": results}), 200, response_headers)
