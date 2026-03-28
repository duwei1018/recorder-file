# Changelog

## [1.0.0] - 2026-03-27

### Initial Release

**Core pipeline (Phase 1) — fully functional**

- `pipeline/transcribe.py` — Whisper-based audio-to-text (supports mp3/wav/m4a/mp4/flac/ogg/wma/aac), model cached globally for batch runs
- `pipeline/dialogue.py` — LLM reformats raw transcript into interviewer/respondent Q&A pairs
- `pipeline/summarize.py` — LLM extracts 5-section structured research summary (key points, data, industry status, risks, follow-ups); full dialogue appended at end of output file
- `utils/llm.py` — Ollama caller with auto-chunking (>3000 chars split by paragraph) and retry logic (up to 3 attempts with backoff)
- `utils/cache.py` — JSON-based file cache to skip already-processed audio
- `utils/logger.py` — Unified logger writing to `agent.log`
- `main.py` — CLI entry point with `--file / --step / --force / --model` flags; environment checks for input dir and Ollama connectivity
- `config.yaml` — Input: `D:\icloud\iCloudDrive\Desktop\recorder-file`; Output: `D:\SynologyDrive\行业研究\访谈纪要`
- `启动.ps1` — Interactive menu launcher (English prompts to avoid encoding issues)
- `scripts/backup_code.ps1` — Desktop backup script matching info-collector scheme (7 timestamped snapshots + latest)

**Automation**
- Windows Task Scheduler task `RecorderFile-AutoRun` set to poll every 30 minutes silently (`-WindowStyle Hidden`)

**Stubs (Phase 2 & 3 — not yet implemented)**
- `knowledge/store.py` — ChromaDB vector store (placeholder)
- `knowledge/indexer.py` — Document embedding indexer (placeholder)
- `knowledge/retriever.py` — Semantic retrieval (placeholder)
- `inference/engine.py` — Cross-document inference engine (placeholder)
