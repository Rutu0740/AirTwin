# UrbanAir Twin — System Requirements Specification (`REQUIREMENTS.md`)

Enumerates functional, data, modeling, UI, and contractual requirements for the UrbanAir Twin prototype, aligned to the ENR-01 Master Project Brief **and** the approved `stitch_urbanair_twin_dashboard` UI export. Cross-reference: `RULES.md` for constraints, `PHASES.md` for delivery order, `README.md` for full UI/design spec.

---

## 1. Functional Requirements Matrix

| ID | Category | Requirement | Success Criteria |
|---|---|---|---|
| FR-01 | Forecast | Forecast hourly PM2.5 for Pune. | Continuous 1h–72h predictions with upper/lower bounds; shown on the **Forecast** screen's 6-hour+3-day micro-trajectory chart. |
| FR-02 | Attribution | Attribute pollution across ≥3 source categories. | Traffic / Industry / Dust-Burning / Background % splits, summing to 100%, shown as the "What May Be Influencing Air Quality" bars (Overview) and "Causal Attribution" panel (Hotspots). |
| FR-03 | Simulation | Compare ≥3 distinct policy interventions. | Interactive sliders (Traffic Reduction, Road Dust Control, Industrial Emissions) on the **Scenario Lab** screen. |
| FR-04 | Mapping | Display pollution hotspots on an interactive spatial map. | ~500m grid + point stations on the Overview "Spatial Interpolation Canvas" and Hotspots "Sensor Cluster Telemetry" map. |
| FR-05 | Validation | Validate forecasts against historical test periods. | Held-out, time-separated evaluation reporting MAE, RMSE, R² (Forecast screen "Validation Factor," e.g. Sensor R² vs. reference). |
| FR-06 | State Safety | Disambiguate observed from modeled/scenario results. | Text badges `OBSERVED`, `DERIVED`, `FORECAST`, `SIMULATED`/`MODELED SCENARIO` on every output. |
| FR-07 | Digital Twin | Re-predict counterfactual states dynamically. | Model re-run on modified features; zero hardcoded reductions; Scenario Lab "Modeled Atmospheric Outcome" card shows current → scenario. |
| FR-08 | Auditability | Every scenario reproducible. | `scenario_id` + `model_version` returned; surfaced in Scenario Lab "Session Run History" strip. |

---

## 2. Canonical Input Parameter Groups (12)

| # | Parameter Group | Key Fields | Unit / Type | Classification |
|---|---|---|---|---|
| 1 | Wind Direction (+ Speed) | `wind_direction`, `wind_speed`, `wind_u`, `wind_v` | degrees / m/s | Met. modifier |
| 2 | Temperature | `temperature`, lags | °C | Met. modifier |
| 3 | Humidity | `relative_humidity`, lags | % | Met. modifier |
| 4 | Rainfall | `rainfall_1h/6h/24h`, `recent_rain_flag` | mm / bool | Met. modifier |
| 5 | Construction & Road Dust | `construction_site_count`, `construction_activity_proxy`, `road_density` | int / proxy | Source: Dust/Burning |
| 6 | Traffic Volume & Emissions (by vehicle type) | `traffic_volume`, `heavy_vehicle_volume`, `two_wheeler_volume`, `average_speed`, `traffic_emission_proxy` | veh/hr / proxy | Source: Traffic |
| 7 | Industrial Pollution | `industrial_facility_count`, `industrial_zone_density`, `industrial_activity_proxy`, `nearest_industry_distance` | int / proxy | Source: Industry |
| 8 | Open Burning | `burning_event_count`, `burning_activity_proxy` | int / proxy | Source: Dust/Burning |
| 9 | Traffic Density | `traffic_density`, `congestion_index` | normalized | Source: Traffic |
| 10 | Building Density / Urban Housing | `building_density`, `built_up_fraction`, `population_density` | fraction / density | Urban-form context |
| 11 | Time of Day / Weekday–Weekend | `hour`, `day_of_week`, `is_weekend`, `is_holiday`, `rush_hour_flag` | datetime-derived | Temporal context |
| 12 | Regional / Background Pollution | `background_pm25`, `regional_transport_index`, `upwind_background` | µg/m³ / normalized | Source: Background |

Supplementary modifier: `boundary_layer_height` (m), shown on the Forecast screen's "Environmental Influences" cards.

> Attribution (FR-02) always collapses inputs 5–8 and 12 down to exactly four categories: **Traffic, Industry, Dust/Burning, Background**.

---

## 3. UI Screens & Requirements (per approved Stitch export)

### 3.1 Global Shell
- Fixed top header (64px): logo + wordmark, 4-item pill nav (`Overview`, `Hotspots`, `Forecast`, `Scenario Lab`), live location/time/feed indicator, profile avatar.
- Compact status strip directly below header on Overview: Sector, PM2.5 (+ `OBSERVED` badge), Air Quality category, 6-hour trend (+ `FORECAST` badge), active node count, interpolation method.
- Footer bar: provenance line ("Pune Metropolitan Environmental Observation System • Sensor Grid Telemetry") + right-aligned system status ("Real-time Spatial Interpolation," "Atmospheric Baseline: Stable").

