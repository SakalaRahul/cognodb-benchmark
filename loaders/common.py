"""Shared helpers for all loaders: batched CSV reading + timing/throughput reporting."""
import csv
import time
import json
import os

BATCH_SIZE = 1000


def read_nodes(path="data/nodes.csv"):
    with open(path) as f:
        reader = csv.DictReader(f)
        return [int(row["id"]) for row in reader]


def read_edges(path="data/edges.csv"):
    with open(path) as f:
        reader = csv.DictReader(f)
        return [(int(row["src"]), int(row["dst"])) for row in reader]


def batched(iterable, size=BATCH_SIZE):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


class LoadTimer:
    """Times a load run and writes a standard results/<platform>_load.json file."""

    def __init__(self, platform: str):
        self.platform = platform
        self.node_count = 0
        self.edge_count = 0
        self.start = None
        self.end = None

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.end = time.perf_counter()
        self.report()

    def report(self):
        wall = self.end - self.start
        result = {
            "platform": self.platform,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "wall_clock_seconds": round(wall, 3),
            "nodes_per_second": round(self.node_count / wall, 2) if wall > 0 else None,
            "relationships_per_second": round(self.edge_count / wall, 2) if wall > 0 else None,
        }
        os.makedirs("results", exist_ok=True)
        out_path = f"results/{self.platform}_load.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(json.dumps(result, indent=2))
        print(f"Saved -> {out_path}")
