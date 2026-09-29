# UrbanAir Twin — Build Memory & Progress Tracker (`MEMORY.md`)

Living document: build milestones, architectural decision records (ADRs), state updates, model run logs, and active assumptions. Update at the end of every session — never delete history, only append.

---

## 1. Project Metadata & Baseline Context

- **Primary geography**: Pune, Maharashtra, India (`Asia/Kolkata`)
- **Bounding box**: `[18.40, 73.75, 18.65, 74.00]`
- **Primary pollutant target**: PM2.5 (µg/m³); PM10/NO2 optional
- **Spatial resolution**: 500m × 500m grid + point monitoring stations
- **Product arc**: OBSERVE → EXPLAIN → PREDICT → SIMULATE → VALIDATE
- **UI reference**: `stitch_urbanair_twin_dashboard` export, theme "Urban Environmental Intelligence" (see `README.md`)
- **Current phase**: Phase 1 (OBSERVE) — see `PHASES.md`

---

## 2. Architectural Decision Records (ADR Log)

| ADR | Topic | Decision | Justification | Date | Status |
|---|---|---|---|---|---|
| ADR-01 | Backend/data stack | FastAPI (backend) + DuckDB/Parquet (analytics) | Zero-config analytical SQL directly on Parquet, minimal latency, native Python ML/GIS support. | 2026-09-27 | Approved |
| ADR-02 | ML model | XGBoost Regressor | Best tabular performance for this feature mix; inference <10ms, fast enough for interactive scenario re-prediction. | 2026-09-27 | Approved |
| ADR-03 | Explainability | TreeSHAP (`shap`) | Exact, fast SHAP values for tree models; supports the 4-category source grouping required by FR-02. | 2026-09-27 | Approved |
| ADR-04 | Spatial indexing | 500m × 500m bounding grid | Best trade-off between local resolution and spatial-feature compute cost for a hackathon-scale demo. | 2026-09-27 | Approved |
| ADR-05 | Data strategy | Live sources where available (OpenAQ/CPCB, ERA5, OSM); documented synthetic/proxy generators otherwise | Guarantees the pipeline runs end-to-end without live API keys. | 2026-09-27 | Approved |
| **ADR-06** | **Frontend stack** | **Static HTML + Tailwind CDN + Material Symbols Outlined + Google Fonts (Inter, Manrope), served as 4 routed screens; Streamlit dropped for the presentation layer** | The approved UI (`stitch_urbanair_twin_dashboard`) was delivered as hand-built Tailwind HTML with a custom design-token theme that Streamlit's component model cannot reproduce faithfully. FastAPI now serves pure JSON (the 4 contracts in `REQUIREMENTS.md` §4) and the frontend consumes it via `fetch`. PyDeck is replaced by a lightweight JS map layer (see `README.md` "Map Implementation Note"). | 2026-09-28 | Approved |
| ADR-07 | Design system | Adopt "Urban Environmental Intelligence" token set (not the alternate cyan "UrbanAir Twin" theme also present in the export) | This is the theme actually used across all 4 delivered screens (`#121413` base, `#adceb8` sage primary, Manrope/Inter type). The cyan theme was a discarded alternate and must not be mixed in. | 2026-09-28 | Approved |

---

## 3. Model Performance & Validation Log

| Run ID | Model Version | Train Period | Held-Out Test Period | MAE (µg/m³) | RMSE (µg/m³) | R² | Notes |
|---|---|---|---|---|---|---|---|
| RUN-001 | xgb_v0.1 | 2020–2024 | 2025–2026 | TBD | TBD | TBD | Baseline: lags + weather only. |
| RUN-002 | xgb_v1.0 | 2020–2024 | 2025–2026 | 7.95 | 9.94 | 0.670 | Full 12-group parameter set + boundary layer height. 131,472 training samples. |
| **RUN-003** | **xgb_v2.0** | **2021-01-02 → 2023-12-31** | **Val: 2024 (n=67,467) / Test: 2025 (n=72,202)** | **8.89** | **13.88** | **0.850** | First run on real fused data (`pune_xgboost_randomforest_training.csv`, 258,144 rows, chronological `split` column already enforced upstream). Train R²=0.902, Val R²=0.631, Test R²=0.850 — val/test gap likely reflects 2024 being an anomalous year in the raw sensor mix rather than leakage (split boundaries verified strictly chronological, no shuffling). Features: PM2.5 autoregressive lags/rolling stats (1h–24h) + full ERA5 met stack + cyclic time encodings + `station_id` (categorical) + `pm25_verified_sensor`/`pm25_legacy_assumed` flags. 600 trees requested, early-stopped at iteration 113 on validation MAE. Model saved as `xgb_pm25_model_v2.joblib`. |

*Log the next run as `RUN-004` — never edit a prior row.*

