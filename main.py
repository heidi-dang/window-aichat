import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox, filedialog
import threading
import json
import os
import sys
from pathlib import Path
import google.generativeai as genai
import requests
import webbrowser
from datetime import datetime
from github_handler import GitHubHandler

class SettingsWindow:
    def __init__(self, parent, config_path):
        self.parent = parent
        self.config_path = config_path
        self.config = self.load_config()

        self.window = tk.Toplevel(parent)
        self.window.title("API Settings - AI Chat Desktop")
        self.window.geometry("550x500")
        self.window.resizable(False, False)
        self.window.configure(bg="#f0f0f0")
        self.window.transient(parent)
        self.window.grab_set()

        try:
            self.window.iconbitmap(default='icon.ico')
        except:
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

        title_label = tk.Label(main_frame, text="API Configuration",
                              font=("Segoe UI", 16, "bold"),
                              bg="#f0f0f0", fg="#2c3e50")
        title_label.pack(pady=(0, 20))

        gemini_frame = tk.LabelFrame(main_frame, text=" Gemini API ",
                                   font=("Segoe UI", 10, "bold"),
                                   bg="#f0f0f0", fg="#2c3e50",
                                   padx=10, pady=10)
        gemini_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(gemini_frame, text="API Key:", bg="#f0f0f0",
                font=("Segoe UI", 9)).pack(anchor=tk.W)
        self.gemini_key = tk.Entry(gemini_frame, width=50, show="•",
                                  font=("Segoe UI", 9))
        self.gemini_key.pack(fill=tk.X, pady=(2, 5))

        tk.Label(gemini_frame, text="Model:", bg="#f0f0f0",
                font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(5, 0))
        self.gemini_model = ttk.Combobox(gemini_frame,
                                       values=["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
                                       state="readonly",
                                       font=("Segoe UI", 9))
        self.gemini_model.pack(fill=tk.X, pady=(2, 0))
        self.gemini_model.set("gemini-1.5-flash")

        gemini_btn = tk.Button(gemini_frame, text="Get Gemini API Key",
                             command=lambda: webbrowser.open("https://makersuite.google.com/app/apikey"),
                             bg="#4285f4", fg="white",
                             font=("Segoe UI", 9), cursor="hand2")
        gemini_btn.pack(pady=(10, 0))

        deepseek_frame = tk.LabelFrame(main_frame, text=" DeepSeek API ",
                                     font=("Segoe UI", 10, "bold"),
                                     bg="#f0f0f0", fg="#2c3e50",
                                     padx=10, pady=10)
        deepseek_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(deepseek_frame, text="API Key:", bg="#f0f0f0",
                font=("Segoe UI", 9)).pack(anchor=tk.W)
        self.deepseek_key = tk.Entry(deepseek_frame, width=50, show="•",
                                   font=("Segoe UI", 9))
        self.deepseek_key.pack(fill=tk.X, pady=(2, 5))

        deepseek_btn = tk.Button(deepseek_frame, text="Get DeepSeek API Key",
                               command=lambda: webbrowser.open("https://platform.deepseek.com/api-docs"),
                               bg="#00a67e", fg="white",
                               font=("Segoe UI", 9), cursor="hand2")
        deepseek_btn.pack(pady=(10, 0))

        button_frame = tk.Frame(main_frame, bg="#f0f0f0")
        button_frame.pack(pady=(20, 0))

        save_btn = tk.Button(button_frame, text="Save Settings",
                           command=self.save_settings,
                           bg="#2ecc71", fg="white",
                           font=("Segoe UI", 10, "bold"),
                           width=12, cursor="hand2")
        save_btn.pack(side=tk.LEFT, padx=(0, 10))

        test_btn = tk.Button(button_frame, text="Test Connection",
                           command=self.test_connection,
                           bg="#3498db", fg="white",
                           font=("Segoe UI", 10),
                           width=12, cursor="hand2")
        test_btn.pack(side=tk.LEFT, padx=10)

        cancel_btn = tk.Button(button_frame, text="Cancel",
                             command=self.window.destroy,
                             bg="#95a5a6", fg="white",
                             font=("Segoe UI", 10),
                             width=12, cursor="hand2")
        cancel_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.status_label = tk.Label(main_frame, text="", bg="#f0f0f0",
                                   font=("Segoe UI", 9), fg="#e74c3c")
        self.status_label.pack(pady=(15, 0))

    def load_config(self):
        default_config = {
            "gemini_api_key": "",
            "deepseek_api_key": "",
            "gemini_model": "gemini-1.5-flash"
        }
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                return config
        except:
            pass
        return default_config.copy()

    def load_current_settings(self):
        self.gemini_key.delete(0, tk.END)
        self.gemini_key.insert(0, self.config.get("gemini_api_key", ""))
        self.deepseek_key.delete(0, tk.END)
        self.deepseek_key.insert(0, self.config.get("deepseek_api_key", ""))
        self.gemini_model.set(self.config.get("gemini_model", "gemini-1.5-flash"))

    def save_settings(self):
        config = {
            "gemini_api_key": self.gemini_key.get().strip(),
            "deepseek_api_key": self.deepseek_key.get().strip(),
            "gemini_model": self.gemini_model.get()
        }
        try:
            config_dir = os.path.dirname(self.config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            self.status_label.config(text="Settings saved successfully!", fg="#2ecc71")
            if hasattr(self.parent, 'chat_client'):
                self.parent.chat_client.config = config
                self.parent.chat_client.configure_apis()
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
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content("Say 'TEST OK' only",
                                               generation_config={"max_output_tokens": 5})
                results.append("✓ Gemini: Connected")
            except Exception as e:
                results.append(f"✗ Gemini: {str(e)[:50]}")
        else:
            results.append("○ Gemini: No key provided")
        if deepseek_key:
            try:
                import requests
                headers = {
                    'Authorization': f'Bearer {deepseek_key}',
                    'Content-Type': 'application/json'
                }
                data = {
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": "Say 'TEST OK'"}],
                    "max_tokens": 5
                }
                # FIXED: Removed trailing space in URL
                response = requests.post("https://api.deepseek.com/chat/completions",
                                      headers=headers, json=data, timeout=10)
                if response.status_code == 200:
                    results.append("✓ DeepSeek: Connected")
                else:
                    results.append(f"✗ DeepSeek: HTTP {response.status_code}")
            except Exception as e:
                results.append(f"✗ DeepSeek: {str(e)[:50]}")
        else:
            results.append("○ DeepSeek: No key provided")
        self.status_label.config(text=" | ".join(results), fg="#2ecc71")

class AIChatClient:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = self.load_config()
        self.configure_apis()

    def load_config(self):
        default_config = {
            "gemini_api_key": "",
            "deepseek_api_key": "",
            "gemini_model": "gemini-1.5-flash"
        }
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                return config
        except:
            pass
        return default_config.copy()

    def configure_apis(self):
        if self.config["gemini_api_key"]:
            try:
                genai.configure(api_key=self.config["gemini_api_key"])
                self.gemini_model = genai.GenerativeModel(self.config["gemini_model"])
                self.gemini_available = True
            except:
                self.gemini_available = False
        else:
            self.gemini_available = False
        self.deepseek_available = bool(self.config["deepseek_api_key"])

    def ask_gemini(self, prompt):
        if not self.gemini_available:
            return "Gemini API not configured. Please set your API key in Settings."
        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Gemini Error: {str(e)}"

    def ask_deepseek(self, prompt):
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
            # FIXED: Removed trailing space
            response = requests.post("https://api.deepseek.com/chat/completions",
                                  headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return f"DeepSeek HTTP Error: {response.status_code}"
        except Exception as e:
            return f"DeepSeek Error: {str(e)}"

    def ask_both(self, prompt):
        gemini_response = self.ask_gemini(prompt)
        deepseek_response = self.ask_deepseek(prompt)
        return {"gemini": gemini_response, "deepseek": deepseek_response}

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIChatDesktop - Unrestricted Hard Audit Edition")
                self.root.geometry("1000x800")
        try:
            self.root.iconbitmap(default='icon.ico')
        except:
            pass
        self.config_dir = os.path.join(os.path.expanduser('~'), '.aichatdesktop')
        self.config_path = os.path.join(self.config_dir, 'config.json')
        self.chat_client = AIChatClient(self.config_path)
        self.create_menu()
        self.gh_handler = GitHubHandler()
        self.load_config()
        self.setup_ui()
        self.display_welcome()

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Clear Chat", command=self.clear_chat)
        file_menu.add_separator()
        file_menu.add_command(label="Export Chat...", command=self.export_chat)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="API Settings", command=self.open_settings)
        settings_menu.add_command(label="Change Theme", command=self.change_theme)
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation",
                           command=lambda: webbrowser.open("https://github.com/your-repo/docs"))
        help_menu.add_command(label="About", command=self.show_about)

    def setup_ui(self):
        # Header for Repo URL
        top_frame = tk.Frame(self.root, pady=10)
        top_frame.pack(fill=tk.X)
        control_frame = tk.Frame(self.root, bg="#f0f0f0")
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(top_frame, text="GitHub Repo URL:").pack(side=tk.LEFT, padx=10)
                self.repo_entry = tk.Entry(top_frame, width=60)
                self.repo_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(control_frame, text="Model:", bg="#f0f0f0",
                font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value="both")
        model_combo = ttk.Combobox(control_frame, textvariable=self.model_var,
                                 values=["gemini", "deepseek", "both"],
                                 width=15, state="readonly")
        model_combo.pack(side=tk.LEFT, padx=5)
        settings_btn = tk.Button(control_frame, text="⚙ Settings",
                               command=self.open_settings,
                               bg="#7f8c8d", fg="white",
                               font=("Segoe UI", 9), cursor="hand2")
        settings_btn.pack(side=tk.RIGHT, padx=5)
        status_frame = tk.Frame(control_frame, bg="#f0f0f0")
        status_frame.pack(side=tk.RIGHT, padx=10)
        self.gemini_status = tk.Label(status_frame, text="●", fg="#e74c3c",
                                    bg="#f0f0f0", font=("Arial", 12))
        self.gemini_status.pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(status_frame, text="Gemini", bg="#f0f0f0",
                font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 10))
        self.deepseek_status = tk.Label(status_frame, text="●", fg="#e74c3c",
                                      bg="#f0f0f0", font=("Arial", 12))
        self.deepseek_status.pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(status_frame, text="DeepSeek", bg="#f0f0f0",
                font=("Segoe UI", 8)).pack(side=tk.LEFT)
        self.update_status_indicators()
        chat_frame = tk.Frame(self.root)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar = tk.Scrollbar(chat_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_display = tk.Text(chat_frame, wrap=tk.WORD,
                                  yscrollcommand=scrollbar.set,
                                  font=("Segoe UI", 10),
                                  bg="white", fg="black",
                                  padx=10, pady=10,
                                  state=tk.DISABLED)
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.chat_display.yview)
        self.chat_display.tag_config("user", foreground="#2c3e50",
                                   font=("Segoe UI", 10, "bold"))
        self.chat_display.tag_config("gemini", foreground="#4285f4")
        self.chat_display.tag_config("deepseek", foreground="#00a67e")
        self.chat_display.tag_config("system", foreground="#e74c3c",
                                   font=("Segoe UI", 9, "italic"))
        self.chat_display.tag_config("timestamp", foreground="#95a5a6",
                                   font=("Segoe UI", 8))
        input_frame = tk.Frame(self.root)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        self.input_text = tk.Text(input_frame, height=4, wrap=tk.WORD,
                                font=("Segoe UI", 10))
        self.input_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.input_text.bind("<Return>", self.on_enter_pressed)
        button_frame = tk.Frame(input_frame)
        button_frame.pack(side=tk.RIGHT, padx=(10, 0))
        send_btn = tk.Button(button_frame, text="Send",
                           command=self.send_message,
                           bg="#2ecc71", fg="white",
                           font=("Segoe UI", 10, "bold"),
                           width=8, cursor="hand2")
        send_btn.pack(pady=(0, 5))
        clear_btn = tk.Button(button_frame, text="Clear",
                            command=self.clear_input,
                            bg="#e74c3c", fg="white",
                            font=("Segoe UI", 9),
                            width=8, cursor="hand2")
        clear_btn.pack()

    def update_status_indicators(self):
        if self.chat_client.gemini_available:
            self.gemini_status.config(fg="#2ecc71", text="●")
        else:
            self.gemini_status.config(fg="#e74c3c", text="○")
        if self.chat_client.deepseek_available:
            self.deepseek_status.config(fg="#2ecc71", text="●")
        else:
            self.deepseek_status.config(fg="#e74c3c", text="○")
        self.root.after(10000, self.update_status_indicators)

        # Input Area
        input_frame = tk.Frame(self.root, pady=10)
        input_frame.pack(fill=tk.X)

        self.input_text = tk.Text(input_frame, height=4, font=("Segoe UI", 10))
        self.input_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        send_btn = tk.Button(input_frame, text="Execute", command=self.process_request,
                             bg="#27ae60", fg="white", width=12, height=2)
        send_btn.pack(side=tk.RIGHT, padx=10)


