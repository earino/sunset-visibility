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

from coastline_analyzer import (
    analyze_coastline,
    search_beach_osm,
    geocode_location,
    find_beaches_near,
    get_direction_name,
    BeachOrientation
)
from sunset_visibility import find_sunset, SunPosition


# ============================================================================
# TIMEZONE ESTIMATION
# ============================================================================

def estimate_timezone(lat: float, lon: float) -> float:
    """Estimate timezone offset from longitude (rough approximation)"""
    # 15 degrees per hour, but this is very approximate
    # Good enough for display purposes
    return round(lon / 15)


# ============================================================================
# BEACH LOOKUP
# ============================================================================

def find_beach(query: str) -> dict:
    """
    Find a beach by name using OpenStreetMap Nominatim.
    If no beach found by name, geocodes the query and finds nearest beach.

    Returns dict with: name, lat, lon, display_name
    """
    print(f"Searching for '{query}'...")

    results = search_beach_osm(query)

    if not results:
        # Try appending "beach" if not already there
        if 'beach' not in query.lower():
            results = search_beach_osm(query + " beach")

    if results:
        best = results[0]
        print(f"Found: {best['name'][:60]}...")
        return {
            'name': query,  # Use user's query as name
            'lat': best['lat'],
            'lon': best['lon'],
            'display_name': best['name']
        }

    # Fallback: geocode the query and find nearest beach
    print(f"No beach named '{query}' found, searching for nearest beach...")

    try:
        location = geocode_location(query)
        print(f"Location: {location['display_name'][:60]}...")
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
    print(f"Nearest beach: {best['name']} ({best['distance_m']/1000:.1f}km away)")

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
    """
    # Analyze coastline to get beach orientation
    print(f"\nAnalyzing coastline...")
    orientation = analyze_coastline(lat, lon)

    # Estimate timezone
    tz_offset = estimate_timezone(lat, lon)

    # Calculate sunset position
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

    return {
        'beach': {
            'name': name,
            'lat': lat,
            'lon': lon,
            'facing': orientation.facing_direction,
            'ocean_view_start': orientation.ocean_view_start,
            'ocean_view_end': orientation.ocean_view_end,
        },
        'date': date.strftime('%Y-%m-%d'),
        'sunset': {
            'local_time': local_time.strftime('%H:%M'),
            'timezone': f"UTC{tz_offset:+.0f}",
            'azimuth': round(sunset.azimuth, 1),
            'direction': direction
        },
        'visibility': {
            'sun_sets_over_ocean': sun_over_ocean,
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

    print("\n" + "=" * 60)
    print(f"SUNSET VISIBILITY: {b['name']}")
    print("=" * 60)

    print(f"\nDate: {results['date']}")
    print(f"Location: {b['lat']:.4f}, {b['lon']:.4f}")
    print(f"Beach faces: {b['facing']}")
    print(f"Ocean view: {b['ocean_view_start']:.0f}° to {b['ocean_view_end']:.0f}°")

    print(f"\n" + "-" * 40)
    print(f"Sunset: {s['local_time']} ({s['timezone']})")
    print(f"Sun position: {s['azimuth']}° ({s['direction']})")

    print(f"\n" + "-" * 40)
    if v['sun_sets_over_ocean']:
        print("YES - Sunset WILL be visible over the ocean!")

        # Show detected features (islands, capes)
        warnings = results.get('analysis', {}).get('headland_warnings', [])
        if warnings:
            print(f"\nNearby features:")
            for w in warnings:
                print(f"  - {w}")

        print(f"\nConfidence: {v['confidence']}")

        # Only show horizon diagram when sunset is visible
        print(f"\n" + "-" * 40)
        print_horizon(s['azimuth'], b['ocean_view_start'], b['ocean_view_end'], warnings)
    else:
        print("NO - Sunset will NOT be over the ocean")

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
            print(f"\n  Sun at {s['azimuth']}° is outside ocean view ({b['ocean_view_start']:.0f}°-{b['ocean_view_end']:.0f}°)")

        print(f"\nConfidence: {v['confidence']}")


def print_horizon(sun_az: float, view_start: float, view_end: float, features: list = None):
    """Print horizon diagram with features"""
    print("\n  S        SW        W        NW        N")
    print("  180      225      270      315      360")
    print("  |--------|--------|--------|--------|")

    # Build horizon line
    line = list("  " + "-" * 40)

    # Mark land (outside ocean view)
    for az in range(180, 361, 5):
        pos = 2 + int((az - 180) / 180 * 40)
        if 0 <= pos < len(line):
            if not is_in_view(az, view_start, view_end):
                line[pos] = "#"
            else:
                line[pos] = "~"

    # Mark features (islands, capes) from headland_warnings
    if features:
        for feat in features:
            # Parse bearing from warning string like "Island 'X' at 207° (1.3km)"
            import re
            match = re.search(r'at (\d+)°', feat)
            if match:
                feat_az = int(match.group(1))
                if 180 <= feat_az <= 360:
                    pos = 2 + int((feat_az - 180) / 180 * 40)
                    if 0 <= pos < len(line):
                        if 'island' in feat.lower():
                            line[pos] = "^"  # Island
                        else:
                            line[pos] = "#"  # Cape/headland

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
        date = datetime.now() + timedelta(days=1)

    # Run analysis
    try:
        results = check_sunset(lat, lon, name, date)
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
