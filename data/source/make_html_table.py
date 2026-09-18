from rdflib import Graph, URIRef, Namespace
from rdflib.namespace import SDO, RDF, SKOS, TIME, GEO
from pathlib import Path
from dominate import document
from dominate.tags import a, br, meta, table, tbody, td, th, thead, title, tr, h1, h2, style
from dominate.util import text
import re
import json
from html import escape

GSSP = Namespace("https://data.stratigraphy.org/def/gssp/")
GTS = Namespace("http://resource.geosciml.org/ontology/timescale/gts#")
RANK = Namespace("http://resource.geosciml.org/ontology/timescale/rank/")
CONTAINMENT = (TIME.intervalStartedBy, TIME.intervalContains, TIME.intervalFinishedBy)
GTSD = Namespace("https://data.stratigraphy.org/data/gts/")
DATASET_IRI = URIRef("https://data.stratigraphy.org/data/gssps")
COLUMNS = ("name", "mya", "loc", "wkt", "bl", "ce", "s", "colour", "cit")

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


def make_html(
    g: Graph,
    output_path: Path | None = None,
    others_output_path: Path | None = None,
) -> Path:
    """Write the main table and a companion table of excluded cited records."""
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
        
        SELECT ?gssp ?t ?name ?mya ?loc ?wkt ?bl ?ce ?s ?colour
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

    columns = COLUMNS

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
        rows[gssp]["interval"] = r["t"]

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

    output_path = output_path or Path(__file__).with_name("gssps.html")
    others_output_path = others_output_path or output_path.with_name("others.html")
    write_table(g, rows, output_path, "GSSPs")
    write_table(g, other_rows(g, set(rows)), others_output_path, "GSSAs & SABS")
    return output_path


def other_rows(g: Graph, included: set[str]) -> dict:
    """Keep cited GSSPs, GSSAs and SABS absent from the main query."""
    rows = {}
    for subject in sorted(g.objects(DATASET_IRI, SDO.hasPart), key=str):
        citations = sorted(g.objects(subject, SDO.citation), key=str)
        if str(subject) in included or not citations:
            continue
        if not any((subject, RDF.type, kind) in g for kind in (GSSP.GSSP, GSSP.GSSA, GSSP.SABS)):
            continue

        # Prefer the interval's own IRI: several boundaries begin multiple ranks,
        # and some workbook boundary names differ from those in chart data.
        local_name = str(subject).split("#", 1)[0].rsplit("/", 1)[-1]
        interval = GTSD[local_name]
        names = sorted(str(name) for name in g.objects(interval, SKOS.prefLabel) if name.language == "en")
        name = names[0] if names else re.sub(r"(?<=[a-z])(?=[A-Z])", " ", local_name)
        if (subject, RDF.type, GSSP.SABS) in g:
            name += " SABS"
        ages = [age for beginning in g.objects(interval, TIME.hasBeginning) for age in g.objects(beginning, GTSD.inMYA)]
        geometry = g.value(subject, GEO.hasGeometry)
        wkt = g.value(geometry, GEO.asWKT) if geometry is not None else None
        rows[str(subject)] = {
            "name": name,
            "interval": interval,
            "mya": str(min(ages, key=float)) if ages else "",
            "loc": str(g.value(subject, SDO.location) or ""),
            "wkt": str(wkt).strip().replace("POINT (", "").strip(")").replace(" ", ", ") if wkt is not None else "",
            "bl": str(g.value(subject, GSSP.boundaryLevel) or ""),
            "ce": str(g.value(subject, GSSP.correlationEvents) or ""),
            "s": str(g.value(subject, SDO.status) or ""),
            "colour": str(g.value(interval, SDO.color) or ""),
            "cit": citations,
        }
    return dict(sorted(rows.items(), key=lambda item: (float(item[1]["mya"]) if item[1]["mya"] else float("inf"), item[1]["name"])))


def interval_label(g: Graph, interval: URIRef) -> str:
    names = sorted(str(name) for name in g.objects(interval, SKOS.prefLabel)
                   if getattr(name, "language", None) == "en")
    return names[0] if names else re.sub(
        r"(?<=[a-z])(?=[A-Z])", " ", str(interval).rsplit("/", 1)[-1])


