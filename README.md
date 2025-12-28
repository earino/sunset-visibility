# Sunset Visibility Calculator

**Will the sunset be over the ocean?** Check any beach on Earth.

```
$ ./sunset_check.py "Nai Harn Beach, Phuket" --date 2025-12-29

SUNSET VISIBILITY: Nai Harn Beach, Phuket
============================================================

Date: 2025-12-29
Beach faces: west-southwest
Ocean view: 205° to 285°

Sunset: 18:19 (UTC+7)
Sun position: 246.7° (west-southwest)

YES - Sunset WILL be visible over the ocean!
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
│ Overpass API    │  Fetch coastline geometry
└────────┬────────┘
         ▼
┌─────────────────┐
│ Analyze         │  Beach orientation (water on right of coast)
│                 │  Nearby islands → scenic features
│                 │  Nearby capes → obstructions
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

## Examples

### Sunset beaches

```
$ ./sunset_check.py "Kuta Beach, Bali"
Beach faces: west
Ocean view: 215° to 315°
Sun position: 247° (west-southwest)
YES - Sunset WILL be visible over the ocean!
```

### Non-sunset beaches

```
$ ./sunset_check.py "Bondi Beach, Sydney"
Beach faces: southeast
Ocean view: 84° to 184°
Sun position: 241° (west-southwest)
NO - Sunset will NOT be over the ocean
```

Bondi faces east - it's a **sunrise** beach.

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

- **Solar calculations**: NOAA algorithm, accurate to ~1 minute
- **Beach orientation**: Depends on OSM coastline data quality (generally good)
- **Confidence levels**: high/medium/low based on coastline geometry complexity

The tool also detects nearby islands and capes from OSM, reporting them as potential scenic features or obstructions.

## License

MIT

---

*Built to answer: "Will the sunset be visible from Nai Harn Beach on December 29th?"*

*Answer: Yes.*
