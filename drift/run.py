"""IntakeWatch drift model (owner: A2).

Simple Lagrangian particle model for surface oil:

    particle velocity = surface current + windage * wind(10 m) + random walk

Particles are released inside the slick polygon and stepped forward in time.
A particle that reaches a cell with no current data (land, or outside the
data grid) STOPS moving. We treat that as "stranded / beached".

Everyone else imports ONE function:

    from drift.run import run_drift

Conventions (see README section 4): UTC times, lat/lon in WGS84, metres, m/s.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
import shapely
import xarray as xr
from shapely.geometry import shape
from shapely.ops import unary_union

M_PER_DEG = 111_320.0  # metres per degree of latitude


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _to_naive_utc(ts) -> pd.Timestamp:
    """Any timestamp string/object -> timezone-naive UTC pandas Timestamp."""
    ts = pd.Timestamp(ts)
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return ts


def _iso(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_slick(src):
    """Slick polygon from a GeoJSON path OR a shapely geometry.

    GeoJSON may be a FeatureCollection, a Feature, or a bare geometry.
    Multiple features are merged into one geometry.
    """
    if hasattr(src, "geom_type"):
        return src
    with open(src) as f:
        gj = json.load(f)
    if gj.get("type") == "FeatureCollection":
        geoms = [shape(ft["geometry"]) for ft in gj["features"]]
    elif gj.get("type") == "Feature":
        geoms = [shape(gj["geometry"])]
    else:
        geoms = [shape(gj)]
    return unary_union(geoms)


def release_particles(geom, n: int, rng: np.random.Generator):
    """n random points uniformly inside geom -> (lat, lon) arrays.

    Works for a MultiPolygon made of many small patches: particles are shared
    between patches in proportion to patch area, then placed inside each patch.
    """
    parts = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    parts = [p for p in parts if p.area > 0]
    if not parts:
        raise ValueError("Slick geometry is empty.")
    areas = np.array([p.area for p in parts])
    counts = rng.multinomial(n, areas / areas.sum())
    xs, ys = [], []
    for part, c in zip(parts, counts):
        if c == 0:
            continue
        minx, miny, maxx, maxy = part.bounds
        got, tries = 0, 0
        while got < c:
            cx = rng.uniform(minx, maxx, max(20 * c, 200))
            cy = rng.uniform(miny, maxy, max(20 * c, 200))
            inside = shapely.contains_xy(part, cx, cy)
            take = min(c - got, int(inside.sum()))
            xs.extend(cx[inside][:take])
            ys.extend(cy[inside][:take])
            got += take
            tries += 1
            if tries > 2000:
                raise ValueError("Could not place particles: is the slick polygon valid?")
    xs, ys = np.array(xs), np.array(ys)
    order = rng.permutation(len(xs))
    return ys[order], xs[order]


# --------------------------------------------------------------------------
# forcing
# --------------------------------------------------------------------------
class Currents:
    """Surface currents from a Copernicus Marine NetCDF (variables uo, vo)."""

    def __init__(self, path: str, u_var: str = "uo", v_var: str = "vo"):
        ds = xr.open_dataset(path)
        ren = {}
        for short, long in (("lat", "latitude"), ("lon", "longitude")):
            if short in ds.coords and long not in ds.coords:
                ren[short] = long
        ds = ds.rename(ren)
        for d in ("depth", "depthu", "deptht", "elevation"):
            if d in ds.dims:
                ds = ds.isel({d: 0})
        ds = ds.sortby(["latitude", "longitude"])
        self.u = ds[u_var].load()
        self.v = ds[v_var].load()
        self.tmin = pd.Timestamp(self.u["time"].values.min())
        self.tmax = pd.Timestamp(self.u["time"].values.max())

    def at(self, t: pd.Timestamp, lat: np.ndarray, lon: np.ndarray):
        """Interpolated (u, v) in m/s at positions. NaN where land / off-grid."""
        pts = dict(
            time=np.datetime64(t),
            latitude=xr.DataArray(lat, dims="p"),
            longitude=xr.DataArray(lon, dims="p"),
        )
        return (
            self.u.interp(**pts, method="linear").values,
            self.v.interp(**pts, method="linear").values,
        )


class NoWind:
    """Zero wind. Used only for quick tests when no wind file exists yet."""

    tmin = pd.Timestamp.min
    tmax = pd.Timestamp.max

    def at(self, t, lat, lon):
        return np.zeros_like(lat), np.zeros_like(lat)


class Wind:
    """10 m wind from a CSV.

    Required column: time_utc
    Either  u10_ms, v10_ms   (east / north components, m/s)
    or      wind_speed_ms, wind_dir_deg  (direction wind blows FROM, degrees)
    Optional: lat, lon (several points). If absent, one value applies everywhere.
    Lines starting with # are ignored.
    """

    def __init__(self, path: str):
        df = pd.read_csv(path, comment="#")
        df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True).dt.tz_convert(None)
        if "u10_ms" not in df.columns:
            spd = df["wind_speed_ms"].to_numpy()
            d = np.radians(df["wind_dir_deg"].to_numpy())
            df["u10_ms"] = -spd * np.sin(d)
            df["v10_ms"] = -spd * np.cos(d)
        if "lat" not in df.columns:
            df["lat"], df["lon"] = 0.0, 0.0
        self.tmin, self.tmax = df["time_utc"].min(), df["time_utc"].max()
        self.t0 = self.tmin
        self.locs, self.series = [], []
        for (la, lo), g in df.groupby(["lat", "lon"]):
            g = g.sort_values("time_utc")
            ts = (g["time_utc"] - self.t0).dt.total_seconds().to_numpy()
            self.series.append((ts, g["u10_ms"].to_numpy(), g["v10_ms"].to_numpy()))
            self.locs.append((la, lo))
        self.locs = np.array(self.locs)

    def at(self, t: pd.Timestamp, lat: np.ndarray, lon: np.ndarray):
        s = (t - self.t0).total_seconds()
        U = np.array([np.interp(s, ts, u) for ts, u, _ in self.series])
        V = np.array([np.interp(s, ts, v) for ts, _, v in self.series])
        if len(U) == 1:
            return np.full_like(lat, U[0]), np.full_like(lat, V[0])
        coslat = np.cos(np.radians(lat.mean()))
        d = (lat[:, None] - self.locs[None, :, 0]) ** 2 + (
            (lon[:, None] - self.locs[None, :, 1]) * coslat
        ) ** 2
        idx = d.argmin(axis=1)
        return U[idx], V[idx]


# --------------------------------------------------------------------------
# arrival detection
# --------------------------------------------------------------------------
def compute_arrivals(lat_h, lon_h, times, dt_s, assets: pd.DataFrame, radius_m: float):
    """Which assets does the oil reach, and when?

    lat_h, lon_h : arrays (T, N)  particle history
    times        : list of Timestamps, length T
    assets       : DataFrame with asset_id, lat, lon
    An asset is 'reached' when any particle is within radius_m of it.
    """
    rows = []
    for a in assets.itertuples():
        dy = (lat_h - a.lat) * M_PER_DEG
        dx = (lon_h - a.lon) * M_PER_DEG * np.cos(np.radians(a.lat))
        within = (dx * dx + dy * dy) <= radius_m**2  # (T, N)
        step_hit = within.any(axis=1)
        frac = within.any(axis=0).mean()
        if step_hit.any():
            k = int(step_hit.argmax())
            rows.append((a.asset_id, _iso(times[k]), k * dt_s / 3600.0, frac))
        else:
            rows.append((a.asset_id, None, np.nan, 0.0))
    return pd.DataFrame(
        rows,
        columns=["asset_id", "first_arrival_utc", "hours_to_arrival", "fraction_particles_arrived"],
    )


# --------------------------------------------------------------------------
# main entry point
# --------------------------------------------------------------------------
def run_drift(
    slick_geojson,
    currents_nc: str,
    wind_csv: str | None,
    start_utc: str,
    hours: int = 72,
    n_particles: int = 1000,
    windage: float = 0.03,
    seed: int = 42,
    assets_csv: str | None = None,
    arrival_radius_m: float = 5000.0,
    diffusivity_m2s: float = 10.0,
    dt_s: float = 3600.0,
    scenario_id: str | None = None,
    out_dir: str | None = None,
    current_vars: tuple = ("uo", "vo"),
) -> dict:
    """Run one drift forecast.

    Parameters
    ----------
    slick_geojson : path to GeoJSON, or a shapely geometry (for hypothetical spills)
    currents_nc   : Copernicus Marine NetCDF with uo, vo
    wind_csv      : see class Wind
    start_utc     : e.g. "2026-10-19T06:30:00Z"
    hours         : forecast length
    wind_csv      : path, or None to run on currents only (for quick tests)
    current_vars  : ("uo","vo") = currents without tides (default);
                    ("utotal","vtotal") = with tides + wave drift. Use ONE pair.
    windage       : fraction of 10 m wind speed applied to the oil (typ. 0.01-0.04)
    arrival_radius_m : asset counts as reached within this distance. Default 5 km
                    because coarse current grids cannot get particles closer to
                    shore. STATE THIS VALUE ON THE SLIDE.
    assets_csv    : optional, needs asset_id, lat, lon  (data/assets/assets.csv)
    scenario_id, out_dir : if both given, CSVs are written to out_dir

    Returns
    -------
    {'tracks':   DataFrame[particle_id, time_utc, lat, lon],
     'arrivals': DataFrame[asset_id, first_arrival_utc, hours_to_arrival,
                           fraction_particles_arrived],
     'stranded_fraction': float}
    """
    rng = np.random.default_rng(seed)
    start = _to_naive_utc(start_utc)
    end = start + pd.Timedelta(hours=hours)

    geom = load_slick(slick_geojson)
    cur = Currents(currents_nc, *current_vars)
    if wind_csv:
        wnd = Wind(wind_csv)
    else:
        print("WARNING: no wind file given, running with CURRENTS ONLY (wind = 0).")
        wnd = NoWind()

    for name, f in (("currents", cur), ("wind", wnd)):
        if start < f.tmin or end > f.tmax:
            raise ValueError(
                f"{name} data covers {f.tmin} to {f.tmax} but the run needs {start} to {end}"
            )

    lat, lon = release_particles(geom, n_particles, rng)
    n_steps = int(round(hours * 3600 / dt_s))
    sigma = np.sqrt(2 * diffusivity_m2s * dt_s)  # random-walk step, metres
    active = np.ones(n_particles, dtype=bool)

    times = [start + pd.Timedelta(seconds=k * dt_s) for k in range(n_steps + 1)]
    lat_h = np.empty((n_steps + 1, n_particles))
    lon_h = np.empty((n_steps + 1, n_particles))

    for k, t in enumerate(times):
        lat_h[k], lon_h[k] = lat, lon
        if k == n_steps:
            break
        uc, vc = cur.at(t, lat, lon)
        uw, vw = wnd.at(t, lat, lon)
        active &= ~(np.isnan(uc) | np.isnan(vc))  # land / off-grid -> stops
        if k == 0 and active.mean() < 0.8:
            print(
                f"WARNING: {100 * (1 - active.mean()):.0f}% of particles start on land "
                "or outside the current grid. Check slick position and grid coverage."
            )
        u = np.nan_to_num(uc) + windage * uw
        v = np.nan_to_num(vc) + windage * vw
        du = u * dt_s + rng.normal(0, sigma, n_particles)
        dv = v * dt_s + rng.normal(0, sigma, n_particles)
        lat = np.where(active, lat + dv / M_PER_DEG, lat)
        lon = np.where(active, lon + du / (M_PER_DEG * np.cos(np.radians(lat))), lon)

    tracks = pd.DataFrame(
        {
            "particle_id": np.tile(np.arange(n_particles), n_steps + 1),
            "time_utc": np.repeat([_iso(t) for t in times], n_particles),
            "lat": lat_h.ravel(),
            "lon": lon_h.ravel(),
        }
    )

    if assets_csv:
        assets = pd.read_csv(assets_csv).dropna(subset=["lat", "lon"])
        arrivals = compute_arrivals(lat_h, lon_h, times, dt_s, assets, arrival_radius_m)
    else:
        arrivals = pd.DataFrame(
            columns=["asset_id", "first_arrival_utc", "hours_to_arrival", "fraction_particles_arrived"]
        )

    result = {"tracks": tracks, "arrivals": arrivals, "stranded_fraction": float(1 - active.mean())}

    if out_dir and scenario_id:
        os.makedirs(out_dir, exist_ok=True)
        tracks.to_csv(os.path.join(out_dir, f"{scenario_id}_tracks.csv"), index=False)
        arrivals.to_csv(os.path.join(out_dir, f"{scenario_id}_arrivals.csv"), index=False)

    return result
