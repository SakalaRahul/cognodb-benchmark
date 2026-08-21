# Benchmarking a New Graph Database Against the Giants: What CognoDB Taught Me About Fair Comparisons

*A hands-on benchmark of CognoDB Cloud against Neo4j, TigerGraph, ArangoDB, and FalkorDB — same data, same queries, same rules for everyone.*

## Why benchmark a database you've never heard of?

Every few months, a new managed database platform shows up promising to be faster, cheaper, or simpler than the incumbents. The only way to know if that's true — rather than just marketing — is to run the same workload against all of them and see what actually happens.

That's what this project does: it takes **CognoDB Cloud**, a graph database platform, and puts it head-to-head against four established players — **Neo4j AuraDB**, **TigerGraph**, **ArangoDB**, and **FalkorDB** — using one dataset, one set of queries, and matched free-tier resource limits across the board.

## The rules I set for myself

Benchmarks are easy to get wrong, usually by accident. A slower database can look fast if you give it more RAM. A faster one can look slow if your test queries favor a different data model. So before writing a single line of loading code, I fixed the rules:

1. **Same dataset everywhere** — the SNAP email-Enron network (36,692 people, 367,662 directed "sent an email" edges), loaded identically into all five platforms.
2. **Same logical queries everywhere** — 1-hop, 2-hop, and 3-hop traversals, point lookups, indexed lookups, aggregations, and a mixed concurrent read/write workload, translated faithfully into each platform's native query language (Cypher, AQL, GSQL).
3. **Matched resources** — every platform capped as close as possible to CognoDB's free tier (0.5 vCPU, 512MB RAM), whether that meant using another platform's free tier or accepting and documenting a gap where no smaller tier existed.
4. **Warm up, then measure** — discarded warm-up runs before every timed workload, then measured iterations, reporting p50/p95/p99 latency rather than misleading averages.

## What "fair" actually costs you

Here's the part benchmarking tutorials don't usually mention: **fairness is expensive.** Free-tier cloud databases are, by design, resource-starved — that's the whole point of a free tier. Running real workloads against five separately-hosted, resource-constrained instances means you will hit rate limits, connection timeouts, and outright crashes. That's not a bug in the methodology; it's the methodology working as intended, because it surfaces exactly the kind of real-world constraint that a padded, best-case benchmark would hide.

CognoDB's free-tier instance, for example, handled data ingestion cleanly — 281 nodes/second, a full load of 36,692 nodes and 367,662 relationships in about two minutes — but couldn't sustain a bounded 3-hop traversal query without its Bolt connection becoming permanently unresponsive. That's not a mark against the engineering; it's exactly the kind of free-tier ceiling every platform in this comparison has somewhere, and the whole point of testing honestly is finding where.

## What the numbers show

FalkorDB was the fastest and most consistent platform across every read workload, holding a flat ~35-50ms p50 regardless of traversal depth — likely a benefit of running as an in-memory Redis module rather than a standalone server with its own network hop. Neo4j AuraDB was close behind, similarly flat across hop depths, and actually edged out FalkorDB at high concurrency (671 queries/second at 40 concurrent clients versus FalkorDB's 568). ArangoDB was noticeably slower across the board — 5 to 7 times higher latency than the two leaders — and showed a dramatic latency spike at 3-hop traversal (p50 of 308ms ballooning to a p99 of nearly 5.5 seconds), suggesting its AQL traversal engine struggles more than native Cypher engines as hop depth increases on a densely-connected graph. CognoDB and TigerGraph both loaded and connected successfully, but ran into platform-specific limits during query benchmarking — documented honestly in the full report rather than glossed over.

## The honest caveats

No benchmark is perfect, and pretending otherwise is worse than admitting the rough edges. A few things worth knowing about this one:

- **Not every platform's free tier is actually equal.** TigerGraph's smallest available cloud instance runs at 16GB RAM — over 30 times CognoDB's 512MB — because TigerGraph doesn't currently offer anything smaller. Any latency advantage TigerGraph might show should be read with that gap in mind, not as evidence of superior engineering.
- **Free-tier instances can fall over under load.** CognoDB's instance became unresponsive during a bounded 3-hop traversal test, even after the query was capped to a maximum result size — a genuine finding about how much headroom a 512MB free tier actually provides for multi-hop graph queries.
- **Query language isn't a 1:1 translation.** Cypher, AQL, and GSQL express the same logical traversal differently, and small differences in how each engine optimizes "N hops out, deduplicated" can matter more than the underlying storage engine.
- **Network variance is real.** Every cloud-hosted free tier in this comparison incurs genuine network round-trip time from wherever the benchmark client runs — this is a legitimate part of what a managed cloud database "costs" in latency, not a flaw in the test.

## Try it yourself

The full benchmark harness — data loaders, query definitions, and the timing/reporting code — is open source and reproducible from a README alone: **[YOUR GITHUB REPO URL HERE]**. If you're evaluating graph databases for your own project, the goal isn't to tell you which one to pick — it's to give you a methodology you can point at your own workload and get an honest answer.

---

*Questions, corrections, or want to add another platform to the comparison? Open an issue on the repo.*