#!/usr/bin/env python3
"""
Sunset Visibility Calculator

Check if sunset will be visible over the ocean from any beach on Earth.

Usage:
  sunset_check.py "Nai Harn Beach, Phuket"
  sunset_check.py "Waikiki Beach" --date 2025-06-21
  sunset_check.py --lat 7.7677 --lon 98.3036

All data comes from OpenStreetMap:
  - Beach locations via Nominatim geocoding
  - Coastline orientation via Overpass API
  - Nearby islands/capes for scenic features and obstructions
"""

import argparse
import sys
import json
import math
from datetime import datetime, timedelta


def _log(message: str):
    """Print status message to stderr (not mixed with output)"""
    print(message, file=sys.stderr)

from coastline_analyzer import (
    analyze_coastline,
    search_beach_osm,
    geocode_location,
    find_beaches_near,
    get_direction_name,
    BeachOrientation,
    InlandLocationError
)
from sunset_visibility import find_sunset, SunPosition, NoSunsetError


# ============================================================================
# TIMEZONE LOOKUP
# ============================================================================

import os
import urllib.request
import urllib.error
import urllib.parse

GEONAMES_USERNAME = os.environ.get('GEONAMES_USERNAME', 'demo')
GEONAMES_URL = "http://api.geonames.org/timezoneJSON"


def get_timezone(lat: float, lon: float) -> dict:
    """
    Get timezone info from GeoNames API.

    Returns dict with:
        offset: float - current UTC offset (accounts for DST)
        timezone_id: str - IANA timezone ID (e.g., "Europe/Paris")
        source: str - "geonames" or "estimated"

    Falls back to longitude-based estimation if API fails.
    """
    # Try GeoNames API first
    result = _fetch_geonames_timezone(lat, lon)
    if result:
        return result

    # Fallback to longitude estimation
    _log("  Using estimated timezone (GeoNames unavailable)")
    return {
        'offset': round(lon / 15),
        'timezone_id': None,
        'source': 'estimated'
    }


