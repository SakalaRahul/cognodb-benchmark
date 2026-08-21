"""Reads results/*.json and emits PNG bar charts into report/charts/"""
import json
import os
import matplotlib.pyplot as plt

PLATFORMS = ["cognodb", "neo4j", "arangodb", "falkordb", "tigergraph"]
WORKLOADS = ["hop1", "hop2", "hop3", "point_lookup", "indexed_lookup", "aggregation"]


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def chart_p95_by_workload():
    os.makedirs("report/charts", exist_ok=True)
    for w in WORKLOADS:
        labels, values = [], []
        for p in PLATFORMS:
            d = load_json(f"results/{p}_bench.json")
            if d and w in d.get("workloads", {}):
                labels.append(p)
                values.append(d["workloads"][w]["p95_ms"])
        if not values:
            continue
        plt.figure(figsize=(6, 4))
        plt.bar(labels, values)
        plt.ylabel("p95 latency (ms)")
        plt.title(f"{w} — p95 latency by platform")
        plt.xticks(rotation=20)
        plt.tight_layout()
        plt.savefig(f"report/charts/{w}_p95.png")
        plt.close()
        print(f"Wrote report/charts/{w}_p95.png")


def chart_load_throughput():
    labels, node_rates, rel_rates = [], [], []
    for p in PLATFORMS:
        d = load_json(f"results/{p}_load.json")
        if d:
            labels.append(p)
            node_rates.append(d["nodes_per_second"] or 0)
            rel_rates.append(d["relationships_per_second"] or 0)
    if not labels:
        return
    x = range(len(labels))
    plt.figure(figsize=(7, 4))
    plt.bar([i - 0.2 for i in x], node_rates, width=0.4, label="nodes/sec")
    plt.bar([i + 0.2 for i in x], rel_rates, width=0.4, label="rels/sec")
    plt.xticks(list(x), labels, rotation=20)
    plt.ylabel("throughput")
    plt.title("Ingest throughput by platform")
    plt.legend()
    plt.tight_layout()
    plt.savefig("report/charts/ingest_throughput.png")
    plt.close()
    print("Wrote report/charts/ingest_throughput.png")


def chart_mixed_concurrency():
    plt.figure(figsize=(7, 4))
    for p in PLATFORMS:
        d = load_json(f"results/{p}_bench.json")
        if not d:
            continue
        mixed = d.get("mixed", [])
        if not mixed:
            continue
        xs = [m["concurrency"] for m in mixed]
        ys = [m["queries_per_second"] for m in mixed]
        plt.plot(xs, ys, marker="o", label=p)
    plt.xlabel("concurrent clients")
    plt.ylabel("queries/sec")
    plt.title("Mixed workload QPS vs concurrency")
    plt.legend()
    plt.tight_layout()
    plt.savefig("report/charts/mixed_concurrency.png")
    plt.close()
    print("Wrote report/charts/mixed_concurrency.png")


if __name__ == "__main__":
    chart_p95_by_workload()
    chart_load_throughput()
    chart_mixed_concurrency()
