from rdflib import Graph
# from dominate.tags import *
# from dominate.util import raw
from pathlib import Path
import json
import re


def make_graph() -> Graph:
    g = Graph()
    g.parse(Path(__file__).parent / "gssps.ttl")
    print(len(g))

    chart_path = Path(__file__).parents[3] / "chart-data" / "chart.ttl"
    chart_graph = Graph().parse(chart_path)
    g += chart_graph
    print(len(g))

    gts_path = Path(__file__).parents[3] / "supermodel/resources/datasets/gts2020.ttl"
    gts_graph = Graph().parse(gts_path)
    g += gts_graph
    print(len(g))

    return g


def make_html(g):
    q = """
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX schema: <https://schema.org/>
        PREFIX rank: <http://resource.geosciml.org/ontology/timescale/rank/>
        PREFIX time: <http://www.w3.org/2006/time#>
        PREFIX gts: <http://resource.geosciml.org/ontology/timescale/gts#>
        PREFIX gssp: <https://data.stratigraphy.org/def/gssp/>
        
        SELECT ?name ?d ?wkt ?bl ?ce ?s ?cit ?colour
        WHERE {
            {
                ?gssp 
                    a gssp:GSSP ;
                    gts:stratotypeOf ?base ;
                    geo:hasGeometry/geo:asWKT ?wkt ;
                    gssp:boundaryLevel ?bl ;
                    gssp:correlationEvents ?ce ;
                    schema:citation ?cit ;
                    schema:description ?d ;
                    schema:status ?s ;
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
        }        
        """


if __name__ == "__main__":
    print("hello")
    make_graph()