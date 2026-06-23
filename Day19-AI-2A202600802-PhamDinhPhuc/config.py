import os
from dotenv import load_dotenv
import openai
from qdrant_client import QdrantClient

# Load environment variables from .env
load_dotenv()

# API Keys & Clients
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing from environment. Please verify your .env file.")

# Models config
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# Qdrant Database configuration
QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if not QDRANT_HOST or not QDRANT_API_KEY:
    raise ValueError("Qdrant host or api key is missing in environment.")

# Paths configuration
BASE_DIR = r"e:\VinUni\git-phuc-VinUni\Day19-AI-2A202600802-PhamDinhPhuc"
DATASET_DIR = os.path.join(BASE_DIR, "dataset", "dataset")
OUTPUT_DIR = BASE_DIR

# Ensure output dir exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Initialize global OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialize global Qdrant client
qdrant_client = QdrantClient(
    url=QDRANT_HOST,
    api_key=QDRANT_API_KEY,
    timeout=60.0
)
