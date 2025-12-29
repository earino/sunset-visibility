# Sunset Visibility Calculator

**Will the sunset be over the ocean?** Check any beach on Earth.

```
$ ./sunset_check.py "Nai Harn Beach" --date 2025-12-29

Searching for 'Nai Harn Beach'...
Found: หาดในหาน, ในหาน, ราไวย์, ตำบลราไวย์, อำเภอเมืองภูเก็ต, จังหว...

Analyzing coastline...
Fetching coastline data for 7.7757, 98.3058...
Found 29 coastline segments with 790 points
Checking for nearby headlands, capes, islands...

============================================================
SUNSET VISIBILITY: Nai Harn Beach
============================================================

Date: 2025-12-29
Location: 7.7757, 98.3058
Beach faces: west-southwest
Ocean view: 205° to 285°

----------------------------------------
Sunset: 18:19 (UTC+7)
Sun position: 246.7° (west-southwest)

----------------------------------------
YES - Sunset WILL be visible over the ocean!

Nearby features:
  - Island 'เกาะมัน' at 207° (1.3km) - potential scenic feature

Confidence: medium

----------------------------------------

  S        SW        W        NW        N
  180      225      270      315      360
  |--------|--------|--------|--------|
                *                           <- sun
  #####~^~~-~~~~~~~~~-~~~######-#########-

  ~ = ocean  # = land  ^ = island  * = sunset
```

## How It Works

All data comes from OpenStreetMap - no curated database needed:

```
"Nai Harn Beach"
       │
       ▼
┌─────────────────┐
│ Nominatim API   │  Geocode beach name → coordinates
└────────┬────────┘
         ▼
┌─────────────────┐
│ Overpass API    │  Fetch coastline + nearby islands/capes
└────────┬────────┘
         ▼
┌─────────────────┐
│ Analyze         │  Beach orientation (water on right of coast)
└────────┬────────┘
         ▼
┌─────────────────┐
│ NOAA Algorithm  │  Precise sunset azimuth for date
└────────┬────────┘
         ▼
    YES / NO
```

### Key Insight

OSM coastlines are drawn with **water on the right side**. So the perpendicular-right vector points toward the ocean, giving us the beach's facing direction.

## Usage

```bash
# By beach name
./sunset_check.py "Santa Monica Beach"
./sunset_check.py "Copacabana Beach, Rio"

# Specific date
./sunset_check.py "Waikiki Beach" --date 2025-06-21

# By coordinates
./sunset_check.py --lat 7.7677 --lon 98.3036

# JSON output
./sunset_check.py "Kuta Beach, Bali" --json
```

## Non-Sunset Beaches

For beaches that face away from sunset, the tool explains why:

```
$ ./sunset_check.py "Bondi Beach" --date 2025-12-29

Searching for 'Bondi Beach'...
Found: Bondi Beach, Eastern Suburbs, Sydney, Waverley Council, New ...

Analyzing coastline...
Fetching coastline data for -33.8907, 151.2724...
Found 10 coastline segments with 565 points
Checking for nearby headlands, capes, islands...

============================================================
SUNSET VISIBILITY: Bondi Beach
============================================================

Date: 2025-12-29
Location: -33.8907, 151.2724
Beach faces: southeast
Ocean view: 84° to 184°

----------------------------------------
Sunset: 19:08 (UTC+10)
Sun position: 241.0° (west-southwest)

----------------------------------------
NO - Sunset will NOT be over the ocean

  This beach faces southeast - it's a SUNRISE beach.
  The sunset (west-southwest) is behind you.

Confidence: medium
```

## Files

| File | Purpose |
|------|---------|
| `sunset_check.py` | Main CLI |
| `coastline_analyzer.py` | OSM coastline analysis |
| `sunset_visibility.py` | NOAA solar calculations |

## Requirements

- Python 3.7+
- No external dependencies (standard library only)
- Internet connection (for OSM and GeoNames API queries)

## Timezone Accuracy

For accurate timezone detection, the tool uses the [GeoNames API](http://www.geonames.org/export/web-services.html).
By default it uses the `demo` account which has limited daily requests.

For unlimited requests, [register for a free GeoNames account](http://www.geonames.org/login) and set:

```bash
export GEONAMES_USERNAME=your_username
```

If the API is unavailable, the tool falls back to longitude-based estimation (which may be off by 1-2 hours in some regions, but doesn't affect the sunset azimuth calculation).

## How Accurate?

- **Solar calculations**: NOAA algorithm, verified against timeanddate.com (±1 minute, ±0.3° azimuth)
- **Beach orientation**: Calculated algorithmically from OSM coastline geometry
- **Confidence levels**: high/medium/low based on coastline data quality

### Caveats

- **Timezone**: Uses GeoNames API for accurate timezone detection. Falls back to longitude estimation if unavailable (see [Timezone Accuracy](#timezone-accuracy) above).
- **Coastline heuristics**: Beach orientation is derived from nearby OSM coastline data. Complex coastlines or sparse data may yield less accurate results. The confidence level indicates data quality.
- **Polar regions**: Properly detects midnight sun and polar night.
- **Position on beach**: Results are for the geocoded point. Your actual view may vary depending on where you stand on the beach.
- **Lakes supported**: Works with large lakes (Great Lakes, etc.) in addition to ocean coastlines. Lake shoreline orientation is detected automatically.

## License

MIT

---

*Built to answer: "Will the sunset be visible from Nai Harn Beach on December 29th?"*

*Answer: Yes, and it sets near เกาะมัน (Koh Man) island.*
