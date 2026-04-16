from __future__ import annotations

import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral-small:latest")
# Embedding model must be pulled in Ollama, e.g. `ollama pull nomic-embed-text`
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333").rstrip("/")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "copilot_chunks")

# Chunking for vector index
CHUNK_MAX_CHARS = int(os.getenv("CHUNK_MAX_CHARS", "600"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "80"))

# RAG quality (citations shown to the model and UI)
RAG_MIN_VECTOR_SCORE = float(os.getenv("RAG_MIN_VECTOR_SCORE", "0.28"))
RAG_MAX_CITATIONS = int(os.getenv("RAG_MAX_CITATIONS", "6"))
RAG_MAX_VECTOR = int(os.getenv("RAG_MAX_VECTOR", "4"))
RAG_MAX_KEYWORD = int(os.getenv("RAG_MAX_KEYWORD", "2"))
