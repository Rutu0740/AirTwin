"""Feature construction shared by training and runtime inference.

Every location-dependent feature is computable for an arbitrary (lat, lon), so
the same model scores monitoring stations and the 500 m city grid.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

ERA5_COLS = [
    "era5_temp_2m_k", "era5_dewpoint_2m_k", "era5_wind_u100_ms", "era5_wind_v100_ms",
    "era5_boundary_layer_height_m", "era5_surface_pressure_pa", "era5_total_precipitation_m",
    "era5_total_cloud_cover_frac", "era5_skin_temp_k", "era5_surface_latent_heat_flux_jm2",
    "era5_surface_thermal_radiation_down_jm2", "era5_surface_sensible_heat_flux_jm2",
]


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


_SURVEY = None


def _survey_points():
    global _SURVEY
    if _SURVEY is None:
        s = pd.read_parquet(C.TRAFFIC_SURVEY)
        s = s[(s.survey_type == "Traffic Count") & s.latitude.notna()]
        s = s.assign(w=s.road_category.map(C.ROAD_WEIGHTS).fillna(0.3))
        _SURVEY = s[["latitude", "longitude", "w"]].to_numpy()
    return _SURVEY


def static_spatial(lat, lon) -> pd.DataFrame:
    """Road exposure, industrial exposure and distance to centre for each point."""
    lat = np.asarray(lat, float)[:, None]
    lon = np.asarray(lon, float)[:, None]
    sv = _survey_points()
    d_road = haversine_km(lat, lon, sv[None, :, 0], sv[None, :, 1])
    road = (sv[None, :, 2] * np.exp(-d_road / 1.5)).sum(1)
    iz = np.array([(z[1], z[2]) for z in C.INDUSTRIAL_ZONES])
    d_ind = haversine_km(lat, lon, iz[None, :, 0], iz[None, :, 1])
    ind = np.exp(-d_ind / 3.0).sum(1)
    dc = haversine_km(lat[:, 0], lon[:, 0], C.CITY_CENTER[0], C.CITY_CENTER[1])
    return pd.DataFrame({"road_exposure": road, "industry_exposure": ind, "dist_center_km": dc})


def traffic_profile() -> np.ndarray:
    """24-value hourly traffic intensity in [0.15, 1] from the congestion sample.

    Hours missing in the sample are linearly interpolated (circularly)."""
    c = pd.read_parquet(C.CONGESTION_SAMPLE)
    m = c.groupby("hour").delay.mean().reindex(range(24))
    m = pd.concat([m, m, m]).reset_index(drop=True).interpolate().iloc[24:48].to_numpy()
    m = (m - m.min()) / (m.max() - m.min())
    return 0.15 + 0.85 * m


_TP = None


def add_activity(df: pd.DataFrame) -> pd.DataFrame:
    """Adds the four activity proxies. Needs: hour, dow (0=Mon), month,
    road_exposure, industry_exposure, era5_wind_speed_100m_ms, precip_72h_m."""
    global _TP
    if _TP is None:
        _TP = traffic_profile()
    h = df["hour"].to_numpy()
    dow = df["dow"].to_numpy()
    month = df["month"].to_numpy()
    weekend = np.where(dow >= 5, 0.85, 1.0)
    df["traffic_activity"] = df["road_exposure"] * _TP[h] * weekend

    shift = np.where((h >= 6) & (h <= 22), 1.0, 0.7) * np.where(dow == 6, 0.6, 1.0)
    df["industry_activity"] = df["industry_exposure"] * shift

    dry = np.clip(1.0 - df["precip_72h_m"].to_numpy() / 0.01, 0.0, 1.0)   # 10 mm in 72 h => wet
    wind = np.clip(df["era5_wind_speed_100m_ms"].to_numpy() / 8.0, 0.0, 1.5)
    work = np.where((h >= 8) & (h <= 18), 1.0, 0.4)
    df["dust_activity"] = (df["road_exposure"] + 0.3) * (0.3 + wind) * dry * work

    season = np.select(
        [np.isin(month, [11, 12, 1, 2]), np.isin(month, [10, 3]), np.isin(month, [6, 7, 8, 9])],
        [1.0, 0.6, 0.05], 0.25)
    evening = np.where((h >= 18) | (h <= 1), 1.0, 0.4)
    df["burning_activity"] = season * evening
    return df


def add_derived_weather(df: pd.DataFrame) -> pd.DataFrame:
    u, v = df["era5_wind_u100_ms"], df["era5_wind_v100_ms"]
    if "era5_wind_speed_100m_ms" not in df:
        df["era5_wind_speed_100m_ms"] = np.sqrt(u ** 2 + v ** 2)
    t = df["era5_temp_2m_k"] - 273.15
    td = df["era5_dewpoint_2m_k"] - 273.15
    df["rel_humidity_pct"] = 100 * np.exp(17.625 * td / (243.04 + td)) / np.exp(17.625 * t / (243.04 + t))
    return df


def add_time(df: pd.DataFrame, ts_col: str = "timestamp") -> pd.DataFrame:
    ts = df[ts_col]
    df["hour"] = ts.dt.hour
    df["dow"] = ts.dt.dayofweek
    df["month"] = ts.dt.month
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    return df


def city_weather() -> pd.DataFrame:
    """City-mean hourly ERA5 (2021 → latest) used to drive grid inference."""
    m = pd.read_parquet(C.MASTER_PARQUET, columns=["timestamp"] + ERA5_COLS)
    w = m.groupby("timestamp")[ERA5_COLS].mean().sort_index()
    w = w[w.era5_temp_2m_k.notna()]
    w = w.asfreq("h").interpolate(limit=6)
    w["precip_72h_m"] = w["era5_total_precipitation_m"].rolling(72, min_periods=1).sum()
    w = add_derived_weather(w)
    w.index.name = "timestamp"
    return w.reset_index()
