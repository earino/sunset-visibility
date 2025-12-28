# Sunset Visibility Calculator

**Will the sunset be over the ocean tonight?** Find out for any beach on Earth.

```
$ sunset_check.py "Nai Harn Beach, Phuket"

SUNSET VISIBILITY: Nai Harn Beach
══════════════════════════════════════════════════════════════════════

Date: 2025-12-29
Sunset time: 18:19 (UTC+7)
Sun position: 246.7° (west-southwest)

──────────────────────────────────────────────────
✓ YES - Sunset WILL be visible over the ocean!

  BONUS: Sun sets DIRECTLY behind Koh Man Island!
```

---

## The Problem

You're planning a beach trip. You want to watch the sunset over the ocean. But beaches face different directions, have headlands blocking views, and the sun's position changes throughout the year.

**Will you actually see the sun dip into the water, or will it disappear behind a hill?**

This tool answers that question with precision.

---

## Features

- **Precise solar calculations** using NOAA algorithms (accurate to ~1 minute)
- **Curated database** of 46 popular beaches with verified orientations and obstructions
- **Algorithmic analysis** for any beach using OpenStreetMap coastline data
- **Obstruction detection** - knows about headlands, capes, and islands
- **Scenic feature alerts** - tells you when the sun aligns with famous landmarks

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/yourusername/sunset-visibility.git
cd sunset-visibility

# No dependencies required! Uses only Python standard library.

# Check a beach
./sunset_check.py "Waikiki Beach"

# Check a specific date
./sunset_check.py "Santa Monica Beach" --date 2025-06-21

# Use coordinates directly
./sunset_check.py --lat 7.7677 --lon 98.3036
```

---

## Usage

### Check Any Beach

```bash
# By name (searches curated database, then OpenStreetMap)
./sunset_check.py "Bondi Beach"
./sunset_check.py "Railay Beach, Thailand"
./sunset_check.py "Playa del Carmen"

# By coordinates
./sunset_check.py --lat 34.01 --lon -118.50

# Specific date
./sunset_check.py "Camps Bay" --date 2025-03-15
```

### Browse Beaches

```bash
# List all curated beaches
./sunset_check.py --list

# Search by name or country
./sunset_check.py --search "bali"
./sunset_check.py --search "california"

# Show only sunset-friendly beaches
./sunset_check.py --search "thailand" --sunset
```

### Output Formats

```bash
# Default: detailed human-readable output
./sunset_check.py "Kuta Beach"

# JSON for scripting
./sunset_check.py "Kuta Beach" --json

# Minimal one-line answer
./sunset_check.py "Kuta Beach" --quiet
```

---

## How It Works

### 1. Solar Position Calculation

We use the NOAA solar calculator algorithms to compute the exact azimuth (compass direction) of the sun at sunset for any location and date. This accounts for:

- Earth's axial tilt and orbital eccentricity
- Equation of time corrections
- Atmospheric refraction at the horizon (-0.833°)

### 2. Beach Orientation

For each beach, we determine the **ocean view window** - the range of compass directions where you can see the ocean horizon:

```
         South                    West                    North
           ↓                        ↓                        ↓
     180°      210°      240°      270°      300°      330°      360°
      |---------|---------|---------|---------|---------|---------|
      ██████████████████----------------------████████████████████████
                       ~~~~~~~~~~~~~~~~~~~~~~~~

      █ = Land/obstruction    ~ = Ocean view
```

### 3. Visibility Check

If the sunset azimuth falls within the ocean view window and isn't blocked by any known obstruction, you'll see the sun set over the water.

---

## Beach Database

### Curated Beaches (46 locations)

These beaches have been manually verified with accurate:
- Coastline orientation
- Headland obstructions
- Notable islands and scenic features

| Region | Beaches |
|--------|---------|
| Thailand | Nai Harn, Kata, Railay, Ao Nang |
| Indonesia | Kuta, Seminyak, Uluwatu |
| Hawaii | Waikiki, Sunset Beach, Ka'anapali |
| California | Santa Monica, Malibu, Laguna, Pacific Beach |
| Caribbean | Seven Mile (Cayman), Eagle Beach, Negril |
| Australia | Bondi*, Cottesloe, Cable Beach |
| And more... | 46 beaches across 20+ countries |

*\* East-facing beaches are included but will correctly report "no sunset over ocean"*

### Algorithmic Analysis

For beaches not in our database, we use OpenStreetMap data:

1. **Geocode** the beach name using Nominatim
2. **Fetch coastline** geometry from Overpass API
3. **Calculate orientation** using the OSM convention (water is on the right side of coastline vectors)
4. **Detect obstructions** by finding nearby capes, headlands, and islands

```bash
$ ./sunset_check.py "Unawatuna Beach, Sri Lanka"

