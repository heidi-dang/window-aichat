import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox, filedialog, simpledialog
import threading
import json
import os
import re
from pathlib import Path
import requests
import time
import random
import subprocess
import webbrowser
from datetime import datetime
from typing import Optional, Dict, List
import difflib
import queue
import logging
from cryptography.fernet import Fernet
import shutil
from window_aichat.core.ai_client import AIChatClient
from window_aichat.services.github import GitHubHandler
from window_aichat.utils.logging_config import setup_logging
from window_aichat.desktop.ui.settings_window import SettingsWindow
from window_aichat.desktop.ui.dev_tool_window import DevToolWindow
from window_aichat.desktop.ui.code_chat_window import CodeChatWindow
from window_aichat.desktop.ui.theme_manager import ThemeManager
from window_aichat.desktop.ui.ai_provider import ProviderFactory
from window_aichat.desktop.ui.markdown_renderer import MarkdownRenderer

# Setup logging at module level
setup_logging()
logger = logging.getLogger("main")


class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIChatDesktop - GitHub Aware Edition")
        self.root.geometry("1200x800")

        try:
            self.root.iconbitmap(default="icon.ico")
        except (tk.TclError, FileNotFoundError) as e:
            # Icon file missing or corrupted - not critical, continue without icon
            logger.debug(f"Could not load icon: {e}")

        self.config_dir = os.path.join(os.path.expanduser("~"), ".aichatdesktop")
        self.config_path = os.path.join(self.config_dir, "config.json")
        self.repo_cache_dir = os.path.join(self.config_dir, "repo_cache")

        # Initialize placeholders
        self.chat_client = None
        self.gh_handler = None
        self.message_queue = queue.Queue()
        self.status_update_id = None
        self.view_mode = "full"
        self.repo_context = ""

        # Setup UI immediately
        self.theme_manager = ThemeManager("Dark")
        self.setup_styles()
        self.apply_theme()
        self.setup_ui()
        self.create_menu()

        # Show loading message
        self.display_message("System", "Initializing AI Engine...")

        # Defer backend loading to allow UI to render first
        self.root.after(100, self.initialize_backend)

    def initialize_backend(self):
        """Load heavy modules in background"""
        try:
            logger.info("Initializing backend components...")
            os.makedirs(self.repo_cache_dir, exist_ok=True)

            try:
                self.chat_client = AIChatClient(self.config_path)
                logger.info("AIChatClient initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize AIChatClient: {e}", exc_info=True)
                self.display_message(
                    "System",
                    f"Error initializing AI client: {str(e)}\nPlease check your configuration in Settings.",
                )
                return

            token = self.chat_client.config.get("github_token", "")

            try:
                self.gh_handler = GitHubHandler(self.repo_cache_dir, token=token)
                logger.info("GitHubHandler initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize GitHubHandler: {e}", exc_info=True)
                self.display_message(
                    "System",
                    f"Warning: GitHub integration unavailable: {str(e)}\nYou can still use the chat features.",
                )
                self.gh_handler = None

            self.display_welcome()
            self.process_queue()
            self.update_status_indicators()
        except Exception as e:
            logger.critical(
                f"Critical error during backend initialization: {e}", exc_info=True
            )
            self.display_message(
                "System",
                f"Critical error during initialization: {str(e)}\nPlease restart the application.",
            )

    def create_menu(self):
        """Create application menu with developer tools"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Chat...", command=self.export_chat)
        file_menu.add_separator()
        file_menu.add_command(label="Clear Chat", command=self.clear_chat)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(
            label="Toggle Sidebar (Focus Mode)",
            command=self.toggle_view_mode,
            accelerator="F11",
        )
        view_menu.add_command(label="Change Theme", command=self.change_theme)

        # Developer Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Developer Tools", menu=tools_menu)

        tools_menu.add_command(label="Analyze Code...", command=self.tool_analyze_code)
        tools_menu.add_command(
            label="Generate Documentation...", command=self.tool_generate_docs
        )
        tools_menu.add_command(label="Debug Error...", command=self.tool_debug_error)
        tools_menu.add_command(
            label="Generate Unit Tests...", command=self.tool_generate_tests
        )
        tools_menu.add_separator()
        tools_menu.add_command(label="SQL Optimizer...", command=self.tool_optimize_sql)
        tools_menu.add_command(
            label="Design DB Schema...", command=self.tool_design_db_schema
        )
        tools_menu.add_command(label="Regex Builder...", command=self.tool_build_regex)
        tools_menu.add_separator()
        tools_menu.add_command(
            label="Generate API Endpoint...", command=self.tool_generate_api_endpoint
        )
        tools_menu.add_command(
            label="Security Check...", command=self.tool_check_security
        )
        tools_menu.add_command(
            label="Performance Analysis...", command=self.tool_analyze_performance
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label="Recommend Packages...", command=self.tool_recommend_packages
        )
        tools_menu.add_command(
            label="Explain Algorithm...", command=self.tool_explain_algorithm
        )
        tools_menu.add_command(
            label="Refactor Code...", command=self.tool_refactor_code
        )
        tools_menu.add_command(label="Git Helper...", command=self.tool_git_helper)
        tools_menu.add_command(
            label="Generate Config...", command=self.tool_generate_config
        )

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

        self.root.bind("<F11>", self.toggle_view_mode)

    def setup_styles(self):
        """Define Sendbird-inspired color palette and styles"""
        # Use theme manager for colors
        self.colors = self.theme_manager.colors

    def apply_theme(self):
        """Apply the current theme using ThemeManager."""
        self.colors = self.theme_manager.colors
        self.root.configure(bg=self.colors["bg"])
        style = ttk.Style()
        self.theme_manager.apply_ttk_styles(style)

    def open_dev_tool(
        self, title: str, input_label: str, action_callback, provider_type: str = "auto"
    ):
        """Generic function to open a developer tool window with pluggable AI provider."""
        # Create provider wrapper if chat_client is available
        if self.chat_client:
            provider = ProviderFactory.create_provider(provider_type, self.chat_client)
            if provider and provider.is_available():
                # Wrap the callback: action_callback generates the prompt, provider executes it
                def provider_wrapper(input_content: str) -> str:
                    prompt = action_callback(input_content)
                    return provider.generate_response(prompt)

                DevToolWindow(self.root, title, input_label, provider_wrapper)
            else:
                # Fallback to direct callback (uses Gemini directly)
                logger.warning(
                    f"Provider {provider_type} not available, using direct callback"
                )
                DevToolWindow(
                    self.root,
                    title,
                    input_label,
                    lambda content: (
                        self.chat_client.ask_gemini(action_callback(content))
                        if self.chat_client.gemini_available
                        else "No AI provider available"
                    ),
                )
        else:
            DevToolWindow(
                self.root,
                title,
                input_label,
                lambda content: "AI client not initialized. Please wait for initialization to complete.",
            )

    def tool_analyze_code(self):
        self.open_dev_tool("Analyze Code", "Code to Analyze", self.analyze_code)

    def tool_generate_docs(self):
        self.open_dev_tool(
            "Generate Documentation", "Code to Document", self.generate_documentation
        )

    def tool_debug_error(self):
        self.open_dev_tool(
            "Debug Error", "Paste Error Message and Code Context", self.debug_error
        )

    def tool_generate_tests(self):
        self.open_dev_tool(
            "Generate Unit Tests", "Code to Test", self.generate_unit_tests
        )

    def tool_optimize_sql(self):
        self.open_dev_tool("Optimize SQL", "SQL Query to Optimize", self.optimize_sql)

    def tool_design_db_schema(self):
        self.open_dev_tool(
            "Design DB Schema",
            "Requirements for DB Schema",
            self.design_database_schema,
        )

    def tool_build_regex(self):
        self.open_dev_tool(
            "Build Regex", "Description of what to match", self.build_regex
        )

    def tool_generate_api_endpoint(self):
        self.open_dev_tool(
            "Generate API Endpoint",
            "Description of the API endpoint",
            self.generate_api_endpoint,
        )

    def tool_check_security(self):
        self.open_dev_tool(
            "Check Security", "Code to check for vulnerabilities", self.check_security
        )

    def tool_analyze_performance(self):
        self.open_dev_tool(
            "Analyze Performance",
            "Code to analyze for performance",
            self.analyze_performance,
        )

    def tool_recommend_packages(self):
        self.open_dev_tool(
            "Recommend Packages",
            "Describe the task you need a package for",
            self.recommend_packages,
        )

    def tool_explain_algorithm(self):
        self.open_dev_tool(
            "Explain Algorithm",
            "Algorithm name or code to explain",
            self.explain_algorithm,
        )

    def tool_refactor_code(self):
        CodeChatWindow(self.root, self.chat_client)

    def tool_git_helper(self):
        self.open_dev_tool(
            "Git Helper", "Describe your Git problem or task", self.git_helper
        )

    def tool_generate_config(self):
        self.open_dev_tool(
            "Generate Config",
            "Describe the configuration you need (e.g., 'nginx for a react app')",
            self.generate_config,
        )

    def show_about(self):
        messagebox.showinfo(
            "About", "AI Chat Desktop\nVersion 2.0\nDeveloper Tools Edition"
        )

    def setup_ui(self):
        # Main container using PanedWindow for resizable sidebar
        self.main_split = tk.PanedWindow(
            self.root,
            orient=tk.HORIZONTAL,
            bg=self.colors["bg"],
            sashwidth=2,
            sashrelief=tk.FLAT,
        )
        self.main_split.pack(fill=tk.BOTH, expand=True)

        # --- Sidebar (Left) ---
        self.sidebar = tk.Frame(
            self.main_split, bg=self.colors["sidebar"], width=300, padx=15, pady=15
        )
        self.sidebar.pack_propagate(False)  # Enforce width
        self.main_split.add(self.sidebar)

        # App Header in Sidebar
        tk.Label(
            self.sidebar,
            text="AI Agent Workspace",
            font=("Segoe UI", 14, "bold"),
            bg=self.colors["sidebar"],
            fg="white",
        ).pack(anchor="w", pady=(0, 20))

        # Model Selection
        tk.Label(
            self.sidebar,
            text="AI MODEL",
            font=("Segoe UI", 8, "bold"),
            bg=self.colors["sidebar"],
            fg=self.colors["fg_dim"],
        ).pack(anchor="w", pady=(0, 5))
        self.model_var = tk.StringVar(value="both")
        model_combo = ttk.Combobox(
            self.sidebar,
            textvariable=self.model_var,
            values=["gemini", "deepseek", "both"],
            state="readonly",
            font=("Segoe UI", 9),
        )
        model_combo.pack(fill=tk.X, pady=(0, 20))

        # GitHub Context
        tk.Label(
            self.sidebar,
            text="GITHUB CONTEXT",
            font=("Segoe UI", 8, "bold"),
            bg=self.colors["sidebar"],
            fg=self.colors["fg_dim"],
        ).pack(anchor="w", pady=(0, 5))
        self.repo_entry = tk.Entry(
            self.sidebar,
            font=("Segoe UI", 9),
            bg=self.colors["input_bg"],
            fg="white",
            insertbackground="white",
            relief=tk.FLAT,
        )
        self.repo_entry.pack(fill=tk.X, pady=(0, 5), ipady=3)

        fetch_btn = ttk.Button(
            self.sidebar,
            text="Fetch Repository",
            command=self.fetch_repo_context,
            style="Secondary.TButton",
        )
        fetch_btn.pack(fill=tk.X, pady=(0, 20))

        # Status Section
        tk.Label(
            self.sidebar,
            text="SYSTEM STATUS",
            font=("Segoe UI", 8, "bold"),
            bg=self.colors["sidebar"],
            fg=self.colors["fg_dim"],
        ).pack(anchor="w", pady=(0, 5))

        status_frame = tk.Frame(self.sidebar, bg=self.colors["sidebar"])
        status_frame.pack(fill=tk.X, pady=(0, 20))

        self.gemini_status = tk.Label(
            status_frame,
            text="○ Gemini",
            fg="#e74c3c",
            bg=self.colors["sidebar"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        )
        self.gemini_status.pack(anchor="w", fill=tk.X)
        self.deepseek_status = tk.Label(
            status_frame,
            text="○ DeepSeek",
            fg="#e74c3c",
            bg=self.colors["sidebar"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        )
        self.deepseek_status.pack(anchor="w", fill=tk.X)

        # Bottom Sidebar Controls
        tk.Frame(self.sidebar, bg=self.colors["sidebar"]).pack(
            fill=tk.BOTH, expand=True
        )  # Spacer

        ttk.Button(
            self.sidebar,
            text="⚙ Settings",
            command=self.open_settings,
            style="Secondary.TButton",
        ).pack(fill=tk.X, pady=5)
        ttk.Button(
            self.sidebar,
            text="Code Chat",
            command=self.tool_refactor_code,
            style="TButton",
        ).pack(fill=tk.X, pady=5)
        ttk.Button(
            self.sidebar,
            text="Clear Chat",
            command=self.clear_chat,
            style="Secondary.TButton",
        ).pack(fill=tk.X, pady=5)
        ttk.Button(
            self.sidebar,
            text="Find in Chat",
            command=self.find_in_chat,
            style="Secondary.TButton",
        ).pack(fill=tk.X, pady=5)

        # --- Main Chat Area (Right) ---
        self.chat_area = tk.Frame(self.main_split, bg=self.colors["bg"])
        self.main_split.add(self.chat_area)

        # Chat Header
        header_frame = tk.Frame(
            self.chat_area, bg=self.colors["bg"], height=50, padx=20
        )
        header_frame.pack(fill=tk.X)
        tk.Label(
            header_frame,
            text="Chat Session",
            font=("Segoe UI", 12, "bold"),
            bg=self.colors["bg"],
            fg="white",
        ).pack(side=tk.LEFT, pady=15)

        # Chat History
        history_frame = tk.Frame(
            self.chat_area, bg=self.colors["chat_bg"], padx=20, pady=10
        )
        history_frame.pack(fill=tk.BOTH, expand=True)

        self.chat_display = tk.Text(
            history_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            bg=self.colors["chat_bg"],
            fg=self.colors["fg"],
            insertbackground="white",
            relief=tk.FLAT,
            state=tk.DISABLED,
            padx=10,
            pady=10,
            spacing1=5,
            spacing3=5,
        )
        scrollbar = ttk.Scrollbar(
            history_frame, orient="vertical", command=self.chat_display.yview
        )
        self.chat_display.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._configure_text_tags()

        # Initialize markdown renderer
        self.markdown_renderer = MarkdownRenderer(self.chat_display)

        # Input Area
        input_container = tk.Frame(
            self.chat_area, bg=self.colors["bg"], padx=20, pady=20
        )
        input_container.pack(fill=tk.X)

        input_wrapper = tk.Frame(
            input_container, bg=self.colors["input_bg"], padx=5, pady=5
        )
        input_wrapper.pack(fill=tk.X)

        self.input_text = tk.Text(
            input_wrapper,
            height=3,
            font=("Segoe UI", 10),
            bg=self.colors["input_bg"],
            fg="white",
            insertbackground="white",
            relief=tk.FLAT,
            wrap=tk.WORD,
        )
        self.input_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 10))
        self.input_text.bind("<Return>", self.on_ctrl_enter)
        self.input_text.bind("<Shift-Return>", lambda e: None)

        send_btn = ttk.Button(
            input_wrapper, text="Send", command=self.send_message, style="TButton"
        )
        send_btn.pack(side=tk.RIGHT)

    def toggle_view_mode(self, event=None):
        """Toggle between Full and Focus view modes"""
        if self.view_mode == "full":
            self.main_split.forget(self.sidebar)
            self.view_mode = "focus"
        else:
            self.main_split.add(self.sidebar, before=self.chat_area, width=300)
            self.sidebar.pack_propagate(False)
            self.view_mode = "full"

    def _configure_text_tags(self):
        # User Message Style (Right Aligned - Simulated)
        self.chat_display.tag_config(
            "user_bubble",
            background=self.colors["user_bubble"],
            foreground="white",
            lmargin1=100,
            lmargin2=100,
            rmargin=10,
            font=("Segoe UI", 10),
            spacing1=10,
            spacing3=10,
        )

        # AI Message Style (Left Aligned)
        self.chat_display.tag_config(
            "ai_bubble",
            background=self.colors["ai_bubble"],
            foreground=self.colors["fg"],
            lmargin1=10,
            lmargin2=10,
            rmargin=100,
            font=("Segoe UI", 10),
            spacing1=10,
            spacing3=10,
        )

        self.chat_display.tag_config(
            "system",
            foreground=self.colors["fg_dim"],
            justify="center",
            font=("Segoe UI", 9, "italic"),
            spacing1=5,
            spacing3=5,
        )

        self.chat_display.tag_config(
            "timestamp", foreground=self.colors["fg_dim"], font=("Segoe UI", 7)
        )
        self.chat_display.tag_config("right_align", justify="right")
        self.chat_display.tag_config("left_align", justify="left")

    def update_status_indicators(self):
        if self.gemini_status.winfo_exists() and self.chat_client:
            if self.chat_client.gemini_available:
                latency_text = ""
                if self.chat_client.gemini_latency is not None:
                    latency_text = f" ({self.chat_client.gemini_latency:.1f}s)"
                error_text = ""
                if self.chat_client.gemini_error:
                    error_text = f" - {self.chat_client.gemini_error[:30]}"
                self.gemini_status.config(
                    fg="#2ecc71", text=f"● Gemini{latency_text}{error_text}"
                )
            else:
                error_text = ""
                if self.chat_client.gemini_error:
                    error_text = f" - {self.chat_client.gemini_error[:30]}"
                self.gemini_status.config(fg="#e74c3c", text=f"○ Gemini{error_text}")

        if self.deepseek_status.winfo_exists() and self.chat_client:
            if self.chat_client.deepseek_available:
                latency_text = ""
                if self.chat_client.deepseek_latency is not None:
                    latency_text = f" ({self.chat_client.deepseek_latency:.1f}s)"
                error_text = ""
                if self.chat_client.deepseek_error:
                    error_text = f" - {self.chat_client.deepseek_error[:30]}"
                self.deepseek_status.config(
                    fg="#2ecc71", text=f"● DeepSeek{latency_text}{error_text}"
                )
            else:
                error_text = ""
                if self.chat_client.deepseek_error:
                    error_text = f" - {self.chat_client.deepseek_error[:30]}"
                self.deepseek_status.config(
                    fg="#e74c3c", text=f"○ DeepSeek{error_text}"
                )

        self.status_update_id = self.root.after(10000, self.update_status_indicators)

    def fetch_repo_context(self):
        repo_url = self.repo_entry.get().strip()
        if not repo_url:
            messagebox.showwarning(
                "Input Error", "Please enter a GitHub repository URL"
            )
            return

        self.display_message(
            "system", f"Fetching repository context from {repo_url}..."
        )
        threading.Thread(
            target=self._fetch_repo_thread, args=(repo_url,), daemon=True
        ).start()

    def _fetch_repo_thread(self, repo_url: str):
        try:
            if not self.gh_handler:
                self.message_queue.put(("error", "GitHub handler not initialized"))
                return

            if not self.gh_handler.token_valid and self.gh_handler.token:
                self.message_queue.put(
                    (
                        "error",
                        f"GitHub token is invalid: {self.gh_handler.token_error}\n"
                        "Please update your token in Settings.",
                    )
                )
                return

            context = self.gh_handler.fetch_repo_context(repo_url)
            self.message_queue.put(("repo_context", context))
        except requests.exceptions.HTTPError as e:
            error_msg = str(e)
            if "401" in error_msg or "Token" in error_msg:
                error_msg += "\nPlease update your GitHub token in Settings."
            self.message_queue.put(("error", f"Failed to fetch repo: {error_msg}"))
        except Exception as e:
            logger.error(f"Error fetching repository: {e}", exc_info=True)
            self.message_queue.put(("error", f"Failed to fetch repo: {str(e)}"))

    def process_queue(self):
        try:
            while True:
                msg_type, content = self.message_queue.get_nowait()
                if msg_type == "repo_context":
                    self.repo_context = content
                    self.display_message(
                        "system",
                        f"Repository context loaded. Summary:\n{content[:200]}...",
                    )
                elif msg_type == "error":
                    self.display_message("system", f"Error: {content}")
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def display_message(self, sender: str, message: str):
        self.chat_display.config(state=tk.NORMAL)

        self.chat_display.insert(tk.END, "\n")
        timestamp = datetime.now().strftime("%H:%M")

        if sender.lower() == "you":
            header = f"You  {timestamp}\n"
            self.chat_display.insert(tk.END, header, ("timestamp", "right_align"))
            # User messages: simple text (no markdown for user input)
            self.chat_display.insert(tk.END, f" {message} \n", "user_bubble")
        elif sender.lower() == "system":
            self.chat_display.insert(tk.END, f"--- {message} ---\n", "system")
        else:
            # AI messages: try to render markdown
            header = f"{sender}  {timestamp}\n"
            self.chat_display.insert(tk.END, header, ("timestamp", "left_align"))

            # Check if message contains markdown patterns
            has_markdown = any(
                pattern in message for pattern in ["**", "*", "`", "#", "["]
            )

            if has_markdown:
                try:
                    # Use markdown renderer for AI responses (with ai_bubble base tag)
                    start_pos = self.chat_display.index(tk.END)
                    self.chat_display.insert(tk.END, " ", "ai_bubble")
                    self.markdown_renderer.render(
                        message, start_pos, base_tag="ai_bubble"
                    )
                    self.chat_display.insert(tk.END, "\n")
                except Exception as e:
                    # Fallback to plain text if markdown rendering fails
                    logger.warning(f"Markdown rendering failed: {e}", exc_info=True)
                    self.chat_display.insert(tk.END, f" {message} \n", "ai_bubble")
            else:
                # Plain text
                self.chat_display.insert(tk.END, f" {message} \n", "ai_bubble")

        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def on_ctrl_enter(self, event):
        self.send_message()
        return "break"

    def send_message(self):
        user_input = self.input_text.get("1.0", tk.END).strip()

        if not self.chat_client:
            messagebox.showwarning(
                "Loading", "AI Engine is still initializing. Please wait a moment."
            )
            return

        if not user_input:
            return

        self.display_message("You", user_input)
        self.clear_input()
        selected_model = self.model_var.get()
        self.input_text.config(state=tk.DISABLED)

        thread = threading.Thread(
            target=self.get_ai_response, args=(user_input, selected_model), daemon=True
        )
        thread.start()

    def get_ai_response(self, prompt: str, model: str):
        # Sanitize user input to prevent prompt injection
        sanitized_prompt = self._sanitize_input(prompt)

        full_prompt = sanitized_prompt
        if self.repo_context:
            full_prompt = f"Context from GitHub Repository:\n{self.repo_context}\n\nUser Query:\n{sanitized_prompt}"

        logger.info(f"Processing AI request with model: {model}")
        start_time = time.time()

        try:
            if model == "gemini":
                response = self.chat_client.ask_gemini(full_prompt)
                elapsed = time.time() - start_time
                logger.info(f"Gemini response received in {elapsed:.2f}s")
                self.display_message("Gemini", response)
            elif model == "deepseek":
                response = self.chat_client.ask_deepseek(full_prompt)
                elapsed = time.time() - start_time
                logger.info(f"DeepSeek response received in {elapsed:.2f}s")
                self.display_message("DeepSeek", response)
            else:
                responses = self.chat_client.ask_both(full_prompt)
                elapsed = time.time() - start_time
                logger.info(f"Both models responded in {elapsed:.2f}s")
                self.display_message("Gemini", responses["gemini"])
                self.display_message("DeepSeek", responses["deepseek"])
        except Exception as e:
            logger.error(f"Error getting AI response: {e}", exc_info=True)
            self.display_message("System", f"Error: {str(e)}")
        finally:
            self.root.after(0, lambda: self.input_text.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.input_text.focus())

    def _sanitize_input(self, user_input: str) -> str:
        """Sanitize user input to prevent prompt injection attacks"""
        # Remove or escape potentially dangerous patterns
        # This is a basic implementation - can be enhanced further

        # Remove common injection patterns
        dangerous_patterns = [
            r"ignore\s+previous\s+instructions",
            r"forget\s+all\s+previous",
            r"you\s+are\s+now",
            r"act\s+as\s+if",
            r"pretend\s+to\s+be",
        ]

        sanitized = user_input
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)

        # Limit length to prevent extremely long prompts
        max_length = 10000
        if len(sanitized) > max_length:
            logger.warning(
                f"Input truncated from {len(sanitized)} to {max_length} characters"
            )
            sanitized = sanitized[:max_length]

        return sanitized.strip()

    def clear_input(self):
        self.input_text.delete("1.0", tk.END)

    def clear_chat(self):
        if messagebox.askyesno(
            "Clear Chat", "Are you sure you want to clear the chat history?"
        ):
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.config(state=tk.DISABLED)
            self.display_welcome()

    def find_in_chat(self):
        """Search text in chat history"""
        search_str = simpledialog.askstring(
            "Find in Chat", "Enter text to search:", parent=self.root
        )
        if not search_str:
            return

        self.chat_display.tag_remove("search_match", "1.0", tk.END)

        start = "1.0"
        count = 0
        while True:
            pos = self.chat_display.search(
                search_str, start, stopindex=tk.END, nocase=True
            )
            if not pos:
                break

            end = f"{pos}+{len(search_str)}c"
            self.chat_display.tag_add("search_match", pos, end)
            if count == 0:
                self.chat_display.see(pos)
            start = end
            count += 1

        self.chat_display.tag_config(
            "search_match", background="yellow", foreground="black"
        )
        if count == 0:
            messagebox.showinfo("Find", "No matches found.")

    def export_chat(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if filename:
            try:
                content = self.chat_display.get("1.0", tk.END)
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo(
                    "Export Successful", f"Chat exported to:\n{filename}"
                )
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {str(e)}")

    def open_settings(self):
        SettingsWindow(self.root, self.config_path)
        self.root.after(100, self.update_chat_client)

    def update_chat_client(self):
        self.chat_client = AIChatClient(self.config_path)
        self.update_status_indicators()

    def update_github_handler(self, token: str):
        """Update GitHub handler with new token."""
        try:
            from github_handler import GitHubHandler

            if self.gh_handler:
                self.gh_handler.update_token(token)
            else:
                self.gh_handler = GitHubHandler(self.repo_cache_dir, token=token)

            if self.gh_handler.token_valid:
                logger.info("GitHub handler updated successfully")
            else:
                logger.warning(
                    f"GitHub handler updated but token is invalid: {self.gh_handler.token_error}"
                )
        except Exception as e:
            logger.error(f"Failed to update GitHub handler: {e}", exc_info=True)
            self.display_message(
                "System", f"Warning: Could not update GitHub handler: {str(e)}"
            )

    def change_theme(self):
        """Change the application theme using ThemeManager."""
        available_themes = ", ".join(self.theme_manager.list_themes())
        choice = simpledialog.askstring(
            "Change Theme",
            f"Enter theme name ({available_themes}):",
            initialvalue=self.theme_manager.current_theme,
        )
        if choice and self.theme_manager.set_theme(choice):
            self.colors = self.theme_manager.colors
            self.apply_theme()  # Re-apply styles

            # Update specific widgets that don't auto-update with style changes
            self.root.configure(bg=self.colors["bg"])
            self.sidebar.configure(bg=self.colors["sidebar"])
            self.chat_area.configure(bg=self.colors["bg"])

            # Update text widgets
            self.chat_display.configure(bg=self.colors["chat_bg"], fg=self.colors["fg"])
            self.input_text.configure(
                bg=self.colors["input_bg"],
                fg=(
                    self.colors["fg"]
                    if self.theme_manager.current_theme != "Dark"
                    else "#ffffff"
                ),
            )

            # Update tags
            self._configure_text_tags()

            messagebox.showinfo(
                "Theme Changed", f"Theme changed to {self.theme_manager.current_theme}."
            )
        elif choice:
            messagebox.showwarning(
                "Invalid Theme",
                f"Theme '{choice}' not found. Available themes: {available_themes}",
            )

    def show_about(self):
        about_text = """AI Chat Desktop v2.0

