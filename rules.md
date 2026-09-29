# UrbanAir Twin — System Rules & Non-Negotiable Constraints (`RULES.md`)

Source of truth: ENR-01 UrbanAir Twin Master Project Brief (Sections 4, 9.5, 10.1, 16) **plus** the approved `stitch_urbanair_twin_dashboard` UI export (design system: *Urban Environmental Intelligence*, see `README.md`). Where files conflict, this document wins on rules; `README.md` wins on visual/design specifics.

---

## 1. State Taxonomy & Labeling Rules

1. **State labeling is mandatory.** Every data point, map layer, KPI card, and forecast chart MUST display its state explicitly. Showing a modeled or scenario value beside an observed value without a state label is strictly prohibited.
2. **Four permissible states only:**

| State | Definition | UI Badge Text | Badge Style (per approved UI) |
|---|---|---|---|
| `OBSERVED` | Ground-truth measurement from a physical monitoring station (CPCB / OpenAQ). | `OBSERVED` | Neutral chip — `surface-container-high` background, `primary` (sage `#8FAF9A`) text. |
| `DERIVED` | Computed directly from observed/static data, no model involved (e.g. `wind_u`/`wind_v`). | `DERIVED` | Same neutral chip family, `secondary` (dusty blue-gray `#71868A`) text. |
| `MODELED_FORECAST` | Model prediction under current/expected-future inputs. | `FORECAST` / `MODELED FORECAST` | Neutral chip, `secondary` text; forecast line uses tertiary amber only when a threshold is exceeded. |
| `MODELED_SCENARIO` | Model re-prediction after a counterfactual intervention. | `SIMULATED` / `MODELED SCENARIO` | Distinct chip — `primary-container` background, `on-primary-container` text, always visually separated from `OBSERVED`. |

3. **Text badges are mandatory.** Color alone MUST NOT signal state — every chip carries its text label per the table above.
4. **Severity vs. state are two different badge systems and MUST NOT be merged:**
   - **State chips** (above) answer "where did this number come from?"
   - **Severity chips** answer "how bad is it?" using the design system's three-tone scale: Nominal (`#8FAF9A` sage), Advisory (`#C49A62` amber), Alert (`#B86F67` terracotta). Never use bright red/green/neon — the approved palette is deliberately desaturated.
   - A single metric (e.g. a hotspot row) may carry **both** a state chip and a severity chip, but they are visually distinct components.
5. **Visual rendering separation:**
   - Observed stations → solid circular markers with a pulse ring (per `README.md` "Sensor Status Node").
   - Modeled forecast surfaces → distinct heatmap/line layer, never the same style as observed markers.
   - Modeled scenarios → alternate/translucent layer (the Scenario Lab "Before/After" toggle), with a clear `BEFORE (Baseline)` / `AFTER (Simulated Scenario)` control.
6. **State object contract** — every value passed to the UI carries this shape:
   ```json
   {
     "value": 68.4,
     "state": "MODELED_SCENARIO",
     "timestamp": "2026-09-27T00:00:00+05:30",
     "source": "XGBoost",
     "model_version": "v1.0",
     "scenario_id": "traffic20_industry30_dust20"
   }
   ```

---

## 2. Scientific & Modeling Guardrails

1. **No hard-coded reductions.** Intervention outcomes MUST NOT apply a fixed percentage reduction to PM2.5. Every intervention MUST modify controllable input features and re-run the trained model.
2. **SHAP attribution boundaries.** SHAP values explain statistical model behavior. They MUST NOT be presented as direct physical source apportionment. The Hotspots screen's "Causal Attribution" panel MUST keep the disclaimer line: *"Contributing factors are estimated by the atmospheric twin to provide actionable municipal guidance."*
3. **Meteorological classification.** Wind, temperature, humidity, rainfall, and boundary layer height are atmospheric **modifiers**, not emission sources, and MUST NOT be scored inside the four attribution categories. In the UI they live in the "Current Atmospheric State" / "Environmental Influences" cards, never in the "What May Be Influencing Air Quality" driver list.
4. **Mandatory proxy identification.** Any `_proxy` field MUST be flagged as a proxy in schema, API response, and UI copy.
5. **Background attribution role.** `background_pm25` / `regional_transport_index` / `upwind_background` remain their own attribution category and are never redistributed into Traffic/Industry/Dust-Burning.
6. **No deterministic wind plumes.** Wind vectors MUST NOT be rendered as deterministic plume paths without a full physical dispersion model; the map's "Airflow Vectors" toggle shows direction/speed only.
7. **Negative SHAP values are not negative sources.** Only `max(φ_i, 0)` is summed into the driver percentages shown in "What May Be Influencing Air Quality"; signed feature-level detail stays in the detailed Cause Explorer view.