def interval_path(g: Graph, interval: URIRef, visited=frozenset()) -> tuple:
    """Follow the three OWL-Time containment relations from child to parent."""
    if interval in visited:
        raise ValueError(f"Cycle in interval hierarchy at {interval}")
    parents = {parent for relation in CONTAINMENT
               for parent in g.subjects(relation, interval)
               if g.value(parent, GTS.rank) is not None}
    if not parents:
        # Single-Age Epochs are coextensive: OWL-Time uses intervalEquals
        # instead of the three strict containment relations. Their intervalIn
        # assertion still supplies the intended stratigraphic parent.
        parents = {parent for parent in g.objects(interval, TIME.intervalIn)
                   if g.value(parent, GTS.rank) is not None}
    if not parents:
        return (interval,)
    paths = [interval_path(g, parent, visited | {interval}) for parent in sorted(parents)]
    # Prefer the full hierarchy if the graph also supplies a transitive shortcut.
    return max(paths, key=lambda path: (len(path), tuple(map(str, path)))) + (interval,)


def table_groups(g: Graph, rows: dict) -> dict:
    groups = {}
    for subject, row in rows.items():
        path = interval_path(g, row["interval"])
        periods = [node for node in path if (node, GTS.rank, RANK.Period) in g]
        # Precambrian Era/Eon records have no Period: group those by Eon,
        # as the source website does, without inventing a Period membership.
        eons = [node for node in path if (node, GTS.rank, RANK.Eon) in g]
        group = periods[-1] if periods else (eons[-1] if eons else path[0])
        groups.setdefault(group, []).append((subject, row, path))
    return groups


def write_table(g: Graph, rows: dict, output_path: Path, page_title: str) -> Path:
    """Render Period tables with coloured ancestor and Epoch heading rows."""
    columns = [column for column in COLUMNS if column != "colour"]
    doc = document(title=None)
    with doc.head:
        meta(charset="utf-8")
        title(page_title)
        style("""
            body { font-family: sans-serif; margin: 2rem; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 2rem; }
            th, td { border: 1px solid #777; padding: .45rem; text-align: left;
                     vertical-align: top; }
            thead { background: #eee; }
            .hierarchy th { padding: .6rem; }
            td:last-child { min-width: 12rem; overflow-wrap: anywhere; }
        """)
    with doc:
        h1(page_title)
        for group, entries in table_groups(g, rows).items():
            h2(interval_label(g, group))
            with table(**{"data-interval": str(group)}):
                with thead():
                    with tr():
                        for column in columns:
                            th(column)
                with tbody():
                    previous = ()
                    for subject, row, path in entries:
                        # A Period/Era/Eon can itself have a boundary record;
                        # retain its data row as well as its hierarchy heading.
                        hierarchy = tuple(node for node in path
                                          if (node, GTS.rank, RANK.Age) not in g)
                        common = 0
                        for old, new in zip(previous, hierarchy):
                            if old != new:
                                break
                            common += 1
                        for node in hierarchy[common:]:
                            colour = str(g.value(node, SDO.color) or "")
                            rank = str(g.value(node, GTS.rank) or "").rsplit("/", 1)[-1]
                            with tr(cls="hierarchy", style=f"background-color:{colour}" if colour else "",
                                    **{"data-interval": str(node)}):
                                th(f"{interval_label(g, node)} {rank}", colspan=len(columns), scope="rowgroup")
                        previous = hierarchy
                        with tr(**{"data-record": subject}):
                            for column in columns:
                                value = row[column]
                                if column == "cit":
                                    with td():
                                        for index, item in enumerate(value):
                                            if index:
                                                br()
                                            if isinstance(item, URIRef):
                                                names = sorted(str(name) for name in g.objects(item, SDO.name))
                                                a(names[0] if names else str(item), href=str(item))
                                            else:
                                                text(str(item))
                                elif column == "name" and row["colour"]:
                                    td(value, style=f'background-color:{row["colour"]}')
                                else:
                                    td(value)
    output_path.write_text(doc.render() + "\n", encoding="utf-8")
    return output_path


