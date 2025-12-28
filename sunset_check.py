#!/usr/bin/env python3
"""
Universal Sunset Visibility Calculator

Check if sunset will be visible over the ocean from ANY beach on Earth.

Usage:
  sunset_check.py "Nai Harn Beach, Phuket"
  sunset_check.py "Waikiki Beach" --date 2025-06-21
  sunset_check.py --lat 7.7677 --lon 98.3036 --date 2025-12-29
  sunset_check.py --list  # List all curated beaches
  sunset_check.py --search "bali"  # Search beaches

Data sources:
  - Curated database of 50+ popular beaches with verified orientation
  - OpenStreetMap for any beach not in database (algorithmic analysis)
  - NOAA solar algorithms for precise sun position
"""

import argparse
import sys
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple

# Import our modules
from beaches_database import (
    BEACHES_DATABASE, BeachData, search_beaches, get_beach,
    list_all_beaches, list_beaches_by_country, get_direction_name
)
from coastline_analyzer import analyze_coastline, search_beach_osm, BeachOrientation
from sunset_visibility import (
    sun_position, find_sunset, SunPosition, BeachGeometry,
    analyze_horizon, print_horizon_diagram
)


# ============================================================================
# TIMEZONE DATABASE (simplified)
# ============================================================================

# Approximate timezone offsets by region/country
TIMEZONE_OFFSETS = {
    # Asia
    'thailand': 7, 'vietnam': 7, 'indonesia': 8, 'bali': 8,
    'malaysia': 8, 'singapore': 8, 'philippines': 8,
    'japan': 9, 'korea': 9, 'china': 8, 'india': 5.5,
    'maldives': 5, 'sri lanka': 5.5, 'uae': 4, 'dubai': 4,

    # Pacific
    'hawaii': -10, 'fiji': 12, 'tahiti': -10, 'guam': 10,
    'australia': 10, 'sydney': 11, 'perth': 8, 'queensland': 10,
    'new zealand': 13,

    # Americas
    'california': -8, 'los angeles': -8, 'san diego': -8,
    'florida': -5, 'miami': -5, 'new york': -5,
    'mexico': -6, 'cancun': -5, 'cabo': -7,
    'caribbean': -4, 'aruba': -4, 'jamaica': -5,
    'brazil': -3, 'rio': -3,
    'chile': -3, 'peru': -5, 'costa rica': -6,

    # Europe
    'portugal': 0, 'spain': 1, 'france': 1, 'italy': 1,
    'greece': 2, 'croatia': 1, 'uk': 0, 'ireland': 0,

    # Africa
    'south africa': 2, 'cape town': 2, 'morocco': 1,
    'mauritius': 4, 'seychelles': 4, 'kenya': 3, 'tanzania': 3,

    # Indian Ocean
    'maldives': 5, 'reunion': 4,
}

def estimate_timezone(lat: float, lon: float, location_hint: str = "") -> float:
    """Estimate timezone offset from coordinates and location hint"""
    # Check location hint first
    hint_lower = location_hint.lower()
    for key, offset in TIMEZONE_OFFSETS.items():
        if key in hint_lower:
            return offset

    # Rough estimate from longitude (15° per hour)
    return round(lon / 15)


# ============================================================================
# BEACH RESOLUTION
# ============================================================================

