import json
import os
import hashlib
import chromadb
from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.vector_stores.chromadb import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Initialize local embedding model globally to avoid reloading
print("Loading local HuggingFace embedding model (BAAI/bge-m3)...")
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-m3")

MANIFEST_FILE = ".rag_manifest.json"

def calculate_sha256(file_path: str) -> str:
    """Calculates the SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def validate_path(base_dir: str, target_path: str) -> str:
    """Resolves target_path and ensures it resides within base_dir to prevent directory traversal."""
    abs_base = os.path.abspath(base_dir)
    abs_target = os.path.abspath(target_path)
    if not abs_target.startswith(abs_base):
        raise ValueError(f"Path traversal detected! Path '{target_path}' is outside base directory '{base_dir}'.")
    return abs_target

def load_manifest() -> dict:
    """Loads the manifest file tracking indexed documents and hashes."""
    if os.path.exists(MANIFEST_FILE):
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_manifest(manifest: dict):
    """Saves the manifest file."""
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

def get_allowed_files(directory_path: str) -> list:
    """Recursively lists all files in a directory that are PDF, TXT, or MD."""
    allowed_extensions = {".pdf", ".txt", ".md"}
    found_files = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in allowed_extensions:
                found_files.append(os.path.join(root, file))
    return found_files

def sync_all_documents():
    """Scans all configured directories and performs incremental updates to ChromaDB."""
    # Load configuration
    if not os.path.exists("config.json"):
        print("❌ config.json not found!")
        return

    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    workspace_root = os.getcwd()
    documents_root = os.getenv("DOCUMENTS_DIR", "./documents")
    chroma_db_path = os.getenv("CHROMA_DB_PATH", "./storage/chroma_db")

    # Validate and ensure documents root exists
    if not os.path.exists(documents_root):
        os.makedirs(documents_root)

    db_client = chromadb.PersistentClient(path=chroma_db_path)
    manifest = load_manifest()

    for dir_info in config.get("directories", []):
        name = dir_info["name"]
        raw_path = dir_info["path"]
        collection_name = dir_info["collection_name"]

        # 1. Path Traversal Validation
        try:
            validated_path = validate_path(workspace_root, raw_path)
        except ValueError as err:
            print(f"⚠️ Security Skip: {err}")
            continue

        # Ensure directories exist
        if not os.path.exists(validated_path):
            os.makedirs(validated_path)
            print(f"📁 Created empty directory: {validated_path}")

        print(f"\n🔄 Syncing collection [{collection_name}] from {raw_path}...")

        # Setup ChromaDB collection and store
        chroma_collection = db_client.get_or_create_collection(collection_name)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # 2. Map current files on disk
        disk_files = get_allowed_files(validated_path)
        disk_hashes = {}
        for file_path in disk_files:
            # Keep relative paths for environment independence
            rel_path = os.path.relpath(file_path, workspace_root)
            disk_hashes[rel_path] = calculate_sha256(file_path)

        # 3. Read manifest previous state
        if collection_name not in manifest:
            manifest[collection_name] = {}
        collection_manifest = manifest[collection_name]

        # 4. Detect deleted files
        deleted_files = [f for f in collection_manifest if f not in disk_hashes]
        for rel_path in deleted_files:
            print(f"🗑️ Deleting removed file from index: {rel_path}")
            try:
                vector_store.delete(rel_path)
            except Exception as e:
                print(f"⚠️ Failed to delete {rel_path} from vector store: {e}")
            del collection_manifest[rel_path]

        # 5. Detect new or modified files
        for rel_path, current_hash in disk_hashes.items():
            prev_hash = collection_manifest.get(rel_path)
            
            if prev_hash != current_hash:
                if prev_hash is not None:
                    print(f"✏️ Updating modified file in index: {rel_path}")
                    try:
                        vector_store.delete(rel_path)
                    except Exception as e:
                        print(f"⚠️ Failed to delete old version of {rel_path}: {e}")
                else:
                    print(f"➕ Indexing new file: {rel_path}")

                # Load and index the single file
                full_path = os.path.join(workspace_root, rel_path)
                try:
                    documents = SimpleDirectoryReader(input_files=[full_path]).load_data()
                    # Assign a deterministic doc_id so all chunks reference the file relative path
                    for doc in documents:
                        doc.doc_id = rel_path
                    
                    VectorStoreIndex.from_documents(documents, storage_context=storage_context)
                    collection_manifest[rel_path] = current_hash
                except Exception as e:
                    print(f"❌ Failed to parse/embed file {rel_path}: {e}")

    save_manifest(manifest)
    print("\n✅ Document synchronization completed successfully!")
