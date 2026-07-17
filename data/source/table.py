from rdflib import Graph
# from dominate.tags import *
# from dominate.util import raw
from pathlib import Path
import json
import re


def extract_lat_lon(wkt: str) -> tuple[float, float]:
    POINT_RE = re.compile(
        r"^\s*POINT\s*\(\s*"
        r"(?P<longitude>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
        r"\s+"
        r"(?P<latitude>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
        r"\s*\)\s*$",
        re.IGNORECASE,
    )

    match = POINT_RE.fullmatch(wkt)
    if not match:
        raise ValueError(f"Invalid WKT POINT: {wkt!r}")

    longitude = float(match.group("longitude"))
    latitude = float(match.group("latitude"))

    return latitude, longitude

def make_geojson(combined_graph):
    q = """
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX gts: <http://resource.geosciml.org/ontology/timescale/gts#>
        PREFIX schema: <https://schema.org/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX time: <http://www.w3.org/2006/time#>

        SELECT ?name ?coords ?colour
        WHERE {
            ?gssp 
                geo:hasGeometry/geo:asWKT ?coords ;
                gts:stratotypeOf/^time:hasBeginning ?te ; 
            .

            ?te
                skos:prefLabel ?name ;
                schema:color ?colour ;
            .

            FILTER (LANG(?name) = "en")
        }
        ORDER BY ?name
        """

    feature_collection = {
        "type": "FeatureCollection",
        "features": []
    }
    for r in combined_graph.query(q):
        lat, long = extract_lat_lon(r["coords"])

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    long,
                    lat,
                ]
            },
            "properties": {
                "title": str(r["name"]),
                "marker-color": str(r["colour"])
            }
        }
        feature_collection["features"].append(feature)

    json.dump(feature_collection, open(Path(__file__).parent / "gssps.geojson", "w"), indent=4)


gssps_graph = Graph()
gssps_graph.parse(Path(__file__).parent / "gssps.ttl")

# online chart
# chart_path = "https://raw.githubusercontent.com/i-c-stratigraphy/chart/refs/heads/main/chart.ttl")
# local Chart
chart_path = Path(__file__).parents[3] / "chart-data" / "chart.ttl"
chart_graph = Graph().parse(chart_path)

gts_path = Path(__file__).parent / "gts2026.ttl"
gts_graph = Graph().parse(gts_path)

combined_graph = gssps_graph + chart_graph + gts_graph

# make_geojson(combined_graph)

q = """
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX gts: <http://resource.geosciml.org/ontology/timescale/gts#>
    PREFIX schema: <https://schema.org/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX time: <http://www.w3.org/2006/time#>

    SELECT ?gssp ?x ?te # (COUNT(*) AS ?c)
    WHERE {       
        ?gssp 
            geo:hasGeometry/geo:asWKT ?coords ;
            gts:stratotypeOf ?x ; # /^time:hasBeginning ?te ; 
        .
        OPTIONAL {
            ?x ^time:hasBeginning ?te .
        }
        
        #?te
        #    skos:prefLabel ?name ;
        #    schema:color ?colour ;
        #.

        #FILTER (LANG(?name) = "en")
    }
    ORDER BY ?gssp
    """

for r in combined_graph.query(q):
    print(r)