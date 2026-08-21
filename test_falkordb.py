from falkordb import FalkorDB
import os
from dotenv import load_dotenv

load_dotenv()

db = FalkorDB(
    host=os.environ["FALKORDB_HOST"],
    port=int(os.environ["FALKORDB_PORT"]),
    username=os.environ.get("FALKORDB_USER", "falkordb"),
    password=os.environ["FALKORDB_PASSWORD"],
)

graph = db.select_graph("connection_test")
result = graph.query("RETURN 'Connected successfully!' AS msg")
print(result.result_set[0][0])