"""Runtime twin: Observe / Explain / Predict / Simulate / Decide on one model."""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np
import pandas as pd
import xgboost as xgb

from . import config as C
from . import features as F

DEFAULT_AT = "2025-12-30 18:00"    # latest period with verified sensor observations
CELL_AREA_KM2 = (C.CELL_DEG_LAT * 111.32) * (C.CELL_DEG_LON * 111.32 * np.cos(np.radians(18.55)))
DISCLAIMER = ("Modeled estimate from a statistical model (XGBoost twin_v1.0). Source shares are "
              "model-attributed contributions (TreeSHAP), not causal proof. Activity inputs are labelled proxies.")


# ------------------------------------------------------------------ loading
@lru_cache(None)
def booster() -> xgb.Booster:
    b = xgb.Booster()
    b.load_model(C.ARTIFACTS / "twin_model.json")
    return b


@lru_cache(None)
def model_metrics() -> dict:
    return json.loads((C.ARTIFACTS / "twin_metrics.json").read_text())


@lru_cache(None)
def weather() -> pd.DataFrame:
    w = pd.read_parquet(C.CITY_WEATHER) if C.CITY_WEATHER.exists() else F.city_weather()
    return w.set_index("timestamp")


@lru_cache(None)
def stations() -> pd.DataFrame:
    st = pd.DataFrame([(k, v[0], v[1], v[2]) for k, v in C.STATIONS.items() if not k.startswith("LEGACY")],
                      columns=["station_id", "name", "lat", "lon"])
    return pd.concat([st, F.static_spatial(st.lat, st.lon)], axis=1)


