import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox, filedialog, simpledialog
import threading
import json
import os
import re
import sys
import subprocess
from pathlib import Path
import google.generativeai as genai
import requests
import webbrowser
from datetime import datetime
from typing import Optional, Dict, List
import difflib
import queue
from github_handler import GitHubHandler
from cryptography.fernet import Fernet

class SecureConfig:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.key_file = config_path.replace('.json', '.key')
        self.cipher = self._get_cipher()

    def _get_cipher(self):
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
            with open(self.key_file, 'wb') as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)
        return Fernet(key)

    def save_config(self, config: dict):
        encrypted = self.cipher.encrypt(json.dumps(config).encode())
        with open(self.config_path, 'wb') as f:
            f.write(encrypted)
        os.chmod(self.config_path, 0o600)

    def load_config(self) -> Dict[str, str]:
        default_config = {
            "gemini_api_key": os.getenv('GEMINI_API_KEY', ''),
            "deepseek_api_key": os.getenv('DEEPSEEK_API_KEY', ''),
            "github_token": os.getenv('GITHUB_TOKEN', ''),
            "gemini_model": os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
        }
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'rb') as f:
                    encrypted = f.read()
                decrypted = self.cipher.decrypt(encrypted).decode()
                file_config = json.loads(decrypted)
                default_config.update(file_config)
        except Exception as e:
            print(f"Could not load or decrypt config file: {e}. Using defaults.")
        return default_config


