"""
Runs the full benchmark suite (1/2/3-hop traversal, point lookup,
indexed lookup, aggregation, mixed concurrent read/write) against ONE
platform and writes results/<platform>_bench.json.

Usage:
    python -m benchmarks.run_benchmark cognodb
    python -m benchmarks.run_benchmark neo4j
    python -m benchmarks.run_benchmark memgraph
    python -m benchmarks.run_benchmark arangodb
    python -m benchmarks.run_benchmark janusgraph
    python -m benchmarks.run_benchmark falkordb
    python -m benchmarks.run_benchmark tigergraph
"""
import os
import sys
import json
import time
import random
import argparse
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from loaders.common import read_nodes
from benchmarks.workloads import CYPHER, AQL, GREMLIN, WORKLOAD_NAMES
from benchmarks.stats import percentiles

load_dotenv()

WARMUP = int(os.environ.get("WARMUP_ITERATIONS", 20))
MEASURED = int(os.environ.get("MEASURED_ITERATIONS", 100))
SEED = int(os.environ.get("RANDOM_SEED", 42))


# ---------------------------------------------------------------------------
# Platform adapters: each returns (run_query_fn, close_fn)
# run_query_fn(workload_name, node_id) -> executes and returns nothing (we time it)
# ---------------------------------------------------------------------------

def adapter_cypher(platform_env_prefix):
    from neo4j import GraphDatabase
    uri = os.environ[f"{platform_env_prefix}_URI"]
    user = os.environ.get(f"{platform_env_prefix}_USER") or None
    pwd = os.environ.get(f"{platform_env_prefix}_PASSWORD") or None
    driver = GraphDatabase.driver(uri, auth=(user, pwd) if user else None)

    def run(name, node_id):
        with driver.session() as s:
            s.run(CYPHER[name], id=node_id).consume()

    return run, driver.close


def adapter_arangodb():
    from arango import ArangoClient
    url = os.environ.get("ARANGO_URL", "http://localhost:8529")
    user = os.environ.get("ARANGO_USER", "root")
    pwd = os.environ.get("ARANGO_PASSWORD", "changeme")
    db_name = os.environ.get("ARANGO_DB", "benchmark")
    db = ArangoClient(hosts=url).db(db_name, username=user, password=pwd)

    def run(name, node_id):
        query = AQL[name]
        bind_vars = {"id": str(node_id)} if "@id" in query else {}
        list(db.aql.execute(query, bind_vars=bind_vars))
    return run, (lambda: None)


def adapter_janusgraph():
    from gremlin_python.driver import client as gremlin_client
    url = os.environ.get("JANUSGRAPH_URL", "ws://localhost:8182/gremlin")
    c = gremlin_client.Client(url, "g")

    def run(name, node_id):
        c.submit(GREMLIN[name], {"id": node_id}).all().result()

    return run, c.close


def adapter_falkordb():
    from falkordb import FalkorDB
    db = FalkorDB(
        host=os.environ["FALKORDB_HOST"],
        port=int(os.environ["FALKORDB_PORT"]),
        username=os.environ.get("FALKORDB_USER", "falkordb"),
        password=os.environ["FALKORDB_PASSWORD"],
    )
    graph_name = os.environ.get("FALKORDB_GRAPH", "cognodb_benchmark")
    graph = db.select_graph(graph_name)

    def run(name, node_id):
        graph.query(CYPHER[name], {"id": node_id})

    return run, (lambda: None)