def _fetch_geonames_timezone(lat: float, lon: float, max_retries: int = 3) -> dict:
    """
    Fetch timezone from GeoNames API with retry and error handling.

    Returns dict with offset/timezone_id/source, or None if API fails.
    """
    import time

    params = urllib.parse.urlencode({
        'lat': lat,
        'lng': lon,
        'username': GEONAMES_USERNAME
    })
    url = f"{GEONAMES_URL}?{params}"

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'SunsetVisibilityCalculator/1.0')

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            # Check for API errors
            if 'status' in data:
                error_msg = data.get('status', {}).get('message', 'Unknown error')
                error_code = data.get('status', {}).get('value', 0)

                # Error 10 = auth error, 18 = daily limit, 19 = hourly limit
                if error_code in (10, 18, 19):
                    _log(f"  GeoNames API limit/auth error: {error_msg}")
                    return None  # Don't retry auth/limit errors

                _log(f"  GeoNames API error: {error_msg}")
                if attempt < max_retries - 1:
                    time.sleep((2 ** attempt) * 1)
                    continue
                return None

            # Extract timezone info
            # Use dstOffset if available (current offset including DST)
            # Otherwise use gmtOffset (standard time offset)
            if 'dstOffset' in data:
                offset = data['dstOffset']
            elif 'gmtOffset' in data:
                offset = data['gmtOffset']
            else:
                _log("  GeoNames response missing offset")
                return None

            return {
                'offset': offset,
                'timezone_id': data.get('timezoneId'),
                'source': 'geonames'
            }

        except urllib.error.HTTPError as e:
            if e.code == 429:  # Rate limited
                wait_time = (2 ** attempt) * 2
                if attempt < max_retries - 1:
                    _log(f"  GeoNames rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
            _log(f"  GeoNames HTTP error: {e.code}")
            return None

        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 1
                _log(f"  GeoNames connection error, retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            _log(f"  GeoNames connection failed: {e.reason}")
            return None

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            _log(f"  GeoNames response parse error: {e}")
            return None

        except Exception as e:
            _log(f"  GeoNames unexpected error: {e}")
            return None

    return None


# ============================================================================
# BEACH LOOKUP
# ============================================================================

def find_beach(query: str) -> dict:
    """
    Find a beach by name using OpenStreetMap Nominatim.
    If no beach found by name, geocodes the query and finds nearest beach.

    Returns dict with: name, lat, lon, display_name
    """
    _log(f"Searching for '{query}'...")

    results = search_beach_osm(query)

    if not results:
        # Try appending "beach" if not already there
        if 'beach' not in query.lower():
            results = search_beach_osm(query + " beach")

    if results:
        best = results[0]
        # Show full location to help user verify this is the right place
        _log(f"Found: {best['name']}")
        # If there are other results, hint that they might want to be more specific
        if len(results) > 1:
            _log(f"  (Tip: If this isn't the right location, try a more specific query)")
        return {
            'name': query,  # Use user's query as name
            'lat': best['lat'],
            'lon': best['lon'],
            'display_name': best['name']
        }

    # Fallback: geocode the query and find nearest beach
    _log(f"No beach named '{query}' found, searching for nearest beach...")

    try:
        location = geocode_location(query)
        _log(f"Location: {location['display_name'][:60]}...")
    except ValueError:
        raise ValueError(f"Could not find '{query}'. Try being more specific or use --lat/--lon.")

    # Search for beaches near this location, expanding radius if needed
    for radius in [5000, 10000, 20000]:
        beaches = find_beaches_near(location['lat'], location['lon'], radius)
        if beaches:
            break

    if not beaches:
        raise ValueError(f"No beaches found within 20km of '{query}'.")

    best = beaches[0]
    _log(f"Nearest beach: {best['name']} ({best['distance_m']/1000:.1f}km away)")

    return {
        'name': best['name'],
        'lat': best['lat'],
        'lon': best['lon'],
        'display_name': best['name']
    }


# ============================================================================
# MAIN ANALYSIS
# ============================================================================

def check_sunset(lat: float, lon: float, name: str, date: datetime) -> dict:
    """
    Check if sunset will be visible over the ocean.

    Args:
        lat: latitude
        lon: longitude
        name: beach name for display
        date: date to check

    Returns:
        Analysis results dict

    Raises:
        NoSunsetError: if no sunset on this date (polar regions)
    """
    # Analyze coastline to get beach orientation
    _log(f"Analyzing coastline...")
    orientation = analyze_coastline(lat, lon)

    # Get timezone
    tz_info = get_timezone(lat, lon)
    tz_offset = tz_info['offset']

    # Calculate sunset position (may raise NoSunsetError for polar regions)
    sunset = find_sunset(date, lat, lon, tz_offset)
    local_time = sunset.time + timedelta(hours=tz_offset)

    # Check if sunset is over ocean
    sun_over_ocean = is_in_view(
        sunset.azimuth,
        orientation.ocean_view_start,
        orientation.ocean_view_end
    )

    # Check for scenic features (islands near sunset azimuth)
    scenic_feature = None
    for warning in orientation.headland_warnings:
        if 'island' in warning.lower() or 'Island' in warning:
            # Extract island info
            scenic_feature = warning
            break

    direction = get_direction_name(sunset.azimuth)

    water_type = "lake" if orientation.is_lake else "ocean"

    return {
        'beach': {
            'name': name,
            'lat': lat,
            'lon': lon,
            'facing': orientation.facing_direction,
            'ocean_view_start': orientation.ocean_view_start,
            'ocean_view_end': orientation.ocean_view_end,
            'water_type': water_type,
        },
        'date': date.strftime('%Y-%m-%d'),
        'sunset': {
            'local_time': local_time.strftime('%H:%M'),
            'timezone': tz_info['timezone_id'] or f"UTC{tz_offset:+.0f}",
            'timezone_offset': tz_offset,
            'timezone_source': tz_info['source'],
            'azimuth': round(sunset.azimuth, 1),
            'direction': direction
        },
        'visibility': {
            'sun_sets_over_water': sun_over_ocean,
            'scenic_feature': scenic_feature,
            'confidence': orientation.confidence
        },
        'analysis': {
            'coastline_points': orientation.coastline_points_found,
            'headland_warnings': orientation.headland_warnings
        }
    }


def is_in_view(azimuth: float, view_start: float, view_end: float) -> bool:
    """Check if azimuth falls within ocean view range (handles wraparound)"""
    azimuth = azimuth % 360
    view_start = view_start % 360
    view_end = view_end % 360

    if view_start <= view_end:
        return view_start <= azimuth <= view_end
    else:
        # Wraps around 360
        return azimuth >= view_start or azimuth <= view_end


# ============================================================================
# OUTPUT
# ============================================================================

def print_results(results: dict):
    """Print formatted results"""
    b = results['beach']
    s = results['sunset']
    v = results['visibility']

    water_type = b.get('water_type', 'ocean')
    water_label = "Lake" if water_type == "lake" else "Ocean"

    print("\n" + "=" * 60)
    print(f"SUNSET VISIBILITY: {b['name']}")
    print("=" * 60)

    print(f"\nDate: {results['date']}")
    print(f"Location: {b['lat']:.4f}, {b['lon']:.4f}")
    print(f"Beach faces: {b['facing']}")
    print(f"{water_label} view: {b['ocean_view_start']:.0f}° to {b['ocean_view_end']:.0f}°")

    print(f"\n" + "-" * 40)
    print(f"Sunset: {s['local_time']} ({s['timezone']})")
    print(f"Sun position: {s['azimuth']}° ({s['direction']})")

    print(f"\n" + "-" * 40)
    if v['sun_sets_over_water']:
        print(f"YES - Sunset WILL be visible over the {water_type}!")

        # Show detected features (islands, capes)
        warnings = results.get('analysis', {}).get('headland_warnings', [])
        if warnings:
            print(f"\nNearby features:")
            for w in warnings:
                print(f"  - {w}")

        print_confidence(v['confidence'])

        # Only show horizon diagram when sunset is visible
        print(f"\n" + "-" * 40)
        print_horizon(s['azimuth'], b['ocean_view_start'], b['ocean_view_end'], warnings)
    else:
        print(f"NO - Sunset will NOT be over the {water_type}")

        # Explain WHY
        facing_dir = b['facing']
        sun_dir = s['direction']

        if 'east' in facing_dir:
            print(f"\n  This beach faces {facing_dir} - it's a SUNRISE beach.")
            print(f"  The sunset ({sun_dir}) is behind you.")
        elif 'north' in facing_dir or 'south' in facing_dir:
            print(f"\n  This beach faces {facing_dir}.")
            print(f"  The sunset is at {s['azimuth']}° ({sun_dir}), outside your view.")
        else:
            print(f"\n  Sun at {s['azimuth']}° is outside {water_type} view ({b['ocean_view_start']:.0f}°-{b['ocean_view_end']:.0f}°)")

        print_confidence(v['confidence'])


def print_confidence(confidence: str):
    """Print confidence level with explanation"""
    print(f"\nConfidence: {confidence}")
    if confidence == "low":
        print("  (Limited coastline data; verify with local knowledge)")
    elif confidence == "medium":
        print("  (Based on OSM coastline geometry; may vary by position on beach)")


def print_horizon(sun_az: float, view_start: float, view_end: float, features: list = None):
    """Print horizon diagram with features"""
    print("\n  S        SW        W        NW        N")
    print("  180      225      270      315      360")
    print("  |--------|--------|--------|--------|")

    # Build horizon line - iterate by position to avoid gaps
    line = list("  ")
    for pos in range(40):
        # Convert position to azimuth
        az = 180 + (pos / 40) * 180
        if is_in_view(az, view_start, view_end):
            line.append("~")
        else:
            line.append("#")

    # Mark islands only (not capes - they're already reported in text)
    if features:
        import re
        for feat in features:
            if 'island' in feat.lower():
                match = re.search(r'at (\d+)°', feat)
                if match:
                    feat_az = int(match.group(1))
                    if 180 <= feat_az <= 360:
                        pos = 2 + int((feat_az - 180) / 180 * 40)
                        if 0 <= pos < len(line):
                            line[pos] = "^"

    # Mark sun
    if 180 <= sun_az <= 360:
        sun_pos = 2 + int((sun_az - 180) / 180 * 40)
        sun_line = list(" " * len(line))
        if 0 <= sun_pos < len(sun_line):
            sun_line[sun_pos] = "*"
        print("".join(sun_line) + "  <- sun")

    print("".join(line))
    print("\n  ~ = ocean  # = land  ^ = island  * = sunset")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Check sunset visibility from any beach",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Nai Harn Beach"
  %(prog)s "Santa Monica" --date 2025-06-21
  %(prog)s --lat 7.7677 --lon 98.3036
        """
    )

    parser.add_argument('beach', nargs='?', help='Beach name to search')
    parser.add_argument('--date', '-d', help='Date (YYYY-MM-DD), default: tomorrow')
    parser.add_argument('--lat', type=float, help='Latitude')
    parser.add_argument('--lon', type=float, help='Longitude')
    parser.add_argument('--json', '-j', action='store_true', help='JSON output')

    args = parser.parse_args()

    # Need either beach name or coordinates
    if not args.beach and args.lat is None:
        parser.print_help()
        sys.exit(1)

    # Get coordinates
    if args.lat is not None and args.lon is not None:
        lat, lon = args.lat, args.lon
        name = f"Location ({lat:.4f}, {lon:.4f})"
    else:
        try:
            beach = find_beach(args.beach)
            lat, lon = beach['lat'], beach['lon']
            name = args.beach
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    # Parse date
    if args.date:
        try:
            date = datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print(f"Error: Invalid date '{args.date}'. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        # Default to tomorrow (user's local machine date)
        date = datetime.now() + timedelta(days=1)

    # Run analysis
    try:
        results = check_sunset(lat, lon, name, date)
    except NoSunsetError as e:
        print(f"\n{e}")
        if e.is_polar_day:
            print("  The sun doesn't set at this location on this date (midnight sun).")
        else:
            print("  The sun doesn't rise at this location on this date (polar night).")
        sys.exit(0)
    except InlandLocationError as e:
        print(f"\n{e}")
        print("  Try searching for a specific beach name, or use --lat/--lon for a coastal location.")
        sys.exit(1)
    except Exception as e:
        print(f"Error analyzing location: {e}")
        sys.exit(1)

    # Output
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_results(results)


if __name__ == "__main__":
    main()
