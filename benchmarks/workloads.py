"""
Defines the 5 required workload categories as *logical* operations, then
translates each into the right query language per platform. Keeping this
in one file makes it easy to verify every platform runs the same logic
(same fairness argument the assignment asks for).
"""

# ---- Cypher (CognoDB, Neo4j, Memgraph) ----
CYPHER = {
    "hop1": "MATCH (a:Person {id:$id})-[:SENT]->(b) RETURN count(b)",
       "hop2": "MATCH (a:Person {id:$id})-[:SENT*2]->(b) WITH DISTINCT b LIMIT 1000 RETURN count(b)",
    "hop3": "MATCH (a:Person {id:$id})-[:SENT*3]->(b) WITH DISTINCT b LIMIT 1000 RETURN count(b)",
    "point_lookup": "MATCH (a:Person {id:$id}) RETURN a",
    "indexed_lookup": "MATCH (a:Person) WHERE a.id = $id RETURN a",  # served by person_id index
    "aggregation": "MATCH ()-[r:SENT]->() RETURN count(r)",
    "write": "MATCH (a:Person {id:$id}) CREATE (a)-[:SENT]->(a)",  # self-loop write, cheap & safe
}

# ---- AQL (ArangoDB) ----
AQL = {
    "hop1": """
        FOR v IN 1..1 OUTBOUND CONCAT('persons/', @id) sent
        COLLECT WITH COUNT INTO c RETURN c
    """,
    "hop2": """
        FOR v IN 2..2 OUTBOUND CONCAT('persons/', @id) sent
        COLLECT WITH COUNT INTO c RETURN c
    """,
    "hop3": """
        FOR v IN 3..3 OUTBOUND CONCAT('persons/', @id) sent
        COLLECT WITH COUNT INTO c RETURN c
    """,
    "point_lookup": "RETURN DOCUMENT(CONCAT('persons/', @id))",
    "indexed_lookup": "FOR p IN persons FILTER p.ext_id == @id RETURN p",
    "aggregation": "RETURN LENGTH(sent)",
    "write": """
        LET a = DOCUMENT(CONCAT('persons/', @id))
        INSERT { _from: a._id, _to: a._id } INTO sent
    """,
}

# ---- Gremlin (JanusGraph) ----
GREMLIN = {
    "hop1": "g.V().has('person','ext_id',id).out('sent').count()",
    "hop2": "g.V().has('person','ext_id',id).out('sent').out('sent').dedup().count()",
    "hop3": "g.V().has('person','ext_id',id).out('sent').out('sent').out('sent').dedup().count()",
    "point_lookup": "g.V().has('person','ext_id',id).valueMap()",
    "indexed_lookup": "g.V().has('person','ext_id',id).valueMap()",  # served by composite index
    "aggregation": "g.E().count()",
    "write": "g.V().has('person','ext_id',id).as('a').addE('sent').to('a')",
}

WORKLOAD_NAMES = ["hop1", "hop2", "hop3", "point_lookup", "indexed_lookup", "aggregation"]
