# Antigravity Agentic RAG CLI

An Agentic Retrieval-Augmented Generation (RAG) Command Line Interface (CLI) designed to serve as an intelligent chatbot that answers questions based on internal documents. By referencing company handbooks, grading guidelines, student handbooks, and policy files, it ensures compliance and helps users avoid breaking internal rules or policies.

---

## 🎯 Objective

When employees, students, or team members have questions about company rules, course syllabus structures, or grading parameters, making assumptions can lead to critical violations. This project provides a conversational AI chatbot that references verified internal documents before answering.

By feeding internal resources (e.g., guidelines, developer handbooks, and company policy guides) into a local vector database, the chatbot acts as a compliance assistant, ensuring every output is grounded in official, approved reference materials.

---

## 🗺️ Component & Directory Mapping

### 1. Command-Line Entry Point
* **File:** [main.py](file:///C:/Users/USER/Desktop/VScode/rag-agent/main.py)
* **Purpose:** Built using Typer, it acts as the user CLI interface. It supports three major commands:
  - `sync`: Triggers document scanning and incremental vector database updates. Supports a `--mode` option (e.g. `--mode local` or `--mode typhoon`) to choose the extraction method.
  - `start`: Starts an interactive QA prompt session with the RAG agent router.
  - `remove [name]`: Deletes a mapped collection, its local document folder, and database entries.

### 2. Synchronization Manager
* **File:** [sync_manager.py](file:///C:/Users/USER/Desktop/VScode/rag-agent/sync_manager.py)
* **Purpose:** Handles the RAG database ingestion pipeline. It scans document folders, tracks changes/deletions incrementally using file hash comparisons (`.rag_manifest.json`), parses documents (PDF, TXT, MD), and encodes text chunks into vector embeddings via local models.

### 3. Dynamic PDF Extraction Interface
* **File:** [ocr_reader.py](file:///C:/Users/USER/Desktop/VScode/rag-agent/ocr_reader.py)
* **Purpose:** Implements the `HybridPDFReader` facade which dynamically routes PDF processing based on configuration:
  - **Local Mode (`LocalPDFReader`)**: Extracts embedded text layers instantly via PyMuPDF. If the page is scanned (has no text layer), it falls back to a local deep-learning OCR (`easyocr`) if installed. This ensures complete privacy and zero data leakage.
  - **Typhoon OCR Mode (`TyphoonOCRReader`)**: Submits rendered page images concurrently to OpenTyphoon's VLM-based `typhoon-ocr` API. Features a thread-safe rate-limiting lock that enforces a 3-second cooldown interval between request starts to comply with API limits (20 req/min, 2 req/s).

### 4. Query Router Engine
* **File:** [query_engine.py](file:///C:/Users/USER/Desktop/VScode/rag-agent/query_engine.py)
* **Purpose:** Sets up the agentic routing query engine. It connects to ChromaDB, initializes OpenTyphoon LLM, and builds a `RouterQueryEngine` with `LLMMultiSelector` to automatically route incoming questions to the most relevant document collections.

### 5. Dynamic Mapping Configuration
* **File:** [config.json](file:///C:/Users/USER/Desktop/VScode/rag-agent/config.json)
* **Purpose:** Configures collection directories, database collection names, and semantic descriptions. The router LLM uses these descriptions to dynamically select which document store(s) to query.

---

## 🏗️ System Architecture

The following flow represents the indexing (sync) pipeline supporting hybrid PDF extraction, and the query routing (start) pipeline:

```mermaid
graph TD
    %% Define Node Styles
    classDef client fill:#1f2937,stroke:#3b82f6,stroke-width:2px,color:#fff;
    classDef logic fill:#111827,stroke:#10b981,stroke-width:2px,color:#fff;
    classDef db fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#fff;
    classDef external fill:#7c2d12,stroke:#f97316,stroke-width:2px,color:#fff;

    subgraph "Ingestion (Sync) Pipeline"
        Docs[("Local Documents\n(documents/*)")] --> HashCheck["Manifest Compare\n(.rag_manifest.json)"]
        HashCheck -->|New/Modified PDF| Hybrid["HybridPDFReader\n(Routes based on Mode)"]
        HashCheck -->|New/Modified TXT/MD| TextReader["SimpleDirectoryReader\n(Direct Text Extract)"]
        
        Hybrid -->|local mode| LocalReader["LocalPDFReader\n(PyMuPDF Direct Text)"]
        LocalReader -->|Scanned Fallback| EasyOCR["EasyOCR\n(Local Thai/Eng OCR)"]
        Hybrid -->|typhoon mode| OCR["TyphoonOCRReader\n(Thread-Safe 3s Rate Limited)"]
        
        OCR -->|API Request| TyphoonAPI["Typhoon OCR API\n(Cloud VLM)"]
        TyphoonAPI -->|Markdown Text| Splitter["SentenceSplitter\n(1024 Token Chunks)"]
        
        EasyOCR -->|Extracted Text| Splitter
        LocalReader -->|Direct Text| Splitter
        TextReader -->|Direct Text| Splitter
        
        Splitter -->|Generates Nodes| EmbedModel["HuggingFaceEmbedding\n(multilingual-e5-small)"]
        EmbedModel -->|GPU/CUDA Inference| VectorStore["ChromaVectorStore"]
        VectorStore -->|Writes Embeddings| ChromaDB[("Local ChromaDB\n(storage/chroma_db)")]
    end

    subgraph "Retrieval (Query) Pipeline"
        User["User CLI Prompt"] -->|Asks Question| Router["RouterQueryEngine\n(LLMMultiSelector)"]
        Router -->|Decides Target Store| Config["config.json\n(Collection Descriptions)"]
        Router -->|API Request| LLM["OpenTyphoon API\n(typhoon-v2.5-30b)"]
        Router -->|Fetches Context| ChromaDB
        LLM -->|Generates Answer| User
    end

    %% Apply styles
    class User client;
    class TextReader,Hybrid,LocalReader,EasyOCR,OCR,Splitter,HashCheck,Router logic;
    class Docs,ChromaDB,VectorStore db;
    class EmbedModel,LLM,TyphoonAPI external;
```

---

## 🚀 Getting Started & Installation

### Prerequisites
- Python >= 3.9 (Python 3.12 recommended)
- An active **OpenTyphoon API Key**
- NVIDIA Graphics Card with CUDA support (Optional, recommended for GPU acceleration)

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/PhoengZ/rag-agent-help-studying.git
   cd rag-agent
   ```

2. **Set up Virtual Environment:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies:**
   ```powershell
   pip install --upgrade pip
   pip install -e .
   ```

4. **Install GPU-Accelerated PyTorch & Optional Local OCR Support:**
   - To utilize your GPU and accelerate the PDF indexing process (by 10x-50x), install the CUDA 12.4 version of PyTorch:
     ```powershell
     pip install torch --index-url https://download.pytorch.org/whl/cu124 --force-reinstall
     ```
   - (Optional) Install `easyocr` to support local fallback OCR for scanned PDFs:
     ```powershell
     pip install easyocr
     ```

5. **Configure Environment Variables:**
   Create a `.env` file in the root directory and specify your credentials and mode choice:
   ```env
   TYPHOON_API_KEY=your_typhoon_api_key_here
   CHROMA_DB_PATH=./storage/chroma_db
   DOCUMENTS_DIR=./documents
   PDF_EXTRACT_MODE=local
   ```

6. **Initialize / Index Documents:**
   Place your PDFs/documents inside the mapped directories (configured in `config.json` e.g., `./documents/DSDE`), then run:
   ```powershell
   # Syncs using the default mode in .env (local)
   python main.py sync
   
   # Or explicitly choose the mode via CLI options:
   python main.py sync --mode typhoon
   python main.py sync --mode local
   ```

7. **Start Chatting:**
   ```powershell
   python main.py start
   ```

---

## ⚙️ Environmental Configuration (.env)

The application requires the following environment variables. Set them in a `.env` file in the project root:

```env
# ==========================================
# OpenTyphoon LLM Configurations
# ==========================================
# [Required] Your personal OpenTyphoon API token (compatible with OpenAI Like Client and OCR)
TYPHOON_API_KEY=sk-your-typhoon-api-key

# ==========================================
# Local Storage Configurations
# ==========================================
# [Optional] Relative or absolute path to persistent database files
CHROMA_DB_PATH=./storage/chroma_db

# [Optional] Root directory where your source folders exist
DOCUMENTS_DIR=./documents

# ==========================================
# Ingestion Configurations
# ==========================================
# [Optional] PDF text extraction mode: local or typhoon (default: local)
# Set to 'local' for complete privacy and data-leak prevention.
PDF_EXTRACT_MODE=local
```
