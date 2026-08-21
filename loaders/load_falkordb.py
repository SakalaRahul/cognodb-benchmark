"""
Loads nodes.csv / edges.csv into FalkorDB Cloud using the official
`falkordb` Python package. FalkorDB speaks Cypher but runs over the
Redis protocol, not Bolt -- so it needs its own connection code,
separate from bolt_loader.py.
"""
import os
import sys
from dotenv import load_dotenv
from falkordb import FalkorDB

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from loaders.common import read_nodes, read_edges, batched, LoadTimer

load_dotenv()

HOST = os.environ["FALKORDB_HOST"]
PORT = int(os.environ["FALKORDB_PORT"])
PASSWORD = os.environ["FALKORDB_PASSWORD"]
GRAPH_NAME = os.environ.get("FALKORDB_GRAPH", "cognodb_benchmark")


def load():
    db = FalkorDB(host=HOST, port=PORT, username=os.environ.get("FALKORDB_USER", "falkordb"), password=PASSWORD)
    graph = db.select_graph(GRAPH_NAME)

    try:
        graph.delete()
    except Exception:
        pass

    nodes = read_nodes()
    edges = read_edges()

    with LoadTimer("falkordb") as t:
        for batch in batched(nodes):
            ids_literal = ", ".join(f"{{id: {n}}}" for n in batch)
            graph.query(f"UNWIND [{ids_literal}] AS row CREATE (:Person {{id: row.id}})")
            t.node_count += len(batch)

        graph.query("CREATE INDEX FOR (p:Person) ON (p.id)")

        for batch in batched(edges):
            rows_literal = ", ".join(f"{{src: {s}, dst: {d}}}" for s, d in batch)
            graph.query(
                f"""
                UNWIND [{rows_literal}] AS row
                MATCH (a:Person {{id: row.src}}), (b:Person {{id: row.dst}})
                CREATE (a)-[:SENT]->(b)
                """
            )
            t.edge_count += len(batch)


if __name__ == "__main__":
    load()