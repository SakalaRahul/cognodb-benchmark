"""
Shared loader logic for any Bolt/Cypher-speaking database:
CognoDB, Neo4j AuraDB, and Memgraph all use this same code path,
which is itself part of the fairness story (identical logical operations).
"""
import os
from neo4j import GraphDatabase
from loaders.common import read_nodes, read_edges, batched, LoadTimer


def load_via_bolt(platform: str, uri: str, user: str, password: str):
    auth = (user, password) if user else None
    driver = GraphDatabase.driver(uri, auth=auth)
    nodes = read_nodes()
    edges = read_edges()

    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        session.run("CREATE INDEX person_id IF NOT EXISTS FOR (p:Person) ON (p.id)")

        with LoadTimer(platform) as t:
            for batch in batched(nodes):
                session.run("UNWIND $ids AS id CREATE (:Person {id: id})", ids=batch)
                t.node_count += len(batch)

            for batch in batched(edges):
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (a:Person {id: row.src}), (b:Person {id: row.dst})
                    CREATE (a)-[:SENT]->(b)
                    """,
                    rows=[{"src": s, "dst": d} for s, d in batch],
                )
                t.edge_count += len(batch)

    driver.close()