def resolve_beach(beach_name: str = None, lat: float = None, lon: float = None,
                  country: str = None) -> Tuple[BeachData, bool]:
    """
    Resolve a beach from name or coordinates.

    Returns:
        Tuple of (BeachData, is_from_database)
    """
    # If coordinates provided, use them directly
    if lat is not None and lon is not None:
        print(f"Using provided coordinates: {lat}, {lon}")
        return create_beach_from_coords(lat, lon, beach_name or "Custom Location"), False

    if not beach_name:
        raise ValueError("Must provide either beach name or coordinates")

    # Try curated database first
    normalized = beach_name.lower().replace(" ", "_").replace("-", "_").replace(",", "")

    # Direct match
    if normalized in BEACHES_DATABASE:
        beach = BEACHES_DATABASE[normalized]
        print(f"Found in curated database: {beach.name}")
        return beach, True

    # Search curated database
    matches = search_beaches(beach_name)
    if matches:
        beach = matches[0]
        if len(matches) > 1:
            print(f"Multiple matches found, using: {beach.name}")
            print("Other matches:", ", ".join(b.name for b in matches[1:4]))
        else:
            print(f"Found in curated database: {beach.name}")
        return beach, True

    # Try OSM search
    print(f"'{beach_name}' not in curated database, searching OpenStreetMap...")
    osm_results = search_beach_osm(beach_name, country)

    if osm_results:
        best = osm_results[0]
        print(f"Found on OSM: {best['name']}")
        return create_beach_from_coords(
            best['lat'], best['lon'],
            beach_name,
            location_hint=best['name']
        ), False

    # Try with "beach" appended if not already there
    if 'beach' not in beach_name.lower():
        osm_results = search_beach_osm(beach_name + " beach", country)
        if osm_results:
            best = osm_results[0]
            print(f"Found on OSM: {best['name']}")
            return create_beach_from_coords(
                best['lat'], best['lon'],
                beach_name,
                location_hint=best['name']
            ), False

    raise ValueError(f"Could not find beach '{beach_name}'. Try providing coordinates with --lat and --lon")


def create_beach_from_coords(lat: float, lon: float, name: str,
                             location_hint: str = "") -> BeachData:
    """
    Create BeachData from coordinates using coastline analysis.
    """
    print(f"\nAnalyzing coastline at {lat:.4f}, {lon:.4f}...")

    try:
        orientation = analyze_coastline(lat, lon)

        # Convert orientation to BeachData
        return BeachData(
            name=name,
            country="Unknown",
            region=location_hint or "Unknown",
            latitude=lat,
            longitude=lon,
            timezone_offset=estimate_timezone(lat, lon, location_hint),
            ocean_view_start=orientation.ocean_view_start,
            ocean_view_end=orientation.ocean_view_end,
            obstructions=[],  # Would need elevation data for this
            scenic_features=[],
            facing_direction=orientation.facing_direction,
            notes=f"Algorithmically analyzed. Confidence: {orientation.confidence}. " +
                  (f"Warnings: {'; '.join(orientation.headland_warnings)}" if orientation.headland_warnings else "")
        )

    except Exception as e:
        print(f"Warning: Coastline analysis failed ({e})")
        print("Using default west-facing orientation estimate")

        # Default to west-facing if we can't analyze
        return BeachData(
            name=name,
            country="Unknown",
            region=location_hint or "Unknown",
            latitude=lat,
            longitude=lon,
            timezone_offset=estimate_timezone(lat, lon, location_hint),
            ocean_view_start=225,
            ocean_view_end=315,
            obstructions=[],
            scenic_features=[],
            facing_direction="west (estimated)",
            notes="Could not analyze coastline. Using default west-facing estimate."
        )


# ============================================================================
# MAIN ANALYSIS
# ============================================================================

def check_sunset(beach: BeachData, date: datetime, verbose: bool = True) -> dict:
    """
    Check if sunset will be visible from a beach on a given date.
    """
    # Calculate sunset
    sunset = find_sunset(date, beach.latitude, beach.longitude, beach.timezone_offset)
    local_time = sunset.time + timedelta(hours=beach.timezone_offset)

    # Check visibility
    if beach.ocean_view_start <= beach.ocean_view_end:
        sun_over_ocean = beach.ocean_view_start <= sunset.azimuth <= beach.ocean_view_end
    else:
        # Handle wraparound (e.g., view from 315° to 45°)
        sun_over_ocean = sunset.azimuth >= beach.ocean_view_start or sunset.azimuth <= beach.ocean_view_end

    # Check obstructions
    obstruction = None
    for obs_start, obs_end, desc in beach.obstructions:
        if obs_start <= sunset.azimuth <= obs_end:
            obstruction = desc
            sun_over_ocean = False
            break

    # Check scenic features
    scenic = None
    for az_center, az_width, name, desc in beach.scenic_features:
        if abs(sunset.azimuth - az_center) <= az_width:
            scenic = {'name': name, 'description': desc,
                      'alignment': 'direct' if abs(sunset.azimuth - az_center) < 1 else 'near'}

    direction = get_direction_name(sunset.azimuth)

    results = {
        'beach': {
            'name': beach.name,
            'country': beach.country,
            'region': beach.region,
            'coordinates': {'lat': beach.latitude, 'lon': beach.longitude},
            'facing': beach.facing_direction,
            'ocean_view': {'start': beach.ocean_view_start, 'end': beach.ocean_view_end}
        },
        'date': date.strftime('%Y-%m-%d'),
        'sunset': {
            'local_time': local_time.strftime('%H:%M'),
            'timezone': f"UTC{beach.timezone_offset:+.1f}".replace('.0', ''),
            'azimuth': round(sunset.azimuth, 1),
            'direction': direction
        },
        'visibility': {
            'sun_sets_over_ocean': sun_over_ocean,
            'obstruction': obstruction,
            'scenic_feature': scenic
        },
        'notes': beach.notes
    }

    if verbose:
        print_results(results, beach)

    return results


