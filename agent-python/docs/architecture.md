# High-Level Architecture Overview

## System Purpose
The retrieval system is designed to provide comprehensive codebase analysis, documentation generation, and interactive Q&A capabilities. It leverages various modules to manage different aspects of the system, including ingestion, indexing, retrieval, and processing user queries.

## Module Responsibilities

- **main.py**
  - Initializes and runs the retrieval system.
  - Loads essential components such as a vector store.
  - Handles command-line interactions.

- **qa.py**
  - Provides a Q&A system for interactive use.
  - Manages question answering tasks using a `HybridRetriever`.

- **review.py**
  - Orchestrates a comprehensive code review process.
  - Executes static and semantic analysis on user-provided code.

- **docs.py**
  - Generates and updates documentation for a codebase.
  - Supports incremental updates and full regeneration of documentation.

- **worker.py**
  - Processes user requests to generate analysis findings.
  - Utilizes language models for code snippet analysis.

- **model_manager.py**
  - Manages models in an environment using Ollama.
  - Facilitates unloading, pre-loading, and checking the status of models.

- **orchestrator.py**
  - Coordinates a multi-agent pipeline to handle user requests.
  - Plans the depth of review, executes tasks, and synthesizes results.

- **hybrid_retriever.py**
  - Provides hybrid retrieval of code symbols based on natural language queries.
  - Combines vector search with dependency graph expansion.

- **run_ingest.py**
  - Executes the ingestion process for indexing source code.
  - Orchestrates data acquisition, processing, and storage tasks.

- **embedder.py**
  - Manages documents using a vector store.
  - Provides functionality for embedding and managing documents.

- **dep_graph.py**
  - Analyzes and queries a dependency graph constructed from file analysis data.
  - Supports hybrid retrieval systems by expanding search contexts.

- **ast_parser.py**
  - Parses Python source code and performs static analysis.
  - Utilizes the `ast` module for abstract syntax tree parsing.

- **symbol_index.py**
  - Manages a symbol database using SQLite.
  - Provides indexing and retrieval capabilities for symbols.

## Data Flow Between Modules

1. **main.py** initializes the system and loads shared resources, including the vector store.
2. **run_ingest.py** orchestrates the ingestion process, parsing source code and building an index.
3. **embedder.py** manages document embedding using a vector store, which is then used by other modules for retrieval.
4. **dep_graph.py** constructs and queries a dependency graph, providing context for hybrid retrieval.
5. **ast_parser.py** performs static analysis on Python source code, generating findings that are processed by the review system.
6. **review.py** orchestrates the code review process, utilizing static and semantic analysis results.
7. **qa.py** handles interactive Q&A sessions, using a `HybridRetriever` to retrieve answers based on user queries.
8. **docs.py** generates or updates documentation for the codebase, leveraging the indexed data.
9. **worker.py** processes user requests, generating analysis findings using language models.
10. **model_manager.py** manages model loading and unloading, optimizing performance.
11. **orchestrator.py** coordinates tasks across multiple agents, planning and synthesizing results.

## External Dependencies

- **Vector Store (e.g., ChromaDB)**
  - Used by `embedder.py` for document embedding and retrieval.
  
- **Dependency Graph (NetworkX)**
  - Utilized by `dep_graph.py` for analyzing and querying dependencies.

- **Static Analysis Libraries**
  - Required by `ast_parser.py` for parsing and analyzing Python source code.

- **SQLite Database**
  - Used by `symbol_index.py` for indexing and retrieving symbols.

- **Ollama (Machine Learning Model Management)**
  - Managed by `model_manager.py` for model loading and unloading.

- **Command-Line Interface Libraries**
  - Required by `main.py` for handling user interactions.

- **File System Operations**
  - Used by various modules for reading, writing, and detecting changes in source code files.

- **Network Connectivity**
  - Necessary for communication with Ollama and other external services.

This architecture ensures a modular and scalable system capable of efficiently managing codebase analysis, documentation generation, and interactive Q&A functionalities.