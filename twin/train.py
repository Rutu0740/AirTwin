"""Train + validate the UrbanAir Twin model (RUN-004).

One XGBoost model serves forecast, attribution (TreeSHAP) and scenario simulation.
It deliberately has NO PM2.5 autoregressive lags: lags let a model 'explain'
pollution by pollution, which makes attribution meaningless and makes grid cells
without a monitor impossible to score. Time enters only through weather and the
labelled activity proxies.

Run:  python -m twin.train      (from C:/HM/AirTwin)
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
import xgboost as xgb

from . import config as C
from . import features as F


def metrics(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    ok = ~(np.isnan(y) | np.isnan(p))
    y, p = y[ok], p[ok]
    err = p - y
    ss = ((y - y.mean()) ** 2).sum()
    return {"mae": float(np.abs(err).mean()), "rmse": float(np.sqrt((err ** 2).mean())),
            "r2": float(1 - (err ** 2).sum() / ss), "n": int(ok.sum())}


def load_frame() -> pd.DataFrame:
    cols = ["station_id", "timestamp", "split", "pm2_5_ugm3", "pm25_lag_24h", "pm25_legacy_assumed",
            "era5_wind_speed_100m_ms"] + F.ERA5_COLS
    df = pd.read_csv(C.TRAINING_CSV, usecols=cols)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(C.TZ)
    df = df[df.pm2_5_ugm3.between(0, 500) & (df.pm25_legacy_assumed == 0)]
    df = df[~df.station_id.str.startswith("LEGACY")]
    split = pd.Series(pd.NA, index=df.index, dtype="object")
    for name, (a, b) in C.SPLITS.items():
        split[(df.timestamp >= pd.Timestamp(a, tz=C.TZ)) & (df.timestamp <= pd.Timestamp(b, tz=C.TZ))] = name
    df["split"] = split
    df = df[df.split.notna()].sort_values(["station_id", "timestamp"]).reset_index(drop=True)

    st = pd.DataFrame([(k, v[1], v[2]) for k, v in C.STATIONS.items()], columns=["station_id", "lat", "lon"])
    st = pd.concat([st, F.static_spatial(st.lat, st.lon)], axis=1)
    df = df.merge(st, on="station_id", how="left")

    # 72 h accumulated precipitation per station (time-based window tolerates gaps)
    df["precip_72h_m"] = (
        df.set_index("timestamp").groupby("station_id")["era5_total_precipitation_m"]
        .rolling("72h", min_periods=1).sum().reset_index(drop=True).to_numpy())
    F.add_derived_weather(df)
    F.add_time(df)
    F.add_activity(df)
    return df


def fit(X, y, Xv=None, yv=None, n_estimators=2000):
    params = dict(n_estimators=n_estimators, learning_rate=0.03, max_depth=7, min_child_weight=20,
                  subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0, tree_method="hist",
                  monotone_constraints=tuple(C.MONOTONE.get(f, 0) for f in C.FEATURES),
                  n_jobs=-1, random_state=42)
    if Xv is not None:
        params["early_stopping_rounds"] = 100
        params["eval_metric"] = "mae"
    m = xgb.XGBRegressor(**params)
    m.fit(X, y, eval_set=[(Xv, yv)] if Xv is not None else None, verbose=False)
    return m


def grouped_contribs(booster, X) -> pd.DataFrame:
    contrib = booster.predict(xgb.DMatrix(X), pred_contribs=True)
    cols = list(X.columns) + ["bias"]
    c = pd.DataFrame(contrib, columns=cols)
    out = pd.DataFrame({g: c[fs].sum(axis=1) for g, fs in C.SOURCE_GROUPS.items()})
    out["bias"] = c["bias"]
    return out


def source_shares(g: pd.DataFrame) -> dict:
    """Share of the positive, controllable+met contribution above the model's base value."""
    pos = g.drop(columns="bias").clip(lower=0).mean()
    return {k: round(float(v / pos.sum() * 100), 1) for k, v in pos.items()}