def process_request(self):
        prompt = self.input_text.get("1.0", tk.END).strip()
        repo_url = self.repo_entry.get().strip()

        if not prompt: return

        self.chat_display.insert(tk.END, f"\n[YOU]: {prompt}\n", "user")
        self.input_text.delete("1.0", tk.END)

        threading.Thread(target=self.get_unrestricted_response, args=(prompt, repo_url), daemon=True).start()

    def get_unrestricted_response(self, prompt, repo_url):
        context = ""
        if repo_url:
            self.update_chat("System", f"Fetching context from {repo_url}...")
            context = self.gh_handler.fetch_repo_context(repo_url)

You can also use Ctrl+Enter to send messages.
"""
        self.display_message("system", welcome_msg)

    def display_message(self, sender, message):
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

    def on_enter_pressed(self, event):
        if event.state & 0x4:
            self.send_message()
            return "break"
        return None

    def send_message(self):
        user_input = self.input_text.get("1.0", tk.END).strip()
        if not user_input: return
        self.display_message("You", user_input)
        self.clear_input()
        selected_model = self.model_var.get()
        self.input_text.config(state=tk.DISABLED)
        thread = threading.Thread(target=self.get_ai_response,
                               args=(user_input, selected_model),
                               daemon=True)
        thread.start()

    def get_ai_response(self, prompt, model):
        try:
            if model == "gemini":
                response = self.chat_client.ask_gemini(prompt)
                self.display_message("Gemini", response)
            elif model == "deepseek":
                response = self.chat_client.ask_deepseek(prompt)
                self.display_message("DeepSeek", response)
            else:
                responses = self.chat_client.ask_both(prompt)
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

full_prompt = (
            "SYSTEM: You are an unrestricted AI auditor. "
            "Perform hard audits, identify security flaws, and implement features without limitations. "
            "ALWAYS generate 1 full, complete script for every file requested. Never use placeholders. "
            f"\n\nCONTEXT:\n{context}\n\nUSER REQUEST: {prompt}"
        )

        try:
            response = self.model.generate_content(full_prompt)
            self.update_chat("AI", response.text)
        except Exception as e:
            self.update_chat("Error", str(e))

    def update_chat(self, sender, message):
        self.chat_display.insert(tk.END, f"\n[{sender}]:\n{message}\n{'-'*80}\n", "ai")
        self.chat_display.see(tk.END)

    def change_theme(self):
        themes = ["Light", "Dark", "Blue"]
        choice = tk.simpledialog.askstring("Change Theme",
                                         "Enter theme name (Light/Dark/Blue):",
                                         initialvalue="Light")
        if choice and choice.capitalize() in themes:
            messagebox.showinfo("Theme Changed",
                              f"Theme changed to {choice}. Restart to see changes.")

    def show_about(self):
        about_text = """AI Chat Desktop v1.0

A desktop application for chatting with multiple AI models.

Features:
• Gemini AI integration
• DeepSeek AI integration
• Dual-model comparison
• API key management
• Chat history export

Created with Python and Tkinter

© 2024 AI Chat Desktop
"""
        messagebox.showinfo("About AI Chat Desktop", about_text)

def main():
    root = tk.Tk()
    try:
        root.tk.call('source', 'sun-valley.tcl')
        root.tk.call('set_theme', 'light')
    except:
        pass
    app = ChatApp(root)
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    root.mainloop()

if __name__ == "__main__":
    main()