class SettingsWindow:
    def __init__(self, parent, config_path):
        self.parent = parent
        self.config_path = config_path
        self.secure_config = SecureConfig(config_path)
        self.config = self.secure_config.load_config()

        self.window = tk.Toplevel(parent)
        self.window.title("API Settings - AI Chat Desktop")
        self.window.geometry("550x650")
        self.window.resizable(False, False)
        self.window.configure(bg="#f0f0f0")
        self.window.transient(parent)
        self.window.grab_set()

        try:
            self.window.iconbitmap(default='icon.ico')
        except Exception:
            pass

        self.center_window()
        self.create_widgets()
        self.load_current_settings()

    def center_window(self):
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        main_frame = tk.Frame(self.window, bg="#f0f0f0", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = tk.Label(
            main_frame,
            text="API Configuration",
            font=("Segoe UI", 16, "bold"),
            bg="#f0f0f0",
            fg="#2c3e50"
        )
        title_label.pack(pady=(0, 20))

        self._create_gemini_frame(main_frame)
        self._create_deepseek_frame(main_frame)
        self._create_github_frame(main_frame)
        self._create_button_frame(main_frame)

        self.status_label = tk.Label(
            main_frame,
            text="",
            bg="#f0f0f0",
            font=("Segoe UI", 9),
            fg="#e74c3c"
        )
        self.status_label.pack(pady=(15, 0))

    def _create_gemini_frame(self, parent):
        gemini_frame = tk.LabelFrame(
            parent,
            text=" Gemini API ",
            font=("Segoe UI", 10, "bold"),
            bg="#f0f0f0",
            fg="#2c3e50",
            padx=10,
            pady=10
        )
        gemini_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(gemini_frame, text="API Key:", bg="#f0f0f0", font=("Segoe UI", 9)).pack(anchor=tk.W)
        self.gemini_key = tk.Entry(gemini_frame, width=50, show="•", font=("Segoe UI", 9))
        self.gemini_key.pack(fill=tk.X, pady=(2, 5))

        tk.Label(gemini_frame, text="Model:", bg="#f0f0f0", font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(5, 0))
        self.gemini_model = ttk.Combobox(
            gemini_frame,
            values=["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
            state="readonly",
            font=("Segoe UI", 9)
        )
        self.gemini_model.pack(fill=tk.X, pady=(2, 0))
        self.gemini_model.set("gemini-1.5-flash")

        gemini_btn = tk.Button(
            gemini_frame,
            text="Get Gemini API Key",
            command=lambda: webbrowser.open("https://makersuite.google.com/app/apikey"),
            bg="#4285f4",
            fg="white",
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        gemini_btn.pack(pady=(10, 0))

    def _create_deepseek_frame(self, parent):
        deepseek_frame = tk.LabelFrame(
            parent,
            text=" DeepSeek API ",
            font=("Segoe UI", 10, "bold"),
            bg="#f0f0f0",
            fg="#2c3e50",
            padx=10,
            pady=10
        )
        deepseek_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(deepseek_frame, text="API Key:", bg="#f0f0f0", font=("Segoe UI", 9)).pack(anchor=tk.W)
        self.deepseek_key = tk.Entry(deepseek_frame, width=50, show="•", font=("Segoe UI", 9))
        self.deepseek_key.pack(fill=tk.X, pady=(2, 5))

        deepseek_btn = tk.Button(
            deepseek_frame,
            text="Get DeepSeek API Key",
            command=lambda: webbrowser.open("https://platform.deepseek.com/api-docs"),
            bg="#00a67e",
            fg="white",
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        deepseek_btn.pack(pady=(10, 0))

    def _create_github_frame(self, parent):
        gh_frame = tk.LabelFrame(
            parent,
            text=" GitHub Configuration ",
            font=("Segoe UI", 10, "bold"),
            bg="#f0f0f0",
            fg="#2c3e50",
            padx=10,
            pady=10
        )
        gh_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(gh_frame, text="Personal Access Token:", bg="#f0f0f0", font=("Segoe UI", 9)).pack(anchor=tk.W)
        self.github_token = tk.Entry(gh_frame, width=50, show="•", font=("Segoe UI", 9))
        self.github_token.pack(fill=tk.X, pady=(2, 5))
        
        tk.Label(gh_frame, text="(Required for private repos and higher rate limits)", 
                 bg="#f0f0f0", fg="#7f8c8d", font=("Segoe UI", 8)).pack(anchor=tk.W)

    def _create_button_frame(self, parent):
        button_frame = tk.Frame(parent, bg="#f0f0f0")
        button_frame.pack(pady=(20, 0))

        save_btn = tk.Button(
            button_frame,
            text="Save Settings",
            command=self.save_settings,
            bg="#2ecc71",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=12,
            cursor="hand2"
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 10))

        test_btn = tk.Button(
            button_frame,
            text="Test Connection",
            command=self.test_connection,
            bg="#3498db",
            fg="white",
            font=("Segoe UI", 10),
            width=12,
            cursor="hand2"
        )
        test_btn.pack(side=tk.LEFT, padx=10)

        cancel_btn = tk.Button(
            button_frame,
            text="Cancel",
            command=self.window.destroy,
            bg="#95a5a6",
            fg="white",
            font=("Segoe UI", 10),
            width=12,
            cursor="hand2"
        )
        cancel_btn.pack(side=tk.LEFT, padx=(10, 0))

    def load_current_settings(self):
        self.gemini_key.delete(0, tk.END)
        self.gemini_key.insert(0, self.config.get("gemini_api_key", ""))
        self.deepseek_key.delete(0, tk.END)
        self.deepseek_key.insert(0, self.config.get("deepseek_api_key", ""))
        self.github_token.delete(0, tk.END)
        self.github_token.insert(0, self.config.get("github_token", ""))
        self.gemini_model.set(self.config.get("gemini_model", "gemini-1.5-flash"))

    def save_settings(self):
        config = {
            "gemini_api_key": self.gemini_key.get().strip(),
            "deepseek_api_key": self.deepseek_key.get().strip(),
            "github_token": self.github_token.get().strip(),
            "gemini_model": self.gemini_model.get()
        }
        try:
            config_dir = os.path.dirname(self.config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)
            self.secure_config.save_config(config)
            self.status_label.config(text="Settings saved successfully!", fg="#2ecc71")
            if hasattr(self.parent, 'chat_client'):
                self.parent.chat_client.config = config
                self.parent.chat_client.configure_apis()
            if hasattr(self.parent, 'update_github_handler'):
                self.parent.update_github_handler(config.get("github_token", ""))
        except Exception as e:
            self.status_label.config(text=f"Error saving settings: {str(e)}", fg="#e74c3c")

    def test_connection(self):
        gemini_key = self.gemini_key.get().strip()
        deepseek_key = self.deepseek_key.get().strip()
        self.status_label.config(text="Testing connections...", fg="#f39c12")
        self.window.update()
        results = []

        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content("Say 'TEST OK' only", generation_config={"max_output_tokens": 5})
                results.append("✓ Gemini: Connected")
            except Exception as e:
                results.append(f"✗ Gemini: {str(e)[:50]}")
        else:
            results.append("○ Gemini: No key provided")

        if deepseek_key:
            try:
                headers = {
                    'Authorization': f'Bearer {deepseek_key}',
                    'Content-Type': 'application/json'
                }
                data = {
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": "Say 'TEST OK'"}],
                    "max_tokens": 5
                }
                response = requests.post(
                    "https://api.deepseek.com/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=10
                )
                if response.status_code == 200:
                    results.append("✓ DeepSeek: Connected")
                else:
                    results.append(f"✗ DeepSeek: HTTP {response.status_code}")
            except Exception as e:
                results.append(f"✗ DeepSeek: {str(e)[:50]}")
        else:
            results.append("○ DeepSeek: No key provided")

        self.status_label.config(text=" | ".join(results), fg="#2ecc71")


class DevToolWindow(tk.Toplevel):
    def __init__(self, parent, title: str, input_label_text: str, action_callback):
        super().__init__(parent)
        self.title(title)
        self.geometry("900x700")
        self.transient(parent)
        self.grab_set()

        try:
            self.iconbitmap(default='icon.ico')
        except Exception:
            pass

        self.action_callback = action_callback

        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        paned_window = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # Input frame
        input_container = tk.Frame(paned_window, padx=5, pady=5)
        input_frame = tk.LabelFrame(input_container, text=input_label_text, padx=5, pady=5)
        input_frame.pack(fill=tk.BOTH, expand=True)
        self.input_text = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, height=10, font=("Segoe UI", 10))
        self.input_text.pack(fill=tk.BOTH, expand=True)
        paned_window.add(input_container)

        # Output frame
        output_container = tk.Frame(paned_window, padx=5, pady=5)
        output_frame = tk.LabelFrame(output_container, text="Result", padx=5, pady=5)
        output_frame.pack(fill=tk.BOTH, expand=True)
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Segoe UI", 10))
        self.output_text.pack(fill=tk.BOTH, expand=True)
        paned_window.add(output_container)

        # Button frame
        button_frame = tk.Frame(main_frame, pady=5)
        button_frame.pack(fill=tk.X)

        self.run_btn = tk.Button(button_frame, text="Run", command=self.run_action, bg="#2ecc71", fg="white", font=("Segoe UI", 10, "bold"))
        self.run_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.copy_btn = tk.Button(button_frame, text="Copy Result", command=self.copy_result, bg="#3498db", fg="white", font=("Segoe UI", 10))
        self.copy_btn.pack(side=tk.LEFT)

        self.status_label = tk.Label(main_frame, text="Ready. Paste your content and click 'Run'.", anchor='w')
        self.status_label.pack(fill=tk.X, pady=(5,0))

    def run_action(self):
        input_content = self.input_text.get("1.0", tk.END).strip()
        if not input_content:
            messagebox.showwarning("Input Missing", "Please provide input code/text.", parent=self)
            return

        self.status_label.config(text="Processing request with Gemini...")
        self.run_btn.config(state=tk.DISABLED)
        self.update()
        
        threading.Thread(target=self._execute_callback, args=(input_content,), daemon=True).start()

    def _execute_callback(self, content):
        try:
            result = self.action_callback(content)
            self.after(0, self.display_result, result)
        except Exception as e:
            self.after(0, self.display_result, f"An error occurred: {e}")

    def display_result(self, result):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, result)
        self.output_text.config(state=tk.DISABLED)
        self.status_label.config(text="Done.")
        self.run_btn.config(state=tk.NORMAL)

    def copy_result(self):
        result = self.output_text.get("1.0", tk.END).strip()
        if result:
            self.clipboard_clear()
            self.clipboard_append(result)
            self.status_label.config(text="Result copied to clipboard.")
        else:
            self.status_label.config(text="Nothing to copy.")


class CodeChatWindow(tk.Toplevel):
    def __init__(self, parent, chat_client):
        super().__init__(parent)
        self.title("Code Chat Workspace")
        self.geometry("1400x900")
        self.transient(parent)
        
        self.chat_client = chat_client
        self.current_folder = ""
        self.file_changes = {}  # {filepath: new_content}
        self.selected_file = None

        try:
            self.iconbitmap(default='icon.ico')
        except Exception:
            pass

        self.setup_ui()

    def setup_ui(self):
        # Toolbar
        toolbar = tk.Frame(self, padx=5, pady=5, bg="#f0f0f0")
        toolbar.pack(fill=tk.X)
        
        tk.Button(toolbar, text="📂 Open Folder", command=self.open_folder, bg="#ecf0f1").pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="📄 Open File", command=self.open_file, bg="#ecf0f1").pack(side=tk.LEFT, padx=5)
        self.status_label = tk.Label(toolbar, text="Ready", bg="#f0f0f0", fg="#7f8c8d")
        self.status_label.pack(side=tk.LEFT, padx=15)

        # Main Splitter
        self.main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=4, bg="#bdc3c7")
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left Pane: File List
        left_frame = tk.Frame(self.main_paned)
        self.main_paned.add(left_frame, width=250)
        
        tk.Label(left_frame, text="Explorer / Changes", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=2)
        self.file_tree = ttk.Treeview(left_frame, selectmode="browse")
        self.file_tree.pack(fill=tk.BOTH, expand=True)
        self.file_tree.heading("#0", text="Files", anchor="w")
        self.file_tree.bind("<<TreeviewSelect>>", self.on_file_select)

        # Right Pane: Work Area
        right_frame = tk.Frame(self.main_paned)
        self.main_paned.add(right_frame)

        # Code Splitter (Original vs AI)
        self.code_paned = tk.PanedWindow(right_frame, orient=tk.HORIZONTAL, sashwidth=4, bg="#bdc3c7")
        self.code_paned.pack(fill=tk.BOTH, expand=True)

        # Original Code View
        orig_frame = tk.LabelFrame(self.code_paned, text="Original Code")
        self.code_paned.add(orig_frame, width=500)
        self.orig_text = scrolledtext.ScrolledText(orig_frame, wrap=tk.NONE, font=("Consolas", 10))
        self.orig_text.pack(fill=tk.BOTH, expand=True)

        # AI Suggestion View
        ai_frame = tk.LabelFrame(self.code_paned, text="AI Suggestion / Chat Response")
        self.code_paned.add(ai_frame, width=500)
        self.ai_text = scrolledtext.ScrolledText(ai_frame, wrap=tk.NONE, font=("Consolas", 10), bg="#f4f6f7")
        self.ai_text.pack(fill=tk.BOTH, expand=True)

        # Chat Input Area
        input_frame = tk.Frame(right_frame, pady=5)
        input_frame.pack(fill=tk.X)
        
        self.chat_input = tk.Text(input_frame, height=4, font=("Segoe UI", 10))
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.chat_input.bind("<Control-Return>", lambda e: self.send_message())

        btn_frame = tk.Frame(input_frame)
        btn_frame.pack(side=tk.RIGHT, padx=5)
        
        tk.Button(btn_frame, text="Send (Ctrl+Enter)", command=self.send_message, bg="#2ecc71", fg="white", font=("Segoe UI", 9, "bold")).pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="Apply Changes", command=self.apply_current_change, bg="#3498db", fg="white", font=("Segoe UI", 9)).pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="Format Code", command=self.format_code, bg="#9b59b6", fg="white", font=("Segoe UI", 9)).pack(fill=tk.X, pady=2)

    def open_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.current_folder = folder
            self.refresh_file_tree()
            self.status_label.config(text=f"Folder loaded: {folder}")

    def open_file(self):
        filepath = filedialog.askopenfilename()
        if filepath:
            self.current_folder = os.path.dirname(filepath)
            self.refresh_file_tree(single_file=filepath)

    def refresh_file_tree(self, single_file=None):
        self.file_tree.delete(*self.file_tree.get_children())
        if single_file:
            self.file_tree.insert("", "end", single_file, text=os.path.basename(single_file), open=True)
            return
        
        for root, dirs, files in os.walk(self.current_folder):
            # Skip .git and other hidden folders
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            rel_path = os.path.relpath(root, self.current_folder)
            parent_node = "" if rel_path == "." else rel_path
            
            if parent_node and not self.file_tree.exists(parent_node):
                # This simplifies tree building; for deep trees, proper parent lookup is needed
                # For now, we just list files flat or simple hierarchy
                pass 

            for f in files:
                full_path = os.path.join(root, f)
                # Use full path as ID
                self.file_tree.insert("", "end", full_path, text=f"{f} ({os.path.relpath(full_path, self.current_folder)})")

    def on_file_select(self, event):
        selected = self.file_tree.selection()
        if not selected: return
        filepath = selected[0]
        self.selected_file = filepath
        
        if os.path.isfile(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.orig_text.delete("1.0", tk.END)
                self.orig_text.insert(tk.END, content)
                
                # Check if we have pending changes for this file
                if filepath in self.file_changes:
                    self.ai_text.delete("1.0", tk.END)
                    self.ai_text.insert(tk.END, self.file_changes[filepath])
                    self.status_label.config(text="Viewing pending changes.")
                else:
                    self.ai_text.delete("1.0", tk.END)
                    self.status_label.config(text="Viewing original file.")
            except Exception as e:
                self.orig_text.delete("1.0", tk.END)
                self.orig_text.insert(tk.END, f"Error reading file: {e}")

    def format_code(self):
        if not self.selected_file:
            return
        
        content = self.orig_text.get("1.0", tk.END).strip()
        if not content: return

        ext = os.path.splitext(self.selected_file)[1].lower()
        formatted = None
        error = None

        try:
            if ext in ['.py', '.pyw']:
                cmd = ['black', '-', '-q']
                res = subprocess.run(cmd, input=content, capture_output=True, text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                if res.returncode == 0: formatted = res.stdout
                else: error = res.stderr
            elif ext in ['.js', '.ts', '.jsx', '.tsx', '.json', '.html', '.css']:
                cmd = ['npx.cmd' if os.name == 'nt' else 'npx', 'prettier', '--stdin-filepath', self.selected_file]
                res = subprocess.run(cmd, input=content, capture_output=True, text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                if res.returncode == 0: formatted = res.stdout
                else: error = res.stderr
            else:
                messagebox.showinfo("Format", f"No formatter configured for {ext}")
                return

            if formatted:
                self.orig_text.delete("1.0", tk.END)
                self.orig_text.insert(tk.END, formatted)
            elif error:
                messagebox.showerror("Format Error", error)
        except FileNotFoundError:
            messagebox.showerror("Error", "Formatter tool not found. Ensure 'black' (Python) or 'prettier' (JS) is installed and in PATH.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def send_message(self):
        prompt = self.chat_input.get("1.0", tk.END).strip()
        if not prompt: return
        
        context = ""
        if self.selected_file and os.path.isfile(self.selected_file):
            context = self.orig_text.get("1.0", tk.END)
            
        full_prompt = f"""You are a coding assistant in an IDE.
User Request: {prompt}

Current File Context ({self.selected_file}):
```
{context}
```

IMPORTANT: If you generate code changes, you MUST use the following format for EACH file changed:
FILE: <absolute_file_path>
```language
<new_code_content>
```

If the file path is relative, assume it is relative to the current workspace.
If you are just chatting, just provide text.
"""
        self.status_label.config(text="AI is thinking...")
        self.chat_input.delete("1.0", tk.END)
        threading.Thread(target=self._process_ai_request, args=(full_prompt,), daemon=True).start()

    def _process_ai_request(self, prompt):
        try:
            response = self.chat_client.ask_gemini(prompt)
            self.after(0, self.handle_ai_response, response)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def handle_ai_response(self, response):
        self.status_label.config(text="Response received.")
        self.ai_text.delete("1.0", tk.END)
        self.ai_text.insert(tk.END, response)
        
        # Parse for files
        # Regex to find FILE: path \n ```code```
        pattern = r"FILE:\s*(.*?)\s*\n```.*?\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)
        
        if matches:
            count = 0
            for filepath, content in matches:
                filepath = filepath.strip()
                # Handle relative paths
                if not os.path.isabs(filepath) and self.current_folder:
                    filepath = os.path.join(self.current_folder, filepath)
                elif not os.path.isabs(filepath) and self.selected_file:
                    filepath = self.selected_file # Fallback to current file if path is ambiguous
                
                self.file_changes[filepath] = content.strip()
                
                # Highlight in tree
                if self.file_tree.exists(filepath):
                    self.file_tree.item(filepath, tags=("changed",))
                else:
                    # Add if not exists (new file)
                    self.file_tree.insert("", "end", filepath, text=f"*{os.path.basename(filepath)}", tags=("changed",))
                count += 1
            
            self.file_tree.tag_configure("changed", foreground="red", font=("Segoe UI", 9, "bold"))
            messagebox.showinfo("Changes Generated", f"AI suggested changes for {count} file(s).\nSelect red files in the list to review.")
            
            # If current file was changed, refresh view
            if self.selected_file in self.file_changes:
                self.ai_text.delete("1.0", tk.END)
                content = self.file_changes[self.selected_file]
                self.ai_text.insert(tk.END, content)
                self.apply_highlighting(self.ai_text, content, self.detect_language(self.selected_file))

    def apply_current_change(self):
        if not self.selected_file or self.selected_file not in self.file_changes:
            messagebox.showinfo("Info", "No pending changes for the selected file.")
            return
        
        if messagebox.askyesno("Apply Changes", f"Overwrite {os.path.basename(self.selected_file)}?"):
            try:
                with open(self.selected_file, 'w', encoding='utf-8') as f:
                    f.write(self.file_changes[self.selected_file])
                
                del self.file_changes[self.selected_file]
                self.file_tree.item(self.selected_file, tags=()) # Remove red tag
                self.on_file_select(None) # Refresh view
                messagebox.showinfo("Success", "File updated.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

class AIChatClient:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.secure_config = SecureConfig(config_path)
        self.config = self.secure_config.load_config()
        self.gemini_available = False
        self.deepseek_available = False
        self.configure_apis()

    def configure_apis(self):
        if self.config.get("gemini_api_key"):
            try:
                genai.configure(api_key=self.config["gemini_api_key"])
                self.gemini_model = genai.GenerativeModel(self.config["gemini_model"])
                self.gemini_available = True
            except Exception as e:
                print(f"Gemini config error: {e}")
                self.gemini_available = False
        else:
            self.gemini_available = False

        self.deepseek_available = bool(self.config.get("deepseek_api_key"))

    def ask_gemini(self, prompt: str) -> str:
        if not self.gemini_available:
            return "Gemini API not configured. Please set your API key in Settings."
        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Gemini Error: {str(e)}"

    def ask_deepseek(self, prompt: str) -> str:
        if not self.deepseek_available:
            return "DeepSeek API not configured. Please set your API key in Settings."

        headers = {
            'Authorization': f'Bearer {self.config["deepseek_api_key"]}',
            'Content-Type': 'application/json'
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        try:
            response = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return f"DeepSeek HTTP Error: {response.status_code}"
        except Exception as e:
            return f"DeepSeek Error: {str(e)}"

    def ask_both(self, prompt: str) -> Dict[str, str]:
        gemini_response = self.ask_gemini(prompt)
        deepseek_response = self.ask_deepseek(prompt)
        return {"gemini": gemini_response, "deepseek": deepseek_response}


class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIChatDesktop - GitHub Aware Edition")
        self.root.geometry("1200x800")

        try:
            self.root.iconbitmap(default='icon.ico')
        except Exception:
            pass

        self.config_dir = os.path.join(os.path.expanduser('~'), '.aichatdesktop')
        self.config_path = os.path.join(self.config_dir, 'config.json')
        self.repo_cache_dir = os.path.join(self.config_dir, 'repo_cache')
        os.makedirs(self.repo_cache_dir, exist_ok=True)

        self.chat_client = AIChatClient(self.config_path)
        token = self.chat_client.config.get("github_token", "")
        self.gh_handler = GitHubHandler(self.repo_cache_dir, token=token)
        self.message_queue = queue.Queue()
        self.status_update_id = None
        self.view_mode = "full"
        self.repo_context = ""

        self.setup_ui()
        self.display_welcome()
        self.create_menu()
        self.process_queue()

    
    def create_menu(self):
        """Create application menu with developer tools"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Clear Chat", command=self.clear_chat)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Change View Mode", command=self.toggle_view_mode, accelerator="F11")

        # Developer Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Developer Tools", menu=tools_menu)

        tools_menu.add_command(label="Analyze Code...", command=self.tool_analyze_code)
        tools_menu.add_command(label="Generate Documentation...", command=self.tool_generate_docs)
        tools_menu.add_command(label="Debug Error...", command=self.tool_debug_error)
        tools_menu.add_command(label="Generate Unit Tests...", command=self.tool_generate_tests)
        tools_menu.add_separator()
        tools_menu.add_command(label="SQL Optimizer...", command=self.tool_optimize_sql)
        tools_menu.add_command(label="Design DB Schema...", command=self.tool_design_db_schema)
        tools_menu.add_command(label="Regex Builder...", command=self.tool_build_regex)
        tools_menu.add_separator()
        tools_menu.add_command(label="Generate API Endpoint...", command=self.tool_generate_api_endpoint)
        tools_menu.add_command(label="Security Check...", command=self.tool_check_security)
        tools_menu.add_command(label="Performance Analysis...", command=self.tool_analyze_performance)
        tools_menu.add_separator()
        tools_menu.add_command(label="Recommend Packages...", command=self.tool_recommend_packages)
        tools_menu.add_command(label="Explain Algorithm...", command=self.tool_explain_algorithm)
        tools_menu.add_command(label="Refactor Code...", command=self.tool_refactor_code)
        tools_menu.add_command(label="Git Helper...", command=self.tool_git_helper)
        tools_menu.add_command(label="Generate Config...", command=self.tool_generate_config)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
        self.root.bind("<F11>", self.toggle_view_mode)

    def open_dev_tool(self, title: str, input_label: str, action_callback):
        """Generic function to open a developer tool window."""
        DevToolWindow(self.root, title, input_label, action_callback)

    def tool_analyze_code(self): self.open_dev_tool("Analyze Code", "Code to Analyze", self.analyze_code)
    def tool_generate_docs(self): self.open_dev_tool("Generate Documentation", "Code to Document", self.generate_documentation)
    def tool_debug_error(self): self.open_dev_tool("Debug Error", "Paste Error Message and Code Context", self.debug_error)
    def tool_generate_tests(self): self.open_dev_tool("Generate Unit Tests", "Code to Test", self.generate_unit_tests)
    def tool_optimize_sql(self): self.open_dev_tool("Optimize SQL", "SQL Query to Optimize", self.optimize_sql)
    def tool_design_db_schema(self): self.open_dev_tool("Design DB Schema", "Requirements for DB Schema", self.design_database_schema)
    def tool_build_regex(self): self.open_dev_tool("Build Regex", "Description of what to match", self.build_regex)
    def tool_generate_api_endpoint(self): self.open_dev_tool("Generate API Endpoint", "Description of the API endpoint", self.generate_api_endpoint)
    def tool_check_security(self): self.open_dev_tool("Check Security", "Code to check for vulnerabilities", self.check_security)
    def tool_analyze_performance(self): self.open_dev_tool("Analyze Performance", "Code to analyze for performance", self.analyze_performance)
    def tool_recommend_packages(self): self.open_dev_tool("Recommend Packages", "Describe the task you need a package for", self.recommend_packages)
    def tool_explain_algorithm(self): self.open_dev_tool("Explain Algorithm", "Algorithm name or code to explain", self.explain_algorithm)
    def tool_refactor_code(self): CodeChatWindow(self.root, self.chat_client)
    def tool_git_helper(self): self.open_dev_tool("Git Helper", "Describe your Git problem or task", self.git_helper)
    def tool_generate_config(self): self.open_dev_tool("Generate Config", "Describe the configuration you need (e.g., 'nginx for a react app')", self.generate_config)

    def show_about(self):
        messagebox.showinfo("About", "AI Chat Desktop\nVersion 2.0\nDeveloper Tools Edition")


    def setup_ui(self):
        self.top_frame = tk.Frame(self.root, bg="#f0f0f0", pady=10)
        self.top_frame.pack(fill=tk.X)

        tk.Label(self.top_frame, text="GitHub Repo URL:", bg="#f0f0f0", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=10)
        self.repo_entry = tk.Entry(self.top_frame, width=60, font=("Segoe UI", 9))
        self.repo_entry.pack(side=tk.LEFT, padx=5)

        fetch_btn = tk.Button(
            self.top_frame,
            text="Fetch Repo",
            command=self.fetch_repo_context,
            bg="#3498db",
            fg="white",
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        fetch_btn.pack(side=tk.LEFT, padx=5)

        self.control_frame = tk.Frame(self.root, bg="#f0f0f0", padx=10, pady=5)
        self.control_frame.pack(fill=tk.X)

        tk.Label(self.control_frame, text="Model:", bg="#f0f0f0", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 5))
        self.model_var = tk.StringVar(value="both")
        model_combo = ttk.Combobox(
            self.control_frame,
            textvariable=self.model_var,
            values=["gemini", "deepseek", "both"],
            width=15,
            state="readonly"
        )
        model_combo.pack(side=tk.LEFT, padx=5)

        settings_btn = tk.Button(
            self.control_frame,
            text="⚙ Settings",
            command=self.open_settings,
            bg="#7f8c8d",
            fg="white",
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        settings_btn.pack(side=tk.RIGHT, padx=5)

        status_frame = tk.Frame(self.control_frame, bg="#f0f0f0")
        status_frame.pack(side=tk.RIGHT, padx=10)

        self.gemini_status = tk.Label(status_frame, text="●", fg="#e74c3c", bg="#f0f0f0", font=("Arial", 12))
        self.gemini_status.pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(status_frame, text="Gemini", bg="#f0f0f0", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 10))

        self.deepseek_status = tk.Label(status_frame, text="●", fg="#e74c3c", bg="#f0f0f0", font=("Arial", 12))
        self.deepseek_status.pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(status_frame, text="DeepSeek", bg="#f0f0f0", font=("Segoe UI", 8)).pack(side=tk.LEFT)

        self.update_status_indicators()

        self.chat_frame = tk.Frame(self.root)
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = tk.Scrollbar(self.chat_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.chat_display = tk.Text(
            self.chat_frame,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            font=("Segoe UI", 10),
            bg="white",
            fg="black",
            padx=10,
            pady=10,
            state=tk.DISABLED
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.chat_display.yview)

        self._configure_text_tags()

        input_frame = tk.Frame(self.root, padx=10, pady=10)
        input_frame.pack(fill=tk.X)

        self.input_text = tk.Text(input_frame, height=4, wrap=tk.WORD, font=("Segoe UI", 10))
        self.input_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.input_text.bind("<Control-Return>", self.on_ctrl_enter)

        button_frame = tk.Frame(input_frame)
        button_frame.pack(side=tk.RIGHT, padx=(10, 0))

        send_btn = tk.Button(
            button_frame,
            text="Send",
            command=self.send_message,
            bg="#2ecc71",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=8,
            cursor="hand2"
        )
        send_btn.pack(pady=(0, 5))

        clear_btn = tk.Button(
            button_frame,
            text="Clear",
            command=self.clear_input,
            bg="#e74c3c",
            fg="white",
            font=("Segoe UI", 9),
            width=8,
            cursor="hand2"
        )
        clear_btn.pack()

    def toggle_view_mode(self, event=None):
        """Toggle between Full and Focus view modes"""
        if self.view_mode == "full":
            self.top_frame.pack_forget()
            self.control_frame.pack_forget()
            self.view_mode = "focus"
        else:
            self.top_frame.pack(before=self.chat_frame, fill=tk.X)
            self.control_frame.pack(before=self.chat_frame, fill=tk.X)
            self.view_mode = "full"

    def _configure_text_tags(self):
        self.chat_display.tag_config("user", foreground="#2c3e50", font=("Segoe UI", 10, "bold"))
        self.chat_display.tag_config("gemini", foreground="#4285f4")
        self.chat_display.tag_config("deepseek", foreground="#00a67e")
        self.chat_display.tag_config("system", foreground="#e74c3c", font=("Segoe UI", 9, "italic"))
        self.chat_display.tag_config("timestamp", foreground="#95a5a6", font=("Segoe UI", 8))

    def update_status_indicators(self):
        if self.gemini_status.winfo_exists():
            if self.chat_client.gemini_available:
                self.gemini_status.config(fg="#2ecc71", text="●")
            else:
                self.gemini_status.config(fg="#e74c3c", text="○")

        if self.deepseek_status.winfo_exists():
            if self.chat_client.deepseek_available:
                self.deepseek_status.config(fg="#2ecc71", text="●")
            else:
                self.deepseek_status.config(fg="#e74c3c", text="○")

        self.status_update_id = self.root.after(10000, self.update_status_indicators)

    def fetch_repo_context(self):
        repo_url = self.repo_entry.get().strip()
        if not repo_url:
            messagebox.showwarning("Input Error", "Please enter a GitHub repository URL")
            return

        self.display_message("system", f"Fetching repository context from {repo_url}...")
        threading.Thread(target=self._fetch_repo_thread, args=(repo_url,), daemon=True).start()

    def _fetch_repo_thread(self, repo_url: str):
        try:
            context = self.gh_handler.fetch_repo_context(repo_url)
            self.message_queue.put(("repo_context", context))
        except Exception as e:
            self.message_queue.put(("error", f"Failed to fetch repo: {str(e)}"))

    def process_queue(self):
        try:
            while True:
                msg_type, content = self.message_queue.get_nowait()
                if msg_type == "repo_context":
                    self.repo_context = content
                    self.display_message("system", f"Repository context loaded. Summary:\n{content[:200]}...")
                elif msg_type == "error":
                    self.display_message("system", f"Error: {content}")
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def display_message(self, sender: str, message: str):
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")

        if sender.lower() == "you":
            self.chat_display.insert(tk.END, f"{sender}:\n", "user")
        elif "gemini" in sender.lower():
            self.chat_display.insert(tk.END, f"{sender}:\n", "gemini")
        elif "deepseek" in sender.lower():
            self.chat_display.insert(tk.END, f"{sender}:\n", "deepseek")
        else:
            self.chat_display.insert(tk.END, f"{sender}:\n", "system")

        self.chat_display.insert(tk.END, f"{message}\n{'─'*60}\n\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def on_ctrl_enter(self, event):
        self.send_message()
        return "break"

    def send_message(self):
        user_input = self.input_text.get("1.0", tk.END).strip()
        if not user_input:
            return

        self.display_message("You", user_input)
        self.clear_input()
        selected_model = self.model_var.get()
        self.input_text.config(state=tk.DISABLED)

        thread = threading.Thread(
            target=self.get_ai_response,
            args=(user_input, selected_model),
            daemon=True
        )
        thread.start()

    def get_ai_response(self, prompt: str, model: str):
        full_prompt = prompt
        if self.repo_context:
            full_prompt = f"Context from GitHub Repository:\n{self.repo_context}\n\nUser Query:\n{prompt}"

        try:
            if model == "gemini":
                response = self.chat_client.ask_gemini(full_prompt)
                self.display_message("Gemini", response)
            elif model == "deepseek":
                response = self.chat_client.ask_deepseek(full_prompt)
                self.display_message("DeepSeek", response)
            else:
                responses = self.chat_client.ask_both(full_prompt)
                self.display_message("Gemini", responses["gemini"])
                self.display_message("DeepSeek", responses["deepseek"])
        except Exception as e:
            self.display_message("System", f"Error: {str(e)}")
        finally:
            self.root.after(0, lambda: self.input_text.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.input_text.focus())

    def clear_input(self):
        self.input_text.delete("1.0", tk.END)

    def clear_chat(self):
        if messagebox.askyesno("Clear Chat", "Are you sure you want to clear the chat history?"):
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.config(state=tk.DISABLED)
            self.display_welcome()

    def export_chat(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if filename:
            try:
                content = self.chat_display.get("1.0", tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Export Successful", f"Chat exported to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {str(e)}")

    def open_settings(self):
        SettingsWindow(self.root, self.config_path)
        self.root.after(100, self.update_chat_client)

    def update_chat_client(self):
        self.chat_client = AIChatClient(self.config_path)
        self.update_status_indicators()
        
    def update_github_handler(self, token: str):
        self.gh_handler = GitHubHandler(self.repo_cache_dir, token=token)

    def change_theme(self):
        themes = ["Light", "Dark", "Blue"]
        choice = simpledialog.askstring("Change Theme", "Enter theme name (Light/Dark/Blue):", initialvalue="Light")
        if choice and choice.capitalize() in themes:
            messagebox.showinfo("Theme Changed", f"Theme changed to {choice}. Restart to see changes.")

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
    try:
        root.tk.call('source', 'sun-valley.tcl')
        root.tk.call('set_theme', 'light')
    except Exception:
        pass

    app = ChatApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    root.mainloop()


if __name__ == "__main__":
    main()
