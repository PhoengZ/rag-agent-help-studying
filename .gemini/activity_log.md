# Activity Log

## [2026-06-02] - Initial Review and Feasibility Analysis of plan.md
- **Attempted**: Initiated feasibility, vulnerability, and architectural review of the proposed Agentic RAG CLI in `plan.md`.
- **Hypothesis**: The proposed plan has significant security vulnerabilities (hardcoding keys, global ENV leaks, CLI configuration injection), performance issues (re-reading and re-embedding all files every sync run), and scaling issues with `ChromaDB` and LlamaIndex selectors.
- **Observed Result/Outcome**: Completed the in-depth review and published the detailed report in `feasibility_report.md`. Key findings show severe crash vulnerabilities due to missing embedding model settings, performance decay from redundant ingestion, security path traversal vectors, and sub-optimal routing behaviors. Suggested a robust design replacing shell aliases with entry points, adding file-hash tracking for synchronization, and using local Thai-compatible embedding models.

## [2026-06-02] - Comparison with VectifyAI's OpenKB
- **Attempted**: Conducted comparative analysis between the proposed LlamaIndex + ChromaDB RAG CLI structure and VectifyAI's OpenKB (Open LLM Knowledge Base) framework.
- **Hypothesis**: OpenKB's vectorless PageIndex tree and Markdown compilation approach offers superior context synthesis but incurs much higher LLM compilation token costs, slower indexing speeds, and dependency on powerful LLMs (like Claude/GPT-4o) compared to our local embedding RAG CLI design.
- **Observed Result/Outcome**: Report compiled in `openkb_comparison.md`.

## [2026-06-02] - Debugging 404 Not Found in OpenTyphoon API
- **Attempted**: Isolated 404 Not Found error occurred during user queries.
- **Hypothesis**: The model name `typhoon-v1.5x-70b-instruct` was deprecated, and the completions endpoint `/v1/completions` was not supported by OpenTyphoon.
- **Observed Result/Outcome**: Verified that OpenTyphoon only supports `/v1/chat/completions`. Updated the model to `typhoon-v2.5-30b-a3b-instruct` and added the parameter `is_chat_model=True` to the `OpenAILike` initialization to route completions correctly. System verified functional.

## [2026-06-02] - Debugging PDF Embedding Slowness
- **Attempted**: Diagnosed slow embedding of PDF files (e.g. `1_DataScienceOverview.pdf`) and verified GPU CUDA availability.
- **Hypothesis**:
  1. The installed `torch` library was CPU-only (`2.12.0+cpu`), preventing GPU acceleration.
  2. The default model `BAAI/bge-m3` is too large (567M params) and slow on CPU.
  3. The PDF is parsed into a single large string chunk with 6.8 million characters, resulting in 8327 text nodes, causing a massive bottleneck when embedding chunk-by-chunk.
- **Observed Result/Outcome**:
  1. Verified user has an NVIDIA GeForce RTX 3050 Laptop GPU. Force-reinstalled `torch` with CUDA 12.4 support (`2.6.0+cu124`).
  2. Created scratch benchmark scripts to isolate performance:
     - PDF parsing takes ~0.29 seconds.
     - PDF yields 8327 nodes.
     - On CUDA GPU, `BAAI/bge-m3` processes 5.05 chunks/sec (~27.5 minutes for full doc).
     - On CUDA GPU, `intfloat/multilingual-e5-small` processes ~70 chunks/sec (~2.0 minutes for full doc).
  3. Decided to switch embedding model to `intfloat/multilingual-e5-small` and enable CUDA device loading with batch size of 64.

## [2026-06-02] - Update Gitignore
- **Attempted**: Updated `.gitignore` to prevent tracking of local document files.
- **Hypothesis**: Adding `documents/` to `.gitignore` will ignore local files/folders under the documents directory.
- **Observed Result/Outcome**: Appended `documents/` to `.gitignore`. Ran `git status` and verified that untracked directories like `documents/DSDE/` and `documents/IOT/` are now successfully ignored by Git.

## [2026-06-02] - Typhoon OCR Integration
- **Attempted**: Created a custom `TyphoonOCRReader` implementing LlamaIndex's `BaseReader` to render PDF pages into images in-memory (using `pymupdf`) and call `typhoon-ocr` via parallel threads. Integrated the reader into `sync_manager.py` for `.pdf` files.
- **Hypothesis**: In-memory rendering combined with concurrent API calls will efficiently extract text from lecture slides and image-only PDFs, which can then be successfully embedded by `multilingual-e5-small`.
- **Observed Result/Outcome**: Installed `pymupdf` dependency. Verified with a test script on `3_Grader Handbook.pdf` that page-by-page OCR works correctly. Executed incremental synchronization (`main.py sync`) which successfully updated the vector store index using the new OCR pipeline.


## [2026-06-03] - Hybrid PDF Text Extraction & User Choice Mode
- **Attempted**: Designed and implemented a hybrid PDF text extraction strategy in `ocr_reader.py`, `sync_manager.py`, and `main.py` allowing users to choose between `local` extraction (first trying direct PyMuPDF text layer parsing, with local EasyOCR fallback) and `typhoon` (cloud-based Typhoon OCR).
- **Hypothesis**: Giving users choice via `--mode` CLI flag and `PDF_EXTRACT_MODE` environment variable allows privacy-first operation (preventing data leakage) while maintaining high-fidelity cloud-based OCR when requested.
- **Observed Result/Outcome**: Refactored `ocr_reader.py` to create `LocalPDFReader` and `HybridPDFReader` wrapper, updated `sync_manager.py` and `main.py` to support passing `--mode` options. Created a verification script (`scratch/test_hybrid_reader.py`) and verified that it successfully runs direct text extraction on digital pages, falls back gracefully to print a warning when `easyocr` is missing for scanned pages, and routes calls dynamically based on CLI/environment flags.
