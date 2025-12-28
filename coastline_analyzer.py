#!/usr/bin/env python3
"""
Coastline Analyzer - Algorithmic Beach Orientation from OpenStreetMap Data

This module fetches coastline data from OSM and calculates:
1. Beach orientation (which direction the beach faces)
2. Ocean view azimuth range
3. Potential headland obstructions

Key insight: OSM coastlines are drawn with water on the RIGHT side.
So the normal vector pointing right of travel direction = pointing to ocean.
"""

import math
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

# ============================================================================
# GEOMETRY UTILITIES
# ============================================================================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in meters"""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi/2)**2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c

def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate bearing from point 1 to point 2 in degrees"""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    x = math.sin(delta_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)

    theta = math.atan2(x, y)
    return (math.degrees(theta) + 360) % 360

def point_to_segment_distance(px: float, py: float,
                               x1: float, y1: float,
                               x2: float, y2: float) -> Tuple[float, float, float]:
    """
    Find distance from point to line segment and closest point on segment.
    Returns (distance, closest_x, closest_y)
    Using simple Euclidean approximation (fine for small areas)
    """
    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == 0:
        return math.sqrt((px-x1)**2 + (py-y1)**2), x1, y1

    t = max(0, min(1, ((px-x1)*dx + (py-y1)*dy) / (dx*dx + dy*dy)))

    closest_x = x1 + t * dx
    closest_y = y1 + t * dy

    dist = math.sqrt((px-closest_x)**2 + (py-closest_y)**2)
    return dist, closest_x, closest_y


@dataclass
class CoastlineSegment:
    """A segment of coastline"""
    lat1: float
    lon1: float
    lat2: float
    lon2: float
    bearing: float  # Direction of travel (water on right)
    ocean_direction: float  # Azimuth pointing toward ocean

@dataclass
class BeachOrientation:
    """Calculated beach orientation from coastline analysis"""
    latitude: float
    longitude: float
    facing_azimuth: float  # Direction the beach faces (toward ocean)
    facing_direction: str  # Human readable (e.g., "west")
    ocean_view_start: float  # Left edge of ocean view
    ocean_view_end: float  # Right edge of ocean view
    coastline_bearing: float  # Local coastline direction
    confidence: str  # "high", "medium", "low"
    headland_warnings: List[str]  # Potential obstructions detected
    analysis_radius_m: float  # How far we looked for coastline
    coastline_points_found: int


# ============================================================================
# OSM OVERPASS API INTERFACE
# ============================================================================

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def fetch_with_retry(query: str, max_retries: int = 5) -> dict:
    """Fetch from Overpass API with exponential backoff"""
    import time

    for attempt in range(max_retries):
        try:
            data = urllib.parse.urlencode({'data': query}).encode('utf-8')
            req = urllib.request.Request(OVERPASS_URL, data=data)
            req.add_header('User-Agent', 'SunsetVisibilityCalculator/1.0')

            timeout = 45 + (attempt * 20)  # 45, 65, 85, 105, 125 seconds
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode('utf-8'))

        except urllib.error.HTTPError as e:
            if e.code in (429, 504, 503, 502):  # Rate limit or server errors
                wait_time = (2 ** attempt) * 3  # 3, 6, 12, 24, 48 seconds
                if attempt < max_retries - 1:
                    print(f"  Server busy, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
            raise
        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 3
                print(f"  Connection error, retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            raise
        except TimeoutError:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 3
                print(f"  Timeout, retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            raise

    return {}


def fetch_coastline(lat: float, lon: float, radius_m: float = 2000) -> List[List[Tuple[float, float]]]:
    """
    Fetch coastline data from OSM Overpass API.

    Args:
        lat: center latitude
        lon: center longitude
        radius_m: search radius in meters

    Returns:
        List of coastline ways, each way is a list of (lat, lon) points
    """
    # Overpass QL query for coastlines
    query = f"""
    [out:json][timeout:30];
    (
      way["natural"="coastline"](around:{radius_m},{lat},{lon});
    );
    out body;
    >;
    out skel qt;
    """

    try:
        result = fetch_with_retry(query)

        # Parse the result
        nodes = {}
        ways = []

        for element in result.get('elements', []):
            if element['type'] == 'node':
                nodes[element['id']] = (element['lat'], element['lon'])
            elif element['type'] == 'way':
                ways.append(element.get('nodes', []))

        # Convert ways to coordinate lists
        coastlines = []
        for way in ways:
            coords = []
            for node_id in way:
                if node_id in nodes:
                    coords.append(nodes[node_id])
            if len(coords) >= 2:
                coastlines.append(coords)

        return coastlines

    except Exception as e:
        print(f"Warning: Could not fetch coastline data: {e}")
        return []


def fetch_nearby_features(lat: float, lon: float, radius_m: float = 5000) -> Dict:
    """
    Fetch geographic features that might create obstructions.
    Looks for: headlands, capes, peninsulas, cliffs, islands
    """
    query = f"""
    [out:json][timeout:30];
    (
      node["natural"="cape"](around:{radius_m},{lat},{lon});
      node["natural"="cliff"](around:{radius_m},{lat},{lon});
      way["natural"="cape"](around:{radius_m},{lat},{lon});
      way["natural"="cliff"](around:{radius_m},{lat},{lon});
      way["natural"="peninsula"](around:{radius_m},{lat},{lon});
      node["place"="island"](around:{radius_m},{lat},{lon});
      way["place"="island"](around:{radius_m},{lat},{lon});
      relation["place"="island"](around:{radius_m},{lat},{lon});
    );
    out center;
    """

    try:
        result = fetch_with_retry(query)

        features = {
            'capes': [],
            'cliffs': [],
            'islands': [],
            'peninsulas': []
        }

        for element in result.get('elements', []):
            # Get coordinates
            if element['type'] == 'node':
                feat_lat, feat_lon = element['lat'], element['lon']
            elif 'center' in element:
                feat_lat = element['center']['lat']
                feat_lon = element['center']['lon']
            else:
                continue

            tags = element.get('tags', {})
            name = tags.get('name', 'Unnamed')

            # Calculate bearing from beach to feature
            feat_bearing = bearing(lat, lon, feat_lat, feat_lon)
            distance = haversine_distance(lat, lon, feat_lat, feat_lon)

            feature_info = {
                'name': name,
                'lat': feat_lat,
                'lon': feat_lon,
                'bearing': feat_bearing,
                'distance_m': distance
            }

            if tags.get('natural') == 'cape':
                features['capes'].append(feature_info)
            elif tags.get('natural') == 'cliff':
                features['cliffs'].append(feature_info)
            elif tags.get('natural') == 'peninsula':
                features['peninsulas'].append(feature_info)
            elif tags.get('place') == 'island':
                features['islands'].append(feature_info)

        return features

    except Exception as e:
        print(f"Warning: Could not fetch feature data: {e}")
        return {'capes': [], 'cliffs': [], 'islands': [], 'peninsulas': []}


# ============================================================================
# COASTLINE ANALYSIS
# ============================================================================

def analyze_coastline(lat: float, lon: float, radius_m: float = 2000) -> BeachOrientation:
    """
    Analyze coastline near a point to determine beach orientation.

    This function:
    1. Fetches nearby coastline from OSM
    2. Finds the closest coastline segment
    3. Calculates the ocean-facing direction
    4. Estimates the view range based on local coastline curvature
    5. Looks for potential obstructions

    Args:
        lat: beach latitude
        lon: beach longitude
        radius_m: search radius

    Returns:
        BeachOrientation with calculated values
    """
    print(f"Fetching coastline data for {lat:.4f}, {lon:.4f}...")
    coastlines = fetch_coastline(lat, lon, radius_m)

    if not coastlines:
        # Try with larger radius
        print(f"No coastline found within {radius_m}m, expanding search...")
        radius_m = 5000
        coastlines = fetch_coastline(lat, lon, radius_m)

    total_points = sum(len(c) for c in coastlines)
    print(f"Found {len(coastlines)} coastline segments with {total_points} points")

    if not coastlines:
        raise ValueError(f"No coastline found within {radius_m}m of {lat}, {lon}")

    # Find the closest coastline segment to our point
    # Convert lat/lon to approximate x/y for distance calculation
    # (using cos(lat) correction for longitude)
    cos_lat = math.cos(math.radians(lat))

    closest_segment = None
    min_dist = float('inf')

    all_segments = []

    for coastline in coastlines:
        for i in range(len(coastline) - 1):
            lat1, lon1 = coastline[i]
            lat2, lon2 = coastline[i + 1]

            # Convert to approximate meters for distance calculation
            x1, y1 = lon1 * cos_lat * 111320, lat1 * 110540
            x2, y2 = lon2 * cos_lat * 111320, lat2 * 110540
            px, py = lon * cos_lat * 111320, lat * 110540

            dist, _, _ = point_to_segment_distance(px, py, x1, y1, x2, y2)

            # Calculate segment bearing (direction of travel along coastline)
            seg_bearing = bearing(lat1, lon1, lat2, lon2)

            # Ocean is to the right of travel direction (OSM convention)
            # So ocean direction is bearing + 90°
            ocean_dir = (seg_bearing + 90) % 360

            segment = CoastlineSegment(
                lat1=lat1, lon1=lon1,
                lat2=lat2, lon2=lon2,
                bearing=seg_bearing,
                ocean_direction=ocean_dir
            )

            all_segments.append((dist, segment))

            if dist < min_dist:
                min_dist = dist
                closest_segment = segment

    if closest_segment is None:
        raise ValueError("Could not find valid coastline segment")

    # The beach faces toward the ocean
    facing_azimuth = closest_segment.ocean_direction

    # Analyze nearby segments to estimate view range
    # Get segments within reasonable distance
    nearby_segments = [(d, s) for d, s in all_segments if d < 1000]  # within 1km
    nearby_segments.sort(key=lambda x: x[0])

    # Calculate view range from coastline geometry
    # Look at the spread of ocean directions from nearby segments
    if len(nearby_segments) >= 3:
        ocean_dirs = [s.ocean_direction for _, s in nearby_segments[:10]]

        # Handle wraparound at 0/360
        # Convert to vectors and average
        sin_sum = sum(math.sin(math.radians(d)) for d in ocean_dirs)
        cos_sum = sum(math.cos(math.radians(d)) for d in ocean_dirs)
        avg_ocean_dir = math.degrees(math.atan2(sin_sum, cos_sum)) % 360

        # Calculate spread
        deviations = []
        for d in ocean_dirs:
            diff = (d - avg_ocean_dir + 180) % 360 - 180
            deviations.append(abs(diff))

        max_deviation = max(deviations) if deviations else 30

        # If coastline is fairly straight, we have wider view
        # If coastline curves, view is more restricted
        if max_deviation < 10:
            # Straight coastline, wide view
            view_half_width = 60
            confidence = "high"
        elif max_deviation < 25:
            # Moderate curvature
            view_half_width = 50
            confidence = "medium"
        else:
            # Significant curvature (bay or cove)
            view_half_width = 40
            confidence = "medium"

        facing_azimuth = avg_ocean_dir
    else:
        view_half_width = 50
        confidence = "low"

    ocean_view_start = (facing_azimuth - view_half_width) % 360
    ocean_view_end = (facing_azimuth + view_half_width) % 360

    # Fetch nearby features that might cause obstructions
    print("Checking for nearby headlands, capes, islands...")
    features = fetch_nearby_features(lat, lon, 5000)

    headland_warnings = []

    # Check capes and peninsulas
    for cape in features['capes'] + features['peninsulas']:
        cape_bearing = cape['bearing']
        cape_dist = cape['distance_m']

        # Check if cape is within our ocean view
        if is_bearing_in_range(cape_bearing, ocean_view_start, ocean_view_end):
            warning = f"{cape['name']} at {cape_bearing:.0f}° ({cape_dist/1000:.1f}km) may obstruct view"
            headland_warnings.append(warning)

    # Check islands (scenic features rather than obstructions)
    for island in features['islands']:
        island_bearing = island['bearing']
        island_dist = island['distance_m']

        if is_bearing_in_range(island_bearing, ocean_view_start, ocean_view_end):
            if island_dist < 10000:  # Within 10km
                warning = f"Island '{island['name']}' at {island_bearing:.0f}° ({island_dist/1000:.1f}km) - potential scenic feature"
                headland_warnings.append(warning)

    direction_name = get_direction_name(facing_azimuth)

    return BeachOrientation(
        latitude=lat,
        longitude=lon,
        facing_azimuth=facing_azimuth,
        facing_direction=direction_name,
        ocean_view_start=ocean_view_start,
        ocean_view_end=ocean_view_end,
        coastline_bearing=closest_segment.bearing,
        confidence=confidence,
        headland_warnings=headland_warnings,
        analysis_radius_m=radius_m,
        coastline_points_found=total_points
    )


def is_bearing_in_range(bearing: float, start: float, end: float) -> bool:
    """Check if a bearing falls within a range (handling wraparound)"""
    bearing = bearing % 360
    start = start % 360
    end = end % 360

    if start <= end:
        return start <= bearing <= end
    else:
        # Range wraps around 360
        return bearing >= start or bearing <= end


def get_direction_name(azimuth: float) -> str:
    """Convert azimuth to compass direction name"""
    directions = [
        (0, "north"), (22.5, "north-northeast"), (45, "northeast"),
        (67.5, "east-northeast"), (90, "east"), (112.5, "east-southeast"),
        (135, "southeast"), (157.5, "south-southeast"), (180, "south"),
        (202.5, "south-southwest"), (225, "southwest"), (247.5, "west-southwest"),
        (270, "west"), (292.5, "west-northwest"), (315, "northwest"),
        (337.5, "north-northwest"), (360, "north")
    ]

    azimuth = azimuth % 360
    for i in range(len(directions) - 1):
        if directions[i][0] <= azimuth < directions[i+1][0]:
            if azimuth - directions[i][0] < directions[i+1][0] - azimuth:
                return directions[i][1]
            else:
                return directions[i+1][1]
    return "north"


# ============================================================================
# BEACH LOOKUP FROM OSM
# ============================================================================

def search_beach_osm(name: str, country: str = None) -> List[Dict]:
    """
    Search for a beach by name using OSM Nominatim.

    Returns list of matching beaches with coordinates.
    """
    base_url = "https://nominatim.openstreetmap.org/search"

    query = name
    if country:
        query += f", {country}"

    params = {
        'q': query,
        'format': 'json',
        'limit': 10,
        'featuretype': 'natural'
    }

    url = base_url + "?" + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'SunsetVisibilityCalculator/1.0')

        with urllib.request.urlopen(req, timeout=10) as response:
            results = json.loads(response.read().decode('utf-8'))

        beaches = []
        for r in results:
            # Filter for beaches
            if 'beach' in r.get('type', '').lower() or 'beach' in r.get('display_name', '').lower():
                beaches.append({
                    'name': r.get('display_name', ''),
                    'lat': float(r['lat']),
                    'lon': float(r['lon']),
                    'type': r.get('type', ''),
                    'importance': r.get('importance', 0)
                })

        return beaches

    except Exception as e:
        print(f"Warning: Beach search failed: {e}")
        return []


# ============================================================================
# MAIN - STANDALONE TESTING
# ============================================================================

def print_orientation(orientation: BeachOrientation):
    """Pretty print beach orientation analysis"""
    print("\n" + "=" * 60)
    print("COASTLINE ANALYSIS RESULTS")
    print("=" * 60)

    print(f"\nLocation: {orientation.latitude:.4f}°, {orientation.longitude:.4f}°")
    print(f"Analysis radius: {orientation.analysis_radius_m}m")
    print(f"Coastline points analyzed: {orientation.coastline_points_found}")
    print(f"Confidence: {orientation.confidence.upper()}")

    print(f"\n{'─' * 40}")
    print("BEACH ORIENTATION:")
    print(f"  Faces: {orientation.facing_direction} ({orientation.facing_azimuth:.1f}°)")
    print(f"  Coastline bearing: {orientation.coastline_bearing:.1f}°")

    print(f"\n{'─' * 40}")
    print("ESTIMATED OCEAN VIEW:")
    print(f"  Range: {orientation.ocean_view_start:.1f}° to {orientation.ocean_view_end:.1f}°")
    view_width = (orientation.ocean_view_end - orientation.ocean_view_start) % 360
    print(f"  Width: {view_width:.1f}° of horizon")

    if orientation.headland_warnings:
        print(f"\n{'─' * 40}")
        print("POTENTIAL FEATURES/OBSTRUCTIONS:")
        for warning in orientation.headland_warnings:
            print(f"  • {warning}")

    # Check if good for sunset
    print(f"\n{'─' * 40}")
    print("SUNSET ASSESSMENT:")

    # Sunset is generally 240-300° (winter) to 280-320° (summer) depending on latitude
    west_range_start = 240
    west_range_end = 300

    view_start = orientation.ocean_view_start
    view_end = orientation.ocean_view_end

    # Handle wraparound
    if view_start > view_end:
        # View wraps around 360
        if west_range_start <= 360 or west_range_start <= view_end:
            sunset_visible = True
        else:
            sunset_visible = view_start <= west_range_end
    else:
        # Check overlap
        sunset_visible = not (view_end < west_range_start or view_start > west_range_end)

    if sunset_visible:
        print("  ✓ This beach likely has sunset views over the ocean")
        print("    (at least during some parts of the year)")
    else:
        print("  ✗ This beach may NOT have sunset over the ocean")
        print(f"    Beach faces {orientation.facing_direction}, sunset is in the west")


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 3:
        lat = float(sys.argv[1])
        lon = float(sys.argv[2])
    else:
        # Default: test with Nai Harn Beach
        print("Usage: python coastline_analyzer.py <latitude> <longitude>")
        print("\nRunning with default location (Nai Harn Beach, Phuket)...")
        lat, lon = 7.7677, 98.3036

    orientation = analyze_coastline(lat, lon)
    print_orientation(orientation)