A desktop application for chatting with multiple AI models with GitHub integration.

Features:
• Gemini AI integration
• DeepSeek AI integration
• Dual-model comparison
• GitHub repository context fetching
• API key management
• Chat history export

Created with Python and Tkinter

© 2024 AI Chat Desktop
"""
        messagebox.showinfo("About AI Chat Desktop", about_text)

    def display_welcome(self):
        welcome_msg = """Welcome to AI Chat Desktop!

📌 Getting Started:
1. Click 'Settings' and configure your API keys
2. Test connections to verify setup
3. Enter a GitHub repo URL to fetch context (optional)
4. Select your AI model and start chatting
5. Use Ctrl+Enter to send messages

💡 Features:
• Dual AI model support (Gemini & DeepSeek)
• Repository context awareness
• Chat history export
• Real-time API status

Use the menu bar for additional options.
"""
        self.display_message("system", welcome_msg)

    def on_closing(self):
        if self.status_update_id:
            self.root.after_cancel(self.status_update_id)
        self.root.quit()

    # ========== DEVELOPER TOOLS ==========

    def analyze_code(self, code_snippet: str) -> str:
        """Analyze code for bugs, performance, and security issues"""
        prompt = f"""As an expert software engineer, analyze the following code snippet.
Provide a report covering:
1. Potential bugs
2. Performance issues
3. Security concerns
4. Improvement suggestions
5. Best practices violations

