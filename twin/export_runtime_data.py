"""Writes the slim runtime bundle (data/) so the app runs from a fresh clone
without the 270 MB training folder. Run after training:  python -m twin.export_runtime_data
"""
import shutil

from . import config as C
from . import features as F
from . import service as S


def main():
    C.RUNTIME_DIR.mkdir(exist_ok=True)
    F.city_weather().to_parquet(C.CITY_WEATHER, index=False, compression="zstd")
    S.observations.cache_clear()
    obs = S.observations() if not C.SENSOR_OBS.exists() else None
    if obs is None:
        C.SENSOR_OBS.unlink()
        S.observations.cache_clear()
        obs = S.observations()
    obs.reset_index(drop=True).to_parquet(C.SENSOR_OBS, index=False, compression="zstd")
    for name in ("pune_traffic_survey_stations.parquet", "pune_traffic_congestion_toy_sample.parquet"):
        shutil.copy(C.DATA_DIR / name, C.RUNTIME_DIR / name)
    for p in sorted(C.RUNTIME_DIR.iterdir()):
        print(f"{p.name}: {p.stat().st_size/1e6:.2f} MB")


if __name__ == "__main__":
    main()
