#!/usr/bin/env python3
"""
Sunset Visibility Calculator for Nai Harn Beach, Phuket

This script calculates whether the sunset will be visible over the ocean
from a specific beach location, taking into account:
- Exact solar position calculations
- Beach orientation and coastline geometry
- Headland/promontory obstructions
- Horizon analysis

Author: Claude
Date: December 2025
"""

import argparse
import math
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Tuple, List, Optional
import json

# ============================================================================
# ASTRONOMICAL CALCULATIONS
# ============================================================================

@dataclass
class SunPosition:
    """Sun position at a given time"""
    azimuth: float  # degrees from North, clockwise
    altitude: float  # degrees above horizon
    time: datetime

def julian_day(dt: datetime) -> float:
    """Calculate Julian Day from datetime (UTC)"""
    year = dt.year
    month = dt.month
    day = dt.day + dt.hour/24.0 + dt.minute/1440.0 + dt.second/86400.0

    if month <= 2:
        year -= 1
        month += 12

    A = int(year / 100)
    B = 2 - A + int(A / 4)

    JD = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5
    return JD

def sun_position(dt: datetime, lat: float, lon: float) -> SunPosition:
    """
    Calculate sun position using NOAA solar calculator algorithms.
    This is a high-precision implementation based on the NOAA spreadsheet.

    Args:
        dt: datetime in UTC
        lat: latitude in degrees (positive North)
        lon: longitude in degrees (positive East)

    Returns:
        SunPosition with azimuth and altitude
    """
    JD = julian_day(dt)
    JC = (JD - 2451545) / 36525  # Julian Century

    # Geometric Mean Longitude of Sun (degrees)
    L0 = (280.46646 + JC * (36000.76983 + 0.0003032 * JC)) % 360

    # Geometric Mean Anomaly of Sun (degrees)
    M = 357.52911 + JC * (35999.05029 - 0.0001537 * JC)

    # Eccentricity of Earth's Orbit
    e = 0.016708634 - JC * (0.000042037 + 0.0000001267 * JC)

    # Sun's Equation of Center
    M_rad = math.radians(M)
    C = (math.sin(M_rad) * (1.914602 - JC * (0.004817 + 0.000014 * JC)) +
         math.sin(2 * M_rad) * (0.019993 - 0.000101 * JC) +
         math.sin(3 * M_rad) * 0.000289)

    # Sun's True Longitude
    sun_lon = L0 + C

    # Sun's Apparent Longitude
    omega = 125.04 - 1934.136 * JC
    sun_app_lon = sun_lon - 0.00569 - 0.00478 * math.sin(math.radians(omega))

    # Mean Obliquity of the Ecliptic
    obliq_mean = 23 + (26 + (21.448 - JC * (46.8150 + JC * (0.00059 - JC * 0.001813))) / 60) / 60

    # Corrected Obliquity
    obliq_corr = obliq_mean + 0.00256 * math.cos(math.radians(omega))

    # Sun's Declination
    sun_declin = math.degrees(math.asin(math.sin(math.radians(obliq_corr)) *
                                         math.sin(math.radians(sun_app_lon))))

    # Equation of Time (minutes)
    var_y = math.tan(math.radians(obliq_corr / 2)) ** 2
    eq_time = 4 * math.degrees(
        var_y * math.sin(2 * math.radians(L0)) -
        2 * e * math.sin(M_rad) +
        4 * e * var_y * math.sin(M_rad) * math.cos(2 * math.radians(L0)) -
        0.5 * var_y ** 2 * math.sin(4 * math.radians(L0)) -
        1.25 * e ** 2 * math.sin(2 * M_rad)
    )

    # True Solar Time
    time_offset = eq_time + 4 * lon  # in minutes
    true_solar_time = (dt.hour * 60 + dt.minute + dt.second/60 + time_offset) % 1440

    # Hour Angle
    if true_solar_time / 4 < 0:
        hour_angle = true_solar_time / 4 + 180
    else:
        hour_angle = true_solar_time / 4 - 180

    # Solar Zenith and Altitude
    lat_rad = math.radians(lat)
    declin_rad = math.radians(sun_declin)
    hour_angle_rad = math.radians(hour_angle)

    cos_zenith = (math.sin(lat_rad) * math.sin(declin_rad) +
                  math.cos(lat_rad) * math.cos(declin_rad) * math.cos(hour_angle_rad))
    cos_zenith = max(-1, min(1, cos_zenith))  # clamp to [-1, 1]

    zenith = math.degrees(math.acos(cos_zenith))
    altitude = 90 - zenith

    # Solar Azimuth
    if hour_angle > 0:
        azimuth = (math.degrees(math.acos(
            ((math.sin(lat_rad) * math.cos(math.radians(zenith))) - math.sin(declin_rad)) /
            (math.cos(lat_rad) * math.sin(math.radians(zenith)))
        )) + 180) % 360
    else:
        azimuth = (540 - math.degrees(math.acos(
            ((math.sin(lat_rad) * math.cos(math.radians(zenith))) - math.sin(declin_rad)) /
            (math.cos(lat_rad) * math.sin(math.radians(zenith)))
        ))) % 360

    return SunPosition(azimuth=azimuth, altitude=altitude, time=dt)

