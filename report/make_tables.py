"""Reads results/*_load.json and results/*_bench.json, emits Markdown tables to report/results_tables.md"""
import json
import glob
import os

PLATFORMS = ["cognodb", "neo4j", "arangodb", "falkordb", "tigergraph"]
WORKLOAD_LABELS = {
    "hop1": "1-hop traversal",
    "hop2": "2-hop traversal",
    "hop3": "3-hop traversal",
    "point_lookup": "Point lookup",
    "indexed_lookup": "Indexed lookup",
    "aggregation": "Aggregation (count)",
}


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def build_load_table():
    lines = ["| Platform | Nodes/sec | Rels/sec | Wall-clock (s) |", "|---|---|---|---|"]
    for p in PLATFORMS:
        d = load_json(f"results/{p}_load.json")
        if d is None:
            lines.append(f"| {p} | n/a | n/a | n/a |")
            continue
        lines.append(f"| {p} | {d['nodes_per_second']} | {d['relationships_per_second']} | {d['wall_clock_seconds']} |")
    return "\n".join(lines)


def build_workload_table(workload_key):
    lines = ["| Platform | p50 (ms) | p95 (ms) | p99 (ms) |", "|---|---|---|---|"]
    for p in PLATFORMS:
        d = load_json(f"results/{p}_bench.json")
        if d is None or workload_key not in d.get("workloads", {}):
            lines.append(f"| {p} | n/a | n/a | n/a |")
            continue
        w = d["workloads"][workload_key]
        lines.append(f"| {p} | {w['p50_ms']} | {w['p95_ms']} | {w['p99_ms']} |")
    return "\n".join(lines)


def build_mixed_table():
    lines = ["| Platform | Concurrency | QPS |", "|---|---|---|"]
    for p in PLATFORMS:
        d = load_json(f"results/{p}_bench.json")
        if d is None:
            lines.append(f"| {p} | n/a | n/a |")
            continue
        for m in d.get("mixed", []):
            lines.append(f"| {p} | {m['concurrency']} | {m['queries_per_second']} |")
    return "\n".join(lines)


def main():
    os.makedirs("report", exist_ok=True)
    out = ["# Results Matrix\n", "## Data Loading\n", build_load_table(), "\n"]
    for key, label in WORKLOAD_LABELS.items():
        out.append(f"## {label}\n")
        out.append(build_workload_table(key))
        out.append("\n")
    out.append("## Mixed Read/Write Throughput\n")
    out.append(build_mixed_table())
    out.append("\n")

    with open("report/results_tables.md", "w") as f:
        f.write("\n".join(out))
    print("Wrote report/results_tables.md")


if __name__ == "__main__":
    main()
