import os
from pathlib import Path
from pydantic_settings import BaseSettings
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from graph_manager import GraphManager
from dotenv import load_dotenv

load_dotenv()

# =============================
# Environment Config
# =============================
class Settings(BaseSettings):
    # JWT Configuration
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Neo4j Configuration
    NEO4J_URL: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str

    # Qdrant Configuration
    QDRANT_URL: str
    COLLECTION_NAME: str

    # Embedding Model
    EMBEDDING_MODEL: str

    # Frontend URL
    FRONTEND_URL: str

    # LLM Configuration (NEW)
    # LLM_PROVIDER: str = "ollama" 
    LLM_PROVIDER: str = "openai" 


    LLM_MODEL: str = "llama3.1:8b-instruct-q4_K_M"
    LLM_BASE_URL: str = "http://localhost:11434"

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL")

    
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1024
    LLM_TIMEOUT: int = 120 

    class Config:
        env_file = ".env"

settings = Settings()

# =============================
# Directories
# =============================
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR.parent / "uploaded_files"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# =============================
# Embeddings
# =============================
embedding = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

# =============================
# Qdrant Initialization
# =============================
qdrant_client = QdrantClient(url=settings.QDRANT_URL)
collection_name = settings.COLLECTION_NAME

try:
    qdrant_client.get_collection(collection_name=collection_name)
except Exception:
    print(f"[INFO] Collection '{collection_name}' not found. Creating it now...")
    qdrant_client.recreate_collection(
        collection_name=collection_name,
        vectors_config=rest.VectorParams(size=1024, distance=rest.Distance.COSINE),
    )
    print(f"[INFO] ✅ Collection '{collection_name}' created.")

# =============================
# Graph Manager
# =============================
graph_manager = GraphManager(
    uri=settings.NEO4J_URL,
    user=settings.NEO4J_USER,
    password=settings.NEO4J_PASSWORD
)

# =============================
# JWT and Frontend Alignment
# =============================
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
FRONTEND_URL = settings.FRONTEND_URL

print(f"[INFO] FRONTEND_URL for CORS set to: {FRONTEND_URL}")
