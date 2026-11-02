"""Download hourly 10 m wind from Open-Meteo for the area of the currents file.

Run from the repo root:

    python -m drift.get_wind

Writes data/wind_oct18_25.csv with columns:
    time_utc, lat, lon, wind_speed_ms, wind_dir_deg
(wind_dir_deg = direction the wind blows FROM, in degrees; run.py converts it)

No account needed. Uses only Python's standard library plus xarray (already installed).
"""
import json
import sys
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd
import xarray as xr

CURRENTS = "data/currents_oct18_25.nc"
OUT = "data/wind_oct18_25.csv"
START, END = "2026-10-18", "2026-10-25"
N_PER_SIDE = 3  # 3 x 3 = 9 wind points across the area

# Historical (ERA5-based) first, then the "historical forecast" service, which
# also covers the most recent days that ERA5 may not have yet.
URLS = [
    "https://archive-api.open-meteo.com/v1/archive",
    "https://historical-forecast-api.open-meteo.com/v1/forecast",
]


def grid_points(nc_path, n=N_PER_SIDE):
    ds = xr.open_dataset(nc_path)
    ren = {k: v for k, v in (("lat", "latitude"), ("lon", "longitude")) if k in ds.coords}
    ds = ds.rename(ren)
    lat0, lat1 = float(ds.latitude.min()), float(ds.latitude.max())
    lon0, lon1 = float(ds.longitude.min()), float(ds.longitude.max())
    # stay a little inside the edges
    lats = np.linspace(lat0, lat1, n + 2)[1:-1]
    lons = np.linspace(lon0, lon1, n + 2)[1:-1]
    return [(round(a, 3), round(b, 3)) for a in lats for b in lons]


def parse_response(data, points):
    """Open-Meteo JSON -> DataFrame. `data` is a dict (1 point) or a list (many)."""
    if isinstance(data, dict):
        data = [data]
    frames = []
    for (lat, lon), d in zip(points, data):
        h = d["hourly"]
        df = pd.DataFrame(
            {
                "time_utc": pd.to_datetime(h["time"]).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "lat": lat,
                "lon": lon,
                "wind_speed_ms": h["wind_speed_10m"],
                "wind_dir_deg": h["wind_direction_10m"],
            }
        )
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    return out


def fetch(base_url, points):
    q = {
        "latitude": ",".join(str(p[0]) for p in points),
        "longitude": ",".join(str(p[1]) for p in points),
        "start_date": START,
        "end_date": END,
        "hourly": "wind_speed_10m,wind_direction_10m",
        "wind_speed_unit": "ms",  # IMPORTANT: metres per second, not km/h
        "timezone": "UTC",
    }
    url = base_url + "?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    points = grid_points(CURRENTS)
    print(f"Requesting wind for {len(points)} points from {START} to {END} ...")
    last_err = None
    for base in URLS:
        try:
            df = parse_response(fetch(base, points), points)
            if df["wind_speed_ms"].isna().any():
                raise ValueError("response has missing values")
            df.to_csv(OUT, index=False)
            print(f"Saved {len(df)} rows to {OUT}  (source: {base})")
            print(df.groupby("time_utc").size().describe()[["count"]].to_string())
            print("wind speed range (m/s):", round(df.wind_speed_ms.min(), 1), "to", round(df.wind_speed_ms.max(), 1))
            return
        except Exception as e:  # try the next service
            last_err = e
            print(f"  {base} failed: {e}")
    sys.exit(f"Could not download wind. Last error: {last_err}")


if __name__ == "__main__":
    main()
