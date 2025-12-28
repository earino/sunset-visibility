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
- Internet connection (for OSM queries)

## How Accurate?

- **Solar calculations**: NOAA algorithm, verified against timeanddate.com
- **Beach orientation**: Calculated from OSM coastline geometry
- **Confidence levels**: high/medium/low based on coastline complexity

## License

MIT

---

*Built to answer: "Will the sunset be visible from Nai Harn Beach on December 29th?"*

*Answer: Yes, and it sets near เกาะมัน (Koh Man) island.*
