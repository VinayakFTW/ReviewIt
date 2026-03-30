"""
tui.py

Textual User Interface for Code-Sentinel.
Uses native Textual Messages for thread-safe cross-communication between 
deep pipeline threads (like ReviewWorker pools) and the main UI event loop.
"""

import os
import gc
from typing import Optional

from dotenv import set_key, load_dotenv
from setup import setup_environment

from textual import work
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import VerticalScroll, Horizontal, Center, Vertical
from textual.widgets import Header, Footer, Input, Markdown, Static, Button
from textual.message import Message

from pipelines.qa import QAPipeline
from pipelines.review import ReviewPipeline
from pipelines.docs import DocsPipeline
from core.paths import get_source_dir, get_persist_dir, get_symbol_db, get_dep_graph,get_env_path,get_meipass_dir
from main import load_shared_resources


# --- Custom Thread-Safe Messages ---

class AgentMessage(Message):
    """Fired by background threads to safely update the chat UI."""
    def __init__(self, text: str, role: str = "agent") -> None:
        self.text = text
        self.role = role
        super().__init__()

class AppStateChange(Message):
    """Fired to safely enable/disable the input box from the main thread."""
    def __init__(self, is_processing: bool) -> None:
        self.is_processing = is_processing
        super().__init__()


# --- UI Widgets ---

class ChatBubble(Static):
    """A widget representing a single chat message."""
    def __init__(self, text: str, role: str) -> None:
        super().__init__()
        self.text = text
        self.role = role
        self.classes = f"message-{self.role}"

    def compose(self) -> ComposeResult:
        if self.role == "agent":
            yield Markdown(self.text)
        else:
            yield Static(self.text)


# --- Screens ---

