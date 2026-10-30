# drift/ (owner: Kamya (A2))

Forecasts where an oil slick drifts and when it reaches each intake, beach or mangrove area.

## How it works

Particles are released inside the slick polygon. Every hour each particle moves with:

    ocean current + (windage x wind) + small random spread

A particle that reaches a cell with no current data (land or outside the data grid) stops. We treat that as stranded.

## Use it

Run from the repo root:

```python
from drift.run import run_drift

result = run_drift(
    slick_geojson="data/.../slick.geojson",   # or a shapely geometry
    currents_nc="data/.../currents.nc",
    wind_csv="data/.../wind.csv",
    start_utc="2026-10-19T06:00:00Z",
    hours=72,
    assets_csv="data/.../assets.csv",         # optional
)

result["tracks"]    # particle_id, time_utc, lat, lon
result["arrivals"]  # asset_id, first_arrival_utc, hours_to_arrival, fraction_particles_arrived
```

## Inputs

| Input | Format |
|---|---|
| Slick | GeoJSON polygon, WGS84 (note GeoJSON order is lon, lat) |
| Currents | NetCDF with variables `uo`, `vo` (m/s) and dims `time`, `latitude`, `longitude` |
| Wind | CSV with `time_utc, u10_ms, v10_ms` (m/s). Alternatively `wind_speed_ms, wind_dir_deg`. Optional `lat, lon` columns for several points |
| Assets | CSV with at least `asset_id, lat, lon` |

All times are UTC. Coordinates are `lat` and `lon` in decimal degrees. Currents and wind must cover the whole run (start to start + hours), otherwise the function raises an error.

## Settings you may change

| Setting | Default | Meaning |
|---|---|---|
| `hours` | 72 | forecast length |
| `n_particles` | 1000 | more is smoother but slower |
| `windage` | 0.03 | fraction of wind speed applied to the oil |
| `arrival_radius_m` | 5000 | an asset counts as reached within this distance. Say this value on the slide |
| `diffusivity_m2s` | 10 | random spread |
| `seed` | 42 | same seed gives the same result |

## Test it without real data

```
python -m drift.make_demo_data   # makes invented test files in data/demo/
python -m drift.demo             # runs the model and saves a picture
```

The demo data is invented. Never use it in the pitch, and do not commit `data/demo/`.

## Known limits

- Currents are coarse near the coast, so oil can strand a little early. This is why the arrival radius is 5 km.
- No oil weathering (evaporation, emulsification) in this simple model.
- Windage is a tuned value, not measured.
- Results are only as good as the slick outline, currents and wind we feed in.