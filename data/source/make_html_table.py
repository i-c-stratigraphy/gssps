from rdflib import Graph, URIRef
from rdflib.namespace import SDO
from pathlib import Path
from dominate import document
from dominate.tags import a, br, meta, table, tbody, td, th, thead, title, tr
from dominate.util import text
import re

def make_graph() -> Graph:
    print("Building graph")
    g = Graph()
    g.parse(Path(__file__).parent / "gssps.ttl")
    print(len(g))

    chart_path = Path(__file__).parents[3] / "chart-data" / "chart.ttl"
    chart_graph = Graph().parse(chart_path)
    g += chart_graph
    print(len(g))

    gts_path = Path(__file__).parents[3] / "supermodel-data/resources/datasets/gtsd.ttl"
    gts_graph = Graph().parse(gts_path)
    g += gts_graph
    print(len(g))

    print("Graph built")

    return g


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


def make_html(g: Graph, output_path: Path | None = None) -> Path:
    print("Making HTML")
    q = """
        PREFIX gtsd: <https://data.stratigraphy.org/data/gts/>
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX schema: <https://schema.org/>
        PREFIX rank: <http://resource.geosciml.org/ontology/timescale/rank/>
        PREFIX time: <http://www.w3.org/2006/time#>
        PREFIX gts: <http://resource.geosciml.org/ontology/timescale/gts#>
        PREFIX gssp: <https://data.stratigraphy.org/def/gssp/>
        
        SELECT ?gssp ?name ?mya ?loc ?wkt ?bl ?ce ?s ?colour
        WHERE {
            {
                ?gssp 
                    a gssp:GSSP ;
                    gts:representsBoundary ?base ;
                    geo:hasGeometry/geo:asWKT ?wkt ;
                    gssp:correlationEvents ?ce ;
                    #schema:citation ?cit ;
                    schema:location ?loc ;
                    schema:status ?s ;
                .

                OPTIONAL { ?gssp gssp:boundaryLevel ?bl . }
        
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
                time:hasBeginning/gtsd:inMYA ?mya ;
            .
            
            FILTER (LANG(?name) = "en")
        }
        ORDER BY ?mya    
        """

    columns = ("name", "mya", "loc", "wkt", "bl", "ce", "s", "colour", "cit")

    rows = {}

    for r in g.query(q):
        gssp = str(r["gssp"])
        rows[gssp] = {}
        for column in columns:
            if column == "cit":
                pass
            elif column == "wkt":
                rows[gssp][column] = str(r[column]).strip().replace("POINT (", "").strip(")").replace(" ",", ")
            else:
                rows[gssp][column] = str(r[column]) if r[column] is not None else ""
        rows[gssp]["cit"] = []

    q2 = """
        PREFIX schema: <https://schema.org/>
        PREFIX gssp: <https://data.stratigraphy.org/def/gssp/>

        SELECT ?gssp ?cit
        WHERE {
            ?gssp 
                a gssp:GSSP ;
                schema:citation ?cit ;
            .
        }
        """

    for r in g.query(q2):
        gssp = str(r["gssp"])
        if rows.get(gssp):
            rows[gssp]["cit"].append(r["cit"])

    doc = document(title=None)
    with doc.head:
        meta(charset="utf-8")
        title("GSSPs")
    with doc:
        with table():
            with thead():
                with tr():
                    for column in columns:
                        if column == "colour":
                            pass
                        else:
                            th(column)
            with tbody():
                for i, row in rows.items():
                    with tr(style=f'background-color:{row["colour"]}'):
                        for column in columns:
                            value = row[column]
                            if column == "colour":
                                pass
                            elif column == "cit":
                                with td():
                                    for index, item in enumerate(value):
                                        if index:
                                            br()
                                        if isinstance(item, URIRef):
                                            label = str(item)
                                            names = sorted(str(name) for name in g.objects(item, SDO.name))
                                            if names:
                                                label = names[0]
                                            a(label, href=str(item))
                                        else:
                                            text(str(item))

                            else:
                                td(value)

    output_path = output_path or Path(__file__).with_name("gssps.html")
    output_path.write_text(doc.render() + "\n", encoding="utf-8")
    return output_path


if __name__ == "__main__":
    g = make_graph()
    make_html(g)