def adapter_tigergraph():
    """
    TigerGraph Savanna adapter using raw REST++ calls (requests library),
    NOT pyTigerGraph -- the official client library had auth incompatibilities
    with Savanna's token endpoint during development (see README caveats).
    """
    import requests
    host = os.environ["TIGERGRAPH_HOST"]
    graph = os.environ["TIGERGRAPH_GRAPH"]
    secret = os.environ["TIGERGRAPH_SECRET"]

    token_resp = requests.post(f"{host}/gsql/v1/tokens", json={"secret": secret, "graph": graph}, timeout=15)
    token_resp.raise_for_status()
    token = token_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    TG_GSQL = {
        "hop1": "INTERPRET QUERY(INT id) FOR GRAPH {graph} {{ Start = {{Person.*}}; S2 = SELECT s FROM Start:s WHERE s.ext_id == id; H1 = SELECT t FROM S2:s -(sent:e)- Person:t; PRINT H1.size(); }}",
        "hop2": "INTERPRET QUERY(INT id) FOR GRAPH {graph} {{ Start = {{Person.*}}; S2 = SELECT s FROM Start:s WHERE s.ext_id == id; H1 = SELECT t FROM S2:s -(sent:e)- Person:t; H2 = SELECT t FROM H1:s -(sent:e)- Person:t; PRINT H2.size(); }}",
        "hop3": "INTERPRET QUERY(INT id) FOR GRAPH {graph} {{ Start = {{Person.*}}; S2 = SELECT s FROM Start:s WHERE s.ext_id == id; H1 = SELECT t FROM S2:s -(sent:e)- Person:t; H2 = SELECT t FROM H1:s -(sent:e)- Person:t; H3 = SELECT t FROM H2:s -(sent:e)- Person:t; PRINT H3.size(); }}",
        "point_lookup": "INTERPRET QUERY(INT id) FOR GRAPH {graph} {{ Start = {{Person.*}}; S2 = SELECT s FROM Start:s WHERE s.ext_id == id; PRINT S2; }}",
        "indexed_lookup": "INTERPRET QUERY(INT id) FOR GRAPH {graph} {{ Start = {{Person.*}}; S2 = SELECT s FROM Start:s WHERE s.ext_id == id; PRINT S2; }}",
        "aggregation": "INTERPRET QUERY() FOR GRAPH {graph} {{ Start = {{Person.*}}; E1 = SELECT t FROM Start:s -(sent:e)- Person:t; PRINT E1.size(); }}",
        "write": "INTERPRET QUERY(INT id) FOR GRAPH {graph} {{ Start = {{Person.*}}; S2 = SELECT s FROM Start:s WHERE s.ext_id == id; INSERT INTO sent VALUES (id, id); }}",
    }

    def run(name, node_id):
        query = TG_GSQL[name].format(graph=graph)
        payload = {"query": query, "params": {"id": node_id}} if "id" in query else {"query": query}
        resp = requests.post(f"{host}/gsql/v1/queries/interpret", json=payload, headers=headers, timeout=30)
        resp.raise_for_status()

    return run, (lambda: None)


PLATFORM_ADAPTERS = {
    "cognodb": lambda: adapter_cypher("COGNODB"),
    "neo4j": lambda: adapter_cypher("NEO4J"),
    "memgraph": lambda: adapter_cypher("MEMGRAPH"),
    "arangodb": adapter_arangodb,
    "janusgraph": adapter_janusgraph,
    "falkordb": adapter_falkordb,
    "tigergraph": adapter_tigergraph,
}


def time_workload(run_fn, name, sample_ids, max_retries=2):
    # Warm-up (discarded) -- tolerate failures here, just skip
    for i in range(WARMUP):
        try:
            run_fn(name, sample_ids[i % len(sample_ids)])
        except Exception as e:
            print(f"  warmup {i} failed: {e}")

    # Measured -- retry once on transient connection errors, else record as failed
    latencies = []
    failures = 0
    for i in range(MEASURED):
        node_id = sample_ids[i % len(sample_ids)]
        for attempt in range(max_retries):
            try:
                t0 = time.perf_counter()
                run_fn(name, node_id)
                t1 = time.perf_counter()
                latencies.append((t1 - t0) * 1000)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    failures += 1
                    print(f"  iteration {i} failed after {max_retries} attempts: {e}")
                else:
                    time.sleep(1)

    if not latencies:
        return {"error": "all iterations failed", "failures": failures}

    result = percentiles(latencies)
    result["failures"] = failures
    return result


def run_mixed_workload(run_fn, sample_ids, concurrency, read_write_ratio=0.9, duration_s=5):
    stop_at = time.perf_counter() + duration_s
    completed = [0]

    def worker():
        rng = random.Random()
        local_count = 0
        while time.perf_counter() < stop_at:
            node_id = rng.choice(sample_ids)
            name = "hop1" if rng.random() < read_write_ratio else "write"
            try:
                run_fn(name, node_id)
                local_count += 1
            except Exception:
                pass
        return local_count

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(worker) for _ in range(concurrency)]
        for f in futures:
            completed[0] += f.result()

    qps = completed[0] / duration_s
    return {
        "concurrency": concurrency,
        "read_write_ratio": read_write_ratio,
        "duration_s": duration_s,
        "completed_ops": completed[0],
        "queries_per_second": round(qps, 2),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("platform", choices=PLATFORM_ADAPTERS.keys())
    parser.add_argument("--concurrency-sweep", nargs="+", type=int, default=[1, 10, 40])
    args = parser.parse_args()

    run_fn, close_fn = PLATFORM_ADAPTERS[args.platform]()

    all_nodes = read_nodes()
    rng = random.Random(SEED)
    sample_ids = rng.sample(all_nodes, min(500, len(all_nodes)))

    results = {"platform": args.platform, "workloads": {}, "mixed": []}

    for name in WORKLOAD_NAMES:
        print(f"[{args.platform}] running {name} ...")
        results["workloads"][name] = time_workload(run_fn, name, sample_ids)

    for c in args.concurrency_sweep:
        print(f"[{args.platform}] mixed workload, concurrency={c} ...")
        results["mixed"].append(run_mixed_workload(run_fn, sample_ids, c))

    close_fn()

    os.makedirs("results", exist_ok=True)
    out_path = f"results/{args.platform}_bench.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(json.dumps(results, indent=2))
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    main()