---

## 3. Data Engineering & Validation Rules

1. **Strict time-separated split.** Train on earlier history, validate/test on later. No shuffling across the time axis.
2. **Hourly temporal alignment**, locked to `Asia/Kolkata`.
3. **Quality control over silent imputation.** Missing/invalid values raise `PASSED` / `FLAGGED` / `OUTAGE`, never silently filled. Negative concentrations are rejected.
4. **Spatial boundary.** Pune, Maharashtra, bounding box `[18.40, 73.75, 18.65, 74.00]`, ~500m × 500m grid (UI copy: "Spatial Interpolation Canvas," 100m or 50m micro-resolution as shown per screen).
5. **No incomparable mixing** — normalize units before joining.

---

## 4. Canonical Parameter Coverage Rule

The pipeline MUST cover all 12 groups. No group may be silently dropped; undocumented substitution is prohibited.

1. Wind Direction (`wind_direction`, `wind_u`, `wind_v`, `wind_speed`)
2. Temperature (`temperature`, lags)
3. Humidity (`relative_humidity`, lags)
4. Rainfall (`rainfall_1h/6h/24h`, `recent_rain_flag`)
5. Construction / Road Dust (`construction_site_count`, `construction_activity_proxy`, `road_density`)
6. Traffic Volume & Emissions by vehicle type (`traffic_volume`, `heavy_vehicle_volume`, `two_wheeler_volume`, `average_speed`, `traffic_emission_proxy`)
7. Industrial Pollution (`industrial_facility_count`, `industrial_zone_density`, `industrial_activity_proxy`, `nearest_industry_distance`)
8. Open Burning (`burning_event_count`, `burning_activity_proxy`)
9. Traffic Density (`traffic_density`, `congestion_index`)
10. Building Density / Urban Housing (`building_density`, `built_up_fraction`, `population_density`)
11. Time of Day / Weekday–Weekend (`hour`, `day_of_week`, `is_weekend`, `is_holiday`, `rush_hour_flag`)
12. Regional / Background Pollution (`background_pm25`, `regional_transport_index`, `upwind_background`)

`boundary_layer_height` rides as an atmospheric-mixing modifier alongside these (Section 2, Rule 3), not a 13th group.

---

## 5. UI Implementation Rules (binding on `app/` / `frontend/`)

1. **Design tokens are law.** Colors, type scale, radii, and spacing MUST come from the `Urban Environmental Intelligence` token set in `README.md` — no ad hoc hex values, no neon/high-saturation colors, no pill-shaped buttons (see Shapes rule: max radius 6px on cards, 4px on controls).
2. **Four screens, fixed names and order:** `Overview` → `Hotspots` → `Forecast` → `Scenario Lab`, matching the top nav exactly as built in the Stitch export.
3. **No page scroll on desktop where the export doesn't have one.** The Overview screen is a fixed-height 12-column shell (map canvas + right telemetry dock); Hotspots/Forecast/Scenario Lab may scroll vertically within their content region.
4. **Typography roles are fixed:** `Manrope` for headlines/metrics, `Inter` for body/labels/tabular data, tabular numerals (`tnum`) mandatory on every numeric readout to prevent jitter on refresh.
5. **Material Symbols Outlined** is the only icon set; no mixed icon libraries.

---

## 6. Reproducibility & Auditability Rules

1. **Scenario audit trail.** Every scenario prediction returns a reproducible `scenario_id`, exact `model_version`, and transformation parameters. The Scenario Lab's "Session Run History" strip is the UI surface for this.
2. **Deterministic inputs.** Identical feature vectors always yield identical predictions.
3. **Illustrative-value rule.** Any example number in docs/mockups is marked "illustrative only."

---

## 7. Final Non-Negotiables (Master Brief §17.4)

- Never mix observed and modeled values without explicit labels.
- Never present SHAP/source percentages as measured physical emissions.
- Never hard-code intervention results as fixed PM2.5 reductions.
- Every intervention must modify model inputs and trigger a new prediction.
- Historical validation must use a time-separated held-out period.
- Future forecasts are labeled `FORECAST`; counterfactuals `SIMULATED` / `MODELED SCENARIO`.
- The three mandatory interventions are Traffic, Industry, and Dust (Burning optional).
- Every scenario is reproducible via `scenario_id` + `model_version`.
- All proxy variables are explicitly identified as proxies, everywhere.
- Meteorological variables are environmental modifiers unless separately justified as sources.
- The system is decision-support only — it does not automatically decide policy.
