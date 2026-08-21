import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Get a fresh token
url = os.environ['TIGERGRAPH_HOST'] + '/gsql/v1/tokens'
resp = requests.post(url, json={
    'secret': os.environ['TIGERGRAPH_SECRET'],
    'graph': os.environ['TIGERGRAPH_GRAPH']
})
token = resp.json()['token']
print("Got token:", token[:20], "...")

# Use the token to query vertex count via REST++
headers = {'Authorization': f'Bearer {token}'}
graph = os.environ['TIGERGRAPH_GRAPH']

vcount_url = f"{os.environ['TIGERGRAPH_HOST']}/restpp/graph/{graph}/vertices/Person?count_only=true"
vresp = requests.get(vcount_url, headers=headers)
print('VERTEX COUNT RESPONSE:', vresp.status_code, vresp.text)