def print_results(results: dict, beach: BeachData):
    """Print formatted results"""
    print("\n" + "=" * 70)
    print(f"SUNSET VISIBILITY: {results['beach']['name']}")
    print("=" * 70)

    print(f"\nDate: {results['date']}")
    print(f"Location: {beach.latitude:.4f}°N, {beach.longitude:.4f}°E")
    if beach.region != "Unknown":
        print(f"Region: {beach.region}, {beach.country}")

    print(f"\nBeach faces: {beach.facing_direction}")
    print(f"Ocean view: {beach.ocean_view_start:.0f}° to {beach.ocean_view_end:.0f}°")

    print(f"\n{'─' * 50}")
    print(f"Sunset time: {results['sunset']['local_time']} ({results['sunset']['timezone']})")
    print(f"Sun position: {results['sunset']['azimuth']}° ({results['sunset']['direction']})")

    print(f"\n{'─' * 50}")
    if results['visibility']['sun_sets_over_ocean']:
        print("✓ YES - Sunset WILL be visible over the ocean!")

        if results['visibility']['scenic_feature']:
            sf = results['visibility']['scenic_feature']
            if sf['alignment'] == 'direct':
                print(f"\n  BONUS: Sun sets DIRECTLY behind {sf['name']}!")
            else:
                print(f"\n  Nice: {sf['name']} will be visible in the sunset scene")
    else:
        print("✗ NO - Sunset will NOT be over the ocean")
        if results['visibility']['obstruction']:
            print(f"  Blocked by: {results['visibility']['obstruction']}")
        else:
            print(f"  Sun sets at {results['sunset']['azimuth']}° which is outside ocean view range")

    if beach.notes:
        print(f"\nNote: {beach.notes}")

    # Simple horizon diagram
    print(f"\n{'─' * 50}")
    print("HORIZON VIEW:")
    print_simple_horizon(results['sunset']['azimuth'], beach)