Code:
```
{code_snippet}
```

Format as clear bullet points."""
        return self.chat_client.ask_gemini(prompt)

    def generate_documentation(self, code: str) -> str:
        """Generate comprehensive documentation and docstrings"""
        prompt = f"""Generate comprehensive documentation for the following code.
Assume the language from the snippet, but default to Python if ambiguous.
Include:
1. Function/class docstrings (with type hints)
2. Inline comments for complex logic
3. A brief usage example
4. Descriptions for parameters and return values

Code:
```
{code}
```"""
        return self.chat_client.ask_gemini(prompt)

    def optimize_sql(self, query: str) -> str:
        """Build and optimize SQL queries"""
        prompt = f"""Optimize the following SQL query. Assume PostgreSQL unless specified otherwise in the query.

Query:
```sql
{query}
```

Provide:
1. Optimized query
2. Explanation of changes
3. Indexing suggestions relevant to the query"""
        return self.chat_client.ask_gemini(prompt)

    def build_regex(self, description: str) -> str:
        """Generate and explain regex patterns"""
        prompt = f"""Create a regex pattern based on the following description.
Include test strings if they are provided in the description.

Description:
{description}

Provide:
1. The regex pattern, compatible with Python's `re` module.
2. A clear explanation of each part of the pattern.
3. Example usage in Python."""
        return self.chat_client.ask_gemini(prompt)

    def generate_api_endpoint(self, description: str) -> str:
        """Generate REST API endpoints with examples"""
        prompt = f"""Generate a REST API endpoint. Assume Flask or FastAPI unless another framework is specified in the description.