'Unawatuna Beach, Sri Lanka' not in curated database, searching OpenStreetMap...
Found on OSM: Unawatuna, Galle District, Southern Province, Sri Lanka
Analyzing coastline... Found 20 segments with 2345 points

Beach faces: southwest
Ocean view: 195° to 275°

✓ YES - Sunset WILL be visible over the ocean!
```

---

## Understanding the Output

### Sunset Position

The **azimuth** tells you where on the horizon the sun sets:

| Azimuth | Direction | When |
|---------|-----------|------|
| 240-250° | SW | Winter (Dec-Jan) at tropical latitudes |
| 260-280° | W | Spring/Fall equinox |
| 290-310° | NW | Summer (Jun-Jul) at tropical latitudes |

### Ocean View Window

The range where ocean is visible from the beach. This depends on:

- Beach orientation (which way it faces)
- Headlands on either side
- Islands or rocks offshore

### Scenic Features

Some beaches have landmarks that create spectacular sunset silhouettes:

```
✓ YES - Sunset WILL be visible over the ocean!

  BONUS: Sun sets DIRECTLY behind Koh Man Island!
```

---

## Examples

### Good Sunset Beaches

```bash
$ ./sunset_check.py "Nai Harn Beach" --date 2025-12-29
✓ YES - Sun sets at 246.7° over the ocean
  BONUS: Directly behind Koh Man Island!

$ ./sunset_check.py "Santa Monica Beach" --date 2025-06-21
✓ YES - Sun sets at 302.1° over the ocean
  Note: Catalina Island visible on clear days

$ ./sunset_check.py "Cable Beach, Broome" --date 2025-04-15
✓ YES - Famous for camel sunset rides!
```

### Beaches That Face the Wrong Way

```bash
$ ./sunset_check.py "Bondi Beach" --date 2025-01-15
✗ NO - Beach faces EAST
  Note: Famous for SUNRISE, not sunset

$ ./sunset_check.py "Copacabana Beach" --date 2025-12-29
✗ NO - Beach faces SOUTHEAST
  Note: Famous for NYE fireworks, sunrise over Atlantic

$ ./sunset_check.py "Playa del Carmen" --date 2025-03-01
✗ NO - Beach faces EAST toward Cozumel
  Try the west coast of Mexico instead!
```

---

## API / Programmatic Use

```python
from sunset_check import resolve_beach, check_sunset
from datetime import datetime

# Get beach data
beach, from_db = resolve_beach("Nai Harn Beach")

# Check sunset visibility
result = check_sunset(beach, datetime(2025, 12, 29), verbose=False)

print(result['visibility']['sun_sets_over_ocean'])  # True
print(result['sunset']['azimuth'])  # 246.7
print(result['sunset']['local_time'])  # "18:19"
```

---

## Files

| File | Description |
|------|-------------|
| `sunset_check.py` | Main CLI tool |
| `sunset_visibility.py` | Core solar calculations |
| `beaches_database.py` | Curated beach data |
| `coastline_analyzer.py` | OSM coastline analysis |

---

## Requirements

- Python 3.7+
- No external dependencies (uses only standard library)
- Internet connection (only needed for OSM lookups of non-curated beaches)

---

## Limitations

- **Weather not included**: We calculate if the sun geometrically sets over the ocean, not if clouds will block it
- **Elevation not modeled**: Hills behind the beach aren't considered (only coastal obstructions)
- **OSM data quality varies**: Algorithmic analysis is only as good as the coastline data
- **Timezone estimates**: For non-curated beaches, timezone is estimated from longitude

---

## Contributing

Want to add a beach to the curated database? PRs welcome! Each beach needs:

```python
"beach_key": BeachData(
    name="Beach Name",
    country="Country",
    region="Region/State",
    latitude=0.0000,
    longitude=0.0000,
    timezone_offset=0.0,
    ocean_view_start=225.0,  # degrees
    ocean_view_end=315.0,    # degrees
    obstructions=[
        (180.0, 225.0, "Southern headland"),
    ],
    scenic_features=[
        (270.0, 5.0, "Island Name", "Description"),
    ],
    facing_direction="west",
    notes="Any notable info"
)
```

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Credits

- Solar position algorithms adapted from [NOAA Solar Calculator](https://gml.noaa.gov/grad/solcalc/)
- Coastline data from [OpenStreetMap](https://www.openstreetmap.org/) via Overpass API
- Beach geocoding via [Nominatim](https://nominatim.org/)

---

*Built because someone wanted to know if they'd see the sunset from Nai Harn Beach on December 29th. (Yes, and it goes right behind Koh Man Island.)*