def find_sunset(date: datetime, lat: float, lon: float, timezone_offset: float = 7.0) -> SunPosition:
    """
    Find the exact sunset time and position for a given date and location.

    Args:
        date: date to calculate sunset for (local date)
        lat: latitude
        lon: longitude
        timezone_offset: hours offset from UTC (Phuket is UTC+7)

    Returns:
        SunPosition at sunset (when altitude crosses 0, accounting for refraction)
    """
    # Start search at local noon, converted to UTC
    local_noon = datetime(date.year, date.month, date.day, 12, 0, 0)
    utc_noon = local_noon - timedelta(hours=timezone_offset)

    # Binary search for sunset (altitude = -0.833 degrees for atmospheric refraction)
    target_altitude = -0.833  # Standard refraction correction

    # Start with coarse search
    dt = utc_noon
    while True:
        pos = sun_position(dt, lat, lon)
        if pos.altitude < target_altitude:
            break
        dt += timedelta(minutes=5)
        if dt > utc_noon + timedelta(hours=12):
            raise ValueError("Could not find sunset")

    # Binary search for precise time
    low = dt - timedelta(minutes=5)
    high = dt

    for _ in range(20):  # ~1 second precision
        mid = low + (high - low) / 2
        pos = sun_position(mid, lat, lon)
        if pos.altitude > target_altitude:
            low = mid
        else:
            high = mid

    final_time = low + (high - low) / 2
    return sun_position(final_time, lat, lon)


# ============================================================================
# GEOGRAPHIC DATA FOR NAI HARN BEACH
# ============================================================================

@dataclass
class BeachGeometry:
    """Geographic information about a beach"""
    name: str
    latitude: float
    longitude: float
    # Azimuth range where ocean is visible (degrees from North)
    ocean_view_start: float  # leftmost ocean view
    ocean_view_end: float    # rightmost ocean view
    # Known obstructions: list of (azimuth_start, azimuth_end, description)
    obstructions: List[Tuple[float, float, str]]
    # Scenic features: islands or silhouettes that enhance (not block) sunset
    # List of (azimuth_center, azimuth_width, name, description)
    scenic_features: List[Tuple[float, float, str, str]]
    # Elevation of viewer (meters above sea level)
    viewer_elevation: float
    description: str

