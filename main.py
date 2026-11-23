"""UrbanAir Twin API — every number served here comes from data or the trained twin model.

Run:  uvicorn main:app --port 8000   (from C:/HM/AirTwin; train first with `python -m twin.train`)
"""
import os
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from twin import config as C
from twin import service as S

HERE = os.path.dirname(os.path.abspath(__file__))
app = FastAPI(title="UrbanAir Twin API", version="twin_v1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def guard(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------- pages
@app.get("/")
def root():
    return RedirectResponse(url="/overview/")


for _page in ("overview", "hotspots", "forecast", "scenario-lab"):
    def _make(p=_page):
        return lambda: FileResponse(os.path.join(HERE, f"{p}.html"))
    app.get(f"/{_page}/", include_in_schema=False)(_make())


# ---------------------------------------------------------------- meta
@app.get("/api/meta")
def meta():
    m = S.model_metrics()
    return {"model_version": m["model_version"], "default_at": S.DEFAULT_AT, "threshold_ugm3": C.HOTSPOT_THRESHOLD,
            "max_reduction_pct": C.MAX_REDUCTION_PCT, "levers": list(C.LEVERS), "proxies": C.PROXY_NOTES,
            "bbox": C.BBOX, "disclaimer": S.DISCLAIMER,
            "weather_range": [str(S.weather().index.min()), str(S.weather().index.max())]}


@app.get("/api/layers")
def layers():
    import pandas as pd
    s = pd.read_parquet(C.TRAFFIC_SURVEY)
    s = s[(s.survey_type == "Traffic Count") & s.latitude.notna()]
    return {
        "traffic_corridors": [{"name": r.location_name, "category": r.road_category, "lat": r.latitude,
                               "lon": r.longitude} for r in s.itertuples()],
        "industrial_zones": [{"name": n, "lat": a, "lon": b} for n, a, b in C.INDUSTRIAL_ZONES],
        "notes": {"traffic_corridors": "ARAI 2021 traffic-count survey locations.",
                  "industrial_zones": "Approximate centroids (assumption) — verify before pilot use."},
    }


@app.get("/api/validation")
def validation():
    return S.model_metrics()


# ---------------------------------------------------------------- OBSERVE
@app.get("/api/stations")
def stations(at: Optional[str] = None):
    return guard(S.station_snapshot, at)


@app.get("/api/observations")
def observations(station: str, at: Optional[str] = None, hours: int = Query(72, ge=1, le=24 * 14)):
    return guard(S.observation_series, station, at, hours)


@app.get("/api/grid")
def grid(at: Optional[str] = None, hours: int = 1):
    if not 1 <= hours <= 24:
        raise HTTPException(400, "hours must be 1–24")
    return guard(S.grid_snapshot, at, hours)


# ---------------------------------------------------------------- EXPLAIN
@app.get("/api/attribution")
def attribution(lat: Optional[float] = None, lon: Optional[float] = None, station: Optional[str] = None,
                at: Optional[str] = None, hours: int = 1):
    if station:
        st = S.stations().set_index("station_id")
        if station not in st.index:
            raise HTTPException(400, f"Unknown station {station}")
        lat, lon = float(st.loc[station, "lat"]), float(st.loc[station, "lon"])
    if lat is None or lon is None:
        raise HTTPException(400, "Provide station or lat & lon")
    return guard(S.attribution, lat, lon, at, hours)


# ---------------------------------------------------------------- PREDICT
@app.get("/api/forecast")
def forecast(station: str, at: Optional[str] = None, horizon: int = 72):
    if not 1 <= horizon <= 72:
        raise HTTPException(400, "horizon must be 1–72 hours")
    return guard(S.forecast, station, at, horizon)


# ---------------------------------------------------------------- SIMULATE / DECIDE
class Area(BaseModel):
    type: Literal["city", "station", "point"] = "city"
    station_id: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius_km: float = Field(2.5, gt=0, le=20)


class ScenarioReq(BaseModel):
    traffic_reduction: float = Field(0, ge=0, le=C.MAX_REDUCTION_PCT)
    industrial_control: float = Field(0, ge=0, le=C.MAX_REDUCTION_PCT)
    dust_control: float = Field(0, ge=0, le=C.MAX_REDUCTION_PCT)
    burning_reduction: float = Field(0, ge=0, le=C.MAX_REDUCTION_PCT)
    area: Area = Area()
    at: Optional[str] = None
    hours: int = Field(4, ge=1, le=24)


def _reductions(r: ScenarioReq):
    return {"traffic": r.traffic_reduction, "industry": r.industrial_control,
            "dust": r.dust_control, "burning": r.burning_reduction}


@app.post("/api/scenario")
def scenario(req: ScenarioReq):
    out = guard(S.run_scenario, _reductions(req), req.area.model_dump(), req.at, req.hours, with_cells=False)
    return out


@app.post("/api/scenario/spatial")
def scenario_spatial(req: ScenarioReq):
    return guard(S.run_scenario, _reductions(req), req.area.model_dump(), req.at, req.hours, with_cells=True)


class DecideReq(BaseModel):
    reduction_pct: float = Field(20, gt=0, le=C.MAX_REDUCTION_PCT)
    area: Area = Area()
    at: Optional[str] = None
    hours: int = Field(4, ge=1, le=24)


@app.post("/api/decide")
def decide(req: DecideReq):
    return guard(S.decide, req.reduction_pct, req.area.model_dump(), req.at, req.hours)


app.mount("/", StaticFiles(directory=HERE), name="static")
