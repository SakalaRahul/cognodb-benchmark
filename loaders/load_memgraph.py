import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from loaders.bolt_loader import load_via_bolt

load_dotenv()

if __name__ == "__main__":
    load_via_bolt(
        platform="memgraph",
        uri=os.environ.get("MEMGRAPH_URI", "bolt://localhost:7687"),
        user=os.environ.get("MEMGRAPH_USER") or None,
        password=os.environ.get("MEMGRAPH_PASSWORD") or None,
    )