**RUN-003 feature importance (top 6, of 45 features):** `pm25_lag_1h` (51.4%), `pm25_roll_mean_3h` (21.2%), `pm25_roll_mean_24h` (2.5%), `pm25_lag_24h` (1.7%), `pm25_lag_3h` (1.2%), `pm25_roll_mean_6h` (1.2%). **Finding:** the model is currently ~75% driven by its own autoregressive PM2.5 history and ERA5 weather (`boundary_layer_height`, latent/sensible heat flux each ~1%); **no traffic/industry/dust/burning activity feature is present in the hourly training matrix at all.** This is a real gap, not a modeling choice — see §4a.

---

## 4. Feature Registry & Active Proxies

| Feature | Canonical Group | Data Source | Type / Unit | Proxy? | Status |
|---|---|---|---|---|---|
| `pm25_observed` | Target | CPCB / OpenAQ | float (µg/m³) | No | Active |
| `wind_direction`, `wind_speed`, `wind_u`, `wind_v` | 1. Wind Direction | ERA5 | float | No | Active |
| `temperature` | 2. Temperature | ERA5 | float (°C) | No | Active |
| `relative_humidity` | 3. Humidity | ERA5 | float (%) | No | Active |
| `rainfall_1h/6h/24h` | 4. Rainfall | ERA5 | float (mm) | No | Active |
| `construction_activity_proxy` | 5. Construction/Dust | Land use / OSM | float (0–1) | **Yes** | Active |
| `traffic_emission_proxy` | 6. Traffic Volume & Emissions | OSM / traffic model | float (0–1) | **Yes** | Active |
| `industrial_activity_proxy` | 7. Industrial Pollution | MPCB / OSM industrial zones | float (0–1) | **Yes** | Active |
| `burning_activity_proxy` | 8. Open Burning | Remote sensing / spatial events | float (0–1) | **Yes** | Active |
| `traffic_density`, `congestion_index` | 9. Traffic Density | Traffic model / OSM | float | Partial | Active |
| `building_density`, `population_density` | 10. Building Density / Urban Housing | OSM / census proxies | float | Partial | Active |
| `hour`, `day_of_week`, `is_weekend` | 11. Time of Day / Weekday-Weekend | Derived from `timestamp` | int / bool | No (derived) | Active |
| `background_pm25`, `regional_transport_index` | 12. Regional/Background Pollution | Upwind station minimums / regional indices | float | Partial | Active |
| `boundary_layer_height` | Met. modifier | ERA5 | float (m) | No | Active |

**Real-data status (as of RUN-003):** columns 1–4 and the met modifier are populated (ERA5, full stack, 0.01% null in the raw master table). Columns 5–9 and 12 (Traffic, Industry, Dust/Burning, Regional Background as *hourly, model-visible* features) are **not yet present** in the ML-ready matrix — see §4a. `pm2_5_ugm3` itself is real but mixed-provenance: `pm25_verified_sensor=1` for 2024–25 IITM/MPCB telemetry, `pm25_legacy_assumed=1` for pre-2024 legacy-portal values whose PM2.5 unit is a documented assumption, not a verified fact (pipeline docstring §3). Both flags are retained as model features so the model can learn provenance-conditional behavior, and must stay visible in the UI per `RULES.md` §1.

**Dataset provenance (delivered 2026-09-28):**

| File | Rows | Role |
|---|---|---|
| `pune_master_dataset_2021_2026.parquet` | 752,490 | Full fused hourly station panel, all raw + met columns, before ML feature selection. |
| `pune_ml_ready.csv` | — | Intermediate cleaned panel with outlier flags, pre-lag/rolling features. |
| `pune_xgboost_randomforest_training.csv` | 258,144 | Final ML matrix used for RUN-003 — pre-split chronologically (`train`/`validation`/`test`), lags + rolling stats + ERA5 + cyclic time. |
| `pune_emission_inventory_baseline_2021.parquet` | 13 | Real ARAI/MPCB sector-level annual PM2.5/PM10/SO2/NOx/CO shares — static, not yet hourly. |
| `pune_emission_inventory_features.parquet` | 100 | Feature-level breakout of the above, with `state_tag: OBSERVED` and `target_policy_lever` per row — directly reusable for Scenario Lab intervention mapping. |
| `pune_traffic_congestion_toy_sample.parquet` | 437 | Toy hour × day-of-week congestion by road (`FREE`/... delay) — **toy sample, not survey data**; usable for a diurnal shape, not absolute traffic volume. |
| `pune_traffic_survey_stations.parquet` | 37 | Real ARAI-surveyed station locations/metadata (Feb–Mar 2021 counts) — no hourly counts included here, location/metadata only. |
| `pune_master_dataset_diagnostic_summary.txt` | — | Null-rate + station-coverage diagnostic confirming the numbers above (752,490 rows, 15 stations, 2021-01-01→2026-09-22). |

---

## 4a. FR-02 Blocker: Source-Attribution Features Are Missing From the Training Matrix

Confirmed by inspecting `urbanair_twin_pipeline.py` and the actual columns of `pune_xgboost_randomforest_training.csv` / `pune_ml_ready.csv`: per the pipeline's own documented guardrail ("PROXY VARIABLES," pipeline docstring §4), **no genuine continuous hourly traffic/industrial/dust activity sensor feed exists in the raw inputs**, and the pipeline deliberately did *not* fabricate one. Instead, real annual sector shares live only as a **static, non-hourly lookup table** — `pune_emission_inventory_baseline_2021.parquet` — which never got joined into the ML-ready hourly matrix.