@lru_cache(None)
def grid() -> pd.DataFrame:
    lats = np.arange(C.BBOX["lat_min"] + C.CELL_DEG_LAT / 2, C.BBOX["lat_max"], C.CELL_DEG_LAT)
    lons = np.arange(C.BBOX["lon_min"] + C.CELL_DEG_LON / 2, C.BBOX["lon_max"], C.CELL_DEG_LON)
    la, lo = np.meshgrid(lats, lons, indexing="ij")
    g = pd.DataFrame({"lat": la.ravel(), "lon": lo.ravel()})
    g = pd.concat([g, F.static_spatial(g.lat, g.lon)], axis=1)
    rng = model_metrics()["training_ranges"]
    inside = np.ones(len(g), bool)
    for f in ("road_exposure", "industry_exposure", "dist_center_km"):
        lo_, hi_ = rng[f]
        inside &= g[f].between(lo_, hi_).to_numpy()
    g["in_training_range"] = inside
    g["cell_id"] = np.arange(len(g))
    if C.POPULATION_GRID.exists():
        pop = pd.read_parquet(C.POPULATION_GRID)
        i = ((pop.lat - C.BBOX["lat_min"]) // C.CELL_DEG_LAT).astype(int)
        j = ((pop.lon - C.BBOX["lon_min"]) // C.CELL_DEG_LON).astype(int)
        nlon = len(lons)
        cell = i * nlon + j
        g["population"] = pop.groupby(cell).population.sum().reindex(g.cell_id).fillna(0).to_numpy()
    return g


@lru_cache(None)
def observations() -> pd.DataFrame:
    if C.SENSOR_OBS.exists():
        return pd.read_parquet(C.SENSOR_OBS)
    m = pd.read_parquet(C.MASTER_PARQUET, columns=["station_id", "timestamp", "pm2_5_ugm3", "pm25_source"])
    m = m[(m.pm25_source == "iitm_mpcb_sensor") & m.pm2_5_ugm3.between(0, 500)]
    return m[["station_id", "timestamp", "pm2_5_ugm3"]].sort_values("timestamp")


def parse_at(at: str | None) -> pd.Timestamp:
    t = pd.Timestamp(at or DEFAULT_AT)
    t = t.tz_localize(C.TZ) if t.tzinfo is None else t.tz_convert(C.TZ)
    return t.floor("h")


# ------------------------------------------------------------------ core model calls
def frame(points: pd.DataFrame, times) -> pd.DataFrame:
    """Cross-join points (with static features) and hourly timestamps; build features."""
    w = weather()
    times = pd.DatetimeIndex(times)
    missing = times.difference(w.index)
    if len(missing):
        raise ValueError(f"No ERA5 weather for {len(missing)} requested hour(s), e.g. {missing[0]}. "
                         f"Weather available {w.index.min()} → {w.index.max()}.")
    ww = w.loc[times].rename_axis("timestamp").reset_index()
    df = points.reset_index(drop=True).assign(_k=1).merge(ww.assign(_k=1), on="_k").drop(columns="_k")
    F.add_time(df)
    F.add_activity(df)
    return df


def scale_levers(df: pd.DataFrame, reductions: dict[str, float]) -> tuple[pd.DataFrame, list[str]]:
    df = df.copy()
    warnings = []
    rng = model_metrics()["training_ranges"]
    for lever, pct in reductions.items():
        if not pct:
            continue
        if pct < 0 or pct > C.MAX_REDUCTION_PCT:
            raise ValueError(f"{lever} reduction must be 0–{C.MAX_REDUCTION_PCT:.0f}% (got {pct}).")
        for f in C.LEVERS[lever]:
            df[f] = df[f] * (1 - pct / 100.0)
            below = float((df[f] < rng[f][0]).mean())
            if below > 0.05:
                warnings.append(f"{below:.0%} of scaled '{f}' values fall below the training range — "
                                f"treat this part of the {lever} result as extrapolation.")
    return df, warnings


def predict(df: pd.DataFrame) -> np.ndarray:
    return np.clip(booster().inplace_predict(df[C.FEATURES].to_numpy(np.float32)), 0, None)


def contribs(df: pd.DataFrame) -> pd.DataFrame:
    c = booster().predict(xgb.DMatrix(df[C.FEATURES], feature_names=C.FEATURES), pred_contribs=True)
    c = pd.DataFrame(c, columns=C.FEATURES + ["bias"])
    out = pd.DataFrame({g: c[fs].sum(axis=1) for g, fs in C.SOURCE_GROUPS.items()})
    out["base_value"] = c["bias"]
    return out


def shares(g: pd.DataFrame) -> dict:
    pos = g.drop(columns="base_value").clip(lower=0).mean()
    tot = float(pos.sum()) or 1.0
    return {k: round(float(v) / tot * 100, 1) for k, v in pos.items()}


# ------------------------------------------------------------------ OBSERVE
def station_snapshot(at: str | None):
    t = parse_at(at)
    st = stations()
    obs = observations()
    recent = obs[(obs.timestamp <= t) & (obs.timestamp > t - pd.Timedelta(hours=3))]
    last = recent.groupby("station_id").last()
    df = frame(st, [t])
    df["modeled"] = predict(df)
    out = []
    for _, r in df.iterrows():
        o = last.pm2_5_ugm3.get(r.station_id)
        out.append({"station_id": r.station_id, "name": r["name"], "lat": r.lat, "lon": r.lon,
                    "observed_pm25": None if o is None or pd.isna(o) else round(float(o), 1),
                    "observed_state": "OBSERVED" if o is not None and not pd.isna(o) else "NO_READING",
                    "modeled_pm25": round(float(r.modeled), 1)})
    return {"timestamp": t.isoformat(), "stations": out,
            "note": "Station coordinates are approximate; verify against CPCB/MPCB metadata."}


def observation_series(station: str, at: str | None, hours: int = 72):
    t = parse_at(at)
    o = observations()
    o = o[(o.station_id == station) & (o.timestamp <= t) & (o.timestamp > t - pd.Timedelta(hours=hours))]
    return {"station_id": station, "state": "OBSERVED",
            "series": [{"timestamp": ts.isoformat(), "pm25": round(float(v), 1)}
                       for ts, v in zip(o.timestamp, o.pm2_5_ugm3)]}


def grid_snapshot(at: str | None, hours: int = 1):
    t = parse_at(at)
    g = grid()
    times = pd.date_range(t, periods=hours, freq="h")
    df = frame(g, times)
    df["pm25"] = predict(df)
    cell = df.groupby("cell_id").pm25.mean()
    thr = C.HOTSPOT_THRESHOLD
    return {"timestamp": t.isoformat(), "hours": hours, "state": "MODELED",
            "cell_deg": [C.CELL_DEG_LAT, C.CELL_DEG_LON], "threshold": thr,
            "cells": [[round(a, 5), round(b, 5), round(float(v), 1), bool(ir)]
                      for a, b, v, ir in zip(g.lat, g.lon, cell.reindex(g.cell_id), g.in_training_range)],
            "cells_schema": ["lat", "lon", "pm25", "in_training_range"],
            "hotspot_area_km2": round(float((cell > thr).sum() * CELL_AREA_KM2), 2),
            "share_cells_in_training_range": round(float(g.in_training_range.mean()), 3)}


# ------------------------------------------------------------------ EXPLAIN
def attribution(lat: float, lon: float, at: str | None, hours: int = 1):
    t = parse_at(at)
    p = pd.DataFrame({"lat": [lat], "lon": [lon]})
    p = pd.concat([p, F.static_spatial(p.lat, p.lon)], axis=1)
    df = frame(p, pd.date_range(t, periods=hours, freq="h"))
    g = contribs(df)
    mean = g.mean()
    return {"lat": lat, "lon": lon, "timestamp": t.isoformat(), "hours": hours,
            "modeled_pm25": round(float(predict(df).mean()), 1),
            "base_value": round(float(mean.base_value), 1),
            "contribution_ugm3": {k: round(float(v), 2) for k, v in mean.drop("base_value").items()},
            "positive_share_pct": shares(g),
            "proxies": C.PROXY_NOTES, "state": "MODEL_ATTRIBUTED", "disclaimer": DISCLAIMER}


# ------------------------------------------------------------------ PREDICT
def forecast(station: str, at: str | None, horizon: int = 72):
    t = parse_at(at)
    st = stations()
    if station not in set(st.station_id):
        raise ValueError(f"Unknown station {station}")
    p = st[st.station_id == station]
    times = pd.date_range(t + pd.Timedelta(hours=1), periods=horizon, freq="h")
    df = frame(p, times)
    raw = predict(df)
    # residual correction from the 24 h before issue time
    past = pd.date_range(t - pd.Timedelta(hours=23), t, freq="h")
    hist = frame(p, past)
    hist["pred"] = predict(hist)
    o = observations()
    o = o[o.station_id == station].set_index("timestamp").pm2_5_ugm3
    hist["obs"] = o.reindex(hist.timestamp).to_numpy()
    r24 = (hist.obs - hist.pred).dropna()
    r24 = float(r24.mean()) if len(r24) >= 6 else 0.0
    rc = model_metrics()["station_forecast_by_horizon_test"]
    hs = np.array([int(k[:-1]) for k in rc])
    ks = np.array([v["k"] for v in rc.values()])
    k = np.interp(np.arange(1, horizon + 1), hs, ks)
    corrected = np.clip(raw + k * r24, 0, None)
    q = model_metrics()["residual_quantiles_validation"]
    actual = o.reindex(times)
    return {"station_id": station, "issued_at": t.isoformat(), "model_version": "twin_v1.0",
            "state": "MODELED_FORECAST", "residual_correction_ugm3": round(r24, 1),
            "weather_note": "Hindcast: ERA5 reanalysis stands in for a live weather-forecast feed.",
            "series": [{"timestamp": ts.isoformat(), "pm25": round(float(c), 1),
                        "lower": round(max(0.0, float(c + q["p10"])), 1), "upper": round(float(c + q["p90"]), 1),
                        "uncorrected": round(float(r), 1),
                        "observed": None if pd.isna(a) else round(float(a), 1)}
                       for ts, c, r, a in zip(times, corrected, raw, actual)],
            "skill_by_horizon": rc}


# ------------------------------------------------------------------ SIMULATE
def area_mask(g: pd.DataFrame, area: dict) -> np.ndarray:
    if not area or area.get("type", "city") == "city":
        return np.ones(len(g), bool)
    if area.get("station_id"):
        s = stations().set_index("station_id").loc[area["station_id"]]
        lat, lon = s.lat, s.lon
    else:
        lat, lon = float(area["lat"]), float(area["lon"])
    return F.haversine_km(g.lat.to_numpy(), g.lon.to_numpy(), lat, lon) <= float(area.get("radius_km", 2.5))


def _summary(df, cells, mask, g):
    cm = df.groupby("cell_id").pm25.mean().reindex(g.cell_id).to_numpy()
    sel = cm[mask]
    thr = C.HOTSPOT_THRESHOLD
    pop = None
    if "population" in g:
        pp = g.population.to_numpy()[mask]
        pop = int(pp[sel > thr].sum())
    traffic_share = shares(cells)["traffic"]
    return {"mean_pm25": round(float(sel.mean()), 2),
            "hotspot_area_km2": round(float((sel > thr).sum() * CELL_AREA_KM2), 2),
            "population_exposed_above_threshold": pop,
            "traffic_share_pct": traffic_share}, cm


SHAP_SAMPLE = 3000   # TreeSHAP rows per summary (paired sample, fixed seed) to keep the UI interactive


def _prepare(area: dict | None, at: str | None, hours: int):
    t = parse_at(at)
    g = grid()
    mask = area_mask(g, area or {})
    if not mask.any():
        raise ValueError("Selected area contains no grid cells.")
    base = frame(g, pd.date_range(t, periods=hours, freq="h"))
    base["pm25"] = predict(base)
    sub = np.where(base.cell_id.isin(g.cell_id[mask]).to_numpy())[0]
    if len(sub) > SHAP_SAMPLE:
        sub = np.random.default_rng(0).choice(sub, SHAP_SAMPLE, replace=False)
    b_sum, b_cells = _summary(base, contribs(base.iloc[sub]), mask, g)
    return {"t": t, "g": g, "mask": mask, "base": base, "sub": sub, "b_sum": b_sum, "b_cells": b_cells}


def run_scenario(reductions: dict[str, float], area: dict | None, at: str | None, hours: int = 4,
                 with_cells: bool = True, prep: dict | None = None):
    P = prep or _prepare(area, at, hours)
    t, g, mask, base, b_sum, b_cells = P["t"], P["g"], P["mask"], P["base"], P["b_sum"], P["b_cells"]
    scen, warns = scale_levers(base, reductions)
    scen["pm25"] = predict(scen)
    s_sum, s_cells = _summary(scen, contribs(scen.iloc[P["sub"]]), mask, g)
    ext = 1 - float(g.in_training_range.to_numpy()[mask].mean())
    if ext > 0.25:
        warns.append(f"{ext:.0%} of cells in this area have road/industry/distance features outside the range "
                     f"seen at monitoring stations — results there are extrapolated.")
    change = {k: (None if b_sum[k] is None else round(s_sum[k] - b_sum[k], 2)) for k in b_sum}
    out = {"state": "MODELED_SCENARIO", "model_version": "twin_v1.0", "window_start": t.isoformat(),
           "hours": hours, "area": area or {"type": "city"}, "reductions_pct": reductions,
           "threshold_ugm3": C.HOTSPOT_THRESHOLD, "n_cells": int(mask.sum()),
           "baseline": b_sum, "scenario": s_sum, "change": change,
           "percent_change_mean_pm25": round(change["mean_pm25"] / b_sum["mean_pm25"] * 100, 2),
           "warnings": warns, "disclaimer": DISCLAIMER,
           "population_note": None if "population" in g else
               "No population raster loaded (add pune_population_grid.parquet, e.g. from WorldPop) — exposure not computed."}
    if with_cells:
        idx = np.where(mask)[0]
        out["cells_schema"] = ["lat", "lon", "baseline", "scenario"]
        out["cells"] = [[round(g.lat.iat[i], 5), round(g.lon.iat[i], 5), round(float(b_cells[i]), 1),
                         round(float(s_cells[i]), 1)] for i in idx]
    return out


# ------------------------------------------------------------------ DECIDE
def decide(pct: float, area: dict | None, at: str | None, hours: int = 4):
    rows = []
    prep = _prepare(area, at, hours)
    for lever in C.LEVERS:
        r = run_scenario({lever: pct}, area, at, hours, with_cells=False, prep=prep)
        rows.append({"lever": lever, "reduction_pct": pct, "baseline": r["baseline"], "scenario": r["scenario"],
                     "change": r["change"], "percent_change_mean_pm25": r["percent_change_mean_pm25"],
                     "warnings": r["warnings"]})
    rows.sort(key=lambda r: (r["change"]["mean_pm25"], r["change"]["hotspot_area_km2"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return {"state": "MODELED_SCENARIO", "window_start": parse_at(at).isoformat(), "hours": hours,
            "area": area or {"type": "city"}, "ranking": rows, "disclaimer": DISCLAIMER,
            "note": "Each lever is applied alone at the same intensity; ranked by change in mean PM2.5, then hotspot area."}