### 3.2 Screen: Overview
- **Center**: Spatial Interpolation Canvas — heatmap/airflow-vector/topography toggle, station pins color-coded by severity, focal-station highlight card.
- **Right dock**: Selected Focal Station card (name, badge, description) → Particulate Load metric (large number + delta) → Current Atmospheric State (Temperature, Humidity, Wind Velocity, Short-term Outlook) → "What May Be Influencing Air Quality" driver bars (Traffic/Dust/Boundary-Layer/Regional) → CTA buttons ("Explore Scenario," "View 24h Trend").
- Requirement: focal station switch updates every card in the right dock in one state update (no partial refresh).

### 3.3 Screen: Hotspots
- **Left**: filter tabs (All Zones / High Priority / Industrial / Transit Corridors) + map + scrollable hotspot list (zone name, severity chip, category, description, PM2.5 value, "Test in Scenario Lab" deep link).
- **Right**: "Why Here?" causal attribution panel for the selected zone — Wind Vector / Inversion Deck / Baseline Delta stat row, then ranked driver list with % and one-line explanation, ending in the mandatory model-attribution disclaimer and an "Immediate Intervention Opportunity" callout.
- Requirement: every hotspot row's "Test in Scenario Lab" link must pre-populate that zone as the Scenario Lab's target context.

### 3.4 Screen: Forecast
- Header stat row: Current Observed (badge `OBSERVED`), Predicted Peak Level (time + badge `FORECAST`), Safe Baseline / NAAQS standard (badge `PERMISSIBLE LIMIT`).
- Primary chart: PM2.5 Ambient Concentration Profile — historical observed line, forecast micro-trajectory line, 95% confidence band, NAAQS limit reference line, "NOW" marker, annotated peak.
- Environmental Influences row: 4 cards (Surface Temperature, Relative Humidity, Wind Velocity, Boundary Layer Height), each with current→projected value and a one-line dispersion explanation.
- Diurnal Trajectory Windows: list of named phases (e.g. Evening Commute, Night Thermal Stagnation, Morning Convective Ventilation) with time ranges and phase-direction indicator.
- Intervention Modeling teaser card linking into Scenario Lab with 1–2 pre-computed "what would this look like" deltas.

### 3.5 Screen: Scenario Lab
- Header: target context (station name), baseline PM2.5 (badge `OBSERVED`).
- Preset tabs: Traffic Focus / Dust Abatement / Combined Action.
- Three sliders (0–50% range each): Traffic Reduction, Road Dust Control, Industrial Emissions — each with description + live % readout. "Run Scenario" button triggers `run_scenario`.
- Modeled Atmospheric Outcome card: Current (badge `OBSERVED`) → Scenario (badge `SIMULATED`) with net variation (absolute + %) and one-line AQI-category shift summary.
- Before/After map toggle with legend (Observed Extreme / Moderate Plume / Counterfactual Cleared Fringe).
- Three outcome KPI cards: PM2.5 concentration change, severe hotspot area change, population exposure index change.
- Session Run History strip: chips for prior runs in-session (label + % change), append-only within the session.

---

## 4. Module Interface Contracts

### 4.1 Forecast Contract — `predict_pm25`
```typescript
interface ForecastRequest { features: Record<string, number>; }

interface ForecastResponse {
  prediction: number;
  lower_bound: number | null;
  upper_bound: number | null;
  state: "MODELED_FORECAST";
  model_version: string;
  timestamp: string;
}
```

### 4.2 Source Attribution Contract — `attribute_sources`
```typescript
interface AttributionResponse {
  traffic: number;
  industry: number;
  dust_burning: number;
  background: number;
  feature_contributions: Record<string, number>;
  assumptions: string[];
}
```

### 4.3 Scenario Engine Contract — `run_scenario`
```typescript
interface ScenarioRequest {
  baseline_features: Record<string, number>;
  traffic_reduction: number;   // 0.0–0.5
  industrial_control: number;  // 0.0–0.5
  dust_control: number;        // 0.0–0.5
  burning_reduction?: number;  // 0.0–1.0, optional
}

interface ScenarioResponse {
  scenario_id: string;
  model_version: string;
  baseline_prediction: number;
  scenario_prediction: number;
  absolute_change: number;
  percent_change: number;
  state: "MODELED_SCENARIO";
}
```

### 4.4 Spatial Scenario Contract — `run_spatial_scenario`
Returns, per 500m grid cell: `grid_id`, `baseline_prediction`, `scenario_prediction`, `delta_pm25`.

---

## 5. Final Definition of Done & Acceptance Checklist

- [ ] Spatial coverage confirmed for Pune bounding box.
- [ ] Master Hourly Table contains all 12 parameter groups + boundary layer height.
- [ ] Trained PM2.5 model producing 1h–72h forecasts.
- [ ] Held-out, time-separated evaluation reporting MAE, RMSE, R².
- [ ] SHAP attribution engine returns exactly 4 source categories.
- [ ] Scenario engine supports Traffic, Industry, Dust (+ optional Burning), re-predicting via the trained model.
- [ ] Spatial delta map renders before/after grid changes with the approved before/after toggle.
- [ ] All 4 screens (Overview, Hotspots, Forecast, Scenario Lab) implemented per §3, using the `Urban Environmental Intelligence` design tokens.
- [ ] `OBSERVED` / `DERIVED` / `FORECAST` / `SIMULATED` labels present on every relevant UI element.
- [ ] All `_proxy` fields labeled as proxies in schema, API, and UI.
- [ ] Every scenario returns a reproducible `scenario_id` + `model_version`, visible in Session Run History.
