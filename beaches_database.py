#!/usr/bin/env python3
"""
Global Beach Database for Sunset Visibility Calculator

This module provides beach geometry data for beaches worldwide.
Data includes coordinates, orientation, ocean view ranges, and known obstructions.

For beaches not in the curated database, algorithmic estimation is available
using coastline analysis.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import math

@dataclass
class BeachData:
    """Complete beach geometry data"""
    name: str
    country: str
    region: str
    latitude: float
    longitude: float
    timezone_offset: float  # hours from UTC
    ocean_view_start: float  # azimuth in degrees
    ocean_view_end: float    # azimuth in degrees
    obstructions: List[Tuple[float, float, str]]  # (start_az, end_az, description)
    scenic_features: List[Tuple[float, float, str, str]]  # (center_az, width, name, desc)
    facing_direction: str  # human readable (e.g., "west", "southwest")
    notes: str

# ============================================================================
# CURATED BEACH DATABASE
# Manually verified beach orientations and obstructions
# ============================================================================

BEACHES_DATABASE: Dict[str, BeachData] = {

    # ========== THAILAND ==========
    "nai_harn": BeachData(
        name="Nai Harn Beach",
        country="Thailand",
        region="Phuket",
        latitude=7.7677,
        longitude=98.3036,
        timezone_offset=7.0,
        ocean_view_start=230.0,
        ocean_view_end=295.0,
        obstructions=[
            (180.0, 230.0, "Promthep Cape (southern headland)"),
            (295.0, 360.0, "Northern headland"),
        ],
        scenic_features=[
            (247.0, 2.5, "Koh Man Island", "Small rocky island - dramatic silhouette at sunset"),
        ],
        facing_direction="west-southwest",
        notes="Famous Phuket beach. Winter sunsets align with Koh Man island."
    ),

    "kata": BeachData(
        name="Kata Beach",
        country="Thailand",
        region="Phuket",
        latitude=7.8206,
        longitude=98.2983,
        timezone_offset=7.0,
        ocean_view_start=245.0,
        ocean_view_end=310.0,
        obstructions=[
            (180.0, 245.0, "Southern headland"),
            (310.0, 360.0, "Northern rocky point"),
        ],
        scenic_features=[
            (260.0, 3.0, "Koh Pu", "Small island visible offshore"),
        ],
        facing_direction="west",
        notes="Popular tourist beach with good sunset views."
    ),

    "railay": BeachData(
        name="Railay West Beach",
        country="Thailand",
        region="Krabi",
        latitude=8.0114,
        longitude=98.8367,
        timezone_offset=7.0,
        ocean_view_start=235.0,
        ocean_view_end=305.0,
        obstructions=[
            (180.0, 235.0, "Southern limestone cliffs"),
            (305.0, 360.0, "Northern cliffs"),
        ],
        scenic_features=[],
        facing_direction="west",
        notes="Stunning limestone karst scenery. Only accessible by boat."
    ),

    # ========== INDONESIA ==========
    "kuta_bali": BeachData(
        name="Kuta Beach",
        country="Indonesia",
        region="Bali",
        latitude=-8.7184,
        longitude=115.1686,
        timezone_offset=8.0,
        ocean_view_start=225.0,
        ocean_view_end=315.0,
        obstructions=[
            (180.0, 225.0, "Airport peninsula"),
            (315.0, 360.0, "Seminyak coastline"),
        ],
        scenic_features=[],
        facing_direction="west",
        notes="Bali's most famous beach. Wide ocean view, excellent sunsets."
    ),

    "seminyak": BeachData(
        name="Seminyak Beach",
        country="Indonesia",
        region="Bali",
        latitude=-8.6913,
        longitude=115.1577,
        timezone_offset=8.0,
        ocean_view_start=220.0,
        ocean_view_end=320.0,
        obstructions=[],
        scenic_features=[],
        facing_direction="west",
        notes="Upscale beach area with unobstructed western horizon."
    ),

    "uluwatu": BeachData(
        name="Uluwatu Beach (Suluban)",
        country="Indonesia",
        region="Bali",
        latitude=-8.8156,
        longitude=115.0872,
        timezone_offset=8.0,
        ocean_view_start=200.0,
        ocean_view_end=300.0,
        obstructions=[
            (180.0, 200.0, "Southern cliffs"),
            (300.0, 360.0, "Northern cliff walls"),
        ],
        scenic_features=[
            (250.0, 5.0, "Sea stacks", "Dramatic rock formations in surf"),
        ],
        facing_direction="southwest",
        notes="Cliff-bottom beach accessed through cave. Dramatic scenery."
    ),

    # ========== HAWAII ==========
    "waikiki": BeachData(
        name="Waikiki Beach",
        country="USA",
        region="Hawaii (Oahu)",
        latitude=21.2766,
        longitude=-157.8275,
        timezone_offset=-10.0,
        ocean_view_start=150.0,
        ocean_view_end=250.0,
        obstructions=[
            (0.0, 150.0, "Diamond Head and coastline"),
            (250.0, 360.0, "Honolulu urban area"),
        ],
        scenic_features=[
            (200.0, 10.0, "Diamond Head silhouette", "Iconic volcanic crater visible to the east"),
        ],
        facing_direction="south-southwest",
        notes="Sunset visible but sun sets to the right of ocean view in winter."
    ),

    "sunset_beach": BeachData(
        name="Sunset Beach",
        country="USA",
        region="Hawaii (Oahu)",
        latitude=21.6786,
        longitude=-158.0428,
        timezone_offset=-10.0,
        ocean_view_start=270.0,
        ocean_view_end=360.0,
        obstructions=[
            (0.0, 270.0, "Land/coastline to south and east"),
        ],
        scenic_features=[],
        facing_direction="north-northwest",
        notes="Famous surf beach. Sun sets over ocean in summer months only."
    ),

    "kaanapali": BeachData(
        name="Ka'anapali Beach",
        country="USA",
        region="Hawaii (Maui)",
        latitude=20.9256,
        longitude=-156.6947,
        timezone_offset=-10.0,
        ocean_view_start=225.0,
        ocean_view_end=340.0,
        obstructions=[
            (180.0, 225.0, "Black Rock (Pu'u Keka'a)"),
        ],
        scenic_features=[
            (280.0, 5.0, "Lanai Island", "Neighboring island visible on horizon"),
            (300.0, 5.0, "Molokai Island", "Neighboring island visible on horizon"),
        ],
        facing_direction="west",
        notes="Excellent sunset beach with island silhouettes on horizon."
    ),

    # ========== CALIFORNIA ==========
    "santa_monica": BeachData(
        name="Santa Monica Beach",
        country="USA",
        region="California",
        latitude=34.0083,
        longitude=-118.4988,
        timezone_offset=-8.0,  # PST (PDT is -7)
        ocean_view_start=200.0,
        ocean_view_end=310.0,
        obstructions=[
            (180.0, 200.0, "Palos Verdes Peninsula"),
            (310.0, 360.0, "Malibu coastline"),
        ],
        scenic_features=[
            (235.0, 3.0, "Catalina Island", "Visible on clear days, 26 miles offshore"),
        ],
        facing_direction="west-southwest",
        notes="Iconic LA beach. Santa Monica Pier nearby."
    ),

    "malibu": BeachData(
        name="Malibu Beach (Zuma)",
        country="USA",
        region="California",
        latitude=34.0151,
        longitude=-118.8225,
        timezone_offset=-8.0,
        ocean_view_start=180.0,
        ocean_view_end=280.0,
        obstructions=[
            (280.0, 360.0, "Point Dume headland"),
        ],
        scenic_features=[],
        facing_direction="south-southwest",
        notes="Wide sandy beach with excellent sunset views."
    ),

    "laguna": BeachData(
        name="Laguna Beach (Main Beach)",
        country="USA",
        region="California",
        latitude=33.5427,
        longitude=-117.7854,
        timezone_offset=-8.0,
        ocean_view_start=200.0,
        ocean_view_end=290.0,
        obstructions=[
            (180.0, 200.0, "Southern bluffs"),
            (290.0, 360.0, "Northern headland"),
        ],
        scenic_features=[],
        facing_direction="west-southwest",
        notes="Artist colony beach with rocky coves."
    ),

    "san_diego_pb": BeachData(
        name="Pacific Beach",
        country="USA",
        region="California (San Diego)",
        latitude=32.7946,
        longitude=-117.2555,
        timezone_offset=-8.0,
        ocean_view_start=220.0,
        ocean_view_end=310.0,
        obstructions=[],
        scenic_features=[],
        facing_direction="west",
        notes="Classic San Diego beach with Crystal Pier."
    ),

    # ========== CARIBBEAN ==========
    "seven_mile": BeachData(
        name="Seven Mile Beach",
        country="Cayman Islands",
        region="Grand Cayman",
        latitude=19.3455,
        longitude=-81.3877,
        timezone_offset=-5.0,
        ocean_view_start=225.0,
        ocean_view_end=315.0,
        obstructions=[],
        scenic_features=[],
        facing_direction="west",
        notes="Famous Caribbean beach with calm waters and clear sunsets."
    ),

    "eagle_beach": BeachData(
        name="Eagle Beach",
        country="Aruba",
        region="Aruba",
        latitude=12.5574,
        longitude=-70.0513,
        timezone_offset=-4.0,
        ocean_view_start=250.0,
        ocean_view_end=340.0,
        obstructions=[],
        scenic_features=[
            (290.0, 2.0, "Fofoti Trees", "Iconic wind-bent divi-divi trees on beach"),
        ],
        facing_direction="west-northwest",
        notes="Wide white sand beach, consistently rated among world's best."
    ),

    "grace_bay": BeachData(
        name="Grace Bay Beach",
        country="Turks and Caicos",
        region="Providenciales",
        latitude=21.7967,
        longitude=-72.1883,
        timezone_offset=-5.0,
        ocean_view_start=330.0,
        ocean_view_end=90.0,  # Wraps around north
        obstructions=[],
        scenic_features=[],
        facing_direction="north",
        notes="Award-winning beach. Faces NORTH - sunset not over ocean."
    ),

    "negril": BeachData(
        name="Seven Mile Beach (Negril)",
        country="Jamaica",
        region="Westmoreland",
        latitude=18.2869,
        longitude=-78.3494,
        timezone_offset=-5.0,
        ocean_view_start=225.0,
        ocean_view_end=315.0,
        obstructions=[],
        scenic_features=[],
        facing_direction="west",
        notes="Famous for spectacular sunsets. Rick's Cafe nearby for cliff views."
    ),

    # ========== MEXICO ==========
    "playa_del_carmen": BeachData(
        name="Playa del Carmen",
        country="Mexico",
        region="Quintana Roo",
        latitude=20.6296,
        longitude=-87.0739,
        timezone_offset=-5.0,
        ocean_view_start=30.0,
        ocean_view_end=150.0,
        obstructions=[],
        scenic_features=[
            (75.0, 5.0, "Cozumel Island", "Large island visible on horizon"),
        ],
        facing_direction="east",
        notes="EAST-facing beach - sunrise beach, NOT sunset."
    ),

    "puerto_vallarta": BeachData(
        name="Playa Los Muertos",
        country="Mexico",
        region="Jalisco (Puerto Vallarta)",
        latitude=20.5958,
        longitude=-105.2347,
        timezone_offset=-6.0,
        ocean_view_start=240.0,
        ocean_view_end=330.0,
        obstructions=[
            (180.0, 240.0, "Southern hills"),
        ],
        scenic_features=[
            (270.0, 3.0, "Los Arcos", "Rock formations visible to the south"),
        ],
        facing_direction="west",
        notes="Popular beach in Banderas Bay with excellent sunset views."
    ),

    "cabo_medano": BeachData(
        name="Playa El Médano",
        country="Mexico",
        region="Baja California Sur (Cabo)",
        latitude=22.8847,
        longitude=-109.8994,
        timezone_offset=-7.0,
        ocean_view_start=90.0,
        ocean_view_end=200.0,
        obstructions=[
            (200.0, 270.0, "Land's End rocks"),
        ],
        scenic_features=[
            (170.0, 10.0, "El Arco", "Famous rock arch at Land's End"),
        ],
        facing_direction="south-southeast",
        notes="Main swimming beach in Cabo. El Arco visible. Sunset behind rocks."
    ),

    # ========== AUSTRALIA ==========
    "bondi": BeachData(
        name="Bondi Beach",
        country="Australia",
        region="New South Wales (Sydney)",
        latitude=-33.8908,
        longitude=151.2743,
        timezone_offset=11.0,  # AEDT (AEST is +10)
        ocean_view_start=30.0,
        ocean_view_end=150.0,
        obstructions=[
            (0.0, 30.0, "North Head"),
            (150.0, 180.0, "South Head"),
        ],
        scenic_features=[],
        facing_direction="east",
        notes="EAST-facing beach - famous for SUNRISE, not sunset."
    ),

    "byron_bay": BeachData(
        name="Main Beach Byron Bay",
        country="Australia",
        region="New South Wales",
        latitude=-28.6434,
        longitude=153.6150,
        timezone_offset=11.0,
        ocean_view_start=10.0,
        ocean_view_end=170.0,
        obstructions=[
            (170.0, 360.0, "Cape Byron and coastline"),
        ],
        scenic_features=[
            (100.0, 5.0, "Julian Rocks", "Marine reserve island"),
        ],
        facing_direction="east-northeast",
        notes="EAST-facing beach at Australia's easternmost point. SUNRISE beach."
    ),

    "surfers_paradise": BeachData(
        name="Surfers Paradise Beach",
        country="Australia",
        region="Queensland (Gold Coast)",
        latitude=-28.0024,
        longitude=153.4290,
        timezone_offset=10.0,
        ocean_view_start=20.0,
        ocean_view_end=160.0,
        obstructions=[],
        scenic_features=[],
        facing_direction="east",
        notes="EAST-facing beach. Good for sunrise, sunset is over the city/hinterland."
    ),

    "cottesloe": BeachData(
        name="Cottesloe Beach",
        country="Australia",
        region="Western Australia (Perth)",
        latitude=-31.9933,
        longitude=115.7511,
        timezone_offset=8.0,
        ocean_view_start=225.0,
        ocean_view_end=315.0,
        obstructions=[],
        scenic_features=[
            (260.0, 3.0, "Rottnest Island", "Island visible on horizon"),
        ],
        facing_direction="west",
        notes="Perth's most popular beach. Excellent Indian Ocean sunsets."
    ),

    "cable_beach": BeachData(
        name="Cable Beach",
        country="Australia",
        region="Western Australia (Broome)",
        latitude=-17.9614,
        longitude=122.2089,
        timezone_offset=8.0,
        ocean_view_start=225.0,
        ocean_view_end=340.0,
        obstructions=[],
        scenic_features=[],
        facing_direction="west-northwest",
        notes="22km of white sand. Famous camel sunset rides. Staircase to the Moon phenomenon."
    ),

    # ========== EUROPE - MEDITERRANEAN ==========
    "barceloneta": BeachData(
        name="Barceloneta Beach",
        country="Spain",
        region="Catalonia (Barcelona)",
        latitude=41.3784,
        longitude=2.1925,
        timezone_offset=1.0,  # CET (CEST is +2)
        ocean_view_start=60.0,
        ocean_view_end=180.0,
        obstructions=[
            (180.0, 360.0, "City and port"),
        ],
        scenic_features=[],
        facing_direction="southeast",
        notes="EAST-facing Mediterranean beach. Sunrise over sea, sunset over city."
    ),

    "ibiza_ses_salines": BeachData(
        name="Ses Salines Beach",
        country="Spain",
        region="Balearic Islands (Ibiza)",
        latitude=38.8667,
        longitude=1.3833,
        timezone_offset=1.0,
        ocean_view_start=120.0,
        ocean_view_end=240.0,
        obstructions=[],
        scenic_features=[
            (180.0, 5.0, "Formentera Island", "Neighboring island visible"),
        ],
        facing_direction="south",
        notes="Southern tip of Ibiza. Sunset to the right of ocean view in summer."
    ),

    "santorini_perissa": BeachData(
        name="Perissa Beach",
        country="Greece",
        region="Santorini",
        latitude=36.3519,
        longitude=25.4733,
        timezone_offset=2.0,
        ocean_view_start=60.0,
        ocean_view_end=180.0,
        obstructions=[
            (0.0, 60.0, "Mesa Vouno rock"),
            (180.0, 360.0, "Island interior"),
        ],
        scenic_features=[],
        facing_direction="east-southeast",
        notes="Black sand beach. EAST-facing. For Santorini sunset, go to Oia village."
    ),

    "nice": BeachData(
        name="Promenade des Anglais Beach",
        country="France",
        region="Côte d'Azur",
        latitude=43.6942,
        longitude=7.2650,
        timezone_offset=1.0,
        ocean_view_start=90.0,
        ocean_view_end=210.0,
        obstructions=[
            (210.0, 270.0, "Cap de Nice"),
        ],
        scenic_features=[],
        facing_direction="south",
        notes="Pebble beach. Faces south - sunset to the right over Cap Ferrat area."
    ),

    "amalfi": BeachData(
        name="Amalfi Beach",
        country="Italy",
        region="Campania (Amalfi Coast)",
        latitude=40.6340,
        longitude=14.6027,
        timezone_offset=1.0,
        ocean_view_start=150.0,
        ocean_view_end=250.0,
        obstructions=[
            (0.0, 150.0, "Eastern cliffs"),
            (250.0, 360.0, "Western headland"),
        ],
        scenic_features=[],
        facing_direction="south-southwest",
        notes="Small beach in dramatic cliff setting. Sunset usually visible over water in summer."
    ),

    # ========== EUROPE - ATLANTIC ==========
    "nazare": BeachData(
        name="Praia da Nazaré",
        country="Portugal",
        region="Leiria",
        latitude=39.5983,
        longitude=-9.0700,
        timezone_offset=0.0,  # WET (WEST is +1)
        ocean_view_start=225.0,
        ocean_view_end=340.0,
        obstructions=[
            (180.0, 225.0, "Sítio headland/cliff"),
        ],
        scenic_features=[
            (280.0, 5.0, "Farilhões Islands", "Rocky islets on horizon"),
        ],
        facing_direction="west-northwest",
        notes="Famous for giant waves. Excellent Atlantic sunsets."
    ),

    "biarritz": BeachData(
        name="Grande Plage Biarritz",
        country="France",
        region="Nouvelle-Aquitaine",
        latitude=43.4845,
        longitude=-1.5580,
        timezone_offset=1.0,
        ocean_view_start=260.0,
        ocean_view_end=350.0,
        obstructions=[
            (180.0, 260.0, "Pointe St-Martin"),
            (350.0, 360.0, "Northern rocks"),
        ],
        scenic_features=[
            (290.0, 2.0, "Rocher de la Vierge", "Iconic rock with statue"),
        ],
        facing_direction="northwest",
        notes="Elegant resort beach. Spectacular Bay of Biscay sunsets."
    ),

    # ========== INDIAN OCEAN ==========
    "belle_mare": BeachData(
        name="Belle Mare Beach",
        country="Mauritius",
        region="Flacq",
        latitude=-20.1833,
        longitude=57.7667,
        timezone_offset=4.0,
        ocean_view_start=20.0,
        ocean_view_end=140.0,
        obstructions=[],
        scenic_features=[],
        facing_direction="east",
        notes="EAST-facing beach. Good for sunrise. Sunset over the island interior."
    ),

    "flic_en_flac": BeachData(
        name="Flic en Flac Beach",
        country="Mauritius",
        region="Black River",
        latitude=-20.2833,
        longitude=57.3667,
        timezone_offset=4.0,
        ocean_view_start=225.0,
        ocean_view_end=315.0,
        obstructions=[],
        scenic_features=[],
        facing_direction="west",
        notes="WEST-facing beach. Excellent for sunsets over the Indian Ocean."
    ),

    "anse_source_argent": BeachData(
        name="Anse Source d'Argent",
        country="Seychelles",
        region="La Digue",
        latitude=-4.3697,
        longitude=55.8311,
        timezone_offset=4.0,
        ocean_view_start=225.0,
        ocean_view_end=315.0,
        obstructions=[
            (180.0, 225.0, "Granite boulders"),
        ],
        scenic_features=[
            (260.0, 10.0, "Praslin Island", "Neighboring island on horizon"),
        ],
        facing_direction="west",
        notes="World-famous beach with giant granite boulders. Good sunset views."
    ),

    "maldives_male": BeachData(
        name="Hulhumalé Beach",
        country="Maldives",
        region="Malé Atoll",
        latitude=4.2117,
        longitude=73.5403,
        timezone_offset=5.0,
        ocean_view_start=45.0,
        ocean_view_end=180.0,
        obstructions=[],
        scenic_features=[],
        facing_direction="east",
        notes="EAST-facing. Most Maldives resorts are on islands with 360° ocean views."
    ),

    # ========== SOUTH AMERICA ==========
    "copacabana": BeachData(
        name="Copacabana Beach",
        country="Brazil",
        region="Rio de Janeiro",
        latitude=-22.9711,
        longitude=-43.1822,
        timezone_offset=-3.0,
        ocean_view_start=30.0,
        ocean_view_end=150.0,
        obstructions=[
            (0.0, 30.0, "Forte de Copacabana"),
            (150.0, 180.0, "Morro do Leme"),
        ],
        scenic_features=[],
        facing_direction="southeast",
        notes="Iconic beach but faces EAST-SOUTHEAST. Famous for sunrise and NYE fireworks."
    ),

    "ipanema": BeachData(
        name="Ipanema Beach",
        country="Brazil",
        region="Rio de Janeiro",
        latitude=-22.9838,
        longitude=-43.2045,
        timezone_offset=-3.0,
        ocean_view_start=60.0,
        ocean_view_end=200.0,
        obstructions=[
            (200.0, 270.0, "Dois Irmãos peaks and Vidigal"),
        ],
        scenic_features=[
            (200.0, 5.0, "Dois Irmãos", "Twin peaks create dramatic sunset silhouette"),
        ],
        facing_direction="south",
        notes="Sun sets behind Dois Irmãos mountains in winter - very scenic."
    ),

    # ========== SOUTH AFRICA ==========
    "camps_bay": BeachData(
        name="Camps Bay Beach",
        country="South Africa",
        region="Western Cape (Cape Town)",
        latitude=-33.9506,
        longitude=18.3778,
        timezone_offset=2.0,
        ocean_view_start=240.0,
        ocean_view_end=330.0,
        obstructions=[
            (180.0, 240.0, "Twelve Apostles mountains"),
            (330.0, 360.0, "Lion's Head"),
        ],
        scenic_features=[
            (200.0, 15.0, "Twelve Apostles", "Dramatic mountain backdrop"),
        ],
        facing_direction="west-northwest",
        notes="Spectacular beach with mountain backdrop. Excellent Atlantic sunsets."
    ),

    "clifton": BeachData(
        name="Clifton 4th Beach",
        country="South Africa",
        region="Western Cape (Cape Town)",
        latitude=-33.9397,
        longitude=18.3756,
        timezone_offset=2.0,
        ocean_view_start=250.0,
        ocean_view_end=340.0,
        obstructions=[
            (180.0, 250.0, "Clifton cliffs"),
            (340.0, 360.0, "Rocks"),
        ],
        scenic_features=[],
        facing_direction="northwest",
        notes="Sheltered cove beach. Excellent sunset views over Atlantic."
    ),

    # ========== ASIA ==========
    "boracay_white": BeachData(
        name="White Beach Boracay",
        country="Philippines",
        region="Aklan",
        latitude=11.9674,
        longitude=121.9248,
        timezone_offset=8.0,
        ocean_view_start=225.0,
        ocean_view_end=315.0,
        obstructions=[],
        scenic_features=[],
        facing_direction="west",
        notes="4km of white sand. World-famous sunset views."
    ),

    "ao_nang": BeachData(
        name="Ao Nang Beach",
        country="Thailand",
        region="Krabi",
        latitude=8.0286,
        longitude=98.8183,
        timezone_offset=7.0,
        ocean_view_start=210.0,
        ocean_view_end=290.0,
        obstructions=[
            (180.0, 210.0, "Southern limestone cliffs"),
            (290.0, 360.0, "Northern headland"),
        ],
        scenic_features=[
            (240.0, 10.0, "Limestone karsts", "Dramatic rock formations in bay"),
        ],
        facing_direction="west-southwest",
        notes="Gateway to Railay. Dramatic karst scenery."
    ),

    "langkawi_cenang": BeachData(
        name="Pantai Cenang",
        country="Malaysia",
        region="Langkawi",
        latitude=6.2917,
        longitude=99.7250,
        timezone_offset=8.0,
        ocean_view_start=225.0,
        ocean_view_end=315.0,
        obstructions=[],
        scenic_features=[
            (240.0, 5.0, "Pulau Rebak", "Small island offshore"),
        ],
        facing_direction="west",
        notes="Langkawi's most popular beach. Good sunset views."
    ),

    "phu_quoc": BeachData(
        name="Long Beach (Bai Truong)",
        country="Vietnam",
        region="Phu Quoc Island",
        latitude=10.1833,
        longitude=103.9667,
        timezone_offset=7.0,
        ocean_view_start=200.0,
        ocean_view_end=290.0,
        obstructions=[],
        scenic_features=[],
        facing_direction="west-southwest",
        notes="20km beach on Vietnam's largest island. Excellent Gulf of Thailand sunsets."
    ),

    "goa_palolem": BeachData(
        name="Palolem Beach",
        country="India",
        region="Goa",
        latitude=15.0100,
        longitude=74.0231,
        timezone_offset=5.5,
        ocean_view_start=225.0,
        ocean_view_end=315.0,
        obstructions=[
            (180.0, 225.0, "Southern headland"),
            (315.0, 360.0, "Northern rocky outcrop"),
        ],
        scenic_features=[
            (250.0, 3.0, "Butterfly Island", "Small island at south end of bay"),
        ],
        facing_direction="west",
        notes="Crescent-shaped beach. Calm waters and good sunsets."
    ),

    # ========== MIDDLE EAST ==========
    "jumeirah": BeachData(
        name="Jumeirah Beach",
        country="UAE",
        region="Dubai",
        latitude=25.2048,
        longitude=55.2708,
        timezone_offset=4.0,
        ocean_view_start=200.0,
        ocean_view_end=340.0,
        obstructions=[],
        scenic_features=[
            (300.0, 5.0, "Burj Al Arab", "Iconic sail-shaped hotel"),
            (320.0, 10.0, "Palm Jumeirah", "Artificial palm island"),
        ],
        facing_direction="west-northwest",
        notes="Persian Gulf beach with iconic Dubai skyline. Good sunset views."
    ),

}

# ============================================================================
# SEARCH AND LOOKUP FUNCTIONS
# ============================================================================

def search_beaches(query: str) -> List[BeachData]:
    """Search for beaches by name, country, or region"""
    query_lower = query.lower()
    results = []

    for key, beach in BEACHES_DATABASE.items():
        # Check various fields
        if (query_lower in beach.name.lower() or
            query_lower in beach.country.lower() or
            query_lower in beach.region.lower() or
            query_lower in key.lower()):
            results.append(beach)

    return results

def get_beach(identifier: str) -> Optional[BeachData]:
    """Get a beach by its key identifier"""
    return BEACHES_DATABASE.get(identifier.lower().replace(" ", "_").replace("-", "_"))

def list_all_beaches() -> List[str]:
    """List all beach identifiers"""
    return list(BEACHES_DATABASE.keys())

def list_beaches_by_country(country: str) -> List[BeachData]:
    """List all beaches in a country"""
    country_lower = country.lower()
    return [b for b in BEACHES_DATABASE.values() if country_lower in b.country.lower()]

def list_sunset_beaches() -> List[BeachData]:
    """List beaches where sunset is typically visible over water"""
    sunset_beaches = []
    for beach in BEACHES_DATABASE.values():
        # Check if west (225-315) falls within ocean view
        # This is simplified - actual visibility depends on date
        if beach.ocean_view_start <= 270 <= beach.ocean_view_end:
            sunset_beaches.append(beach)
        elif beach.ocean_view_start <= 250 <= beach.ocean_view_end:
            sunset_beaches.append(beach)
    return sunset_beaches

# ============================================================================
# ALGORITHMIC BEACH ORIENTATION (for unknown beaches)
# ============================================================================

def estimate_beach_orientation(lat: float, lon: float, coastline_bearing: float) -> dict:
    """
    Estimate beach orientation based on location and coastline bearing.

    Args:
        lat: latitude
        lon: longitude
        coastline_bearing: bearing of coastline in degrees (direction coast runs)

    Returns:
        Dictionary with estimated ocean view range
    """
    # The beach faces perpendicular to the coastline
    # If coastline runs north-south (0/180°), beach faces east or west
    # Ocean is perpendicular to coastline

    facing_direction = (coastline_bearing + 90) % 360

    # Typical beach has about 120° of ocean view (60° each side of perpendicular)
    ocean_view_start = (facing_direction - 60) % 360
    ocean_view_end = (facing_direction + 60) % 360

    return {
        "facing_azimuth": facing_direction,
        "ocean_view_start": ocean_view_start,
        "ocean_view_end": ocean_view_end,
        "estimated": True,
        "note": "Estimated from coastline bearing. Actual obstructions unknown."
    }

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

    for i in range(len(directions) - 1):
        if directions[i][0] <= azimuth < directions[i+1][0]:
            # Return the closer one
            if azimuth - directions[i][0] < directions[i+1][0] - azimuth:
                return directions[i][1]
            else:
                return directions[i+1][1]
    return "north"


if __name__ == "__main__":
    # Print database summary
    print(f"Beach Database: {len(BEACHES_DATABASE)} beaches")
    print()

    # Group by country
    countries = {}
    for beach in BEACHES_DATABASE.values():
        if beach.country not in countries:
            countries[beach.country] = []
        countries[beach.country].append(beach.name)

    print("Beaches by country:")
    for country in sorted(countries.keys()):
        print(f"\n{country}:")
        for name in countries[country]:
            print(f"  - {name}")
