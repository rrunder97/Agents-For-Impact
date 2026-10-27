# Emergency Shelter Agent & Live Evacuation Dashboard

Full-stack emergency shelter finding service, live evacuee dashboard, and ADK tool suite built for the **Agents for Impact 2026 Challenge**.

## Features
- **Spatial Shelter Grounding**: Direct BigQuery spatial queries using `ST_DWITHIN` and `ST_GEOGPOINT` across official FEMA National Shelter System (NSS) data.
- **Turn-by-Turn Driving Navigation**: Real-time travel duration, driving distance, and dynamic navigation links powered by Google Maps Distance Matrix and Geocoding APIs.
- **Real-Time Capacity Tracking**: Live `available_capacity` metrics tracked and displayed in real time.
- **Evacuee Reservation System**: Atomic capacity booking via BigQuery DML upon shelter acceptance.
- **Interactive Web Interface**: Complete responsive emergency UI with live search tips, real-time capacity progress indicators, party size selection, and turn-by-turn navigation buttons.
- **ADK Toolbox Integration**: Modular `google.adk.tools` implementations in `toolbox/` for BigQuery spatial search, capacity booking, and Google Maps routing.

## Structure
```
shelter-agent-backend/
├── main.py                  # Cloud Functions / Cloud Run entrypoint
├── server.py                # Full-stack HTTP server (UI + API)
├── serve_ui.py              # Local testing & development proxy
├── Dockerfile               # Container build configuration for Cloud Run
├── requirements.txt         # Dependencies (bigquery, googlemaps, adk)
├── toolbox/                 # ADK FunctionTool modules
│   ├── __init__.py
│   ├── bigquery_tool.py     # Spatial queries & atomic capacity reservation
│   └── maps_tool.py         # Geocoding, Distance Matrix, directions URL
└── ui/                      # Frontend web application
    ├── index.html           # Emergency shelter dashboard & search UI
    ├── styles.css           # Styling, status badges, capacity meters
    └── app.js               # Reactive search, reservation, directions
```

## Running Locally
```bash
cd shelter-agent-backend
pip install -r requirements.txt
python server.py
# Access at http://localhost:8080
```

## Cloud Run Deployment
```bash
gcloud run deploy shelter-agent-backend \
  --source=. \
  --region=us-central1 \
  --allow-unauthenticated \
  --port=8080 \
  --memory=512Mi
```
