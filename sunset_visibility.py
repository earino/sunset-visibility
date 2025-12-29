#!/usr/bin/env python3
"""
Solar Position Calculator

NOAA solar position algorithms for calculating sun azimuth and altitude.
Used by sunset_check.py for sunset visibility calculations.
"""

import math
from datetime import datetime, timedelta
from dataclasses import dataclass


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
    # Handle edge case when sun is at zenith (directly overhead)
    sin_zenith = math.sin(math.radians(zenith))
    if sin_zenith < 0.0001:  # Sun nearly overhead, azimuth undefined
        azimuth = 180.0  # Arbitrary but consistent value
    else:
        # Calculate azimuth argument, clamping to [-1, 1] to avoid acos domain errors
        az_arg = ((math.sin(lat_rad) * math.cos(math.radians(zenith))) - math.sin(declin_rad)) / \
                 (math.cos(lat_rad) * sin_zenith)
        az_arg = max(-1, min(1, az_arg))

        if hour_angle > 0:
            azimuth = (math.degrees(math.acos(az_arg)) + 180) % 360
        else:
            azimuth = (540 - math.degrees(math.acos(az_arg))) % 360

    return SunPosition(azimuth=azimuth, altitude=altitude, time=dt)


class NoSunsetError(Exception):
    """Raised when there is no sunset on the given date (polar day or polar night)"""
    def __init__(self, message: str, is_polar_day: bool):
        super().__init__(message)
        self.is_polar_day = is_polar_day


def find_sunset(date: datetime, lat: float, lon: float, timezone_offset: float = 0.0) -> SunPosition:
    """
    Find the exact sunset time and position for a given date and location.

    Args:
        date: date to calculate sunset for (local date)
        lat: latitude
        lon: longitude
        timezone_offset: hours offset from UTC

    Returns:
        SunPosition at sunset (when altitude crosses 0, accounting for refraction)

    Raises:
        NoSunsetError: if no sunset occurs (polar day or polar night)
    """
    # Start search at local noon, converted to UTC
    local_noon = datetime(date.year, date.month, date.day, 12, 0, 0)
    utc_noon = local_noon - timedelta(hours=timezone_offset)

    # Binary search for sunset (altitude = -0.833 degrees for atmospheric refraction)
    target_altitude = -0.833  # Standard refraction correction

    # First, check for polar day/night by sampling the day
    min_altitude = float('inf')
    max_altitude = float('-inf')

    for hour in range(0, 24, 2):
        check_time = utc_noon - timedelta(hours=12) + timedelta(hours=hour)
        pos = sun_position(check_time, lat, lon)
        min_altitude = min(min_altitude, pos.altitude)
        max_altitude = max(max_altitude, pos.altitude)

    # Polar night: sun never rises above horizon
    if max_altitude < target_altitude:
        raise NoSunsetError(
            f"No sunset on {date.strftime('%Y-%m-%d')}: polar night (sun stays below horizon)",
            is_polar_day=False
        )

    # Polar day: sun never sets below horizon
    if min_altitude > target_altitude:
        raise NoSunsetError(
            f"No sunset on {date.strftime('%Y-%m-%d')}: midnight sun (sun stays above horizon)",
            is_polar_day=True
        )

    # Start with coarse search from noon going forward
    dt = utc_noon
    iterations = 0
    while iterations < 200:  # Safety limit
        pos = sun_position(dt, lat, lon)
        if pos.altitude < target_altitude:
            break
        dt += timedelta(minutes=5)
        iterations += 1

    if iterations >= 200:
        raise NoSunsetError(
            f"Could not find sunset on {date.strftime('%Y-%m-%d')}",
            is_polar_day=True
        )

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