def main():
    t0 = time.time()
    df = load_frame()
    print(f"loaded {len(df):,} rows in {time.time()-t0:.0f}s")
    tr, va, te = (df[df.split == s] for s in ("train", "validation", "test"))
    X = lambda d: d[C.FEATURES]

    model = fit(X(tr), tr.pm2_5_ugm3, X(va), va.pm2_5_ugm3)
    best = int(model.best_iteration) + 1
    print(f"best iteration {best}")
    res = {"run_id": "RUN-004", "model_version": "twin_v1.0", "best_iteration": best,
           "features": C.FEATURES, "monotone_increasing": list(C.MONOTONE),
           "periods": {s: [str(d.timestamp.min()), str(d.timestamp.max())] for s, d in
                       (("train", tr), ("validation", va), ("test", te))}}
    for name, d in (("train", tr), ("validation", va), ("test", te)):
        res[name] = metrics(d.pm2_5_ugm3, model.predict(X(d)))
    print({k: res[k] for k in ("train", "validation", "test")})

    # ---- Baselines on the test year ------------------------------------------------
    te = te.copy()
    te["pred"] = model.predict(X(te))
    obs = df[["station_id", "timestamp", "pm2_5_ugm3"]]
    lag72 = obs.assign(timestamp=obs.timestamp + pd.Timedelta(hours=72)).rename(columns={"pm2_5_ugm3": "lag72"})
    te = te.merge(lag72, on=["station_id", "timestamp"], how="left")
    # nearest OTHER station reporting at the same hour
    coords = {k: (v[1], v[2]) for k, v in C.STATIONS.items()}
    ids = list(coords)
    D = np.array([[F.haversine_km(*coords[a], *coords[b]) if a != b else np.inf for b in ids] for a in ids])
    order = {a: [ids[j] for j in np.argsort(D[i])] for i, a in enumerate(ids)}
    piv = obs[obs.timestamp.isin(te.timestamp.unique())].pivot_table(
        index="timestamp", columns="station_id", values="pm2_5_ugm3")
    near = np.full(len(te), np.nan)
    for sid, idx in te.groupby("station_id").groups.items():
        ts = te.loc[idx, "timestamp"]
        vals = pd.Series(np.nan, index=idx)
        for other in order[sid]:
            if other not in piv:
                continue
            v = piv[other].reindex(pd.DatetimeIndex(ts)).to_numpy()
            vals = vals.fillna(pd.Series(v, index=idx))
        near[te.index.get_indexer(idx)] = vals.to_numpy()
    te["nearest"] = near
    common = te.dropna(subset=["pm25_lag_24h", "lag72", "nearest"])
    res["baselines_test"] = {
        "note": "Scored on identical test rows where every baseline is available.",
        "n_rows": int(len(common)),
        "twin_model": metrics(common.pm2_5_ugm3, common.pred),
        "persistence_24h": metrics(common.pm2_5_ugm3, common.pm25_lag_24h),
        "persistence_72h": metrics(common.pm2_5_ugm3, common.lag72),
        "nearest_station_same_hour": metrics(common.pm2_5_ugm3, common.nearest),
    }
    print(json.dumps(res["baselines_test"], indent=1))

    # ---- Leave-one-station-out (places with no monitor) ----------------------------
    loso = {}
    for sid in sorted(te.station_id.unique()):
        trs = tr[tr.station_id != sid]
        if len(te[te.station_id == sid]) < 500:
            continue
        m = fit(X(trs), trs.pm2_5_ugm3, n_estimators=best)
        d = te[te.station_id == sid]
        loso[sid] = {"name": C.STATIONS[sid][0], "seen_in_training": bool((tr.station_id == sid).any()),
                     "held_out": metrics(d.pm2_5_ugm3, m.predict(X(d))),
                     "nearest_station": metrics(d.pm2_5_ugm3, d.nearest)}
        print(sid, round(loso[sid]["held_out"]["mae"], 2), round(loso[sid]["nearest_station"]["mae"], 2))
    res["leave_one_station_out_test"] = loso
    res["leave_one_station_out_summary"] = {
        "mean_mae_held_out": float(np.mean([v["held_out"]["mae"] for v in loso.values()])),
        "mean_mae_nearest_station": float(np.mean([v["nearest_station"]["mae"] for v in loso.values()])),
    }

    # ---- Station forecast with residual correction ----------------------------------
    # forecast(t+h) = twin(t+h) + k_h * mean(obs - twin over the 24 h ending at issue time t)
    allp = df[["station_id", "timestamp", "split", "pm2_5_ugm3"]].copy()
    allp["pred"] = model.predict(X(df))
    allp["resid"] = allp.pm2_5_ugm3 - allp.pred
    roll = (allp.set_index("timestamp").groupby("station_id")["resid"]
            .rolling("24h", min_periods=6).mean().rename("r24").reset_index())
    rc = {}
    for h in (6, 24, 48, 72):
        shifted = roll.assign(timestamp=roll.timestamp + pd.Timedelta(hours=h))
        d = allp.merge(shifted, on=["station_id", "timestamp"], how="inner").dropna(subset=["r24"])
        dv, dt = d[d.split == "validation"], d[d.split == "test"]
        ks = np.linspace(0, 1, 21)
        k = float(ks[np.argmin([np.abs(dv.pred + kk * dv.r24 - dv.pm2_5_ugm3).mean() for kk in ks])])
        pers = obs.assign(timestamp=obs.timestamp + pd.Timedelta(hours=h)).rename(columns={"pm2_5_ugm3": "pers"})
        dt = dt.merge(pers, on=["station_id", "timestamp"], how="inner")
        rc[f"{h}h"] = {"k": k, "n": int(len(dt)),
                       "twin_residual_corrected": metrics(dt.pm2_5_ugm3, dt.pred + k * dt.r24),
                       "twin_raw": metrics(dt.pm2_5_ugm3, dt.pred),
                       "persistence": metrics(dt.pm2_5_ugm3, dt.pers)}
        print(h, "k", k, {n: round(v["mae"], 2) for n, v in rc[f"{h}h"].items() if isinstance(v, dict)})
    res["station_forecast_by_horizon_test"] = rc

    # ---- Attribution sanity checks -------------------------------------------------
    booster = model.get_booster()
    samp = te.sample(min(len(te), 30000), random_state=0)
    g = grouped_contribs(booster, X(samp))
    g.index = samp.index
    rush = samp.hour.isin([8, 9, 10, 18, 19, 20])
    night = samp.hour.isin([1, 2, 3, 4])
    winter = samp.month.isin([11, 12, 1, 2])
    monsoon = samp.month.isin([6, 7, 8, 9])
    dry = samp.precip_72h_m < 0.001
    res["attribution_sanity"] = {
        "note": "Mean grouped TreeSHAP contribution (µg/m³) — model-attributed, not causal.",
        "traffic_rush_hour": float(g.loc[rush, "traffic"].mean()),
        "traffic_night": float(g.loc[night, "traffic"].mean()),
        "burning_winter": float(g.loc[winter, "burning"].mean()),
        "burning_monsoon": float(g.loc[monsoon, "burning"].mean()),
        "dust_dry_72h": float(g.loc[dry, "dust"].mean()),
        "dust_wet_72h": float(g.loc[~dry, "dust"].mean()),
        "overall_positive_share_pct": source_shares(g),
    }
    print(json.dumps(res["attribution_sanity"], indent=1))

    # ---- Natural experiment: weekend vs weekday -----------------------------------
    wk = te.dow >= 5
    res["natural_experiment_weekend"] = {
        "note": "Observed vs modeled (weekend - weekday) mean PM2.5 over the test year, same hours.",
        "observed_diff": float(te.loc[wk, "pm2_5_ugm3"].mean() - te.loc[~wk, "pm2_5_ugm3"].mean()),
        "modeled_diff": float(te.loc[wk, "pred"].mean() - te.loc[~wk, "pred"].mean()),
    }
    print(res["natural_experiment_weekend"])

    # ---- Uncertainty band + training ranges for OOD warnings ------------------------
    rv = va.pm2_5_ugm3.to_numpy() - model.predict(X(va))
    res["residual_quantiles_validation"] = {"p10": float(np.quantile(rv, 0.10)), "p90": float(np.quantile(rv, 0.90))}
    res["training_ranges"] = {f: [float(tr[f].quantile(0.01)), float(tr[f].quantile(0.99))] for f in C.FEATURES}

    C.ARTIFACTS.mkdir(exist_ok=True)
    # Deployment model: refit on all verified data with the validated tree count.
    full = fit(X(df), df.pm2_5_ugm3, n_estimators=best)
    booster = full.get_booster()
    res["deployed_model_note"] = "Metrics above come from the chronological split model; the deployed model is refit on all verified 2024-25 data with the same tree count."
    booster.save_model(C.ARTIFACTS / "twin_model.json")
    (C.ARTIFACTS / "twin_metrics.json").write_text(json.dumps(res, indent=2))
    print(f"saved to {C.ARTIFACTS} in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
