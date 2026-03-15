# `embedder.py`

This module provides functionality for embedding and managing documents using a vector store. It includes key classes and functions such as `_make_documents` for converting parsed `FileAnalysis` objects into LangChain Documents, `build_vector_store` for constructing or rebuilding a ChromaDB vector store from these documents, and `load_vector_store` for loading an existing vector store without re-embedding. The module relies on important dependencies like LangChain for document handling and ChromaDB for vector storage.

## Functions

### `def _make_documents(analyses: List[FileAnalysis]) -> List[Document]:`
*ingest/embedder.py:39*

Convert parsed FileAnalysis objects into LangChain Documents.

Each document represents one function or one class.
Metadata is rich enough for the retriever to reconstruct location info.

### `def build_vector_store(analyses: List[FileAnalysis], persist_dir: str=PERSIST_DIRECTORY) -> Chroma:`
*ingest/embedder.py:104*

Build (or rebuild) the ChromaDB vector store from parsed FileAnalysis objects.
Replaces the old ingest.py logic with function-level embeddings.

### `def load_vector_store(persist_dir: str=PERSIST_DIRECTORY) -> Chroma:`
*ingest/embedder.py:140*

Load an existing vector store (no re-embedding).

## Static Analysis Warnings

- **[LOW]** line 39: `_make_documents` is 62 lines long (limit: 60).
