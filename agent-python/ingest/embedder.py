"""
ingest/embedder.py

Embeds code at function/class granularity rather than arbitrary text chunks.

Why this matters
----------------
The old approach split files by character count (chunk_size=1000). A function
could be split mid-body, losing context. A docstring could land in a different
chunk than its implementation.

This embedder creates one embedding unit per symbol:
    [signature] + [docstring] + [source body]

Each chunk is a semantically complete unit. Retrieval therefore returns whole
functions rather than orphaned fragments.
"""

from typing import List

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv

from ingest.ast_parser import FileAnalysis

from core.paths import get_embedding_model, get_persist_dir,get_env_path

load_dotenv(dotenv_path=get_env_path())
COLLECTION_NAME = "codebase_symbols"

_GLOBAL_EMBEDDING_FN = None
def _make_documents(analyses: List[FileAnalysis]) -> List[Document]:
    """
    Convert parsed FileAnalysis objects into LangChain Documents.

    Each document represents one function or one class.
    Metadata is rich enough for the retriever to reconstruct location info.
    """
    docs: List[Document] = []

    for analysis in analyses:
        if analysis.parse_error:
            continue

        for fn in analysis.functions:
            # Embed: signature + docstring + source body
            # The signature appears first so the embedding captures
            # the function's type contract prominently.
            text_parts = [fn.signature]
            if fn.docstring:
                text_parts.append(f'"""{fn.docstring}"""')
            text_parts.append(fn.source)
            text = "\n".join(text_parts)

            docs.append(Document(
                page_content=text,
                metadata={
                    "kind": "function",
                    "name": fn.name,
                    "qualified_name": fn.qualified_name,
                    "source": fn.file,
                    "line_start": fn.line_start,
                    "line_end": fn.line_end,
                    "class_name": fn.class_name or "",
                    "is_method": str(fn.is_method),
                    "signature": fn.signature,
                    "has_docstring": str(bool(fn.docstring)),
                },
            ))

        for cls in analysis.classes:
            text_parts = [f"class {cls.name}({', '.join(cls.bases)}):"]
            if cls.docstring:
                text_parts.append(f'    """{cls.docstring}"""')
            text_parts.append(cls.source)
            text = "\n".join(text_parts)

            docs.append(Document(
                page_content=text,
                metadata={
                    "kind": "class",
                    "name": cls.name,
                    "qualified_name": cls.name,
                    "source": cls.file,
                    "line_start": cls.line_start,
                    "line_end": cls.line_end,
                    "class_name": cls.name,
                    "bases": ", ".join(cls.bases),
                    "signature": f"class {cls.name}",
                    "has_docstring": str(bool(cls.docstring)),
                },
            ))

    return docs

def _get_embedding_fn():
    global _GLOBAL_EMBEDDING_FN
    if _GLOBAL_EMBEDDING_FN is not None:
        return _GLOBAL_EMBEDDING_FN
    model_name = get_embedding_model()
    if model_name:
        print(f"[Embedder] Using model: {model_name}")
        _GLOBAL_EMBEDDING_FN = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cuda", "trust_remote_code": True},
        )
        return _GLOBAL_EMBEDDING_FN
    else:
        print("[Embedder] No embedding model found. Using default HuggingFace model (jinaai/jina-code-embeddings-1.5b).")
        _GLOBAL_EMBEDDING_FN = HuggingFaceEmbeddings(
            model_name="jinaai/jina-code-embeddings-1.5b",
            model_kwargs={"device": "cuda", "trust_remote_code": True},
        )
        return _GLOBAL_EMBEDDING_FN

def build_vector_store(
    analyses: List[FileAnalysis]
    , persist_directory: str = None
) -> Chroma:
    """
    Build (or rebuild) the ChromaDB vector store from parsed FileAnalysis objects.
    Replaces the old ingest.py logic with function-level embeddings.
    """
    docs = _make_documents(analyses)
    print(f"[Embedder] Embedding {len(docs)} symbol documents...")

    embedding_fn = _get_embedding_fn()

    # Batch to avoid OOM on large repos
    BATCH = 1
    db = None
    for i in range(0, len(docs), BATCH):
        batch = docs[i : i + BATCH]
        if db is None:
            db = Chroma.from_documents(
                documents=batch,
                embedding=embedding_fn,
                persist_directory=persist_directory or get_persist_dir(),
                collection_name=COLLECTION_NAME,
            )
        else:
            db.add_documents(batch)
        print(f"  [Embedder] {min(i + BATCH, len(docs))}/{len(docs)} embedded...")

    print(f"[Embedder] Vector store saved to '{persist_directory or get_persist_dir()}'.")
    return db


def load_vector_store(persist_directory: str = get_persist_dir()) -> Chroma:
    """Load an existing vector store (no re-embedding)."""
    return Chroma(
        persist_directory=persist_directory or get_persist_dir(),
        embedding_function=_get_embedding_fn(),
        collection_name=COLLECTION_NAME,
    )
