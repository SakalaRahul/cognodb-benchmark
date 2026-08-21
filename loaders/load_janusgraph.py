import os
import sys
from dotenv import load_dotenv
from gremlin_python.driver import client as gremlin_client

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from loaders.common import read_nodes, read_edges, batched, LoadTimer

load_dotenv()

URL = os.environ.get("JANUSGRAPH_URL", "ws://localhost:8182/gremlin")


def load():
    c = gremlin_client.Client(URL, "g")

    # Clean slate + composite index on 'ext_id' for point/indexed lookups
    c.submit("g.V().drop().iterate()").all().result()
    c.submit(
        """
        mgmt = graph.openManagement();
        if (mgmt.getPropertyKey('ext_id') == null) {
            extId = mgmt.makePropertyKey('ext_id').dataType(Integer.class).make();
            mgmt.buildIndex('byExtId', Vertex.class).addKey(extId).buildCompositeIndex();
        }
        mgmt.commit();
        """
    ).all().result()

    nodes = read_nodes()
    edges = read_edges()

    with LoadTimer("janusgraph") as t:
        for batch in batched(nodes, size=200):  # smaller batches: Gremlin scripts get large fast
            c.submit(
                "batch.each { id -> g.addV('person').property('ext_id', id).iterate() }",
                {"batch": batch},
            ).all().result()
            t.node_count += len(batch)

        for batch in batched(edges, size=200):
            c.submit(
                """
                batch.each { row ->
                  src = g.V().has('person','ext_id', row[0]).next();
                  dst = g.V().has('person','ext_id', row[1]).next();
                  g.addE('sent').from(src).to(dst).iterate();
                }
                """,
                {"batch": [[s, d] for s, d in batch]},
            ).all().result()
            t.edge_count += len(batch)

    c.close()


if __name__ == "__main__":
    load()
