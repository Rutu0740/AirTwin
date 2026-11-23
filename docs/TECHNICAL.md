# UrbanAir Twin: Technical Documentation

Model version `twin_v1.0` (run log entry RUN-004). This document covers the system architecture, tech stack, model, APIs, data integrations, validation results and known limits.

---

## 1. System architecture

```
┌──────────────────────────── DATA LAYER ────────────────────────────┐
│ CPCB / MPCB / IITM stations   ERA5 reanalysis   ARAI traffic survey │
│ (hourly PM2.5, 2021–2025)     (hourly weather)  + congestion sample │
│ ARAI / MPCB emission inventory                MIDC industrial zones │
└───────────────┬────────────────────────────────────────────────────┘
                │  pipeline (urbanair_twin_pipeline.py): timezone fix,
                │  station matching, QC, hourly alignment → Parquet
┌───────────────▼──────────────── FEATURE LAYER (twin/features.py) ───┐
│ static per location: road exposure, industry exposure, distance to  │
│   centre  →  computable for any (lat, lon): stations AND grid cells  │
│ time-varying: ERA5 met stack, 72 h rain, humidity, season           │
│ activity proxies: traffic · industry · dust · burning (labelled)    │
└───────────────┬────────────────────────────────────────────────────┘
┌───────────────▼──────────────── MODEL LAYER (twin/train.py) ────────┐
│ ONE XGBoost regressor (monotone +1 on the four activity proxies)    │
│   ├─ Predict  : hourly PM2.5 + station residual correction + band   │
│   ├─ Explain  : TreeSHAP contributions, summed per source group     │
│   └─ Simulate : scale a lever's proxy → re-predict → diff baseline  │
└───────────────┬────────────────────────────────────────────────────┘
┌───────────────▼──────────────── SERVICE + API (twin/service.py, main.py)
│ 500 m grid (3,819 cells) · area masks · hotspot area · decide ranking│
│ FastAPI + Pydantic: 11 typed JSON endpoints, OpenAPI docs at /docs   │
└───────────────┬────────────────────────────────────────────────────┘
┌───────────────▼──────────────── PRESENTATION (*.html, twin-ui.js) ──┐
│ Overview · Hotspots · Forecast · Scenario Lab (Tailwind + Leaflet)  │
│ smooth heat map: value-field bilinear upsampling + CPCB isolines    │
└────────────────────────────────────────────────────────────────────┘
```

**Design principle: one model, three jobs.** Forecasting, attribution and simulation all use the same trained booster. That keeps the outputs consistent with each other: the source that the Explain step blames is the same lever the Simulate step moves.

**Why the model has no PM2.5 lags.** The earlier RUN-003 model scored R² 0.85, but it was about 75% driven by its own lagged PM2.5. A model like that explains pollution with pollution, which makes attribution meaningless and makes grid cells with no monitor impossible to score. The twin instead uses only inputs that exist for any location and hour. Station forecasts recover short-term skill through a residual correction (§3.2).

## 2. Tech stack

| Layer | Technology | Why |
|---|---|---|
| Model | **XGBoost 3.2** (hist trees, monotone constraints) | Best fit for tabular geospatial data; trains in seconds; exact TreeSHAP |
| Explainability | **TreeSHAP** via XGBoost `pred_contribs` | Exact per-prediction contributions, fast enough for interactive maps |
| Data | **pandas 3, PyArrow, Parquet (zstd)** | Columnar, fast, no database server needed |
| API | **FastAPI 0.115 + Pydantic 2** | Typed request validation (e.g. levers capped at 0–50%), auto OpenAPI docs |
| Server | **Uvicorn** | ASGI server |
| Front end | **HTML + Tailwind CSS**, vanilla JS | Faithful to the approved design system, no build step |
| Maps | **Leaflet 1.9.4 + OpenStreetMap tiles** | Lightweight; heat map rendered client-side on a canvas |
| Fonts / icons | Manrope, Inter, Material Symbols | Design-system type scale |

Upgrade path for a pilot: PostGIS for spatial queries, MapLibre GL for vector tiles, and a scheduled retraining job.

## 3. The model

### 3.1 Features (`twin/config.py → FEATURES`)

| Group | Features | Source |
|---|---|---|
| Traffic | `traffic_activity`, `road_exposure` | Road exposure = distance-decayed sum over the 15 ARAI 2021 traffic-count corridors (Major 1.0 / Intermediate 0.6 / Minor 0.3, 1.5 km decay) × hourly congestion profile × weekend factor 0.85 |
| Industry | `industry_activity`, `industry_exposure` | Distance-decayed exposure to 5 MIDC centroids (3 km decay) × shift profile (night 0.7, Sunday 0.6) |
| Dust | `dust_activity` | Road exposure × wind speed × dryness (no rain in prior 72 h) × construction hours |
| Burning | `burning_activity` | Seasonal (Nov–Feb peak, monsoon minimum) × evening profile |
| Meteorology | 12 ERA5 variables + wind speed, 72 h rain, relative humidity | Copernicus ERA5 |
| Seasonal / background | month sin/cos, distance to centre | Calendar, geometry |

