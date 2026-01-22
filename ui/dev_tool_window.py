import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import threading

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
