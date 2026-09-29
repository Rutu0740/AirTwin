# UrbanAir Twin — Technology Stack Documentation

This document outlines the entire technology stack used across the UrbanAir Twin digital twin project, detailing where and how each technology is implemented.

---

## 1. Backend & API Layer

- **Python (3.10+)**: The core programming language for the entire data pipeline, machine learning modeling, and backend server.
- **FastAPI**: Used as the primary web framework to expose the high-performance REST APIs (`/api/observations`, `/api/forecast`, `/api/attribution`, `/api/scenario`). It handles the routing and serves the frontend static files.
- **Uvicorn**: The ASGI web server used to run the FastAPI application, providing lightning-fast request handling (started via `uvicorn backend.main:app --reload`).
- **Pydantic**: Integrated closely with FastAPI for robust data validation and serialization of the API requests and responses.

## 2. Frontend & User Interface

- **Static HTML5**: Used as the structural backbone for the 4 core screens (Overview, Hotspots, Forecast, Scenario Lab).
- **Tailwind CSS (via CDN)**: The utility-first CSS framework used for all styling, layout, and responsiveness. We employ the custom *Urban Environmental Intelligence* design tokens (dark theme, sage/amber/terracotta color palette).
- **Vanilla JavaScript**: Used for all client-side logic without needing a heavy frontend framework. It handles:
  - Fetching live data from the FastAPI backend.
  - Dynamically manipulating the DOM to update UI elements (like station names, PM2.5 metrics, and attribution bars).
  - Injecting interactivity into the map markers and hotspot lists.
- **Google Fonts & Material Symbols**: `Inter` and `Manrope` are used for typography, and Material Symbols Outlined are used for scalable UI iconography.

## 3. Geospatial & Mapping

- **Leaflet.js**: The lightweight open-source JavaScript library used to render interactive maps on the *Overview* and *Hotspots* pages.
- **Geoapify API (CartoDB Dark Matter)**: The map tile provider used to render the dark-themed basemap tiles via the authenticated API key, ensuring visual consistency with the UI design system.

## 4. Data Visualization

- **Chart.js**: An HTML5 Canvas-based charting library used on the *Forecast* screen to render the interactive "PM2.5 Ambient Concentration Profile" micro-trajectory curve, displaying both historical sequences and predicted trends.

## 5. Machine Learning & Data Engineering Pipeline (Core Architecture)

- **XGBoost (`xgboost`)**: The tabular machine learning algorithm chosen for the PM2.5 forecasting engine due to its execution speed and high accuracy on mixed weather/pollution datasets.
- **Pandas & NumPy**: Utilized for in-memory data manipulation, hourly resampling, and constructing the Master Hourly Feature Table.
- **GeoPandas & DuckDB**: Used for heavy geospatial indexing (500m × 500m grid), spatial joins, and fast analytical querying over large Parquet files.
- **PyArrow**: Handles the efficient reading/writing of `.parquet` files for the master datasets.
- **TreeSHAP (`shap`)**: The explainability framework used to decompose the XGBoost model predictions into actionable source attribution categories (Traffic, Industry, Dust, Background).
- **Joblib**: Used for serializing and deserializing the trained XGBoost model artifact (`xgb_pm25_model.joblib`) for rapid inference in the FastAPI layer.

---

### Integration Flow Summary
1. The **Data Pipeline (Pandas/GeoPandas)** cleans raw telemetry and builds features.
2. The **ML Engine (XGBoost/SHAP)** trains on this data and saves the model.
3. The **Backend (FastAPI)** loads the model and exposes endpoints for forecasting and scenario simulation.
4. The **Frontend (Vanilla JS/Tailwind)** fetches from these endpoints and visualizes the results on interactive **Leaflet** maps and **Chart.js** graphs.
