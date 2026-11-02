# IntakeWatch

**From satellite to safe water: oil-spill drift forecasts with a countdown for every desalination intake.**

Team Sail Space · Supernova x SpacePoint Hackathon, BITS Pilani Dubai Campus · Theme: Seas of Data

## The problem

In October 2026 oil from the *Gem No.2* spilled off Umm Al Quwain (UAE). Satellites imaged the slick on 21 Oct, but the spill was only confirmed publicly on 23 Oct and beaches closed after that. The UAE's northern emirates depend on seawater desalination, and a plant that draws in oil can lose its output for days. Operators have no tool that turns "a slick was seen" into "oil reaches *our* intake in X hours", plus proof when it does.

## Our solution

Sentinel-1 spots the slick → IntakeWatch forecasts drift + countdown → IW-1 buoy confirms oil upstream of the intake → 4G alert to plant operator → operator can close the intake in time

- **Early warning (hours to days ahead):** a drift model moves the observed slick with ocean currents and wind and gives an arrival-time window for each desalination intake.
- **Impact:** each countdown is translated into people and litres/day of water at risk.
- **Confirmation (about 5 to 14 hours before oil reaches the intake):** the IW-1 sensor buoy, moored ~5 km up-drift of an intake, detects oil with a UV-fluorescence sensor and sends a 4G alert.
- **Replay:** we replay the *Gem No.2* spill from the Sentinel-1 slick of 21 Oct 2026 02:14 UTC and compare the forecast with the slick observed on 24 Oct 2026.

## What is in this repo

| Path | Contents |
|---|---|
| `drift/` | Drift model and runs: `run_real.py` (forecast on the real slick), `get_wind.py` (wind download) |
| `impact/impact.py` | Turns arrival times into people and water at risk |
| `data/` | Slick outlines (Cerulean / Sentinel-1), Copernicus Marine currents, wind, intake and buoy positions (`data/assets/`), model outputs (`data/processed/`) |
| `app/app.py` | Streamlit app: replay slider, map, countdown cards, buoy positions |
| `cad/` | IW-1 buoy: render, exploded view, STEP file, parts list, system diagram, placement map |

## Tech stack

Python, NumPy, pandas, xarray / netCDF4, Matplotlib, Streamlit, Folium, Onshape (CAD).

Data: Sentinel-1 slick detections via SkyTruth Cerulean, Copernicus Marine currents, Open-Meteo wind, public desalination-plant sources.

## How to run

```bash
git clone https://github.com/9245dharsans-dotcom/IntakeWatch.git
cd IntakeWatch
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install numpy pandas xarray netcdf4 matplotlib streamlit folium streamlit-folium
streamlit run app/app.py
```

The app opens at http://localhost:8501. The forecast outputs are already in `data/processed/`, so the app runs without re-running the model.

To re-run the drift forecast: `python drift/run_real.py`

## Results (Gem No.2 replay, 84 h forecast from 21 Oct 02:14 UTC)

| Intake | Oil within 5 km | Arrival after satellite image |
|---|---|---|
| Umm Al Quwain IWP | yes | T+38 h (Thu 22 Oct 20:14 UAE) |
| Ras Al Khaimah Al Hamra SWRO | yes | T+48 h (Fri 23 Oct 06:14 UAE) |
| Ajman Al Zawra SWRO | no | not reached in 84 h |
| Sharjah Hamriyah SWRO | no | not reached in 84 h |

The spill was confirmed publicly on 23 Oct, so IntakeWatch's countdown would have been running about two days earlier.

## IW-1 buoy (CAD)

- 3D model (opens in browser): https://cad.onshape.com/documents/deff1cf110091c8aeea66122/w/954e32585dce9f36b9fb6a9a/e/5a808307233ffceeecf55385
- About $2,700 per buoy; ~24.5 kg buoy on a hull that supports ~200 kg; 20 W solar + 256 Wh battery gives ~4 days without sun
- Files in `cad/`

## Limitations

- The forecast starts on 21 Oct. Cerulean has no *Gem No.2* slick for 19 Oct, so we do not claim an earlier detection.
- Currents are on a ~9 km grid, so near-shore arrival times are rough. We show windows, not single numbers.
- The drift model is deliberately simple (currents + windage + diffusion, no weathering or evaporation).
- Desalination plant data comes from public sources; intake positions are approximate.
- The buoy is a concept design, not a tested device.

## Credits

Contains modified Copernicus Sentinel data (2026), processed by SkyTruth Cerulean. Currents: Copernicus Marine Service. Wind: Open-Meteo.

## Team
SailSpace: 
1. Kamya Chandebhamar
2. Eshel Wasim
3. Dharsan Srinivasan
4. Eesha Boob
