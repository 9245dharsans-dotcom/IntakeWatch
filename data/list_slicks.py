import json

with open("data/cerulean_raw.geojson") as f:
    data = json.load(f)


def center(geom):
    # a Polygon is one shape; a MultiPolygon is a list of shapes
    if geom["type"] == "Polygon":
        polys = [geom["coordinates"]]
    else:
        polys = geom["coordinates"]

    pts = []
    for poly in polys:        # each separate patch
        for ring in poly:     # outer edge (+ any holes)
            pts.extend(ring)  # each point is [lon, lat]

    lons = [pt[0] for pt in pts]
    lats = [pt[1] for pt in pts]
    return round(sum(lats) / len(lats), 3), round(sum(lons) / len(lons), 3)


rows = []
for feat in data["features"]:
    p = feat["properties"]
    area_km2 = p["area"] / 1_000_000
    if area_km2 > 10:
        lat, lon = center(feat["geometry"])
        rows.append((p["slick_timestamp"], p["id"], round(area_km2, 1), lat, lon))

rows.sort()
for t, sid, a, lat, lon in rows:
    print(t, sid, a, "km2", "center:", lat, lon)