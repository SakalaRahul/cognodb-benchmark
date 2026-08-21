import os
import sys
from dotenv import load_dotenv
from arango import ArangoClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from loaders.common import read_nodes, read_edges, batched, LoadTimer

load_dotenv()

URL = os.environ.get("ARANGO_URL", "http://localhost:8529")
USER = os.environ.get("ARANGO_USER", "root")
PASSWORD = os.environ.get("ARANGO_PASSWORD", "changeme")
DB_NAME = os.environ.get("ARANGO_DB", "benchmark")


def load():
    client = ArangoClient(hosts=URL)
    sys_db = client.db("_system", username=USER, password=PASSWORD)

    if not sys_db.has_database(DB_NAME):
        sys_db.create_database(DB_NAME)
    db = client.db(DB_NAME, username=USER, password=PASSWORD)

    if db.has_collection("persons"):
        db.delete_collection("persons")
    if db.has_collection("sent"):
        db.delete_collection("sent")

    persons = db.create_collection("persons")
    persons.add_persistent_index(fields=["ext_id"], unique=True)  # matches "indexed lookup" claim
    sent = db.create_collection("sent", edge=True)

    nodes = read_nodes()
    edges = read_edges()

    with LoadTimer("arangodb") as t:
        for batch in batched(nodes):
            docs = [{"_key": str(n), "ext_id": n} for n in batch]
            persons.insert_many(docs, overwrite=False, silent=True)
            t.node_count += len(batch)

        for batch in batched(edges):
            docs = [
                {"_from": f"persons/{s}", "_to": f"persons/{d}"} for s, d in batch
            ]
            sent.insert_many(docs, silent=True)
            t.edge_count += len(batch)


if __name__ == "__main__":
    load()
