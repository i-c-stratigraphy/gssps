import pandas as pd
from rdflib import Graph, URIRef, Literal, BNode, Namespace
from rdflib.namespace import OWL, RDF, SKOS, TIME, GEO, SDO, XSD
from pathlib import Path
import re
from datetime import date

DATASET_IRI = URIRef("https://data.stratigraphy.org/data/gssps")


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


GSSP = Namespace('https://data.stratigraphy.org/def/gssp/')
GSSPS = Namespace('https://data.stratigraphy.org/data/gssps/')
GTS = Namespace('http://resource.geosciml.org/ontology/timescale/gts#')
GTS2020 = Namespace('https://data.stratigraphy.org/data/gts2020/')

df = pd.read_excel("GSSPs.xlsx", sheet_name="GSSPs")
g = Graph()

print(df.columns)

for index, row in df.iterrows():
    iri = URIRef(row["IRI"])

    g.add((iri, RDF.type, GSSP.GSSP))

    g.add((iri, GTS.stratotypeOf, URIRef(row["stratotypeOf"])))

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
    if status == "ratified":
        # g.add((iri, RDF.type, GEO.Feature))
        if "Defined chronometrically" not in str(row["Location"]):
            wkt = coordinates_to_wkt(row["Coordinates"])
            geom = BNode()
            g.add((iri, GEO.hasGeometry, geom))
            g.add((geom, RDF.type, GEO.Geometry))
            g.add((geom, GEO.asWKT, Literal(wkt, datatype=GEO.wktLiteral)))
    else:
        g.add((iri, SDO.status, Literal(status)))

    if not pd.isnull(row["References"]):
        g.add((iri, SDO.citation, Literal(str(row["References"]))))

    g.add((DATASET_IRI, SDO.hasPart, iri))


# g = Graph().parse("chart.ttl")
# q = """
#     SELECT ?iri ?mya
#     WHERE {
#         ?iri a skos:Concept ;
#             time:hasBeginning/ischart:inMYA ?mya
#         .
#     }
#     ORDER BY ?mya
#     """
# for row in g.query(q, initNs={"time": TIME, "ischart": "http://resource.geosciml.org/classifier/ics/ischart/"}):
#     print(f'{row["iri"]}')

# add names
g2 = Graph()
for t in g:
    g2.add((t))
chart_path = Path(__file__).parent / "chart.ttl"
g2.parse(chart_path)

for s, o in g2.subject_objects(GTS.stratotypeOf):
    age = URIRef(str(o).replace("Base", ""))
    for o2 in g2.objects(age, SKOS.prefLabel):
        if o2.language == "en":
            name = str(o2)
    g.add((s, SDO.name, Literal(f"GSSP for the {name}")))


g += add_metadata()

g.bind("gssps", GSSPS)
g.bind("gssp", GSSP)
g.bind("gts", GTS)
g.bind("gts2020", GTS2020)
g.bind("ds", DATASET_IRI)
g.serialize(destination="gssps.ttl", format="longturtle")