"""
Downloads the SNAP email-Enron dataset (36,692 nodes / 183,831 edges)
and writes clean nodes.csv / edges.csv used by every loader.

Source: https://snap.stanford.edu/data/email-Enron.html
"""
import gzip
import io
import csv
import sys
import requests

URL = "https://snap.stanford.edu/data/email-Enron.txt.gz"
NODES_OUT = "data/nodes.csv"
EDGES_OUT = "data/edges.csv"


def download():
    print(f"Downloading {URL} ...")
    resp = requests.get(URL, timeout=60)
    resp.raise_for_status()
    raw = gzip.decompress(resp.content).decode("utf-8")
    return raw


def parse(raw: str):
    edges = []
    node_ids = set()
    for line in raw.splitlines():
        if line.startswith("#"):
            continue
        parts = line.strip().split()
        if len(parts) != 2:
            continue
        src, dst = int(parts[0]), int(parts[1])
        edges.append((src, dst))
        node_ids.add(src)
        node_ids.add(dst)
    return sorted(node_ids), edges


def write_csvs(node_ids, edges):
    with open(NODES_OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id"])
        for n in node_ids:
            w.writerow([n])

    with open(EDGES_OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["src", "dst"])
        for src, dst in edges:
            w.writerow([src, dst])

    print(f"Wrote {len(node_ids)} nodes -> {NODES_OUT}")
    print(f"Wrote {len(edges)} edges -> {EDGES_OUT}")


if __name__ == "__main__":
    raw = download()
    node_ids, edges = parse(raw)
    write_csvs(node_ids, edges)
    if not (100_000 <= len(edges) <= 500_000):
        print(f"WARNING: edge count {len(edges)} outside the 100k-500k target range.", file=sys.stderr)
