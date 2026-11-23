"""Static configuration for the UrbanAir Twin model.

Everything here that is an ASSUMPTION is labelled as such. Coordinates are
approximate public locations of monitoring stations / industrial estates and
must be verified against CPCB/MPCB station metadata before any pilot use.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent           # C:/HM/AirTwin
DATA_DIR = ROOT.parent / "datasets for training"
ARTIFACTS = ROOT / "artifacts"

TRAINING_CSV = DATA_DIR / "pune_xgboost_randomforest_training.csv"
MASTER_PARQUET = DATA_DIR / "pune_master_dataset_2021_2026.parquet"
TRAFFIC_SURVEY = DATA_DIR / "pune_traffic_survey_stations.parquet"
CONGESTION_SAMPLE = DATA_DIR / "pune_traffic_congestion_toy_sample.parquet"
EMISSION_INVENTORY = DATA_DIR / "pune_emission_inventory_baseline_2021.parquet"
POPULATION_GRID = DATA_DIR / "pune_population_grid.parquet"   # optional: cols lat, lon, population

TZ = "Asia/Kolkata"

# Grid: ~500 m cells. Extended north to 18.70 so Alandi / Nigdi stations fall inside.
BBOX = {"lat_min": 18.40, "lat_max": 18.70, "lon_min": 73.73, "lon_max": 74.00}
CELL_DEG_LAT = 0.0045    # ~500 m
CELL_DEG_LON = 0.00475   # ~500 m at 18.5°N
CITY_CENTER = (18.5204, 73.8567)

# Legacy 2021-23 "assumed PM2.5" portal values run ~2.5x the verified 2024-25 sensor
# PM2.5 at the same stations, so the twin trains on verified sensor data only.
SPLITS = {  # chronological, never shuffled
    "train": ("2024-01-01", "2024-12-31 23:59"),
    "validation": ("2025-01-01", "2025-03-31 23:59"),
    "test": ("2025-04-01", "2025-12-31 23:59"),
}

# CPCB NAAQS 24-hour PM2.5 standard (µg/m³) — default hotspot threshold.
HOTSPOT_THRESHOLD = 60.0

# ASSUMPTION: approximate station coordinates (verify against CPCB CAAQMS metadata).
STATIONS = {
    "site_292":  ("Karve Road (MPCB)", 18.5010, 73.8165),
    "site_5404": ("Mhada Colony (IITM)", 18.5770, 73.8930),
    "site_5405": ("Alandi (IITM)", 18.6770, 73.8960),
    "site_5406": ("Bhosari (IITM)", 18.6290, 73.8470),
    "site_5407": ("Hadapsar (IITM)", 18.5018, 73.9270),
    "site_5408": ("Transport Nagar-Nigdi (IITM)", 18.6560, 73.7680),
    "site_5409": ("Revenue Colony-Shivajinagar (IITM)", 18.5300, 73.8490),
    "site_5766": ("Katraj Dairy (MPCB)", 18.4530, 73.8610),
    "site_5767": ("SPPU (MPCB)", 18.5480, 73.8250),
    "site_5988": ("Bhumkar Nagar (IITM)", 18.6040, 73.7570),
    "site_5996": ("Panchawati Pashan (IITM)", 18.5350, 73.7980),
    "site_6012": ("Dhankawadi (IITM)", 18.4630, 73.8530),
    "LEGACY_KARVENAGAR":    ("Karvenagar (legacy)", 18.4900, 73.8200),
    "LEGACY_MIT_KOTHRUD":   ("MIT Kothrud (legacy)", 18.5180, 73.8150),
    "LEGACY_SHIVAJI_NAGAR": ("Shivaji Nagar (legacy)", 18.5310, 73.8470),
}

# ASSUMPTION: approximate centroids of industrial estates (MIDC etc.).
INDUSTRIAL_ZONES = [
    ("Bhosari MIDC", 18.6250, 73.8350),
    ("Pimpri-Chinchwad MIDC", 18.6400, 73.8000),
    ("Hadapsar Industrial Estate", 18.5050, 73.9150),
    ("Talawade / Chikhli", 18.6800, 73.7800),
    ("Chakan MIDC", 18.7600, 73.8600),
]

ROAD_WEIGHTS = {"Major Road": 1.0, "Intermediate Road": 0.6, "Minor Road": 0.3}

# Feature groups used for attribution (TreeSHAP contributions are summed per group).
SOURCE_GROUPS = {
    "traffic":  ["traffic_activity", "road_exposure"],
    "industry": ["industry_activity", "industry_exposure"],
    "dust":     ["dust_activity"],
    "burning":  ["burning_activity"],
    "meteorology": [
        "era5_temp_2m_k", "era5_dewpoint_2m_k", "era5_wind_u100_ms", "era5_wind_v100_ms",
        "era5_boundary_layer_height_m", "era5_surface_pressure_pa", "era5_total_precipitation_m",
        "era5_total_cloud_cover_frac", "era5_skin_temp_k", "era5_surface_latent_heat_flux_jm2",
        "era5_surface_thermal_radiation_down_jm2", "era5_surface_sensible_heat_flux_jm2",
        "era5_wind_speed_100m_ms", "precip_72h_m", "rel_humidity_pct",
    ],
    "seasonal_background": ["month_sin", "month_cos", "dist_center_km"],
}

# Activity proxies the Scenario Lab can scale; all trained with monotone +1 constraints.
LEVERS = {
    "traffic":  ["traffic_activity"],
    "industry": ["industry_activity"],
    "dust":     ["dust_activity"],
    "burning":  ["burning_activity"],
}
MAX_REDUCTION_PCT = 50.0   # emission-inventory policy lever range is 0-50 %

FEATURES = [f for g in SOURCE_GROUPS.values() for f in g]
MONOTONE = {f: 1 for fs in LEVERS.values() for f in fs}

PROXY_NOTES = {
    "traffic_activity": "PROXY: road exposure (ARAI 2021 traffic-survey corridors) x hourly congestion profile (toy congestion sample) x weekend factor 0.85 (assumption).",
    "industry_activity": "PROXY: distance-decayed exposure to approximate MIDC centroids x shift profile (night 0.7, Sunday 0.6; assumption).",
    "dust_activity": "PROXY: road exposure x wind speed x dryness (no rain in prior 72 h, ERA5) x daytime construction hours.",
    "burning_activity": "PROXY: seasonal (Nov-Feb peak, monsoon minimum) x evening profile. No satellite fire detections loaded yet.",
}