def get_nai_harn_beach_geometry() -> BeachGeometry:
    """
    Returns detailed geometry for Nai Harn Beach, Phuket.

    Nai Harn Beach is located at the southern tip of Phuket island.
    The beach faces roughly west-southwest, nestled in a bay between
    two prominent headlands:

    - Promthep Cape (to the south/southeast) - the famous viewpoint
    - A smaller headland to the north

    The beach coordinates and orientation are based on satellite imagery
    and topographic analysis.
    """
    return BeachGeometry(
        name="Nai Harn Beach, Phuket, Thailand",
        latitude=7.7677,
        longitude=98.3036,
        # The beach faces roughly west-southwest
        # Ocean view spans approximately from 225° (SW) to 305° (NW)
        # The bay opening is roughly 80 degrees wide
        ocean_view_start=230.0,  # Southern limit (Promthep Cape blocks beyond this)
        ocean_view_end=295.0,    # Northern limit (northern headland blocks beyond this)
        obstructions=[
            # Promthep Cape - the large headland to the south
            # Blocks views from roughly 180° to 230°
            (180.0, 230.0, "Promthep Cape (southern headland)"),
            # Northern headland of the bay
            # Blocks views from roughly 295° to 360°
            (295.0, 360.0, "Northern headland"),
        ],
        scenic_features=[
            # Koh Man - small rocky island offshore to the southwest
            # Located at approximately 247° from center of beach
            # Island spans roughly 246°-248° depending on viewing position on beach
            # Creates beautiful silhouette during winter sunsets
            (247.0, 2.5, "Koh Man Island",
             "Small rocky island that creates a dramatic silhouette when sun sets behind it"),
        ],
        viewer_elevation=2.0,  # Standing on the beach
        description="""
Nai Harn Beach is a crescent-shaped bay on the southwestern coast of Phuket.
The beach is approximately 1km long and faces west-southwest. It is bounded by:

- SOUTH: Promthep Cape, a dramatic rocky headland that extends into the sea.
  This is one of Phuket's most famous sunset viewpoints, but from the beach
  itself, it blocks southern views.

- NORTH: A smaller vegetated headland that forms the northern boundary of
  the bay.

- WEST: Open Andaman Sea with unobstructed horizon.

The bay opens to the west-southwest, with the main ocean view spanning
roughly from 230° to 295° azimuth (measured from North, clockwise).

During winter months (December-January), the sun sets at azimuths around
245-250°, which is well within the ocean view window, making sunset
over the ocean visible from this beach.
"""
    )


# ============================================================================
# OBSTRUCTION ANALYSIS
# ============================================================================

@dataclass
class HorizonPoint:
    """A point on the horizon with elevation angle"""
    azimuth: float
    elevation: float  # degrees above mathematical horizon
    obstruction: Optional[str]

def analyze_horizon(beach: BeachGeometry, sun_azimuth: float) -> Tuple[bool, str]:
    """
    Analyze whether the sun at a given azimuth is obstructed.

    Returns:
        Tuple of (is_visible, explanation)
    """
    # Check if azimuth is within ocean view
    if beach.ocean_view_start <= sun_azimuth <= beach.ocean_view_end:
        # Check for specific obstructions
        for obs_start, obs_end, description in beach.obstructions:
            if obs_start <= sun_azimuth <= obs_end:
                return False, f"Blocked by {description}"
        return True, "Clear ocean horizon"
    else:
        if sun_azimuth < beach.ocean_view_start:
            return False, f"Sun sets too far south (blocked by land/headland)"
        else:
            return False, f"Sun sets too far north (blocked by land/headland)"


# ============================================================================
# MAIN ANALYSIS
# ============================================================================

