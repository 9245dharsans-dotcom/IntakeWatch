"""B1: turn drift arrival times into impact numbers (litres/day and people at risk).

Run from the repo root, after drift.run_real has produced an arrivals file:

    python -m impact.impact                       # uses the 'notides' run
    python -m impact.impact --arrivals data/processed/drift/real_tides_w0.03_arrivals.csv

Writes data/processed/impact.csv and prints one plain sentence per asset
that you can paste straight into the pitch.
"""
import argparse
import glob
import os

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arrivals", default=None, help="arrivals csv from drift (default: newest real_*_arrivals.csv)")
    ap.add_argument("--assets", default="data/assets/assets.csv")
    ap.add_argument("--out", default="data/processed/impact.csv")
    a = ap.parse_args()

    arr_path = a.arrivals or max(glob.glob("data/processed/drift/real_*_arrivals.csv"), key=os.path.getmtime)
    arr = pd.read_csv(arr_path)
    assets = pd.read_csv(a.assets)
    print("arrivals file:", arr_path)

    m = assets.merge(arr, on="asset_id", how="left")
    m["reached"] = m["hours_to_arrival"].notna()
    # litres per day: 1 m3 = 1000 litres. Only desal plants have a capacity.
    m["litres_per_day_at_risk"] = (m["capacity_m3_day"] * 1000).where(m["reached"])
    m["people_at_risk"] = m["population_served"].where(m["reached"])
    m["exposure_rank"] = m["hours_to_arrival"].rank(method="min")   # 1 = oil arrives first
    cols = ["asset_id", "name", "type", "lat", "lon", "reached", "first_arrival_utc",
            "hours_to_arrival", "fraction_particles_arrived",
            "litres_per_day_at_risk", "people_at_risk", "exposure_rank", "confidence", "notes"]
    out = m[[c for c in cols if c in m.columns]].sort_values("exposure_rank")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    out.to_csv(a.out, index=False)

    print("\nPitch sentences:")
    for r in out.itertuples():
        if r.reached:
            lit = f"{r.litres_per_day_at_risk / 1e6:,.0f} million litres/day" if pd.notna(r.litres_per_day_at_risk) else None
            extra = f": {lit} of water supply at risk" if lit else ""
            print(f"- {r.name}: oil reaches it in about {r.hours_to_arrival:.0f} h{extra}  [{r.confidence}]")
        else:
            print(f"- {r.name}: not reached within the forecast")
    print("\nsaved:", a.out)


if __name__ == "__main__":
    main()
