# UrbanAir Twin — UI Build Guide (`README.md`)

This is the canonical reference for reproducing the approved UI, sourced from the `stitch_urbanair_twin_dashboard` export (4 screens + design system). It supersedes any earlier UI guidance in `PROMPT.md`/`PHASES.md`. Pair this with `REQUIREMENTS.md` §3–4 for the data each screen needs and `RULES.md` §1/§5 for the non-negotiable labeling rules.

> **Which theme?** The export ships two alternate color themes (`urbanair_twin` — cyan/navy, and `urban_environmental_intelligence` — sage/charcoal). **All 4 delivered screens use the sage/charcoal "Urban Environmental Intelligence" theme.** Treat the cyan theme as discarded; do not mix its tokens in.

---

## 1. Design Tokens

### Colors

| Token | Hex | Usage |
|---|---|---|
| `background` / `surface` | `#121413` | App canvas |
| `surface-container-lowest` | `#0d0f0e` | Map/viewport base |
| `surface-container-low` | `#1a1c1b` | Header, status strip, nav chrome |
| `surface-container` | `#1e201f` | Standard cards |
| `surface-container-high` | `#282a29` | Elevated cards, neutral chips |
| `surface-container-highest` | `#333534` | Dividers, hover states |
| `on-surface` | `#e2e3e0` | Primary text |
| `on-surface-variant` | `#c2c8c1` | Secondary text |
| `outline` | `#8c928c` | Labels, muted icons |
| `outline-variant` | `#424843` | Hairline borders |
| `primary` | `#adceb8` | Sage — active nav, primary buttons, OBSERVED accents |
| `on-primary` | `#193627` | Text on primary-filled elements |
| `primary-container` | `#8faf9a` | Active nav pill fill, SIMULATED badge fill |
| `secondary` | `#b5cacf` | Dusty blue — secondary telemetry (wind, humidity) |
| `tertiary` | `#ecbf83` | Amber — advisory/moderate severity, forecast highlight |
| `tertiary-container` | `#cba068` | Advisory fills |
| `error` | `#ffb4ab` | Critical/alert severity text |

Severity scale (not the same as state — see `RULES.md` §1.4): **Nominal** sage `#8FAF9A` · **Advisory** amber `#C49A62` · **Alert** terracotta `#B86F67`. Never substitute bright red/green.

### Typography

| Role | Font | Size / Weight | Usage |
|---|---|---|---|
| `display-lg` | Manrope 600 | 40px / 48px lh | Rare — hero numbers only |
| `headline-xl` | Manrope 600 | 28px / 34px lh | Screen titles ("Active Hotspots & Factors") |
| `headline-lg` | Manrope 600 | 22px / 28px lh | Section titles ("WHAT IF?") |
| `headline-md` | Manrope 500 | 18px / 24px lh | Card titles |
| `title-sm` | Inter 600 | 15px / 20px lh | Nav items, station names |
| `body-lg` / `body-md` / `body-sm` | Inter 400 | 15/13/12px | Descriptions, paragraph copy |
| `label-md` / `label-sm` | Inter 500 | 12/11px, uppercase, tracked | Field labels, badges |
| `code-metric` | Inter 500 (tabular nums) | 12px | All numeric readouts, coordinates, timestamps |

Load via: `Inter:wght@100..900`, `Manrope:wght@100..900` (Google Fonts) + `Material Symbols Outlined` for all icons.

### Shape, Spacing, Elevation

- Radius: `4px` default (cards, buttons, inputs), `6px` max on large panels. No pill buttons.
- Spacing rhythm: 4px base — `space-xs 4px`, `space-sm 8px`, `space-md 16px`, `space-lg 24px`, `space-xl 40px`. Desktop gutter `24px`.
- No drop shadows for depth — use surface brightness steps (`surface` → `surface-container` → `surface-container-high`) plus 1px hairline borders (`rgba(232,232,225,0.08)` default, `rgba(143,175,154,0.35)` on hover, `#8FAF9A` on focus).
- Layout: 12-column grid, full-height (`100vh`) shell on Overview (map canvas + fixed-width right dock, ~380–440px). Hotspots/Forecast/Scenario Lab scroll vertically within a padded content column.

---

## 2. Shared Shell (every screen)

**Header (64px, fixed top, `surface-container-low` + blur):**
- Left: circular logo mark (sage wavy line on dark disc) + "UrbanAir Twin" (title-sm) / "Metropolitan Intelligence" (label-sm, muted).
- Center: 4-item segmented nav pill (`bg-surface-container`, `rounded-lg`) — **Overview · Hotspots · Forecast · Scenario Lab**. Active item: `bg-primary-container`, `text-on-primary-container`, semibold.
- Right: live status chip (pulsing primary dot + "Pune, India" + time `HH:MM IST` + "Municipal Live Feed"), circular avatar (`bg-primary`).

**Footer (thin bar):** left — "Pune Metropolitan Environmental Observation System • Sensor Grid Telemetry"; right — "Real-time Spatial Interpolation" / "Atmospheric Baseline: Stable".