def analyze_sunset_visibility(date: datetime, beach: BeachGeometry, verbose: bool = True) -> dict:
    """
    Perform complete sunset visibility analysis.

    Args:
        date: date to analyze
        beach: beach geometry
        verbose: print detailed output

    Returns:
        Dictionary with analysis results
    """
    # Calculate sunset position
    sunset = find_sunset(date, beach.latitude, beach.longitude)

    # Convert UTC time to local time (UTC+7 for Phuket)
    local_sunset_time = sunset.time + timedelta(hours=7)

    # Analyze visibility
    is_visible, visibility_reason = analyze_horizon(beach, sunset.azimuth)

    # Calculate how far into the ocean view window the sunset is
    view_center = (beach.ocean_view_start + beach.ocean_view_end) / 2
    view_width = beach.ocean_view_end - beach.ocean_view_start
    offset_from_center = sunset.azimuth - view_center

    # Direction description
    if sunset.azimuth < 247.5:
        direction = "south-southwest"
    elif sunset.azimuth < 270:
        direction = "west-southwest"
    elif sunset.azimuth < 292.5:
        direction = "west-northwest"
    else:
        direction = "northwest"

    results = {
        "date": date.strftime("%Y-%m-%d"),
        "location": beach.name,
        "coordinates": {
            "latitude": beach.latitude,
            "longitude": beach.longitude
        },
        "sunset": {
            "local_time": local_sunset_time.strftime("%H:%M:%S"),
            "utc_time": sunset.time.strftime("%H:%M:%S UTC"),
            "azimuth": round(sunset.azimuth, 2),
            "direction": direction
        },
        "visibility": {
            "sun_sets_over_ocean": is_visible,
            "reason": visibility_reason,
            "ocean_view_range": {
                "start": beach.ocean_view_start,
                "end": beach.ocean_view_end,
                "width_degrees": view_width
            },
            "sunset_position_in_view": {
                "degrees_from_center": round(offset_from_center, 2),
                "position_description": "within view" if is_visible else "outside view"
            }
        },
        "notes": []
    }

    # Add contextual notes
    if is_visible:
        results["notes"].append(
            f"The sun will set at {sunset.azimuth:.1f}° azimuth, which is {direction}."
        )
        results["notes"].append(
            f"This is within the beach's ocean view window ({beach.ocean_view_start}° to {beach.ocean_view_end}°)."
        )
        margin_south = sunset.azimuth - beach.ocean_view_start
        margin_north = beach.ocean_view_end - sunset.azimuth
        results["notes"].append(
            f"Margin from Promthep Cape obstruction: {margin_south:.1f}° (comfortable clearance)"
        )
        # Check for scenic features (islands that create beautiful silhouettes)
        for az_center, az_width, name, desc in beach.scenic_features:
            az_start = az_center - az_width
            az_end = az_center + az_width
            if az_start <= sunset.azimuth <= az_end:
                distance_from_center = abs(sunset.azimuth - az_center)
                if distance_from_center < 0.5:
                    results["notes"].append(
                        f"SPECIAL: Sun will set DIRECTLY BEHIND {name}! "
                        f"({desc})"
                    )
                    results["visibility"]["scenic_feature"] = {
                        "name": name,
                        "alignment": "direct",
                        "description": desc
                    }
                elif distance_from_center < 1.5:
                    results["notes"].append(
                        f"BEAUTIFUL: Sun will set very close to {name}, creating a dramatic silhouette. "
                        f"({desc})"
                    )
                    results["visibility"]["scenic_feature"] = {
                        "name": name,
                        "alignment": "adjacent",
                        "description": desc
                    }
                else:
                    results["notes"].append(
                        f"Sun will set near {name} - visible in the sunset scene."
                    )
                    results["visibility"]["scenic_feature"] = {
                        "name": name,
                        "alignment": "nearby",
                        "description": desc
                    }
    else:
        results["notes"].append(
            f"The sun sets at {sunset.azimuth:.1f}°, outside the ocean view range."
        )

    if verbose:
        print_analysis(results, beach)

    return results

def print_analysis(results: dict, beach: BeachGeometry):
    """Print formatted analysis results"""
    print("=" * 70)
    print(f"SUNSET VISIBILITY ANALYSIS")
    print(f"Location: {results['location']}")
    print(f"Date: {results['date']}")
    print("=" * 70)
    print()

    print("COORDINATES:")
    print(f"  Latitude:  {results['coordinates']['latitude']:.4f}°N")
    print(f"  Longitude: {results['coordinates']['longitude']:.4f}°E")
    print()

    print("SUNSET TIMING:")
    print(f"  Local Time (UTC+7): {results['sunset']['local_time']}")
    print(f"  UTC Time:           {results['sunset']['utc_time']}")
    print()

    print("SUNSET POSITION:")
    print(f"  Azimuth:   {results['sunset']['azimuth']}° (measured clockwise from North)")
    print(f"  Direction: {results['sunset']['direction']}")
    print()

    print("BEACH ORIENTATION:")
    print(f"  Ocean view spans: {beach.ocean_view_start}° to {beach.ocean_view_end}°")
    print(f"  View width: {beach.ocean_view_end - beach.ocean_view_start}° of horizon")
    print()

    print("OBSTRUCTIONS:")
    for obs_start, obs_end, desc in beach.obstructions:
        print(f"  {obs_start}° - {obs_end}°: {desc}")
    print()

    print("=" * 70)
    print("RESULT:")
    print("=" * 70)
    if results['visibility']['sun_sets_over_ocean']:
        print(f"  ✓ YES - The sunset WILL be visible over the ocean")
        print(f"  {results['visibility']['reason']}")
    else:
        print(f"  ✗ NO - The sunset will NOT be visible over the ocean")
        print(f"  Reason: {results['visibility']['reason']}")
    print()

    print("ANALYSIS NOTES:")
    for note in results['notes']:
        print(f"  • {note}")
    print()

    # Visual representation
    print("HORIZON VIEW (from beach, facing ocean):")
    print()
    print_horizon_diagram(results['sunset']['azimuth'], beach)

