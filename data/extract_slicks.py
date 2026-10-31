import json

with open("data/cerulean_raw.geojson") as f:
    data = json.load(f)


def center(geom):
    if geom["type"] == "Polygon":
        polys = [geom["coordinates"]]
    else:
        polys = geom["coordinates"]
    pts = []
    for poly in polys:
        for ring in poly:
            pts.extend(ring)
    lons = [pt[0] for pt in pts]
    lats = [pt[1] for pt in pts]
    return round(sum(lats) / len(lats), 3), round(sum(lons) / len(lons), 3)


# 1) double-check: every slick near UAQ, ANY size, sorted by time
print("Slicks near UAQ:")
feats = sorted(data["features"], key=lambda f: f["properties"]["slick_timestamp"])
for feat in feats:
    p = feat["properties"]
    lat, lon = center(feat["geometry"])
    if 25.4 <= lat <= 26.2 and 55.2 <= lon <= 56.0:
        print(" ", p["slick_timestamp"], p["id"], round(p["area"] / 1e6, 1), "km2", lat, lon)


# 2) save one slick as its own GeoJSON file
def save(slick_id, path):
    for feat in data["features"]:
        if str(feat["properties"]["id"]) == str(slick_id):
            out = {"type": "FeatureCollection", "features": [feat]}
            with open(path, "w") as f:
                json.dump(out, f)
            print("saved", path)
            return
    print("NOT FOUND", slick_id)


save(5302861, "data/slick_oct21.geojson")
save(5311367, "data/slick_oct24.geojson")