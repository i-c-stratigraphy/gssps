import pandas as pd
from rdflib import Graph, URIRef, Literal, BNode, Namespace
from rdflib.namespace import OWL, RDF, SKOS, TIME, GEO, SDO, XSD
from pathlib import Path
import re
from datetime import date
import json

DATASET_IRI = URIRef("https://data.stratigraphy.org/data/gssps")
GSSP = Namespace("https://data.stratigraphy.org/def/gssp/")
GSSPS = Namespace("https://data.stratigraphy.org/data/gssps/")
GTS = Namespace("http://resource.geosciml.org/ontology/timescale/gts#")
GTSD = Namespace("https://data.stratigraphy.org/data/gts/")

PREFIXES = {
    "ds": DATASET_IRI,
    "gssp": GSSP,
    "gssps": GSSPS,
    "gts": GTS,
    "gtsd": GTSD,
}

def coordinates_to_wkt(value: str) -> str:
    COORD_RE = re.compile(
        r"^\s*"
        r"(?P<latitude>\d+(?:\.\d+)?)\s*[°º]\s*(?P<lat_dir>[NS])"
        r"\s*,?\s*"
        r"(?P<longitude>\d+(?:\.\d+)?)\s*[°º]\s*(?P<lon_dir>[EW])"
        r"\s*$",
        re.IGNORECASE,
    )

    match = COORD_RE.fullmatch(value)
    if not match:
        raise ValueError(f"Invalid coordinates: {value!r}")

    latitude = float(match.group("latitude"))
    longitude = float(match.group("longitude"))

    if match.group("lat_dir").upper() == "S":
        latitude = -latitude

    if match.group("lon_dir").upper() == "W":
        longitude = -longitude

    # WKT POINT order is longitude, then latitude.
    return f"POINT ({longitude} {latitude})"


def extract_lat_lon(wkt: str) -> tuple[float, float]:
    """Extracts latitude and longitude from a WKT string"""

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


def add_metadata():
    g = Graph()
    today = date.today().isoformat()
    metadata = f"""
                PREFIX schema: <https://schema.org/>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                
                <{DATASET_IRI}>
                    a schema:Dataset ;
                    schema:name "ICS Global Boundary Stratotype Section and Points" ;
                    schema:dateCreated "{today}"^^xsd:date ;
                    schema:dateModified "{today}"^^xsd:date ;
                .
                """
    g.parse(data=metadata, format="turtle")
    return g


def make_rdf() -> Graph:
    df = pd.read_excel("GSSPs.xlsx", sheet_name="GSSPs")
    g = Graph()

    for index, row in df.iterrows():
        iri = URIRef(row["IRI"])

        if row["Type"] in ["GSSP", "GSSA"]:  # do not process SABS for now
            g.add((iri, RDF.type, GSSP[row["Type"]]))

            g.add((iri, GTS.representsBoundary, URIRef(row["representsBoundary"])))

            # get name from Chart
            # g.add((iri, SDO.name, Literal(row["Stage"] + " GSSP")))

            if not pd.isnull(row["Location"]):
                g.add((iri, SDO.description, Literal(row["Location"])))
            if not pd.isnull(row["Boundary Level"]):
                g.add((iri, GSSP.boundaryLevel, Literal(row["Boundary Level"])))
            if not pd.isnull(row["Correlation Events"]):
                g.add((iri, GSSP.correlationEvents, Literal(row["Correlation Events"])))

            if not pd.isnull(row["DOIs"]):
                dois = [doi.strip() for doi in str(row["DOIs"]).split("http")]
                for doi in dois:
                    if doi != "nan" and doi != "":
                        g.add((iri, SDO.citation, Literal("http" + doi if doi.startswith("s://") else doi, datatype=XSD.anyURI)))

            if not pd.isnull(row["PDFs"]):
                pdfs = [doi.strip() for doi in str(row["PDFs"]).split("http")]
                for pdf in pdfs:
                    if pdf != "nan" and pdf != "":
                        g.add((iri, SDO.citation, Literal("http" + pdf if pdf.startswith("s://") else pdf, datatype=XSD.anyURI)))

            status = str(row["Status"])
            if status == "Ratified":
                g.add((iri, SDO.status, Literal(str(row["RatificationNote"]))))
            else:
                g.add((iri, SDO.status, Literal("Proposed")))

            if not pd.isnull(row["Coordinates"]):
                wkt = coordinates_to_wkt(row["Coordinates"])
                geom = BNode()
                g.add((iri, GEO.hasGeometry, geom))
                g.add((geom, RDF.type, GEO.Geometry))
                g.add((geom, GEO.asWKT, Literal(wkt, datatype=GEO.wktLiteral)))

            if not pd.isnull(row["References"]):
                g.add((iri, SDO.citation, Literal(str(row["References"]))))

            g.add((DATASET_IRI, SDO.hasPart, iri))

    g += add_metadata()

    for k, v in PREFIXES.items():
        g.bind(k, v)

    g.serialize(destination="gssps.ttl", format="longturtle")
    print("Made GSSPs RDF")
    return g


def make_geojson(g):
    g += Graph().parse(Path(__file__).parents[3] / "supermodel/resources/datasets/gtsd.ttl")
    g += Graph().parse(Path(__file__).parents[3] / "chart-data/chart.ttl")

    q = """
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX schema: <https://schema.org/>
        PREFIX rank: <http://resource.geosciml.org/ontology/timescale/rank/>
        PREFIX time: <http://www.w3.org/2006/time#>
        PREFIX gts: <http://resource.geosciml.org/ontology/timescale/gts#>
        PREFIX gssp: <https://data.stratigraphy.org/def/gssp/>
        
        SELECT ?gssp ?wkt ?name ?colour
        WHERE {
            {
                ?gssp 
                    a gssp:GSSP ;
                    gts:representsBoundary ?base ;
                    geo:hasGeometry/geo:asWKT ?wkt ;
                    schema:status ?status ;
                .
        
                OPTIONAL {
                    ?t1
                        gts:rank rank:Age ;
                        time:hasBeginning ?base ;
                    .
                }
        
                OPTIONAL {
                    ?t2
                        gts:rank rank:Period ;
                        time:hasBeginning ?base ;
                    .
                }
        
                BIND (COALESCE(?t1, ?t2) AS ?t)
            }
            
            ?t
                skos:prefLabel ?name ;
                schema:color ?colour ;
            .
            
            FILTER (LANG(?name) = "en")
            FILTER (?status != "Proposed")
        }
        """

    fc = {
        "type": "FeatureCollection",
        "features": []
    }
    for r in g.query(q):
        lat, long = extract_lat_lon(r["wkt"])
        fc["features"].append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    long,
                    lat
                ]
            },
            "properties": {
                "title": r["name"],
                "marker-color": r["colour"]
            }
        })

    # write to the root dir
    json.dump(fc, open(Path(__file__).parents[2] / "gssps.geojson", "w"), indent=4)
    print("Made GSSPs GeoJSON")


if __name__ == "__main__":
    g = make_rdf()

    make_geojson(g)