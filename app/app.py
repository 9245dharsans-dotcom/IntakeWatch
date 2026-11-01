import json
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# ---------- settings ----------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TRACKS_CSV = DATA / "processed" / "drift" / "real_notides_w0.02_tracks.csv"
IMPACT_CSV = DATA / "processed" / "impact.csv"
BUOYS_CSV = DATA / "assets" / "buoys.csv"
SLICK_START = DATA / "slick_oct21.geojson"
SLICK_CHECK = DATA / "slick_oct24.geojson"

ARRIVAL_RADIUS_M = 5000   # Kamya's model: "reached" = oil within 5 km
SHOW_EVERY = 4            # draw 1 in 4 particles so the map stays fast
COLORS = {"safe": "green", "incoming": "orange", "arrived": "red"}

st.set_page_config(page_title="IntakeWatch", layout="wide")


# ---------- loading (cached: runs once, not on every slider move) ----------
@st.cache_data
def load_geojson(path):
    with open(path) as f:
        return json.load(f)


@st.cache_data
def load_tracks(path):
    df = pd.read_csv(path)
    df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True)
    start = df["time_utc"].min()
    df["hour"] = ((df["time_utc"] - start).dt.total_seconds() // 3600).astype(int)
    return df, start


@st.cache_data
def load_impact(path):
    df = pd.read_csv(path)
    df["first_arrival_utc"] = pd.to_datetime(df["first_arrival_utc"], utc=True)
    df["short_name"] = df["name"].str.split(" \\(").str[0]
    return df.sort_values("hours_to_arrival", na_position="last")


@st.cache_data
def load_buoys(path):
    if not Path(path).exists():   # app still works if the file isn't there
        return None
    return pd.read_csv(path)


def status(row, hour):
    if pd.isna(row["hours_to_arrival"]):
        return "safe"
    return "arrived" if hour >= row["hours_to_arrival"] else "incoming"


tracks, start_utc = load_tracks(TRACKS_CSV)
impact = load_impact(IMPACT_CSV)
buoys = load_buoys(BUOYS_CSV)
slick_start = load_geojson(SLICK_START)
slick_check = load_geojson(SLICK_CHECK)
max_hour = int(tracks["hour"].max())
start_uae = start_utc.tz_convert("Asia/Dubai")

# ---------- sidebar ----------
st.sidebar.header("Replay time")
hour = st.sidebar.slider("Hours after satellite image", 0, max_hour, 0)
now_utc = start_utc + pd.Timedelta(hours=hour)
now_uae = now_utc.tz_convert("Asia/Dubai")
# one element for all three, so they always refresh together
st.sidebar.markdown(
    f"### {now_uae:%a %d %b, %H:%M} UAE\n"
    f"{now_utc:%a %d %b, %H:%M} UTC  \n"
    f"**T+{hour} h** after satellite image"
)
st.sidebar.markdown("---")
show_check = st.sidebar.checkbox("Show real slick on 24 Oct (validation)")
st.sidebar.caption(
    f"Start slick: Sentinel-1, {start_utc:%d %b %H:%M} UTC, via SkyTruth Cerulean. "
    f"An intake counts as reached when oil comes within {ARRIVAL_RADIUS_M // 1000} km."
)

# ---------- header ----------
st.title("IntakeWatch")
st.caption("Gem No.2 oil spill replay, off Umm Al Quwain, October 2026")
st.info(
    f"Satellite saw the slick: **{start_uae:%a %d %b, %H:%M} UAE**. "
    "Ministry confirmed the spill: **Fri 23 Oct**. "
    "IntakeWatch's countdown would have been running for about two days."
)

# ---------- countdown cards ----------
st.subheader("Countdown to each desalination intake")
cols = st.columns(len(impact))
for col, (_, row) in zip(cols, impact.iterrows()):
    with col:
        s = status(row, hour)
        if s == "safe":
            st.metric(row["short_name"], "Not reached")
            st.caption(f"No oil within {ARRIVAL_RADIUS_M // 1000} km in {max_hour} h")
        else:
            left = row["hours_to_arrival"] - hour
            st.metric(row["short_name"], "OIL ARRIVED" if s == "arrived" else f"{left:.0f} h left")
            arr_uae = row["first_arrival_utc"].tz_convert("Asia/Dubai")
            st.caption(
                f"Arrives {arr_uae:%a %d %b %H:%M} UAE "
                f"(T+{row['hours_to_arrival']:.0f} h after satellite image) · "
                f"{row['fraction_particles_arrived']:.0%} of oil particles"
            )
            st.caption(f"{row['people_at_risk'] / 1e6:.1f} M people · {row['litres_per_day_at_risk'] / 1e6:.0f} M litres/day")
        st.caption("Intake location: approximate")

# ---------- map key ----------
st.markdown(
    "**Map key:** red dots = forecast oil · dashed outline = satellite slick, 21 Oct · "
    "purple = real satellite slick, 24 Oct · intake pins: 🟢 not reached, 🟠 oil on the way, 🔴 oil arrived "
    f"(circle = {ARRIVAL_RADIUS_M // 1000} km) · ⚓ blue pins = oil-sensor buoys"
)

# ---------- map ----------
m = folium.Map(location=[25.68, 55.6], zoom_start=10, tiles="OpenStreetMap")
m.fit_bounds([[25.40, 55.15], [26.05, 55.85]])   # always show all 4 intakes + the slick

folium.GeoJson(
    slick_start,
    name="Satellite slick (start)",
    style_function=lambda f: {"color": "black", "fillColor": "black", "fillOpacity": 0.1, "weight": 2, "dashArray": "6,4"},
).add_to(m)

if show_check:
    folium.GeoJson(
        slick_check,
        name="Satellite slick, 24 Oct (validation)",
        style_function=lambda f: {"color": "purple", "fillColor": "purple", "fillOpacity": 0.3, "weight": 2},
    ).add_to(m)

now = tracks[(tracks["hour"] == hour) & (tracks["particle_id"] % SHOW_EVERY == 0)]
for lat, lon in zip(now["lat"], now["lon"]):
    folium.CircleMarker([lat, lon], radius=2, color="#d62728", fill=True, fill_opacity=0.8, weight=0).add_to(m)

for _, row in impact.iterrows():
    c = COLORS[status(row, hour)]
    folium.Circle([row["lat"], row["lon"]], radius=ARRIVAL_RADIUS_M, color=c, fill=True, fill_opacity=0.08, weight=1).add_to(m)
    folium.Marker(
        [row["lat"], row["lon"]],
        tooltip=row["name"],
        icon=folium.Icon(color=c, icon="tint"),
    ).add_to(m)

if buoys is not None:
    for _, b in buoys.iterrows():
        folium.Marker(
            [b["lat"], b["lon"]],
            tooltip=f"Oil-sensor buoy: {b['name']}",
            icon=folium.Icon(color="blue", icon="anchor", prefix="fa"),
        ).add_to(m)

st_folium(m, height=600, use_container_width=True, returned_objects=[])

st.caption(
    f"Red dots: forecast oil particles ({len(now)} shown of {len(now) * SHOW_EVERY}). "
    "Model: ocean current + 2% of wind + random spread. Coarse currents near the coast, no oil weathering."
)