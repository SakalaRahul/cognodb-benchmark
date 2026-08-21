# CognoDB Cloud Benchmark

Reproducible benchmark of **CognoDB Cloud** against **Neo4j AuraDB Free**,
**ArangoDB Oasis**, **FalkorDB Cloud**, and **TigerGraph Savanna**, on the same
dataset, same logical queries, and (as closely as each platform's free tier allows)
matched resources.

## Why these four platforms

- **Neo4j AuraDB Free** — the direct reference comparison: CognoDB speaks Bolt/Cypher
  via the official Neo4j driver, so this is the closest apples-to-apples baseline.
- **FalkorDB Cloud** — also Cypher-compatible, but runs as a Redis module rather
  than a standalone server — isolates protocol/architecture differences from
  storage-engine design.
- **ArangoDB Oasis** — multi-model, queried in AQL — tests a genuinely different
  query engine and storage model against the same logical workloads.
- **TigerGraph Savanna** — GSQL-based, purpose-built for large-scale graph analytics —
  the most architecturally distinct competitor, and the only one with a
  significantly larger free-tier footprint (see Caveats).

## Dataset

**SNAP email-Enron** (https://snap.stanford.edu/data/email-Enron.html)
- 36,692 nodes, 367,662 directed edges (raw file lists each direction of
  communication explicitly; SNAP's own summary page reports 183,831 when
  collapsing reciprocal pairs into a single undirected edge — we use the
  raw directed count since every platform loads the file as-is)
- Well within the assignment's 100k–500k relationship range
- Loaded identically into every platform as `Person {id}` nodes and `SENT` /
  `sent` directed edges, from `data/nodes.csv` / `data/edges.csv`
- All five platforms confirmed loading exactly 36,692 nodes and 367,662 edges

## Environment & instance specs

CognoDB's free tier is the fairness baseline: **burst to 0.5 vCPU / 512 MB RAM / 1 GiB disk**
(confirmed from the CognoDB console). Every other platform's free/entry tier was
used as-is; where a platform's smallest tier is larger than CognoDB's, that gap
is documented below and in Caveats rather than hidden.

| Platform | Tier | vCPU | RAM | Disk | Hosting |
|---|---|---|---|---|---|
| CognoDB Cloud | Free (c0) | burst to 0.5 | 512 MB | 1 GiB | Managed cloud |
| Neo4j AuraDB | Free | shared/burstable | ~shared | ~1 GB | Managed cloud |
| ArangoDB Oasis | Free trial (14-day) | shared | shared | — | Managed cloud |
| FalkorDB Cloud | Free | shared | 100 MB dataset limit | — | Managed cloud (Redis-based) |
| TigerGraph Savanna | Free (TG-00) | 2 | 16 GiB | — | Managed cloud |

Client machine: Windows, benchmarks run via PowerShell/Python against all five
cloud-hosted platforms in the same development session.

## Setup — step by step

### 1. Clone and install
```bash
git clone <your-repo-url>
cd cognodb-benchmark
python -m pip install -r requirements.txt
copy .env.example .env
```

### 2. CognoDB Cloud
1. Sign up at https://console.cognodb.com/signup (no credit card needed).
2. Create a free `c0` instance, pick a region.
3. Copy the `bolt+s://...` URI and the one-time password into `.env`.

### 3. Neo4j AuraDB Free
1. Sign up at https://console.neo4j.io.
2. Create a free instance, download the generated credentials file.
3. Fill `NEO4J_URI`, `NEO4J_USER=neo4j`, `NEO4J_PASSWORD` in `.env`.

### 4. ArangoDB Oasis
1. Sign up at https://cloud.arangodb.com (14-day free trial, no card required).
2. Create a deployment, smallest/single-node tier.
3. Fill `ARANGO_URL`, `ARANGO_USER=root`, `ARANGO_PASSWORD` in `.env`.

### 5. FalkorDB Cloud
1. Sign up at https://app.falkordb.cloud/signup.
2. Create a Free Tier instance.
3. Fill `FALKORDB_HOST`, `FALKORDB_PORT`, `FALKORDB_USER=falkordb`,
   `FALKORDB_PASSWORD` in `.env`.

### 6. TigerGraph Savanna
1. Sign up at https://tgcloud.io.
2. Create a workspace on the Free Tier, design a `Person` vertex (`ext_id: INT`)
   and a self-referential `sent` directed edge (`Person -> Person`).
3. Generate an API secret under Admin Portal → Management → Users → Secrets.
4. Fill `TIGERGRAPH_HOST`, `TIGERGRAPH_USER` (your account email),
   `TIGERGRAPH_SECRET`, `TIGERGRAPH_GRAPH` in `.env`.

### 7. Download the dataset
```bash
python data/download_dataset.py
```
Writes `data/nodes.csv` and `data/edges.csv`.

### 8. Load into every platform
```bash
python -m loaders.load_cognodb
python -m loaders.load_neo4j
python -m loaders.load_arangodb
python -m loaders.load_falkordb
```
TigerGraph was loaded via its web UI CSV import wizard (Design Schema → Load Data)
rather than a Python script — see Caveats for why.

Each Python loader writes `results/<platform>_load.json` with node/rel throughput
and wall-clock time.

### 9. Run the benchmark suite against every platform
```bash
python -m benchmarks.run_benchmark cognodb
python -m benchmarks.run_benchmark neo4j
python -m benchmarks.run_benchmark arangodb
python -m benchmarks.run_benchmark falkordb
python -m benchmarks.run_benchmark tigergraph
```
Each run does warm-up iterations + measured iterations per workload (1/2/3-hop
traversal, point lookup, indexed lookup, aggregation), then a mixed read/write
concurrency sweep at 1/10/40 clients. Writes `results/<platform>_bench.json`.
(Iteration counts are configurable via `WARMUP_ITERATIONS` / `MEASURED_ITERATIONS`
in `.env` — see Caveats regarding the reduced counts used for this submission.)

### 10. Generate the report
```bash
python -m report.make_tables    # -> report/results_tables.md
python -m report.make_charts    # -> report/charts/*.png
```

## Results matrix

### Data Loading
| Platform | Nodes/sec | Rels/sec | Wall-clock (s) |
|---|---|---|---|
| CognoDB | 281.14 | 2817.09 | 130.5 |
| Neo4j | 796.86 | 7984.76 | 46.0 |
| ArangoDB | 262.11 | 2626.36 | 140.0 |
| FalkorDB | 455.10 | 4560.16 | 80.6 |
| TigerGraph | n/a (loaded via UI wizard; ~6.5s per console timer) | | |

### 1-hop traversal (p50 / p95 / p99, ms)
| Platform | p50 | p95 | p99 |
|---|---|---|---|
| CognoDB | n/a — see Caveats | | |
| Neo4j | 48.04 | 57.81 | 67.30 |
| ArangoDB | 260.69 | 289.07 | 340.63 |
| FalkorDB | 35.31 | 41.81 | 52.21 |
| TigerGraph | n/a — see Caveats | | |

### 2-hop traversal (p50 / p95 / p99, ms)
| Platform | p50 | p95 | p99 |
|---|---|---|---|
| CognoDB | n/a | | |
| Neo4j | 48.37 | 52.65 | 85.14 |
| ArangoDB | 261.44 | 553.12 | 760.34 |
| FalkorDB | 35.20 | 39.00 | 40.05 |
| TigerGraph | n/a | | |

### 3-hop traversal (p50 / p95 / p99, ms)
| Platform | p50 | p95 | p99 |
|---|---|---|---|
| CognoDB | n/a | | |
| Neo4j | 48.43 | 61.39 | 72.84 |
| ArangoDB | 307.69 | 2080.37 | 5489.18 |
| FalkorDB | 35.38 | 45.57 | 56.06 |
| TigerGraph | n/a | | |

### Point lookup (p50 / p95 / p99, ms)
| Platform | p50 | p95 | p99 |
|---|---|---|---|
| CognoDB | n/a | | |
| Neo4j | 48.06 | 52.66 | 56.74 |
| ArangoDB | 259.29 | 331.71 | 649.80 |
| FalkorDB | 35.47 | 47.49 | 52.44 |
| TigerGraph | n/a | | |

### Indexed lookup (p50 / p95 / p99, ms)
| Platform | p50 | p95 | p99 |
|---|---|---|---|
| CognoDB | n/a | | |
| Neo4j | 48.86 | 55.99 | 62.12 |
| ArangoDB | 261.19 | 307.24 | 317.44 |
| FalkorDB | 36.65 | 50.97 | 58.89 |
| TigerGraph | n/a | | |

### Aggregation / count (p50 / p95 / p99, ms)
| Platform | p50 | p95 | p99 |
|---|---|---|---|
| CognoDB | n/a | | |
| Neo4j | 48.12 | 61.53 | 96.83 |
| ArangoDB | 260.41 | 325.38 | 657.91 |
| FalkorDB | 36.08 | 38.82 | 39.31 |
| TigerGraph | n/a | | |

### Mixed read/write throughput (90% read / 10% write)
| Platform | Concurrency | QPS |
|---|---|---|
| CognoDB | — | n/a |
| Neo4j | 1 | 19.4 |
| Neo4j | 10 | 162.6 |
| Neo4j | 40 | 671.0 |
| ArangoDB | 1 | 3.4 |
| ArangoDB | 10 | 34.4 |
| ArangoDB | 40 | 125.4 |
| FalkorDB | 1 | 27.6 |
| FalkorDB | 10 | 224.2 |
| FalkorDB | 40 | 568.0 |
| TigerGraph | — | n/a |

Full generated tables and charts: [`report/results_tables.md`](report/results_tables.md), [`report/charts/`](report/charts/)

## Indexing

| Platform | Indexed property |
|---|---|
| CognoDB / Neo4j / FalkorDB | `Person.id` (Cypher `CREATE INDEX`) |
| ArangoDB | `persons.ext_id` (persistent index, unique) |
| TigerGraph | `Person.ext_id` (primary ID, inherently indexed) |

## Analysis

**FalkorDB was the fastest and most consistent platform across every read
workload**, holding a flat ~35–50ms p50 regardless of traversal depth (1-hop
through 3-hop). This is consistent with its architecture — FalkorDB runs as a
Redis module, giving it in-memory, low-overhead query execution without a
separate network hop to a query-planning layer.

**Neo4j AuraDB was the second-most consistent performer**, holding steady
~48ms p50 across all workloads and posting the best raw throughput at high
concurrency (671 QPS at 40 clients on the mixed workload, versus FalkorDB's
568). Neo4j's flat latency across hop depths suggests most of the observed
time is network round-trip to Neo4j's cloud region rather than query
execution cost — the six workload types differ by execution cost but not
by measured latency, which points to network RTT dominating the signal.

**ArangoDB was substantially slower and less predictable.** It ran 5–7x
higher latency than Neo4j/FalkorDB on every workload, and 3-hop traversal
showed severe tail latency (p50 308ms but p99 5,489ms — a 17x spread).
This points to AQL's graph traversal engine handling multi-hop expansion
less efficiently than native Cypher engines at this edge density
(~10 average out-degree per node in this dataset).

**CognoDB Cloud** ingested data at a respectable 281 nodes/sec on its free
tier — faster than ArangoDB, slower than Neo4j and FalkorDB — but could not
sustain query workload testing under the resource constraints of its free
tier. See Caveats.

**TigerGraph** loaded and authenticated successfully (confirmed via a live
REST++ vertex-count query returning the correct 36,692), but its GSQL-based
benchmark queries could not be completed within the assignment's time
constraints. See Caveats.

## Caveats

- **CognoDB benchmark results are load-only.** Query workload testing
  (1/2/3-hop, lookups, aggregation, mixed) could not be completed: even a
  3-hop traversal bounded with `WITH DISTINCT b LIMIT 1000 RETURN count(b)`
  caused the free-tier instance's Bolt connection to become permanently
  unresponsive (`OSError('No data')`, followed by persistent SSL handshake
  failures on every reconnect attempt — verified directly against the
  console, which showed the instance briefly hit 89% of its 512MB memory
  limit around the time of failure). Data loading itself succeeded cleanly
  (36,692 nodes, 367,662 relationships, 281 nodes/sec, 130.5s wall-clock).
  This is a genuine finding: CognoDB's free tier does not appear to have
  enough headroom to sustain multi-hop traversal workloads on a graph of
  this size, even when the traversal is result-bounded.

- **TigerGraph benchmark results are load-only.** Data loading (via the
  Savanna web UI's CSV import wizard, not a Python script — see below),
  authentication, and vertex-count verification (confirmed via a direct
  REST++ call returning the correct count of 36,692) all succeeded. The
  ad-hoc GSQL `INTERPRET QUERY` syntax used for the benchmark's 1/2/3-hop
  and aggregation queries returned `400 Bad Request` and could not be
  debugged within the assignment's time window. This is a query-syntax
  issue in our benchmark harness, not a TigerGraph platform failure.

- **TigerGraph free tier is not resource-matched to the other platforms.**
  Savanna's smallest available workspace tier (`TG-00`) provisions 2 vCPU /
  16 GiB RAM — over 30x CognoDB's 512MB. No smaller tier is offered. We used
  it anyway since no alternative exists, but any future throughput/latency
  results from this platform should be read with that resource gap in mind.

- **TigerGraph was loaded via its web UI, not a Python script**, because a
  `pyTigerGraph` (v1.8.0) client incompatibility prevented programmatic
  loading: the library's `getToken()` call consistently returned
  `User authentication failed` against a verified-valid secret (independently
  confirmed working via direct `curl`/`requests` calls to the
  `/gsql/v1/tokens` REST endpoint, which succeeded and returned a valid JWT).
  We used TigerGraph's REST++ API directly via `requests` for benchmark
  connectivity, bypassing the official client library entirely.

- **Reduced iteration counts due to the assignment's time constraint.**
  Benchmarks in this submission used 5 warm-up + 30 measured iterations per
  workload (rather than a larger count) and a 5-second mixed-workload window
  per concurrency level (rather than a longer sustained window), configurable
  via `WARMUP_ITERATIONS` / `MEASURED_ITERATIONS` in `.env` and the
  `duration_s` parameter in `benchmarks/run_benchmark.py`. This trades some
  statistical smoothness for completing the full 5-platform sweep inside the
  submission deadline; p50/p95/p99 remain directionally meaningful at n=30
  but would benefit from a larger sample in a non-time-constrained re-run.

- **Development-time network instability.** Intermittent DNS resolution
  failures on the development machine caused transient connection errors
  across multiple platforms during setup (not specific to any one database,
  and not present in the final benchmark runs reported above). Disclosed
  for full transparency about the testing environment.

- **Query-language differences.** Workloads are logically identical (same
  hop depth, same aggregation, same lookup semantics) but not byte-identical
  across Cypher / AQL / GSQL — see `benchmarks/workloads.py` for the exact
  translation of each workload per platform.

- **Dataset edge count.** The SNAP email-Enron dataset's official summary
  page reports 183,831 edges (treating the network as undirected), but the
  raw downloadable file lists 367,662 directed rows (both communication
  directions explicitly present — confirmed via the SuiteSparse Matrix
  Collection's technical metadata, which shows 100% pattern symmetry for
  this graph). We use the raw directed count since every platform loads the
  file as-is; all five platforms confirmed loading exactly 367,662 edges.

## Repo structure

```
cognodb-benchmark/
├── data/download_dataset.py     # fetches + parses SNAP email-Enron
├── loaders/                     # one loader per platform (CognoDB, Neo4j, ArangoDB, FalkorDB)
├── benchmarks/
│   ├── workloads.py              # logical workload definitions per query language
│   ├── stats.py                  # p50/p95/p99 calculation
│   └── run_benchmark.py          # warm-up + timed runs + concurrency sweep, all 5 platforms
├── report/
│   ├── make_tables.py            # results/*.json -> Markdown tables
│   └── make_charts.py            # results/*.json -> PNG charts
├── docs/
│   └── blog-post.md              # evangelism / communication write-up (assignment Section 1)
└── results/                      # raw JSON output per platform (generated)
```

## Security note

No credentials are committed. All connection URIs, secrets, and passwords are
read from environment variables via `.env` (gitignored) — see `.env.example`
for the required shape.