import json

fc = {
    "type": "FeatureCollection",
    "features": None
}

features = []

with open("gssps.csv") as f:
    for i, line in enumerate(f.readlines()):
        if i > 0:
            words = line.split(",")
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(words[2]), float(words[3])]
                },
                "properties": {
                    "title": words[1],
                    "marker-color": words[4].strip()
                }
            })

fc["features"] = features
print(json.dumps(fc, indent=4))
