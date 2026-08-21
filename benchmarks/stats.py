import numpy as np


def percentiles(latencies_ms):
    """latencies_ms: list of floats (milliseconds). Returns p50/p95/p99/mean."""
    arr = np.array(latencies_ms)
    return {
        "p50_ms": round(float(np.percentile(arr, 50)), 3),
        "p95_ms": round(float(np.percentile(arr, 95)), 3),
        "p99_ms": round(float(np.percentile(arr, 99)), 3),
        "mean_ms": round(float(np.mean(arr)), 3),
        "n": len(arr),
    }