Description:
{description}

Include:
1. Complete endpoint code
2. Request/response examples
3. Error handling
4. Input validation"""
        return self.chat_client.ask_gemini(prompt)

    def design_database_schema(self, requirements: str) -> str:
        """Design database schemas with relationships"""
        prompt = f"""Design a database schema based on the following requirements. Assume PostgreSQL unless specified otherwise.

Requirements:
{requirements}

Provide:
1. Table structures with columns and types
2. Primary/Foreign keys and relationships
3. Indexes recommendations
4. Sample `CREATE TABLE` statements"""
        return self.chat_client.ask_gemini(prompt)

    def debug_error(self, full_input: str) -> str:
        """Debug errors and get solutions"""
        prompt = f"""Help me debug the following error. The input may contain a traceback, error message, and relevant code.

Input:
```
{full_input}
```

Provide:
1. Root cause analysis
2. Step-by-step fix
3. Code with the fix applied
4. Prevention tips"""
        return self.chat_client.ask_gemini(prompt)

    def generate_unit_tests(self, code: str) -> str:
        """Generate unit tests with edge cases"""
        prompt = f"""Generate unit tests for the following code. Assume pytest for Python, Jest for JS, etc., unless specified.

Code:
```
{code}
```

Include:
1. Test cases for normal scenarios
2. Edge cases and boundary conditions
3. Error/exception handling tests
4. Mocks or stubs where appropriate"""
        return self.chat_client.ask_gemini(prompt)

    def analyze_performance(self, code: str) -> str:
        """Analyze performance bottlenecks"""
        prompt = f"""Analyze the performance of the following code:

