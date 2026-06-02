import json
import os
import chromadb
from dotenv import load_dotenv
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.selectors import LLMMultiSelector
from llama_index.core.tools import QueryEngineTool
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

# Get the base directory where this file resides to resolve absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load environment variables from .env file anchored to base directory
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

# Initialize Global Settings
TYPHOON_API_KEY = os.getenv("TYPHOON_API_KEY")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./storage/chroma_db")
if not os.path.isabs(CHROMA_DB_PATH):
    CHROMA_DB_PATH = os.path.abspath(os.path.join(BASE_DIR, CHROMA_DB_PATH))

print("Initializing Typhoon LLM...")
Settings.llm = OpenAILike(
    model="typhoon-v2.5-30b-a3b-instruct",
    api_base="https://api.opentyphoon.ai/v1",
    api_key=TYPHOON_API_KEY,
    is_chat_model=True,
    temperature=0.1
)

print("Loading local HuggingFace embedding model (BAAI/bge-m3)...")
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-m3")

def validate_path(base_dir: str, target_path: str) -> str:
    """Ensures paths remain inside the base directory."""
    abs_base = os.path.abspath(base_dir)
    abs_target = os.path.abspath(target_path)
    if not abs_target.startswith(abs_base):
        raise ValueError(f"Path traversal detected! Path '{target_path}' is outside base directory '{base_dir}'.")
    return abs_target

def build_agentic_router_engine():
    """Builds the multi-selector router engine from configured collections."""
    config_path = os.path.join(BASE_DIR, "config.json")
    manifest_path = os.path.join(BASE_DIR, ".rag_manifest.json")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"config.json configuration file not found at {config_path}.")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    db_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    query_engine_tools = []
    
    # Set workspace root to the absolute project base directory
    workspace_root = BASE_DIR

    # Verify if manifest exists in the project base directory
    if not os.path.exists(manifest_path):
        raise ValueError("System has not been synchronized. Please run 'rag sync' first.")

    for dir_info in config.get("directories", []):
        name = dir_info["name"]
        raw_path = dir_info["path"]
        collection_name = dir_info["collection_name"]
        description = dir_info["description"]

        # Resolve raw_path relative to BASE_DIR if it is relative
        if not os.path.isabs(raw_path):
            raw_path = os.path.abspath(os.path.join(BASE_DIR, raw_path))

        # Validate path
        validate_path(workspace_root, raw_path)

        # Check if collection exists in Chroma DB and contains nodes
        try:
            chroma_collection = db_client.get_collection(collection_name)
            if chroma_collection.count() == 0:
                print(f"[Warning] Collection '{collection_name}' is empty. Skipping from routing tools.")
                continue
        except Exception:
            print(f"[Warning] Collection '{collection_name}' not initialized. Skipping from routing tools.")
            continue

        # Load Chroma Vector Store
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        index = VectorStoreIndex.from_vector_store(vector_store)
        engine = index.as_query_engine()

        # Wrap as a tool for the router
        tool = QueryEngineTool.from_defaults(
            query_engine=engine,
            name=f"{name.lower()}_search",
            description=description
        )
        query_engine_tools.append(tool)

    if not query_engine_tools:
        raise ValueError("No active/populated collections found. Please insert documents and run 'rag sync' first.")

    # Construct the supervisor engine using LLMMultiSelector to support complex queries across collections
    print("Constructing Agentic Router Engine with LLMMultiSelector...")
    router_engine = RouterQueryEngine(
        selector=LLMMultiSelector.from_defaults(),
        query_engine_tools=query_engine_tools
    )

    return router_engine
