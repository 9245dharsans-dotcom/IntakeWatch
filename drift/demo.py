"""Run the drift model on the SYNTHETIC demo data and save a picture.
Run from the repo root:   python -m drift.demo
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from drift.run import run_drift

res = run_drift(
    slick_geojson="data/demo/slick_demo.geojson",
    currents_nc="data/demo/currents_demo.nc",
    wind_csv="data/demo/wind_demo.csv",
    start_utc="2026-10-19T06:00:00Z",
    hours=72,
    assets_csv="data/demo/assets_demo.csv",
    scenario_id="demo",
    out_dir="data/processed/drift",
)
print(res["arrivals"].to_string(index=False))
print("stranded fraction:", round(res["stranded_fraction"], 2))

tr, assets = res["tracks"], pd.read_csv("data/demo/assets_demo.csv")
fig, ax = plt.subplots(figsize=(7, 6))
first, last = tr[tr.time_utc == tr.time_utc.min()], tr[tr.time_utc == tr.time_utc.max()]
ax.scatter(first.lon, first.lat, s=3, label="start")
ax.scatter(last.lon, last.lat, s=3, label="after 72 h")
ax.scatter(assets.lon, assets.lat, marker="^", c="k", label="assets")
ax.set_title("DEMO (synthetic data)"); ax.legend(); ax.set_xlabel("lon"); ax.set_ylabel("lat")
fig.savefig("data/processed/drift/demo.png", dpi=120)
print("saved data/processed/drift/demo.png")