**State badge component** (`RULES.md` §1): small rectangular chip, `label-sm`, uppercase — `OBSERVED` (neutral bg, primary text), `FORECAST` (neutral bg, secondary text), `SIMULATED`/`MODELED SCENARIO` (`primary-container` bg, `on-primary-container` text).

**Severity chip component:** 22px chip, 12%-opacity tint bg + 20%-opacity border + full-tone text, in Nominal/Advisory/Alert per §1.

---

## 3. Screen 1 — Overview

**Layout:** 12-col grid under a compact status strip. Map canvas `lg:col-span-8/9`, right dock `col-span-3/4`.

**Status strip** (`surface-container-low`, thin): Sector name · PM2.5 value + `OBSERVED` badge · Air Quality category (colored dot + severity word) · 6-Hour Trend (direction + delta) + `FORECAST` badge · Active Node count · Interpolation method note.

**Spatial Interpolation Canvas (center):**
- Toolbar: "SPATIAL INTERPOLATION CANVAS" label, grid resolution note, dispersion-model note, and 3 view toggles — Heatmap / Airflow Vectors / Topography.
- Dark basemap with soft glow blobs sized/colored by PM2.5 severity at each station pixel position; faint road/river line art; station pins labeled with name + µg/m³.
- One pin is the "focal/active" station: outlined card with name, `ACTIVE` badge, value + severity word.
- Bottom-left: zoom controls (+/−/Reset). Bottom-center: Air Quality legend (Low/Moderate/High/Very High dots).

**Right dock (top → bottom):**
1. Selected Focal Station card — name, `OBSERVED` badge, sub-area name, one-line description.
2. Particulate Load (PM2.5) — large `code-metric` number + severity badge + delta line ("+12 µg/m³ above seasonal morning baseline").
3. Current Atmospheric State — 2×2 mini-grid: Temperature, Humidity, Wind Velocity, Short-term Outlook, each with a one-line qualifier.
4. "What May Be Influencing Air Quality" — ranked driver bars (Traffic Activity, Road Dust & Resuspension, Boundary Layer Weather, Regional Air Transport), each a colored dot + label + % + horizontal bar, footed by a one-line model disclaimer.
5. CTAs: primary button "Explore Scenario →", secondary button "View 24h Trend".

**Data bindings:** station list + focal station ← `GET /api/observations`; 6-hour trend ← `GET /api/forecast?horizon=6h`; driver bars ← `GET /api/attribution?station=`.

---

## 4. Screen 2 — Hotspots

**Layout:** left column (map + list) ~60%, right column (attribution panel) ~40%, both scroll independently.

**Left:**
- Header: "SPATIAL DIAGNOSTICS • Sensor Cluster Telemetry" eyebrow, "Active Hotspots & Factors" title, one-line subtitle.
- Filter tabs, right-aligned above the map: "All Zones (N)" / "High Priority (N)" / "Industrial" / "Transit Corridors".
- Compact map: basemap + severity-colored station dots, one labeled/selected.
- Hotspot list: one row per zone — icon, zone name + severity chip + category tag, one-line description, PM2.5 value (right-aligned, large), "Test in Scenario Lab →" link.

**Right — "Why Here?" causal panel for the selected zone:**
- Eyebrow "CAUSAL ATTRIBUTION" + priority badge.
- Title "WHY HERE? — {station name}" + one-line intro.
- 3-stat row: Wind Vector, Inversion Deck (height + qualifier), Baseline Delta (% vs. average).
- Ranked driver list (icon + label + %, horizontal bar, one-line explanation) — e.g. Traffic & Commute Congestion, Meteorological Stagnation, Road & Construction Dust, Industrial Inflow, Regional Agricultural Conditions.
- Disclaimer callout: "Contributing factors are estimated by the atmospheric twin to provide actionable municipal guidance." (mandatory, verbatim intent — see `RULES.md` §2.2)
- Primary button: "Explore Countermeasures in Scenario Lab ⇄".
- Below the panel: "Immediate Intervention Opportunity" card — one concrete, quantified suggestion (e.g. "...could mitigate up to **19%** of local PM2.5 elevation").

**Data bindings:** hotspot list ← `GET /api/hotspots`; causal panel ← `GET /api/attribution?station=`; "Test in Scenario Lab" deep-links to `/scenario-lab?station=`.

---

## 5. Screen 3 — Forecast

**Layout:** single scrolling column, full-width cards.

**Header row:** title "Pollution Forecast" + eyebrow badge "FORECAST — 6-HOUR MICRO-TRAJECTORY"; right side: station selector, "Atmospheric Dispersion Run" link.

**Stat strip (3 cards):** Current Observed (value + `OBSERVED` badge) · Predicted Peak Level (value + time + `FORECAST` badge) · Safe Baseline/NAAQS Standard (value + `PERMISSIBLE LIMIT` badge).