def print_horizon_diagram(sun_azimuth: float, beach: BeachGeometry):
    """Print ASCII diagram of the horizon view"""
    # Show azimuths from 180 to 360 (south to north, through west)
    print("         South                    West                    North")
    print("           ↓                        ↓                        ↓")
    print("     180°      210°      240°      270°      300°      330°      360°")
    print("      |---------|---------|---------|---------|---------|---------|")

    # Create the horizon line
    horizon = list("      |" + "-" * 63 + "|")

    # Mark obstructions
    for obs_start, obs_end, _ in beach.obstructions:
        for az in range(int(obs_start), int(obs_end) + 1):
            if 180 <= az <= 360:
                pos = 6 + int((az - 180) / 180 * 63)
                if 0 <= pos < len(horizon):
                    horizon[pos] = "█"

    # Mark scenic features (islands)
    for az_center, az_width, name, _ in beach.scenic_features:
        az_start = int(az_center - az_width)
        az_end = int(az_center + az_width)
        for az in range(az_start, az_end + 1):
            if 180 <= az <= 360:
                pos = 6 + int((az - 180) / 180 * 63)
                if 0 <= pos < len(horizon):
                    horizon[pos] = "▲"

    # Mark ocean view
    ocean_line = list(" " * len(horizon))
    for az in range(int(beach.ocean_view_start), int(beach.ocean_view_end) + 1):
        pos = 6 + int((az - 180) / 180 * 63)
        if 0 <= pos < len(ocean_line):
            ocean_line[pos] = "~"

    # Mark sun position
    sun_pos = 6 + int((sun_azimuth - 180) / 180 * 63)
    sun_line = list(" " * len(horizon))
    if 0 <= sun_pos < len(sun_line):
        sun_line[sun_pos] = "☀"

    print("".join(sun_line) + f"  ← Sun ({sun_azimuth:.1f}°)")
    print("".join(horizon))
    print("".join(ocean_line) + "  ← Ocean view")
    print()
    print("Legend: █ = Land/obstruction, ▲ = Island, ~ = Ocean view, ☀ = Sunset position")


def main():
    parser = argparse.ArgumentParser(
        description="Calculate sunset visibility from Nai Harn Beach, Phuket",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      # Check tomorrow's sunset
  %(prog)s --date 2025-12-29    # Check specific date
  %(prog)s --json               # Output as JSON
  %(prog)s --info               # Show beach information
        """
    )
    parser.add_argument(
        "--date", "-d",
        type=str,
        help="Date to analyze (YYYY-MM-DD format). Default: tomorrow"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--info", "-i",
        action="store_true",
        help="Show detailed beach information"
    )

    args = parser.parse_args()

    # Get beach geometry
    beach = get_nai_harn_beach_geometry()

    if args.info:
        print("=" * 70)
        print("BEACH INFORMATION")
        print("=" * 70)
        print(beach.description)
        print()
        print(f"Coordinates: {beach.latitude}°N, {beach.longitude}°E")
        print(f"Ocean view: {beach.ocean_view_start}° to {beach.ocean_view_end}°")
        print()
        print("Obstructions:")
        for obs_start, obs_end, desc in beach.obstructions:
            print(f"  {obs_start}° - {obs_end}°: {desc}")
        return

    # Parse date
    if args.date:
        try:
            date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD.")
            return
    else:
        # Default to tomorrow
        date = datetime.now() + timedelta(days=1)

    # Run analysis
    results = analyze_sunset_visibility(date, beach, verbose=not args.json)

    if args.json:
        print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