**Consequence:** RUN-003's SHAP values (once computed, Phase 3) will attribute almost everything to autoregression + weather, because Traffic/Industry/Dust/Burning simply aren't columns the model can see. This will make Phase 3's "4-category driver bars" degenerate. **This must be fixed before Phase 3 is meaningful** — see Phase 3 gate note in `PHASES.md`.

**Independent reference (not yet wired into the model) — 2021 Pune district PM2.5 emission inventory, ARAI/MPCB CAP India Report:**

| Sector | PM2.5 share | Maps to attribution category |
|---|---|---|
| Transport | 20.14% | Traffic |
| Industries | 18.64% | Industry |
| Re-suspended Road Dust | 18.61% | Dust/Burning |
| Construction Activities | 11.90% | Dust/Burning |
| Agricultural Residue Burning | 9.79% | Dust/Burning |
| Residential | 6.38% | *(no clean bucket — see below)* |
| Open Waste Burning | 6.35% | Dust/Burning |
| Non-Industrial Diesel Generators | 3.96% | Industry (informal) |
| Brick Kilns | 2.25% | Industry |
| Hotels/Restaurants/Bakeries | 1.59% | *(no clean bucket)* |
| Crematoria | 0.38% | *(no clean bucket)* |
| Aircraft | ~0.00% | *(negligible)* |

Rolled into the 4 FR-02 categories: **Traffic ≈ 20%, Industry ≈ 25%, Dust/Burning ≈ 47%, Unclassified (Residential/Hospitality/Crematoria) ≈ 8%.** This is a real, citable, physically-measured apportionment (not SHAP-derived) and should be used two ways: (1) as engineered static/seasonal features once disaggregated to hourly resolution, and (2) as a sanity-check ceiling/floor for whatever SHAP produces once traffic/industry/dust features exist — if SHAP attribution lands wildly outside these ranges, that's a signal to investigate, not to force-match.

**Recommended fix (does not violate the zero-fabrication guardrail):** disaggregate the static annual sector shares into hourly features using *real* available temporal patterns already in hand — `pune_traffic_congestion_toy_sample.parquet` (hour × day-of-week congestion by road) and `pune_traffic_survey_stations.parquet` (37 real ARAI-surveyed count stations with coordinates) for the traffic profile; documented rush-hour/weekday curves for construction/industry. This produces a *documented, proxy-flagged* hourly activity feature — not a fabricated sensor reading — consistent with `RULES.md` §2.4.

---

## 5. Active Assumptions & System Disclaimers

1. Traffic volumes rely on road-class density and hourly congestion proxies due to raw sensor sparsity in Pune.
2. Background PM2.5 is modeled using upwind station minimums and regional transport indices, not direct background sensors.
3. `boundary_layer_height` is the primary vertical-mixing proxy and is treated strictly as a dispersion modifier, never a source.
4. All `_proxy` fields are flagged in the feature registry and the UI per `RULES.md` §2.4.
5. SHAP-based attribution percentages are model-attributed contributions, not measured physical source apportionment (`RULES.md` §2.2).
6. The Stitch export's illustrative numbers (e.g. "118 µg/m³," "132 µg/m³ peak," "41% Traffic") are UI mockup placeholders only and must be replaced by live API values before demo.

---

## 6. Session Log

| Date | Phase Worked | Summary | Blockers |
|---|---|---|---|
| 2026-09-27 | Phase 1 (OBSERVE) | Spec files redesigned and aligned to Master Project Brief; ADR log established. | Live data source credentials not yet confirmed — pipeline defaults to synthetic generators. |
| 2026-09-28 | Phase 5 (UI) | Ingested `stitch_urbanair_twin_dashboard` export; identified actual-use design theme ("Urban Environmental Intelligence"); recorded ADR-06/ADR-07; rewrote `REQUIREMENTS.md` §3 and `PHASES.md` Phase 5 to match the 4 delivered screens; authored `README.md` as the canonical UI build guide. | None — pending: wire the 4 static screens to live FastAPI endpoints instead of the Stitch export's placeholder numbers/images. |
| 2026-09-28 | Phase 2 (PREDICT) | Received real fused datasets (`pune_master_dataset_2021_2026.parquet`, `pune_ml_ready.csv`, `pune_xgboost_randomforest_training.csv`, emission inventory + traffic survey tables) plus the documented `urbanair_twin_pipeline.py`. Trained XGBoost on the pre-split chronological `train`/`validation`/`test` data — logged as RUN-003 (§3). Verified the dataset's own honesty guardrails (no fabricated hourly proxies; legacy PM2.5 explicitly flagged `legacy_portal_assumed_pm25`). Discovered and documented the FR-02 blocker in §4a. | **Blocking Phase 3**: traffic/industry/dust/burning activity features are not present in the hourly training matrix — must engineer them from the traffic survey + congestion tables before SHAP attribution is meaningful. |