class RepoSelectScreen(Screen):
    """Screen to select and validate the repository path."""
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Center(id="welcome-container"):
            with Vertical(id="repo-dialog"):
                yield Static("📁 Select Repository", id="welcome-title")
                yield Static("Enter the absolute path to your codebase:", id="welcome-text")
                yield Input(placeholder="e.g., C:\\Projects\\MyRepo or /Users/me/repo", id="repo-input")
                yield Static("", id="repo-error", classes="error-text")
                with Horizontal(id="button-container"):
                    yield Button("Continue", variant="primary", id="btn_repo_continue")
        yield Footer()

    def on_mount(self) -> None:
        """Pre-fill the input if a repo was previously selected."""
        current_repo = os.environ.get("SOURCE_DIR", "")
        inp = self.query_one("#repo-input", Input)
        if current_repo:
            inp.value = current_repo
        inp.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_repo_continue":
            self.process_repo()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Allow hitting Enter in the input box to submit."""
        if event.input.id == "repo-input":
            self.process_repo()

    def process_repo(self) -> None:
        """Validates the path and configures the environment."""
        repo_path = self.query_one("#repo-input", Input).value.strip().strip('"').strip("'")
        error_label = self.query_one("#repo-error", Static)

        if not repo_path:
            error_label.update("Path cannot be empty.")
            return

        if not os.path.exists(repo_path):
            error_label.update(f"Error: Path '{repo_path}' does not exist.")
            return

        error_label.update("") # Clear errors
        
        # 1. Ensure .env exists
        env_path = get_env_path()
        if not os.path.exists(env_path):
            open(env_path, 'a').close()
        
        # 2. Set the environment variables in memory
        setup_environment(repo_path)
        
        # 3. Persist them to .env across restarts
        for key in ["SOURCE_DIR", "DATA_DIR", "PERSIST_DIRECTORY", "SYMBOL_DB_PATH", "DEP_GRAPH_PATH", "DOCS_DIR"]:
            if key in os.environ:
                set_key(env_path, key, os.environ[key])
        
        # 4. Reload them just to be perfectly synced
        load_dotenv(dotenv_path=env_path, override=True)
        
        # 5. Move to the Index check screen!
        self.app.switch_screen(WelcomeScreen())


class WelcomeScreen(Screen):
    """Elegant startup screen asking whether to ingest or use existing indexes."""
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Center(id="welcome-container"):
            with Vertical(id="welcome-dialog"):
                yield Static("🛡️ Code-Sentinel v2", id="welcome-title")
                
                # Check if indexes exist
                vector_dir = get_persist_dir()
                symbol_db = get_symbol_db()
                dep_graph = get_dep_graph()
                
                needs_ingest = not (
                    os.path.exists(vector_dir) and 
                    os.path.exists(symbol_db) and 
                    os.path.exists(dep_graph)
                )

                if needs_ingest:
                    yield Static("No indexes found for this repository.\nWe need to scan and ingest the codebase before starting.", id="welcome-text")
                    with Horizontal(id="button-container"):
                        yield Button("Start Ingestion", variant="success", id="btn_ingest")
                else:
                    yield Static("Existing indexes found for this repository.\nWould you like to re-scan the codebase or use the existing data?", id="welcome-text")
                    with Horizontal(id="button-container"):
                        yield Button("Use Existing Indexes", variant="primary", id="btn_skip")
                        yield Button("Re-Ingest Codebase", variant="warning", id="btn_reingest")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        
        chat_screen = ChatScreen()
        self.app.push_screen(chat_screen)

        if button_id == "btn_skip":
            chat_screen.start_loading_resources(reingest=False)
        elif button_id in ("btn_ingest", "btn_reingest"):
            chat_screen.start_loading_resources(reingest=True, verbose=True)


class ChatScreen(Screen):
    """The main chat interface."""
    
    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="chat-container"):
            yield Static(id="chat-history")
        with Horizontal(id="input-container"):
            yield Input(placeholder="Ask about the code or type a /command...", id="chat-input")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Input).disabled = True

    # --- Native Textual Event Handlers (Run strictly on Main Thread) ---
    
    def on_agent_message(self, message: AgentMessage) -> None:
        """Handles chat updates from any background thread safely."""
        chat_container = self.query_one("#chat-container")
        new_bubble = ChatBubble(message.text, message.role)
        chat_container.mount(new_bubble)
        new_bubble.scroll_visible()

    def on_app_state_change(self, message: AppStateChange) -> None:
        """Safely toggles the input box state."""
        inp = self.query_one(Input)
        inp.disabled = message.is_processing
        if not message.is_processing:
            inp.focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value.strip()
        if not user_text:
            return

        # Clear and disable input immediately
        input_widget = self.query_one(Input)
        input_widget.value = ""
        self.post_message(AppStateChange(is_processing=True))
        
        self.post_message(AgentMessage(user_text, "user"))
        self.process_request_bg(user_text)

    # --- Background Workers ---
    
    def _pipeline_print(self, text: str) -> None:
        """
        The callback passed to pipelines. 
        `self.post_message` is inherently thread-safe in Textual!
        """
        self.post_message(AgentMessage(str(text), "agent"))

    @work(thread=True,exclusive=True)
    def start_loading_resources(self, reingest: bool, verbose: bool = False) -> None:
        """Background thread for heavy IO/Index loading."""
        app = self.app
        source_dir = get_source_dir()
        
        if reingest:
            self.post_message(AgentMessage("Starting codebase ingestion. This might take a minute..."))
            from ingest.run_ingest import run_ingest
            try:
                # If we are re-ingesting mid-session, we MUST free DB locks first
                app.free_database_locks()
                if verbose:
                    self._pipeline_print("Verbose mode enabled: Ingest will print detailed logs to the chat.")
                    run_ingest(source_dir, clean=True, verbose=verbose, output_callback=self._pipeline_print)
                else:
                    run_ingest(source_dir, clean=True)
                self.post_message(AgentMessage("Ingestion complete! Loading resources..."))
            except Exception as e:
                self.post_message(AgentMessage(f"Ingestion failed: {e}. You may need to restart the app."))
                self.post_message(AppStateChange(is_processing=False))
                return

        self.post_message(AgentMessage("Loading ChromaDB and local indexes into memory..."))
        
        # Load resources
        app.retriever = load_shared_resources()
        app.qa_pipeline = QAPipeline(app.retriever, output_callback=self._pipeline_print)
        app.review_pipeline = ReviewPipeline(
            retriever=app.retriever, 
            symbol_index=app.retriever.si, 
            source_dir=source_dir,
            output_callback=self._pipeline_print
        )
        app.docs_pipeline = DocsPipeline(
            retriever=app.retriever, 
            source_dir=source_dir,
            output_callback=self._pipeline_print
        )
        
        self.post_message(AgentMessage("System Online. You can ask questions, or use `/review`, `/docs`, or `/reindex`."))
        self.post_message(AppStateChange(is_processing=False))

    @work(thread=True,exclusive=True)
    def process_request_bg(self, text: str) -> None:
        """Background thread for LLM generation and Pipeline logic."""
        app = self.app
        
        try:
            if text.startswith("/"):
                command = text.lower()
                
                if command.startswith("/review"):
                    self.post_message(AgentMessage("Starting full codebase audit..."))
                    review_md, _ = app.review_pipeline.run(user_request="Full codebase audit")
                    self.post_message(AgentMessage(f"Review complete!\n\n{review_md}"))
                    self.post_message(AgentMessage("You can ask questions, or use `/review`, `/docs`, or `/reindex`."))
                    
                elif command.startswith("/docs"):
                    parts = text.split()
                    arg = parts[1] if len(parts) > 1 else "inc"
                    
                    if arg.lower() == "full":
                        self.post_message(AgentMessage("Running FULL codebase documentation..."))
                        app.docs_pipeline.run_full()
                    else:
                        # If it's not "full" and not "inc", assume the user typed a git ref
                        since_ref = "HEAD~1" if arg.lower() == "inc" else arg
                        self.post_message(AgentMessage(f"Running incremental docs since `{since_ref}`..."))
                        app.docs_pipeline.run_incremental(since=since_ref)
                        
                    self.post_message(AgentMessage("Documentation generation complete."))
                    self.post_message(AgentMessage("You can ask questions, or use `/review`, `/docs`, or `/reindex`."))
                elif command.startswith("/reindex"):
                    self.post_message(AgentMessage("Attempting to release file locks and re-index..."))
                    if text.split()[1] == 'verbose':
                        self.app.call_from_thread(self.start_loading_resources(reingest=True,verbose=True))
                    else:
                        self.app.call_from_thread(self.start_loading_resources(reingest=True,verbose=False))
                    
                    self.post_message(AgentMessage("You can ask questions, or use `/review`, `/docs`, or `/reindex`."))
                    return # start_loading_resources handles the AppStateChange internally
                else:
                    self.post_message(AgentMessage(f"Unknown command: `{command}`"))
                    
            else:
                answer = app.qa_pipeline.ask(text, verbose=False)
                self.post_message(AgentMessage(answer))
        
        except Exception as e:
            self.post_message(AgentMessage(f"Pipeline error: {str(e)}"))
        finally:
            self.post_message(AppStateChange(is_processing=False))


class CodeSentinelUI(App):
    """The master application class."""
    
    CSS_PATH = os.path.join(get_meipass_dir(), "app.tcss")
    TITLE = "Code-Sentinel v2"
    SUB_TITLE = "Local AI Code Intelligence"
    
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+r", "clear_chat", "Clear Chat")
    ]

    def __init__(self) -> None:
        super().__init__()
        self.retriever = None
        self.qa_pipeline = None
        self.review_pipeline = None
        self.docs_pipeline = None

    def on_mount(self) -> None:
        self.install_screen(ChatScreen(), name="chat")
        self.install_screen(WelcomeScreen(), name="welcome")
        
        # Push the Repository Selection screen first
        self.push_screen(RepoSelectScreen())

    def free_database_locks(self) -> None:
        """
        Crucial for Windows: Drops object references to force the underlying 
        C++ ChromaDB and SQLite drivers to release their file handle locks.
        """
        if self.retriever and hasattr(self.retriever, 'si'):
            try:
                self.retriever.si.close()
            except Exception:
                pass
        
        # Drop references
        self.retriever = None
        self.qa_pipeline = None
        self.review_pipeline = None
        self.docs_pipeline = None
        
        # Force garbage collection to clean up unreferenced file handles
        gc.collect()

    def action_clear_chat(self) -> None:
        """Bound to Ctrl+R."""
        try:
            chat_screen = self.query_one("ChatScreen")
            container = chat_screen.query_one("#chat-container")
            for child in container.children:
                if child.id != "chat-history":
                    child.remove()
            chat_screen.post_message(AgentMessage("Chat history cleared."))
        except Exception:
            pass


if __name__ == "__main__":
    app = CodeSentinelUI()
    app.run()