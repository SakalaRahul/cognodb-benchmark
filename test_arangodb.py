from arango import ArangoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = ArangoClient(hosts=os.environ['ARANGO_URL'])
sys_db = client.db('_system', username=os.environ['ARANGO_USER'], password=os.environ['ARANGO_PASSWORD'])
print('Connected! Server version:', sys_db.version())