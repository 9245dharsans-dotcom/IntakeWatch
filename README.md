# IntakeWatch

**From satellite to safe water: oil-spill drift forecasts with a countdown for every desalination intake.**

Team Sail Space · Supernova x SpacePoint Hackathon, BITS Pilani Dubai Campus · Theme: Seas of Data

## The problem

In October 2026 oil from the *Gem No.2* spilled off Umm Al Quwain (UAE). Satellites imaged slicks within days, but beach closures only followed later. The UAE's northern emirates depend on seawater desalination, and a plant that draws in oil can lose its output for days. Operators have no tool that turns "a slick was seen" into "oil reaches *our* intake in X hours, and here is the proof when it does."

## Our solution

```
Sentinel-1 spots the slick  ->  IntakeWatch forecasts drift + countdown  ->  IW-1 buoy confirms oil at the intake  ->  alert to plant operator  ->  operator closes intake
```

- **Early warning (hours to days ahead):** a drift model moves the observed slick with ocean currents and wind and gives an arrival-time *window* (first, median) for each intake, beach and mangrove area.
- **Impact:** each countdown is translated into water at risk (m3/day) for the plant concerned.
- **Confirmation (before oil reaches the intake):** the IW-1 sensor buoy, moored upstream of an intake, detects oil in the water and alerts the operator. A CAD design, exploded view and costed parts list are in `cad/`.
- **Replay:** we replay the *Gem No.2* spill, starting from the Sentinel-1 slick of 21 Oct 2026 02:14 UTC and comparing the 84-hour forecast with the slick observed on 24 Oct 2026 14:23 UTC.

## What is in this repo

| Path | Contents |
|---|---|
| `drift_model.py` | Drift model: `drift()` moves particles with current + windage x wind + diffusion, returns tracks and arrival-time windows per target |
| `run_drift.py` | Loads slicks, currents and wind, runs the forecast, scores it against the 24 Oct slick, plots the result |
| `data/` | Slick outlines (Cerulean / Sentinel-1), Copernicus Marine currents, desalination plant table |
| `app/` | Streamlit app: map, drift animation, countdown cards |
| `cad/` | IW-1 buoy: render, exploded view, STEP file, `parts_list.csv` |

## Tech stack

Python, NumPy, SciPy, xarray / netCDF4, Matplotlib, Streamlit, Onshape (CAD).

Data: Sentinel-1 slick detections via SkyTruth Cerulean (Copernicus Sentinel data), Copernicus Marine currents, Open-Meteo wind, public desalination-plant sources listed in `data/desal_plants.csv`.

## How to run

```bash
git clone https://github.com/<owner>/IntakeWatch.git
cd IntakeWatch
python3 -m venv .venv && source .venv/bin/activate
pip install numpy scipy xarray netcdf4 matplotlib streamlit
```

Forecast and validation:

```bash
python run_drift.py \
  --slick data/slick_oct21.geojson --valid data/slick_oct24.geojson \
  --currents data/currents_oct18_25.nc --wind data/wind_openmeteo.csv \
  --targets data/targets.csv --out out/
```

Outputs in `out/`: `summary.json` (arrival windows, validation scores), `forecast_vs_observed.png`, `tracks.npy`.
Useful options: `--pair utotal` (currents incl. tides), `--windage 0.03`, `--deflection 0`, `--diffusion 2.0`.

App (TODO: confirm entry point): `streamlit run app/<entry_file>.py`

## Results

TODO: fill from `out/summary.json` after the final run. Report only what the run produced: fraction of forecast particles inside or within 5 km of the 24 Oct slick, centroid error in km, arrival windows for the targets.

## Limitations 

- The forecast starts on 21 Oct. Cerulean has no *Gem No.2* slick for 19 Oct, so we do not claim an earlier detection.
- Currents are on a ~9 km grid, so near-shore arrival times are rough. We show windows, not single numbers.
- The drift model is deliberately simple (currents + windage + random diffusion, no weathering or evaporation).
- Desalination plant data is compiled from public sources; every row has an `estimate_flag`. Intake positions are read from satellite imagery and are approximate where marked. "People-equivalent" figures assume a per-person water use and are not official served-population numbers.
- The buoy is a concept design, not a tested device.

## Credits

Contains modified Copernicus Sentinel data (2026), processed by SkyTruth Cerulean. Currents: Copernicus Marine Service. Wind: Open-Meteo.

## Team

SailSpace
