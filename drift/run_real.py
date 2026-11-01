"""First REAL run: start from the Oct 21 slick, forecast 84 h, compare with the Oct 24 slick.

Run from the repo root:

    python -m drift.run_real                 # currents without tides (uo, vo)
    python -m drift.run_real --tides         # currents with tides + waves (utotal, vtotal)
    python -m drift.run_real --windage 0.02  # try another windage

Needs (in data/): slick_oct21.geojson, slick_oct24.geojson, currents_oct18_25.nc
Optional:         wind_oct18_25.csv  (make it with: python -m drift.get_wind)
                  assets/assets.csv  (desal intakes, beaches, mangroves)

Writes results and a picture to data/processed/drift/.
"""
import argparse
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shapely

from drift.run import load_slick, run_drift

START_UTC = "2026-10-21T02:14:30Z"   # image time of slick_oct21
HOURS = 84                           # ~ Oct 24 14:14 UTC; slick_oct24 image is 14:23
KM_PER_DEG = 111.32


def to_km(geom, lat0):
    """Flat-earth conversion of a geometry from lon/lat degrees to km."""
    c = np.cos(np.radians(lat0))
    return shapely.transform(geom, lambda xy: np.column_stack([xy[:, 0] * KM_PER_DEG * c, xy[:, 1] * KM_PER_DEG]))


def draw(ax, geom, **kw):
    for g in (geom.geoms if hasattr(geom, "geoms") else [geom]):
        x, y = g.exterior.xy
        ax.plot(x, y, **kw)
        kw.pop("label", None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--tides", action="store_true", help="use utotal/vtotal instead of uo/vo")
    ap.add_argument("--windage", type=float, default=0.03)
    ap.add_argument("--particles", type=int, default=2000)
    a = ap.parse_args()

    d = a.data
    wind = f"{d}/wind_oct18_25.csv"
    wind = wind if os.path.exists(wind) else None
    assets = f"{d}/assets/assets.csv"
    assets = assets if os.path.exists(assets) else None
    vars_ = ("utotal", "vtotal") if a.tides else ("uo", "vo")
    tag = ("tides" if a.tides else "notides") + f"_w{a.windage:g}" + ("" if wind else "_nowind")

    res = run_drift(
        slick_geojson=f"{d}/slick_oct21.geojson",
        currents_nc=f"{d}/currents_oct18_25.nc",
        wind_csv=wind,
        start_utc=START_UTC,
        hours=HOURS,
        n_particles=a.particles,
        windage=a.windage,
        assets_csv=assets,
        current_vars=vars_,
        scenario_id=f"real_{tag}",
        out_dir=f"{d}/processed/drift",
    )
    tr = res["tracks"]
    end = tr[tr.time_utc == tr.time_utc.max()]
    s21, s24 = load_slick(f"{d}/slick_oct21.geojson"), load_slick(f"{d}/slick_oct24.geojson")

    # --- simple comparison with the Oct 24 slick -------------------------------
    lat0 = float(end.lat.mean())
    s24_km = to_km(s24, lat0)
    c = np.cos(np.radians(lat0))
    px, py = end.lon.to_numpy() * KM_PER_DEG * c, end.lat.to_numpy() * KM_PER_DEG
    inside = shapely.contains_xy(s24_km, px, py).mean()
    dist = shapely.distance(s24_km, shapely.points(px, py))
    cen24 = s24_km.centroid
    cen_err = float(np.hypot(px.mean() - cen24.x, py.mean() - cen24.y))
    print(f"\nRun: {tag}   ({HOURS} h from {START_UTC})")
    print(f"particles inside Oct 24 slick : {100 * inside:5.1f} %")
    print(f"particles within 5 km of it   : {100 * (dist <= 5).mean():5.1f} %")
    print(f"particles within 10 km of it  : {100 * (dist <= 10).mean():5.1f} %")
    print(f"centre of particles vs centre of Oct 24 slick: {cen_err:.1f} km apart")
    print(f"stranded (stopped on land/off grid): {100 * res['stranded_fraction']:.0f} %")
    if len(res["arrivals"]):
        print("\n" + res["arrivals"].to_string(index=False))

    # --- picture ---------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 7))
    draw(ax, s21, color="tab:blue", label="Oct 21 slick (start)")
    draw(ax, s24, color="tab:red", label="Oct 24 slick (observed)")
    ax.scatter(end.lon, end.lat, s=2, c="orange", alpha=0.5, label=f"forecast after {HOURS} h")
    if assets:
        as_ = pd.read_csv(assets).dropna(subset=["lat", "lon"])
        ax.scatter(as_.lon, as_.lat, marker="^", c="k", s=40, label="assets")
    ax.set_xlabel("lon"); ax.set_ylabel("lat"); ax.legend(loc="best")
    ax.set_title(f"IntakeWatch drift check ({tag})")
    ax.set_aspect(1 / np.cos(np.radians(lat0)))
    out = f"{d}/processed/drift/real_{tag}.png"
    fig.savefig(out, dpi=130, bbox_inches="tight")
    print("\nsaved picture:", out)


if __name__ == "__main__":
    main()