The four activity inputs are **proxies** and are labelled as such in the UI, in `/api/meta` and in every attribution response. Monotone (+1) constraints guarantee that lowering a proxy can never raise modeled PM2.5.

### 3.2 Training and forecasting

- **Target:** verified IITM/MPCB sensor PM2.5, 2024–2025 (139,633 station-hours). The 2021–23 legacy portal values are excluded, because they run about 2.5× the sensor readings at the same stations and are only an assumed PM2.5.
- **Chronological split:** train 2024; validate Jan–Mar 2025; test Apr–Dec 2025. Early stopping on validation MAE (139 trees). The deployed model is refit on all verified data with the same tree count.
- **Station forecast:** `forecast(t+h) = twin(t+h) + k_h × mean(observed − twin over the 24 h before issue)`. The factor k_h is tuned on the validation period (0.90 at 6 h, falling to 0.75 at 72 h). The 10–90% band comes from validation residual quantiles.

### 3.3 Attribution

For each prediction, the TreeSHAP contributions of the features in a group are summed, giving µg/m³ relative to the model's base value. Shares count only positive contributions. Interactive responses cap SHAP at 3,000 sampled rows (paired, fixed seed) to stay under a few seconds.

### 3.4 Scenario simulation and decision

1. Build the feature frame for every grid cell in the area × each hour in the window.
2. Scale the chosen proxy by (1 − reduction%). The API rejects anything outside 0–50%, the policy-lever range in the emission inventory.
3. Re-predict, then diff against the baseline per cell.
4. Outputs: mean PM2.5 in the area, hotspot area above the CPCB 24-h standard (60 µg/m³, cells of 0.25 km²), population exposed (once a population raster is added), and traffic share.
5. **Warnings** appear when more than 5% of scaled values fall below the training range, or when more than 25% of the area's cells have spatial features outside the range seen at monitoring stations.
6. **Decide** runs each lever alone at the same strength and ranks them by change in mean PM2.5, then by change in hotspot area.

## 4. API reference

Base URL `http://localhost:8000`. Interactive docs at `/docs`. Times are `YYYY-MM-DD HH:00` in IST; the default is `2025-12-30 18:00`.

| Method | Endpoint | Purpose | Key parameters |
|---|---|---|---|
| GET | `/api/meta` | Model version, levers, proxy notes, threshold, weather range | none |
| GET | `/api/validation` | Full validation results (metrics JSON) | none |
| GET | `/api/stations` | Latest observed reading + modeled value per station | `at` |
| GET | `/api/observations` | Observed hourly series for a station | `station`, `at`, `hours` (≤ 336) |
| GET | `/api/grid` | Modeled PM2.5 for all 3,819 cells; hotspot area | `at`, `hours` (1–24) |
| GET | `/api/layers` | Traffic corridors, industrial zones | none |
| GET | `/api/attribution` | Grouped TreeSHAP for a point or station | `lat`+`lon` or `station`, `at`, `hours` |
| GET | `/api/forecast` | Hourly forecast, band, observed overlay, skill by horizon | `station`, `at`, `horizon` (1–72) |
| POST | `/api/scenario` | Scenario summary (baseline / scenario / change) | body below |
| POST | `/api/scenario/spatial` | Same, plus per-cell baseline and scenario values | body below |
| POST | `/api/decide` | Rank the four levers at one strength | `reduction_pct`, `area`, `at`, `hours` |

Scenario request body:

```json
{
  "traffic_reduction": 20, "industrial_control": 0, "dust_control": 0, "burning_reduction": 0,
  "area": {"type": "station", "station_id": "site_5409", "radius_km": 3},
  "at": "2025-12-30 18:00", "hours": 4
}
```

`area.type` is `city`, `station` (with `station_id`) or `point` (with `lat`/`lon`). Response excerpt:

```json
{ "state": "MODELED_SCENARIO", "model_version": "twin_v1.0", "n_cells": 115,
  "baseline": {"mean_pm25": 56.88, "hotspot_area_km2": 7.03, "population_exposed_above_threshold": null, "traffic_share_pct": 12.5},
  "scenario": {"mean_pm25": 56.48, "hotspot_area_km2": 7.03, "population_exposed_above_threshold": null, "traffic_share_pct": 11.5},
  "change":   {"mean_pm25": -0.4, "hotspot_area_km2": 0.0, "population_exposed_above_threshold": null, "traffic_share_pct": -1.0},
  "warnings": ["7% of scaled 'traffic_activity' values fall below the training range — ..."],
  "disclaimer": "Modeled estimate from a statistical model ..." }
```

Errors return HTTP 400 (out-of-range input, unknown station, no weather for that hour) or 422 (schema validation), each with a readable `detail`.

## 5. Data integrations