def print_simple_horizon(sun_azimuth: float, beach: BeachData):
    """Print a simple horizon diagram"""
    print("\n  S           SW          W           NW          N")
    print("  180°        225°        270°        315°        360°")
    print("  |-----------|-----------|-----------|-----------|")

    # Create horizon string
    horizon = list("  " + "-" * 48)

    # Mark ocean view
    for az in range(180, 361):
        pos = 2 + int((az - 180) / 180 * 48)
        if 0 <= pos < len(horizon):
            in_view = False
            if beach.ocean_view_start <= beach.ocean_view_end:
                in_view = beach.ocean_view_start <= az <= beach.ocean_view_end
            else:
                in_view = az >= beach.ocean_view_start or az <= beach.ocean_view_end

            if in_view:
                horizon[pos] = "~"

    # Mark obstructions
    for obs_start, obs_end, _ in beach.obstructions:
        for az in range(int(obs_start), int(obs_end) + 1):
            if 180 <= az <= 360:
                pos = 2 + int((az - 180) / 180 * 48)
                if 0 <= pos < len(horizon):
                    horizon[pos] = "█"

    # Mark sun
    if 180 <= sun_azimuth <= 360:
        sun_pos = 2 + int((sun_azimuth - 180) / 180 * 48)
        sun_line = list(" " * len(horizon))
        if 0 <= sun_pos < len(sun_line):
            sun_line[sun_pos] = "☀"
        print("".join(sun_line))

    print("".join(horizon))
    print("\n  █ = land  ~ = ocean view  ☀ = sunset position")


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Check sunset visibility from any beach on Earth",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Nai Harn Beach"                    # Check tomorrow
  %(prog)s "Waikiki Beach" --date 2025-06-21   # Check specific date
  %(prog)s "Bondi Beach" --date 2025-01-15     # Sydney beach
  %(prog)s --lat 34.01 --lon -118.50           # Santa Monica coords
  %(prog)s --list                               # List all beaches
  %(prog)s --search bali                        # Search beaches
  %(prog)s --search thailand --sunset           # Thailand sunset beaches
        """
    )

    parser.add_argument('beach', nargs='?', help='Beach name to look up')
    parser.add_argument('--date', '-d', help='Date (YYYY-MM-DD), default: tomorrow')
    parser.add_argument('--lat', type=float, help='Latitude (if not using beach name)')
    parser.add_argument('--lon', type=float, help='Longitude (if not using beach name)')
    parser.add_argument('--country', '-c', help='Country hint for search')

    parser.add_argument('--list', '-l', action='store_true', help='List all curated beaches')
    parser.add_argument('--search', '-s', help='Search beaches by name/country')
    parser.add_argument('--sunset', action='store_true', help='Only show beaches good for sunset')

    parser.add_argument('--json', '-j', action='store_true', help='Output as JSON')
    parser.add_argument('--quiet', '-q', action='store_true', help='Minimal output')

    args = parser.parse_args()

    # Handle list mode
    if args.list:
        print(f"\nCurated Beach Database ({len(BEACHES_DATABASE)} beaches)")
        print("=" * 60)

        # Group by country
        by_country = {}
        for beach in BEACHES_DATABASE.values():
            if beach.country not in by_country:
                by_country[beach.country] = []
            by_country[beach.country].append(beach)

        for country in sorted(by_country.keys()):
            print(f"\n{country}:")
            for beach in by_country[country]:
                sunset_ok = "☀" if 225 <= (beach.ocean_view_start + beach.ocean_view_end)/2 <= 315 else "  "
                print(f"  {sunset_ok} {beach.name} ({beach.region}) - faces {beach.facing_direction}")

        print("\n☀ = good for sunset over ocean")
        return

    # Handle search mode
    if args.search:
        query = args.search.lower()
        matches = search_beaches(query)

        if args.sunset:
            # Filter for sunset beaches
            matches = [b for b in matches if 220 <= b.ocean_view_start or b.ocean_view_end >= 280]

        if matches:
            print(f"\nFound {len(matches)} matches for '{args.search}':")
            for beach in matches:
                sunset_ok = "☀" if 225 <= (beach.ocean_view_start + beach.ocean_view_end)/2 <= 315 else "  "
                print(f"  {sunset_ok} {beach.name}, {beach.country} - faces {beach.facing_direction}")
        else:
            print(f"No matches for '{args.search}'")
        return

    # Need beach name or coordinates
    if not args.beach and args.lat is None:
        parser.print_help()
        return

    # Resolve beach
    try:
        beach, from_db = resolve_beach(
            beach_name=args.beach,
            lat=args.lat,
            lon=args.lon,
            country=args.country
        )
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Parse date
    if args.date:
        try:
            date = datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print(f"Error: Invalid date '{args.date}'. Use YYYY-MM-DD format.")
            sys.exit(1)
    else:
        date = datetime.now() + timedelta(days=1)

    # Run analysis
    results = check_sunset(beach, date, verbose=not args.json and not args.quiet)

    if args.json:
        print(json.dumps(results, indent=2))
    elif args.quiet:
        if results['visibility']['sun_sets_over_ocean']:
            print(f"YES - {results['sunset']['local_time']} at {results['sunset']['azimuth']}°")
        else:
            print(f"NO - sun at {results['sunset']['azimuth']}°, ocean view {beach.ocean_view_start}°-{beach.ocean_view_end}°")


if __name__ == "__main__":
    main()
