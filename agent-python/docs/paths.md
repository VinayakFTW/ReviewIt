# `paths.py`

This module provides utility functions to retrieve various directory paths used by an application, ensuring they are writable where necessary. Key functions include `get_app_dir`, which returns the directory that owns the process; `get_meipass_dir`, for accessing files unpacked by PyInstaller; and `get_env_path`, which locates the `.env` file. Other important functions like `get_data_dir`, `get_persist_dir`, and `get_docs_dir` provide paths to data, persistent storage, and documentation directories respectively. The module also includes functions to get paths for specific files such as the symbol database (`get_symbol_db`) and dependency graph (`get_dep_graph`). Additionally, it retrieves environment variables like `SOURCE_DIR` and `EMBEDDING_MODEL_PATH`. This module relies on the `os`, `sys`, and `pathlib` libraries to handle file system operations and path manipulations.

## Functions

### `def get_app_dir() -> str:`
*D:\CodeSentinel\agent-python\core\paths.py:14*

The directory that owns the process. Always writable.
  - Frozen exe  : dirname(sys.executable)  → dist/CodeSentinel/
  - Script mode : project root (two levels up from core/paths.py)

### `def get_meipass_dir() -> str:`
*D:\CodeSentinel\agent-python\core\paths.py:26*

Where PyInstaller unpacks --add-data files.
  - PyInstaller 6+ : dist/CodeSentinel/_internal/   (sys._MEIPASS)
  - PyInstaller 5  : dist/CodeSentinel/              (sys._MEIPASS == exe dir)
  - Script mode    : project root (same as get_app_dir)
Never hardcode _internal/ — always read sys._MEIPASS.

### `def get_env_path() -> str:`
*D:\CodeSentinel\agent-python\core\paths.py:39*

.env file lives next to the exe (or project root in dev).
Never os.path.dirname(__file__) — that resolves to _internal/ when frozen.

### `def get_data_dir() -> str:`
*D:\CodeSentinel\agent-python\core\paths.py:47*

data/ directory — writable, next to the exe.
Reads DATA_DIR env var first (set by cli.py after user picks a repo).

### `def get_persist_dir() -> str:`
*D:\CodeSentinel\agent-python\core\paths.py:58*

Returns the directory path for persistent storage. If the environment variable PERSIST_DIRECTORY is set, it returns its value; otherwise, it constructs a path by joining the data directory with 'chroma_db'. Returns: str - The directory path. Raises: None.

### `def get_symbol_db() -> str:`
*D:\CodeSentinel\agent-python\core\paths.py:63*

Returns the path to the symbol database. If the environment variable SYMBOL_DB_PATH is set, it returns its value; otherwise, it constructs a default path by joining the data directory with 'symbol_index.db'. No parameters. Returns a string representing the file path. Raises no exceptions.

### `def get_dep_graph() -> str:`
*D:\CodeSentinel\agent-python\core\paths.py:68*

Returns the path to the dependency graph file. If the environment variable DEP_GRAPH_PATH is set, returns its value; otherwise, constructs and returns a path by joining the data directory with 'dep_graph.graphml'. No parameters. Returns a string representing the file path. Raises no exceptions.

### `def get_embedding_model() -> str:`
*D:\CodeSentinel\agent-python\core\paths.py:73*

Priority:
1. offline_model/ bundled via --add-data  (frozen exe, sys._MEIPASS)
2. offline_model/ in project root          (dev / script mode)
3. EMBEDDING_MODEL_NAME env var            (HuggingFace download fallback)
4. hardcoded HuggingFace default           (last resort)

### `def get_docs_dir(source_dir: str=None) -> str:`
*D:\CodeSentinel\agent-python\core\paths.py:104*

Returns the directory path for documentation files. Uses the environment variable `DOCS_DIR` if set; otherwise, constructs a path within the source directory or app directory. Parameters: source_dir (str): Optional source directory path. Returns: str: Path to the documentation directory. Raises: None.

### `def get_source_dir() -> str:`
*D:\CodeSentinel\agent-python\core\paths.py:109*

Retrieves the value of the SOURCE_DIR environment variable. If the variable is not set, raises an EnvironmentError with a message prompting the user to run cli.py to configure a repository.

Parameters:
- None

Return Value:
- str: The value of the SOURCE_DIR environment variable.

Raises:
- EnvironmentError: If the SOURCE_DIR environment variable is not set.