Code:
```
{code}
```

Provide:
1. Time complexity analysis (Big O)
2. Space complexity analysis (Big O)
3. Identification of bottlenecks
4. Concrete optimization strategies with refactored code examples"""
        return self.chat_client.ask_gemini(prompt)

    def check_security(self, code: str) -> str:
        """Scan code for security vulnerabilities"""
        prompt = f"""Check the following code for security vulnerabilities.

Code:
```
{code}
```

Identify:
1. A list of potential vulnerabilities (e.g., SQL Injection, XSS, etc.).
2. For each vulnerability, explain the risk.
3. Provide a corrected or more secure version of the code.
4. Mention relevant OWASP Top 10 categories."""
        return self.chat_client.ask_gemini(prompt)

    def recommend_packages(self, requirement: str) -> str:
        """Get package and dependency recommendations"""
        prompt = f"""Recommend packages/libraries for the following requirement. Assume Python unless another language is specified.

Requirement: {requirement}

Provide:
1. Top 3 package recommendations
2. Pros/cons of each
3. Installation commands
4. A simple usage example for the top recommendation"""
        return self.chat_client.ask_gemini(prompt)

    def explain_algorithm(self, algorithm_input: str) -> str:
        """Explain algorithms with complexity analysis"""
        prompt = f"""Explain the algorithm provided either by name or as a code snippet.

