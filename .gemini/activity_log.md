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