| Source | Provides | Used for | How it's integrated |
|---|---|---|---|
| CPCB / MPCB / IITM CAAQMS (15 stations) | Hourly PM2.5 and co-pollutants | Training target, observed layer, forecast verification | Fused by the pipeline; sensor rows bundled in `data/sensor_observations.parquet` |
| Copernicus ERA5 | Wind, temperature, dewpoint, boundary-layer height, fluxes, precipitation | Weather features; city-mean drives the grid | `data/city_weather_era5.parquet` (hourly, 2021 → Sep 2026) |
| ARAI 2021 traffic survey | 15 traffic-count corridors with road class | Road exposure, traffic proxy, corridor layer | `data/pune_traffic_survey_stations.parquet` |
| Congestion sample | Mean delay by hour | Diurnal traffic profile | `data/pune_traffic_congestion_toy_sample.parquet` |
| ARAI / MPCB CAP emission inventory (2021) | Sector PM2.5 shares and loads | Lever ranges (0–50%), sector grouping | Reference tables |
| OpenStreetMap | Basemap | Map tiles | Leaflet tile layer |
| CPCB NAAQS / National AQI | 60 µg/m³ 24-h standard, PM2.5 breakpoints | Hotspot threshold, colour scale | Constants in config and UI |

The pipeline (`datasets for training/urbanair_twin_pipeline.py`) documents its data fixes. Station timestamps labelled "+0000" are actually IST, as solar radiation and temperature peaks prove. Ambiguous legacy stations are kept separate rather than merged by guesswork.

## 6. Front end

- `twin-ui.js` is shared by all screens. It holds the API client, Leaflet map factory, colour ramps anchored on the CPCB breakpoints, state badges and the **smooth heat-map renderer**.
- **Heat map:** the cell values are bilinearly upsampled 10× on a canvas. The values are interpolated, not the colours, so blends never turn muddy. Pixels are coloured on a continuous ramp with isolines at 30/60/90/120/250, the raster edge is feathered, and extrapolated cells fade. Hovering and clicking resolve to the nearest underlying cell.
- Every output carries a state badge (`OBSERVED`, `MODELED`, `MODELED_FORECAST`, `MODELED_SCENARIO`, `MODEL_ATTRIBUTED`).

## 7. Validation results

All results are measured on held-out data, from `artifacts/twin_metrics.json`. Nothing is estimated or invented.

**Hour-by-hour accuracy (test, Apr–Dec 2025, n = 52,634):** MAE 16.4 · RMSE 27.3 · R² 0.43

**Baselines on identical test rows (n = 47,871):**

| Method | MAE (µg/m³) | R² |
|---|---|---|
| Twin model (no lags) | 16.4 | 0.44 |
| Persistence, 24 h | 11.2 | 0.63 |
| Persistence, 72 h | 14.1 | 0.55 |
| Nearest other station, same hour | 20.4 | 0.18 |

**Station forecast with residual correction, by horizon (MAE, µg/m³):**

| Horizon | Twin + correction | Persistence |
|---|---|---|
| 6 h | **10.0** | 13.2 |
| 24 h | 11.3 | **10.7** |
| 48 h | **12.4** | 12.8 |
| 72 h | **12.9** | 14.0 |

**Places with no monitor (leave one station out, 11 stations):** mean MAE 21.5 with the station held out, vs 24.8 using the nearest other station. The twin wins at 8 of 11 stations.

**Attribution sanity checks:** traffic contribution is higher at rush hour (+0.3) than at night (−0.9 µg/m³); burning is higher in winter (+6.0) than in the monsoon (−5.0); dust is higher in dry spells (+0.7) than wet (−0.3).

**Natural experiment, weekends:** observed weekend − weekday difference −1.26 µg/m³; modeled +0.04. The model does not yet reproduce the weekend dip. This is a known limit.

## 8. Limits and roadmap

| Limit | Mitigation now | Next step |
|---|---|---|
| Activity inputs are proxies | Labelled everywhere; monotone constraints; range warnings | Data-sharing with Pune Traffic Police (counts) and PMC; FIRMS fire detections |
| Small scenario response (traffic −20% ≈ −0.4 µg/m³ locally) | Reported as modeled, not tuned | Real traffic counts would let the model separate traffic from the weather-driven daily cycle |
| 12 stations; half the grid outside the training range | Extrapolated cells faded and flagged | Add Sentinel-5P and low-cost sensors as spatial signals |
| Approximate coordinates | Flagged in config and API | Verify against CPCB station metadata |
| Population exposure not computed | API returns `null` with a note | Add WorldPop 100 m raster (`pune_population_grid.parquet`) |
| Hindcast weather | Labelled "hindcast" | Connect a live NWP / IMD forecast feed |
| Model drift | Chronological validation | Scheduled retraining with rolling validation |

Roadmap: (1) a pilot with one ward and live data feeds; (2) a population raster plus satellite fusion; (3) other cities, which needs new data layers and retraining, not a redesign.