Algorithm/Code:
{algorithm_input}

Provide:
1. Step-by-step explanation
2. Time and Space complexity (Big O notation)
3. Common use cases
4. If code is provided, offer a Python implementation if it's not already."""
        return self.chat_client.ask_gemini(prompt)

    def refactor_code(self, code: str) -> str:
        """Refactor code with design patterns"""
        prompt = f"""Refactor the following code to improve its quality.

Code:
```
{code}
```

Apply:
1. Clean code practices (e.g., SOLID, DRY).
2. Improve readability and maintainability.
3. Apply relevant design patterns if applicable.

Provide:
- Refactored code
- A brief explanation of the key changes and their benefits."""
        return self.chat_client.ask_gemini(prompt)

    def git_helper(self, task: str) -> str:
        """Generate git commands and explain workflows"""
        prompt = f"""I need help with Git. My task or problem is:
{task}

Provide:
1. The necessary Git commands in sequence.
2. A step-by-step explanation of what each command does.
3. Any common pitfalls or things to watch out for."""
        return self.chat_client.ask_gemini(prompt)

    def generate_config(self, requirements: str) -> str:
        """Generate configuration files"""
        prompt = f"""Generate a configuration file based on these requirements:
{requirements}

Include:
1. The complete configuration file content.
2. Comments explaining important settings.
3. Security best practices if applicable."""
        return self.chat_client.ask_gemini(prompt)


def main():
    root = tk.Tk()
    app = ChatApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    root.mainloop()


if __name__ == "__main__":
    main()
