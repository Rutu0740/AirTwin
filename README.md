<p align="center"><img src="logo.svg" alt="UrbanAir Twin" width="420"/></p>

# UrbanAir Twin

**A digital twin of Pune's air that tests the cure before the city pays for it.**
Air-quality dashboards tell you where the air is bad. UrbanAir Twin also asks *"what if traffic drops 20%?"*, re-runs a trained model over the chosen area and time window, and shows the modeled change in PM2.5, hotspot area and traffic share, so authorities can compare interventions before enforcing one.

Built for the Sustainable Cities track, Geek Fiesta '26.

| Step | Screen | What it does |
|---|---|---|
| **Observe** | Overview | Observed readings from 12 CPCB/MPCB/IITM stations, plus a modeled 500 m grid (3,819 cells) for neighbourhoods with no monitor |
| **Explain** | Hotspots | Click any cell or station to see which source groups the model relied on (traffic, industry, dust, burning, meteorology), via TreeSHAP |
| **Predict** | Forecast | 72-hour station forecast with an uncertainty band, a 3-day hotspot outlook, and the full validation results |
| **Simulate** | Scenario Lab | Sliders for traffic, industry, dust and burning re-run the model and show baseline, scenario and change maps |
| **Decide** | Scenario Lab | Ranks the four levers at the same strength by change in PM2.5 and hotspot area |

Every number on screen comes from data or the trained model, and is labelled **observed**, **modeled**, **modeled forecast** or **modeled scenario**.

## Quick start (about 2 minutes)

Requires Python 3.10 or newer.

```bash
git clone https://github.com/Rutu0740/AirTwin.git
cd AirTwin
pip install -r requirements.txt
python -m uvicorn main:app --port 8000
```

Open **http://localhost:8000**, which redirects to the Overview screen. API docs (Swagger) are at **http://localhost:8000/docs**.

The repo ships the trained model (`artifacts/`) and a 4.5 MB runtime data bundle (`data/`), so no dataset download is needed to run the app. The app replays the most recent period with verified sensor data (December 2025).

### Retraining (optional)

Place the full dataset folder `datasets for training/` next to the repo folder, then run:

```bash
python -m twin.train                  # trains + validates, writes artifacts/
python -m twin.export_runtime_data    # refreshes the slim data/ bundle
```

## Documentation

- [Technical documentation](docs/TECHNICAL.md): architecture, tech stack, model, APIs, integrations, validation, limits
- [Demo video script](docs/DEMO_SCRIPT.md): the 3–5 minute walkthrough
- [UI build guide](docs/UI_BUILD_GUIDE.md): design tokens and screen specs
- [`memory.md`](memory.md): architecture decisions and model run log (RUN-004 is the current model)

## Repository layout

```
main.py               FastAPI app: pages + 11 JSON endpoints
twin/                 config, features, train, service (the model runtime)
artifacts/            trained XGBoost model + validation metrics (JSON)
data/                 runtime bundle: city ERA5 weather, sensor observations, traffic tables
twin-ui.js            shared front-end: API client, Leaflet maps, smooth heat-map renderer
*.html                Overview, Hotspots, Forecast, Scenario Lab
logo.svg / logo-mark.svg
```

## Honest limits

- The traffic, industry, dust and burning inputs are **labelled proxies**; no open hourly activity feed exists for Pune.
- Source shares are **model-attributed** (TreeSHAP), not causal proof.
- Station and industrial-zone coordinates are approximate.
- Population exposure is "not computed" until a population raster is added.

Full details and measured accuracy are in the [technical documentation](docs/TECHNICAL.md#7-validation-results).
