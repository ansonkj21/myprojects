"""
Location lookup used by the search box: turns whatever the user types
(an address, postcode, or a named place like "Edinburgh Castle") into
one or more candidate (name, lat, lng) results to pin on the map.
"""

import math

import requests

import config

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

EARTH_RADIUS_MILES = 3958.8


def distance_miles(lat1, lng1, lat2, lng2):
    """Great-circle distance between two points, in miles."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


class PlacesServiceError(Exception):
    pass


def _base_url(default_url):
    """Use a backend proxy if configured, otherwise call Google directly."""
    return config.GOOGLE_PLACES_PROXY_URL or default_url


def search_location(query):
    """
    Search for a location by free text (address, postcode, or place name).
    Tries Places Text Search first (better for named attractions/venues),
    falls back to Geocoding (better for addresses/postcodes) if that
    returns nothing.
    Returns a list of dicts: name, address, lat, lng. May be empty.
    """
    results = _text_search(query)
    if results:
        return results
    return _geocode(query)


def _text_search(query):
    params = {
        "query": f"{query} UK",
        "region": config.DEFAULT_COUNTRY_BIAS,
        "key": config.GOOGLE_PLACES_API_KEY,
    }
    try:
        resp = requests.get(_base_url(TEXTSEARCH_URL), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise PlacesServiceError(f"Network error during search: {e}")

    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        return []

    out = []
    for item in data.get("results", [])[:8]:
        loc = item.get("geometry", {}).get("location", {})
        if loc.get("lat") is None:
            continue
        out.append({
            "name": item.get("name", query),
            "address": item.get("formatted_address", ""),
            "lat": loc["lat"],
            "lng": loc["lng"],
        })
    return out


def search_nearby(origin_lat, origin_lng, category, radius_m=None):
    """
    Find places of a given category (a key in config.CATEGORY_TYPES) near
    the user's current location (origin_lat, origin_lng) — used by the
    Attractions / Petrol Pumps / Restaurants buttons.

    Results include a 'distance_miles' field and are sorted nearest-first,
    so the caller can group them into 1-mile bands for display.
    Returns a list of dicts: name, address, lat, lng, rating, distance_miles.
    """
    if category not in config.CATEGORY_TYPES:
        raise ValueError(f"Unknown category: {category}")

    params = {
        "location": f"{origin_lat},{origin_lng}",
        "radius": radius_m or config.DEFAULT_SEARCH_RADIUS_M,
        "type": config.CATEGORY_TYPES[category],
        "key": config.GOOGLE_PLACES_API_KEY,
    }
    try:
        resp = requests.get(_base_url(NEARBY_URL), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise PlacesServiceError(f"Network error during nearby search: {e}")

    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        raise PlacesServiceError(f"Places API error: {data.get('status')}")

    out = []
    for item in data.get("results", []):
        loc = item.get("geometry", {}).get("location", {})
        if loc.get("lat") is None:
            continue
        dist = distance_miles(origin_lat, origin_lng, loc["lat"], loc["lng"])
        out.append({
            "name": item.get("name", "Unknown"),
            "address": item.get("vicinity", ""),
            "lat": loc["lat"],
            "lng": loc["lng"],
            "rating": item.get("rating"),
            "distance_miles": round(dist, 2),
        })

    out.sort(key=lambda p: p["distance_miles"])
    return out


def _band_label(band_index, band_size):
    low = band_index * band_size
    high = low + band_size
    if band_index == 0:
        return f"0.1 - {high:g} mile"
    return f"{low + 0.1:g} - {high:g} miles"


def group_by_distance_band(places, band_size_miles=None):
    """
    Groups already-sorted (by distance_miles) places into bands:
    0.1-1 mile, 1.1-2 miles, 2.1-3 miles, etc.
    Returns a list of (band_label, [places]) tuples, in nearest-first order,
    skipping any bands with no results.
    """
    band_size = band_size_miles or config.DISTANCE_BAND_MILES
    bands = {}
    order = []

    for place in places:
        band_index = int(place["distance_miles"] // band_size)
        if band_index not in bands:
            bands[band_index] = []
            order.append(band_index)
        bands[band_index].append(place)

    return [(_band_label(i, band_size), bands[i]) for i in order]


def _geocode(query):
    params = {
        "address": f"{query}, UK",
        "components": f"country:{config.DEFAULT_COUNTRY_BIAS}",
        "key": config.GOOGLE_PLACES_API_KEY,
    }
    try:
        resp = requests.get(_base_url(GEOCODE_URL), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise PlacesServiceError(f"Network error during geocoding: {e}")

    if data.get("status") != "OK":
        return []

    out = []
    for item in data.get("results", [])[:8]:
        loc = item["geometry"]["location"]
        out.append({
            "name": item.get("formatted_address", query),
            "address": item.get("formatted_address", ""),
            "lat": loc["lat"],
            "lng": loc["lng"],
        })
    return out
