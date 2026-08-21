import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from loaders.bolt_loader import load_via_bolt

load_dotenv()

if __name__ == "__main__":
    load_via_bolt(
        platform="neo4j",
        uri=os.environ["NEO4J_URI"],
        user=os.environ["NEO4J_USER"],
        password=os.environ["NEO4J_PASSWORD"],
    )
