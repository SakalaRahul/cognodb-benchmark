import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from loaders.bolt_loader import load_via_bolt

load_dotenv()

if __name__ == "__main__":
    load_via_bolt(
        platform="cognodb",
        uri=os.environ["COGNODB_URI"],
        user=os.environ["COGNODB_USER"],
        password=os.environ["COGNODB_PASSWORD"],
    )
