import tkinter as tk
from tkinter import ttk
import webbrowser
import os
import requests
import google.generativeai as genai
from ai_core import SecureConfig

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
            values=["gemini-2.0-flash", "gemini-2.0-pro-exp"],
            state="readonly",
            font=("Segoe UI", 9)
        )
        self.gemini_model.pack(fill=tk.X, pady=(2, 0))
        self.gemini_model.set("gemini-2.0-flash")

        tk.Label(gemini_frame, text="Max Retries on Error:", bg="#f0f0f0", font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(5,0))
        self.gemini_max_retries = tk.Entry(gemini_frame, width=10, font=("Segoe UI", 9))
        self.gemini_max_retries.pack(anchor=tk.W, pady=(2, 5))

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
        self.gemini_max_retries.delete(0, tk.END)
        self.gemini_max_retries.insert(0, self.config.get("gemini_max_retries", "3"))

    def save_settings(self):
        config = {
            "gemini_api_key": self.gemini_key.get().strip(),
            "deepseek_api_key": self.deepseek_key.get().strip(),
            "github_token": self.github_token.get().strip(),
            "gemini_model": self.gemini_model.get(),
            "gemini_max_retries": self.gemini_max_retries.get().strip()
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