def write_jekyll_html(
    gssps_html: Path,
    others_html: Path,
    gssps_geojson: Path,
    template_path: Path,
    output_path: Path | None = None,
) -> Path:
    """Combine the standalone tables and map data with the preserved Jekyll frame.

    The template is maintained separately and never extracted from the generated
    layout on subsequent runs. Jekyll's menu include and content remain intact.
    """
    template = Path(template_path).read_text(encoding="utf-8")
    for marker in ("<!-- GENERATED_TABLES -->", "<!-- GENERATED_GEOJSON -->"):
        if template.count(marker) != 1:
            raise ValueError(f"Template must contain exactly one {marker}")

    geojson = json.loads(Path(gssps_geojson).read_text(encoding="utf-8"))
    if geojson.get("type") != "FeatureCollection" or not isinstance(geojson.get("features"), list):
        raise ValueError("Map input must be a GeoJSON FeatureCollection")
    # Prevent a property value from closing the JSON script element.
    map_data = (json.dumps(geojson, ensure_ascii=True)
                .replace("<", "\\u003c")
                .replace("{% endraw %}", "\\u007b% endraw %}"))
    labels = {
        "name": "Stage / Interval", "mya": "Age (Ma)",
        "loc": "GSSP Location", "wkt": "Longitude, Latitude",
        "bl": "Boundary Level", "ce": "Correlation Events",
        "s": "Status", "cit": "Reference",
    }
    fragments = []
    used_ids = set()
    for path, heading in ((gssps_html, "GSSP Tables"), (others_html, "GSSAs & SABS")):
        source = Path(path).read_text(encoding="utf-8")
        body = re.search(r"<body\b[^>]*>(.*?)</body>", source, re.DOTALL)
        if body is None:
            raise ValueError(f"No HTML body in {path}")
        fragment = re.sub(r"<h1>.*?</h1>", "", body.group(1), count=1, flags=re.DOTALL)

        def period_heading(match):
            label = match.group(1)
            anchor = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
            if anchor in used_ids:
                anchor = "others-" + anchor
            used_ids.add(anchor)
            return f'<h4 id="{escape(anchor, quote=True)}">{label}</h4>'

        fragment = re.sub(r"<h2>(.*?)</h2>", period_heading, fragment, flags=re.DOTALL)
        fragment = fragment.replace("<table ", '<table class="ages" ')
        fragment = re.sub(r"(<thead>\s*)<tr>", r'\1<tr class="headerRow">', fragment)
        for key, label in labels.items():
            fragment = fragment.replace(f"<th>{key}</th>", f"<th>{label}</th>")
        # Preserve the existing sidebar's Proterozoic target even though that
        # Eon is now split into Period tables.
        if "proterozoic" not in used_ids:
            fragment, count = re.subn(
                r'(<tr\b[^>]*data-interval="https://data.stratigraphy.org/data/gts/Proterozoic")',
                r'\1 id="proterozoic"', fragment, count=1)
            if count:
                used_ids.add("proterozoic")
        fragments.append(f'<h3 style="text-align: center;">{escape(heading)}</h3>\n{fragment}')

    # These payloads are data, not Liquid templates. Keep any literal Liquid
    # syntax in citations or GeoJSON properties from being evaluated by Jekyll.
    def raw(value):
        return "{% raw %}" + value.replace("{% endraw %}", "&#123;% endraw %}") + "{% endraw %}"

    result = template.replace("<!-- GENERATED_TABLES -->", raw("\n".join(fragments)))
    result = result.replace("<!-- GENERATED_GEOJSON -->", raw(map_data))
    output_path = output_path or Path(__file__).parents[2] / "_layouts/table.html"
    Path(output_path).write_text(result, encoding="utf-8")
    return Path(output_path)


if __name__ == "__main__":
    g = make_graph()
    make_html(g)
    source_dir = Path(__file__).resolve().parent
    write_jekyll_html(
        source_dir / "gssps.html",
        source_dir / "others.html",
        source_dir.parents[1] / "gssps.geojson",
        source_dir / "table_page_template.html",
    )
