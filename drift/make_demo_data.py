"""Create SYNTHETIC test data in data/demo/ so the pipeline can be tested
before real data arrives.  NOTHING here is real: invented slick, invented
currents, invented wind, invented intakes.  Never use these in the pitch.

Run from the repo root:   python -m drift.make_demo_data
"""
import json
import os

import numpy as np
import pandas as pd
import xarray as xr

OUT = "data/demo"
os.makedirs(OUT, exist_ok=True)

# --- invented slick (offshore, NW of a straight made-up coastline) ---------
slick = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "properties": {"observed_utc": "2026-10-19T06:00:00Z", "source": "DEMO-SYNTHETIC",
                       "scene_id": "none", "notes": "invented"},
        "geometry": {"type": "Polygon", "coordinates": [[
            [55.30, 25.72], [55.40, 25.72], [55.40, 25.80], [55.30, 25.80], [55.30, 25.72]]]},
    }],
}
json.dump(slick, open(f"{OUT}/slick_demo.geojson", "w"))

# --- invented currents: drift toward the SE with a tide-like wobble ---------
t = pd.date_range("2026-10-18", "2026-10-25", freq="h")
lat = np.arange(25.2, 26.0001, 0.02)
lon = np.arange(55.0, 55.9001, 0.02)
hrs = np.arange(len(t))
tide = np.sin(2 * np.pi * hrs / 12.4)
u = (0.10 + 0.05 * tide)[:, None, None] * np.ones((len(t), len(lat), len(lon)))
v = (-0.08 + 0.04 * np.cos(2 * np.pi * hrs / 12.4))[:, None, None] * np.ones_like(u)
LON, LAT = np.meshgrid(lon, lat)
land = LAT < (LON - 30.0)          # straight made-up coast running SW-NE
u[:, land] = np.nan
v[:, land] = np.nan
xr.Dataset(
    {"uo": (("time", "latitude", "longitude"), u), "vo": (("time", "latitude", "longitude"), v)},
    coords={"time": t, "latitude": lat, "longitude": lon},
).to_netcdf(f"{OUT}/currents_demo.nc")

# --- invented wind: steady NW wind, ~5 m/s ----------------------------------
pd.DataFrame({"time_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
              "u10_ms": 3.5 + 0.5 * np.sin(hrs / 7), "v10_ms": -3.5}).to_csv(
    f"{OUT}/wind_demo.csv", index=False)

# --- invented assets ----------------------------------------------------------
pd.DataFrame([
    ["demo_intake_a", "DEMO intake A", "desal_intake", 25.53, 55.50, 100000, 250000, "demo", "assumed"],
    ["demo_intake_b", "DEMO intake B", "desal_intake", 25.43, 55.38, 60000, 120000, "demo", "assumed"],
    ["demo_beach_a", "DEMO beach A", "beach", 25.60, 55.60, None, None, "demo", "assumed"],
    ["demo_intake_far", "DEMO far intake", "desal_intake", 25.20, 55.20, 40000, 80000, "demo", "assumed"],
], columns=["asset_id", "name", "type", "lat", "lon", "capacity_m3_day",
            "population_served", "source_url", "confidence"]).to_csv(f"{OUT}/assets_demo.csv", index=False)

# --- invented hypothetical release points for the exposure ranking -----------
pd.DataFrame([
    ["rp1", 25.75, 55.35, 3], ["rp2", 25.85, 55.20, 3], ["rp3", 25.65, 55.15, 3], ["rp4", 25.90, 55.45, 3],
], columns=["release_id", "lat", "lon", "radius_km"]).to_csv(f"{OUT}/release_points_demo.csv", index=False)

print("Demo data written to", OUT)
