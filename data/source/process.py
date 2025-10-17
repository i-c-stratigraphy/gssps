import pandas as pd
from rdflib import Graph, URIRef, Literal, BNode, Namespace
from rdflib.namespace import RDF, SKOS, TIME, GEO, SDO, XSD

GSSPS = Namespace('http://linked.data.gov.au/def/gssps/')

df = pd.read_excel("GSSPs.xlsx", sheet_name="Sheet1")
g = Graph()

print(df.columns)

for index, row in df.iterrows():
    iri = URIRef(row["IRI"].replace("http://resource.geosciml.org/classifier/ics/ischart/", str(GSSPS) + "gssp/"))

    g.add((iri, RDF.type, GSSPS.GSSP))
    g.add((iri, SDO.name, Literal(row["Stage"] + " GSSP")))
    if str(row["Location"]) is not None:
        g.add((iri, SDO.description, Literal(row["Location"])))
    if str(row["Boundary Level"]) is not None:
        g.add((iri, GSSPS.boundaryLevel, Literal(row["Boundary Level"])))
    if str(row["Correlation Events"]) is not None:
        g.add((iri, GSSPS.correlationEvents, Literal(row["Correlation Events"])))
    # if str(row["Status"]) is not None:
    #     g.add((iri, GSSPS.boundaryLevel, Literal(row["Status"])))

    if str(row["DOIs"]) is not None:
        dois = [doi.strip() for doi in str(row["DOIs"]).split("http")]
        for doi in dois:
            if doi != "nan" and doi != "":
                g.add((iri, SDO.citation, Literal("http" + doi if doi.startswith("s://") else doi, datatype=XSD.anyURI)))

    if str(row["PDFs"]) is not None:
        pdfs = [doi.strip() for doi in str(row["PDFs"]).split("http")]
        for pdf in pdfs:
            if pdf != "nan" and pdf != "":
                g.add((iri, SDO.citation, Literal("http" + pdf if pdf.startswith("s://") else pdf, datatype=XSD.anyURI)))

    status = str(row["Status"])
    if status == "ratified":
        # g.add((iri, RDF.type, GEO.Feature))
        if "Defined chronometrically" not in str(row["Location"]):
            wkt = str(row["Coordinates"])
            wkt = "-" + wkt if "S" in wkt else wkt
            wkt = wkt.replace("N ", "N -") if "W" in wkt else wkt
            wkt = wkt.replace("S ", "S -") if "W" in wkt else wkt
            wkt = wkt.replace("°", "").replace("N", "").replace("S", "").replace("E", "").replace("W", "")
            wkt = f"POINT({wkt})"
            geom = BNode()
            g.add((iri, GEO.hasGeometry, geom))
            g.add((geom, RDF.type, GEO.Geometry))
            g.add((geom, GEO.asWKT, Literal(wkt, datatype=GEO.wktLiteral)))




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
g.bind("gssps", GSSPS)
g.bind("gssp", str(GSSPS) + "gssp/")
g.serialize(destination="gssps.ttl", format="longturtle")