from qdrant_client import QdrantClient
import os
from dotenv import load_dotenv

load_dotenv()
host = os.getenv("QDRANT_HOST")
key = os.getenv("QDRANT_API_KEY")

client = QdrantClient(url=host, api_key=key)
print("Client type:", type(client))
print("Has search attribute:", hasattr(client, "search"))
methods = [m for m in dir(client) if not m.startswith("_")]
print("Available methods:", methods)
