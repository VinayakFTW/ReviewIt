# `embedder.py`

This module provides functionality for embedding file content into a vector store using HuggingFace embeddings and storing it in ChromaDB. The public API includes `build_vector_store` to create or rebuild the vector store from parsed file analysis objects, and `load_vector_store` to load an existing vector store without re-embedding. Key dependencies include LangChain for document handling, HuggingFace for embedding models, and ChromaDB for vector storage.

## Functions

### `def _make_documents(analyses: List[FileAnalysis]) -> List[Document]:`
*D:\CodeSentinel\agent-python\ingest\embedder.py:34*

Convert parsed FileAnalysis objects into LangChain Documents.

Each document represents one function or one class.
Metadata is rich enough for the retriever to reconstruct location info.

### `def _get_embedding_fn():`
*D:\CodeSentinel\agent-python\ingest\embedder.py:98*

Retrieves and returns a HuggingFaceEmbeddings instance configured with the specified model. Prints the model name being used.

Parameters:
- None

Return value:
- A HuggingFaceEmbeddings object initialized with the model specified by `get_embedding_model()`.

Raises:
- None

### `def build_vector_store(analyses: List[FileAnalysis], persist_directory: str=None) -> Chroma:`
*D:\CodeSentinel\agent-python\ingest\embedder.py:106*

Build (or rebuild) the ChromaDB vector store from parsed FileAnalysis objects.
Replaces the old ingest.py logic with function-level embeddings.

### `def load_vector_store(persist_directory: str=get_persist_dir()) -> Chroma:`
*D:\CodeSentinel\agent-python\ingest\embedder.py:139*

Load an existing vector store (no re-embedding).

## Static Analysis Warnings

- **[LOW]** line 34: `_make_documents` is 62 lines long (limit: 60).
- **[LOW]** line 98: `_get_embedding_fn` has no return type annotation.
