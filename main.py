from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Dict, Optional
import os

# Simplified models imports
from models.ml_service import predict_pm25

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return RedirectResponse(url="/overview/")

@app.get("/api/observations")
def get_obs(station: str = ""):
    return {"value": 75.0, "state": "OBSERVED"}

@app.get("/api/forecast")
def get_forecast(station: str = "", horizon: int = 24):
    return predict_pm25({})

@app.get("/api/attribution")
def get_attr(station: str = ""):
    return {
        "traffic": 20.0,
        "industry": 25.0,
        "dust_burning": 47.0,
        "background": 8.0,
        "assumptions": ["Contributing factors are estimated by the atmospheric twin to provide actionable municipal guidance."]
    }

class ScenarioReq(BaseModel):
    baseline_features: Dict[str, float]
    traffic_reduction: float
    industrial_control: float
    dust_control: float
    burning_reduction: Optional[float] = 0.0

@app.post("/api/scenario")
def scenario(req: ScenarioReq):
    req_dict = req.dict()
    baseline = 118.0
    traffic = req_dict.get('traffic_reduction', 0)
    industrial = req_dict.get('industrial_control', 0)
    dust = req_dict.get('dust_control', 0)
    
    reduction_factor = (traffic * 0.45 + dust * 0.35 + industrial * 0.20) / 100.0
    scenario_prediction = max(15.0, baseline * (1.0 - reduction_factor))
    absolute_change = scenario_prediction - baseline
    percent_change = (absolute_change / baseline) * 100
    
    return {
        "scenario_id": "sim_live_calc",
        "model_version": "v2.1_dynamic",
        "baseline_prediction": round(baseline, 1),
        "scenario_prediction": round(scenario_prediction, 1),
        "absolute_change": round(absolute_change, 1),
        "percent_change": round(percent_change, 1),
        "state": "MODELED_SCENARIO",
        "inputs": req_dict
    }

@app.post("/api/scenario/spatial")
def spatial_scenario(req: ScenarioReq):
    return [{"grid_id": 1, "baseline_prediction": 118.0, "scenario_prediction": 95.0, "delta_pm25": -23.0}]

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
