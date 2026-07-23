"""
Configuration for the UK Trip Planner app — first release.

SECURITY NOTE:
Never ship a real Google API key inside a public APK — anyone can
decompile the app and extract it. For a real release, route requests
through your own small backend (e.g. a Cloud Function) that holds the
key server-side, and point GOOGLE_PLACES_PROXY_URL below at that
backend instead of calling Google directly. For development/testing,
you can use the key directly.
"""

import os

# --- Google Geocoding API (used for the location search box) ---
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "YOUR_API_KEY_HERE")

# Optional backend proxy — leave blank to call Google directly during dev.
GOOGLE_PLACES_PROXY_URL = os.environ.get("GOOGLE_PLACES_PROXY_URL", "")

DEFAULT_COUNTRY_BIAS = "uk"

# --- Nearby category search (Attractions / Petrol Stations / Restaurants) ---
DEFAULT_SEARCH_RADIUS_M = 8000  # 8 km
CATEGORY_TYPES = {
    "Attractions": "tourist_attraction",
    "Petrol Pumps": "gas_station",
    "Restaurants": "restaurant",
}

# Category results are grouped into bands by distance from the user's
# current GPS location: 0.1-1 mile, 1.1-2 miles, 2.1-3 miles, etc.
DISTANCE_BAND_MILES = 1.0

# --- Map defaults (centered on the UK) ---
DEFAULT_MAP_LAT = 54.5
DEFAULT_MAP_LNG = -3.0
DEFAULT_MAP_ZOOM = 6

# --- Days ---
DEFAULT_NUM_DAYS = 3  # app starts with Day 1 / Day 2 / Day 3
MAX_DAYS = 30

# Marker colors, cycled per day so pins are visually distinguishable on the map
DAY_MARKER_COLORS = [
    (0.90, 0.20, 0.20, 1),  # red
    (0.20, 0.45, 0.90, 1),  # blue
    (0.20, 0.75, 0.35, 1),  # green
    (0.95, 0.65, 0.10, 1),  # orange
    (0.60, 0.25, 0.85, 1),  # purple
    (0.10, 0.75, 0.75, 1),  # teal
]