**Primary chart card — "PM2.5 Ambient Concentration Profile":**
- Legend: Historical Observed (solid line) / Micro-Trajectory (solid line, different color) / 95% Confidence Band (shaded) / NAAQS Limit (dashed reference line).
- X-axis: hourly ticks spanning past + "NOW" marker + future hours up to the peak/inversion window.
- Annotated peak callout ("Peak: 132 µg/m³ • Evening Buildup & Inversion") and an "Observed: 118 µg/m³" marker at NOW.
- Footer line: model dynamics note + validation factor (e.g. "Sensor R² = 0.94 vs reference").

**Environmental Influences row (4 cards):** Surface Temperature, Relative Humidity, Wind Velocity, Boundary Layer Height — each: icon, label, current → projected value, one-line dispersion explanation, thin progress/severity bar.

**Diurnal Trajectory Windows (list):** named phases (Evening Commute Window, Night Thermal Stagnation, Morning Convective Ventilation) with time range, one-line description, and a phase tag (Buildup Phase ↑ / Trap Equilibrium — / Dispersion Rebound ↓).

**Intervention teaser card:** "Mitigate Predicted Peak" + 1–2 precomputed deltas (e.g. "Freight Arterial Diversion: −18 µg/m³ peak") + primary button "Simulate Countermeasures in Scenario Lab →".

**Data bindings:** stat strip + chart ← `GET /api/forecast?station=&horizon=72h`; environmental influence cards ← `GET /api/observations` (current) + `GET /api/forecast` (projected); diurnal windows can be derived client-side from the same forecast series.

---

## 6. Screen 4 — Scenario Lab

**Layout:** single scrolling column, full-width cards, in this order.

**Header:** eyebrow "SCENARIO LAB | Target Context: {station}, Pune"; title "WHAT IF?" + one-line intro; right-aligned baseline card (value + `OBSERVED` badge + station id).

**Preset + sliders card:**
- Preset tabs: Traffic Focus / Dust Abatement / Combined Action (active tab highlighted `primary-container`).
- 3 sliders, each: icon, name, one-line description, `0% ——●—— 50%` track, live numeric readout chip.
  - Traffic Reduction — "Reduce vehicular flow & divert heavy transit in central corridor."
  - Road Dust Control — "Surface wetting cycles and continuous mechanical street sweeping."
  - Industrial Emissions — "Thermal load shifting and industrial perimeter dust containment."
- Footer: "Simulated in {t}s based on Pune atmospheric twin." + primary button "RUN SCENARIO →" (with a refresh/loading icon state).

**Modeled Atmospheric Outcome card:** "CURRENT: {baseline} `OBSERVED` → SCENARIO: {value} `SIMULATED`" + right-aligned net variation (absolute + % change) + one-line AQI-category shift ("Air Quality Index shifting from Severe to Moderate").

**Before/After map card:**
- Header: "MODELED SCENARIO — Affected high-pollution area contracts by {x}%" + toggle: "BEFORE (Baseline)" / "AFTER (Simulated Scenario) — Active".
- Basemap with concentration glow, station labels with modeled deltas.
- Legend: Observed Extreme (>110) / Moderate Plume (85–100) / Counterfactual Cleared Fringe.

**3 outcome KPI cards:** PM2.5 Concentration (before → after, Δ), Severe Hotspot Area (km² before → after, Δ), Population Exposure Index (qualitative shift + %).

**Session Run History strip:** append-only chips for each run this session — label + net % change, most recent first/highlighted.

**Data bindings:** sliders + Run Scenario ← `POST /api/scenario` (`REQUIREMENTS.md` §4.3); before/after map ← `POST /api/scenario/spatial` (§4.4); Session Run History is client-side state seeded from each `scenario_id` returned.

---

## 7. Map Implementation Note

The Stitch export renders the map as static illustrative art (glow blobs + line-art roads), not a live tile provider. For the working build:
- Keep the same dark basemap aesthetic (no bright web-map tiles — they break the design system's contrast rules).
- Implement station points, the 500m grid heatmap, and wind vectors as an SVG/Canvas overlay (or MapLibre GL with a custom dark style) positioned by lat/lon → screen-space projection within the Pune bounding box `[18.40, 73.75, 18.65, 74.00]`.
- Severity color-coding for grid cells and pins always follows the 3-tone severity scale in §1 — never the raw AQI palette from a third-party map SDK.

---

## 8. What Changed From the Original Spec Files

- Frontend is no longer Streamlit + PyDeck (see `MEMORY.md` ADR-06) — it's the static Tailwind build above, served by FastAPI.
- The dashboard is 4 screens (`Overview`, `Hotspots`, `Forecast`, `Scenario Lab`), not a generic 3-panel layout — `REQUIREMENTS.md` §3 and `PHASES.md` Phase 5 have been updated to match this exactly.
- All illustrative numbers baked into the Stitch export (118 µg/m³, 132 µg/m³ peak, 41% Traffic, etc.) are mockup placeholders only and must be replaced by live `/api/...` values — see `MEMORY.md` §5, point 6.
