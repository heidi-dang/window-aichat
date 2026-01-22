import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox, filedialog, simpledialog
import os
import re
import difflib
import time
import threading
import subprocess

try:
    from pygments import lex
    from pygments.lexers import get_lexer_for_filename, get_lexer_by_name
    from pygments.token import Token
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

# --- Helper Classes for Code Editor with Line Numbers ---
class CustomText(tk.Text):
    def __init__(self, *args, **kwargs):
        tk.Text.__init__(self, *args, **kwargs)
        self._orig = self._w + "_orig"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._proxy)

    def _proxy(self, *args):
        cmd = (self._orig,) + args
        try:
            result = self.tk.call(cmd)
        except Exception:
            return None
        if (args[0] in ("insert", "replace", "delete") or
            args[0:3] == ("mark", "set", "insert") or
            args[0:2] == ("xview", "moveto") or
            args[0:2] == ("xview", "scroll") or
            args[0:2] == ("yview", "moveto") or
            args[0:2] == ("yview", "scroll")
        ):
            self.event_generate("<<Change>>", when="tail")
        return result

class TextLineNumbers(tk.Canvas):
    def __init__(self, *args, **kwargs):
        tk.Canvas.__init__(self, *args, **kwargs)
        self.textwidget = None

    def attach(self, text_widget):
        self.textwidget = text_widget

    def redraw(self, *args):
        self.delete("all")
        i = self.textwidget.index("@0,0")
        while True :
            dline= self.textwidget.dlineinfo(i)
            if dline is None: break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(2,y,anchor="nw", text=linenum, fill="#606366", font=("Consolas", 9))
            i = self.textwidget.index("%s+1line" % i)

class CodeEditor(tk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text = CustomText(self, wrap=tk.NONE, font=("Consolas", 10), undo=True)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.linenumbers = TextLineNumbers(self, width=35, bg="#f0f0f0")
        self.linenumbers.attach(self.text)

        self.linenumbers.pack(side="left", fill="y")
        self.vsb.pack(side="right", fill="y")
        self.hsb.pack(side="bottom", fill="x")
        self.text.pack(side="top", fill="both", expand=True)

        self.text.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        self.text.bind("<<Change>>", self._on_change)
        self.text.bind("<Configure>", self._on_change)

    def _on_change(self, event):
        self.linenumbers.redraw()

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
        self.is_diff_view = False
        self.diff_hunks = [] # Stores (orig_start_line, orig_end_line, ai_start_line, ai_end_line)
        self.current_hunk_index = -1
        self.bind('<Control-f>', self.find_text)

        try:
            self.iconbitmap(default='icon.ico')
        except Exception:
            pass

        self.setup_ui()
        self.setup_highlight_tags()

    def setup_ui(self):
        # Toolbar
        toolbar = tk.Frame(self, padx=5, pady=5, bg="#f0f0f0")
        toolbar.pack(fill=tk.X)

        tk.Button(toolbar, text="📂 Open Folder", command=self.open_folder, bg="#ecf0f1").pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="📄 Open File", command=self.open_file, bg="#ecf0f1").pack(side=tk.LEFT, padx=5)

        self.diff_view_btn = tk.Button(toolbar, text="Show Diff", command=self.toggle_diff_view, bg="#ecf0f1")
        self.diff_view_btn.pack(side=tk.LEFT, padx=5)

        self.prev_change_btn = tk.Button(toolbar, text="< Prev Change", command=self._go_to_prev_change, bg="#ecf0f1", state=tk.DISABLED)
        self.prev_change_btn.pack(side=tk.LEFT, padx=2)
        self.next_change_btn = tk.Button(toolbar, text="Next Change >", command=self._go_to_next_change, bg="#ecf0f1", state=tk.DISABLED)
        self.next_change_btn.pack(side=tk.LEFT, padx=2)

        tk.Button(toolbar, text="🔍 Find", command=self.find_text, bg="#ecf0f1").pack(side=tk.LEFT, padx=5)

        tk.Button(toolbar, text="💾 Save All", command=self.save_all_changes, bg="#27ae60", fg="white").pack(side=tk.LEFT, padx=(10, 5))
        tk.Button(toolbar, text="❌ Reset All", command=self.reset_all_changes, bg="#c0392b", fg="white").pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(toolbar, text="Ready", bg="#f0f0f0", fg="#7f8c8d")
        self.status_label.pack(side=tk.LEFT, padx=15)

        self.lang_label = tk.Label(toolbar, text="Language: None", bg="#f0f0f0", fg="#7f8c8d", font=("Segoe UI", 8))
        self.lang_label.pack(side=tk.RIGHT, padx=5)

        self.progress = ttk.Progressbar(toolbar, mode='indeterminate', length=100)
        self.progress.pack(side=tk.RIGHT, padx=5)

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

        # Center Pane: Code Editors
        self.code_paned = tk.PanedWindow(self.main_paned, orient=tk.HORIZONTAL, sashwidth=4, bg="#bdc3c7")
        self.main_paned.add(self.code_paned, width=800)

        # Original Code View
        orig_frame = tk.LabelFrame(self.code_paned, text="Original Code")
        self.code_paned.add(orig_frame, width=500)
        self.orig_editor = CodeEditor(orig_frame)
        self.orig_editor.pack(fill=tk.BOTH, expand=True)
        self.orig_text = self.orig_editor.text # Alias for compatibility

        # AI Suggestion View
        ai_frame = tk.LabelFrame(self.code_paned, text="AI Suggestion / Chat Response")
        self.code_paned.add(ai_frame, width=500)
        self.ai_editor = CodeEditor(ai_frame)
        self.ai_editor.pack(fill=tk.BOTH, expand=True)
        self.ai_text = self.ai_editor.text # Alias for compatibility
        self.ai_text.config(bg="#f4f6f7")

        # Right Pane: Chat Interface
        chat_frame = tk.Frame(self.main_paned, bg="#f0f0f0")
        self.main_paned.add(chat_frame, width=350)

        tk.Label(chat_frame, text="Chat History", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=5, pady=2)
        self.chat_history = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, font=("Segoe UI", 9), state=tk.DISABLED)
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        # Configure chat tags
        self.chat_history.tag_config("user", foreground="#2980b9", font=("Segoe UI", 9, "bold"))
        self.chat_history.tag_config("ai", foreground="#27ae60", font=("Segoe UI", 9, "bold"))
        self.chat_history.tag_config("system", foreground="#7f8c8d", font=("Segoe UI", 9, "italic"))

        # Chat Input Area
        input_frame = tk.Frame(chat_frame, pady=5)
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(input_frame, text="Ask AI:", font=("Segoe UI", 8)).pack(anchor="w")

        self.chat_input = tk.Text(input_frame, height=4, font=("Segoe UI", 10))
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.chat_input.bind("<Control-Return>", lambda e: self.send_message())

        btn_frame = tk.Frame(input_frame)
        btn_frame.pack(side=tk.RIGHT, padx=5)

        self.send_btn = tk.Button(btn_frame, text="Send (Ctrl+Enter)", command=self.send_message, bg="#2ecc71", fg="white", font=("Segoe UI", 9, "bold"))
        self.send_btn.pack(fill=tk.X, pady=2)
        self.apply_btn = tk.Button(btn_frame, text="Apply Changes", command=self.apply_current_change, bg="#3498db", fg="white", font=("Segoe UI", 9))
        self.apply_btn.pack(fill=tk.X, pady=2)
        self.revert_btn = tk.Button(btn_frame, text="Revert Changes", command=self.revert_current_file, bg="#e74c3c", fg="white", font=("Segoe UI", 9))
        self.revert_btn.pack(fill=tk.X, pady=2)

    def setup_highlight_tags(self):
        """Configure tags for syntax highlighting"""
        for text_widget in [self.orig_text, self.ai_text]:
            text_widget.tag_configure("Token.Keyword", foreground="#0000FF")
            text_widget.tag_configure("Token.Keyword.Constant", foreground="#0000FF")
            text_widget.tag_configure("Token.Keyword.Declaration", foreground="#0000FF")
            text_widget.tag_configure("Token.Keyword.Namespace", foreground="#0000FF")
            text_widget.tag_configure("Token.Keyword.Pseudo", foreground="#0000FF")
            text_widget.tag_configure("Token.Keyword.Reserved", foreground="#0000FF")
            text_widget.tag_configure("Token.Keyword.Type", foreground="#0000FF")

            text_widget.tag_configure("Token.Name", foreground="#000000")
            text_widget.tag_configure("Token.Name.Attribute", foreground="#000000")
            text_widget.tag_configure("Token.Name.Builtin", foreground="#0000FF")
            text_widget.tag_configure("Token.Name.Builtin.Pseudo", foreground="#0000FF")
            text_widget.tag_configure("Token.Name.Class", foreground="#2B91AF")
            text_widget.tag_configure("Token.Name.Constant", foreground="#000000")
            text_widget.tag_configure("Token.Name.Decorator", foreground="#2B91AF")
            text_widget.tag_configure("Token.Name.Entity", foreground="#000000")
            text_widget.tag_configure("Token.Name.Exception", foreground="#2B91AF")
            text_widget.tag_configure("Token.Name.Function", foreground="#000000")
            text_widget.tag_configure("Token.Name.Property", foreground="#000000")
            text_widget.tag_configure("Token.Name.Label", foreground="#000000")
            text_widget.tag_configure("Token.Name.Namespace", foreground="#000000")
            text_widget.tag_configure("Token.Name.Other", foreground="#000000")
            text_widget.tag_configure("Token.Name.Tag", foreground="#800000")
            text_widget.tag_configure("Token.Name.Variable", foreground="#000000")
            text_widget.tag_configure("Token.Name.Variable.Class", foreground="#000000")
            text_widget.tag_configure("Token.Name.Variable.Global", foreground="#000000")
            text_widget.tag_configure("Token.Name.Variable.Instance", foreground="#000000")

            text_widget.tag_configure("Token.String", foreground="#A31515")
            text_widget.tag_configure("Token.String.Backtick", foreground="#A31515")
            text_widget.tag_configure("Token.String.Char", foreground="#A31515")
            text_widget.tag_configure("Token.String.Doc", foreground="#A31515")
            text_widget.tag_configure("Token.String.Double", foreground="#A31515")
            text_widget.tag_configure("Token.String.Escape", foreground="#A31515")
            text_widget.tag_configure("Token.String.Heredoc", foreground="#A31515")
            text_widget.tag_configure("Token.String.Interpol", foreground="#A31515")
            text_widget.tag_configure("Token.String.Other", foreground="#A31515")
            text_widget.tag_configure("Token.String.Regex", foreground="#A31515")
            text_widget.tag_configure("Token.String.Single", foreground="#A31515")
            text_widget.tag_configure("Token.String.Symbol", foreground="#A31515")

            text_widget.tag_configure("Token.Number", foreground="#098658")
            text_widget.tag_configure("Token.Number.Bin", foreground="#098658")
            text_widget.tag_configure("Token.Number.Float", foreground="#098658")
            text_widget.tag_configure("Token.Number.Hex", foreground="#098658")
            text_widget.tag_configure("Token.Number.Integer", foreground="#098658")
            text_widget.tag_configure("Token.Number.Integer.Long", foreground="#098658")
            text_widget.tag_configure("Token.Number.Oct", foreground="#098658")

            text_widget.tag_configure("Token.Comment", foreground="#008000")
            text_widget.tag_configure("Token.Comment.Hashbang", foreground="#008000")
            text_widget.tag_configure("Token.Comment.Multiline", foreground="#008000")
            text_widget.tag_configure("Token.Comment.Preproc", foreground="#008000")
            text_widget.tag_configure("Token.Comment.Single", foreground="#008000")
            text_widget.tag_configure("Token.Comment.Special", foreground="#008000")

            text_widget.tag_configure("Token.Operator", foreground="#000000")
            text_widget.tag_configure("Token.Operator.Word", foreground="#0000FF")

            text_widget.tag_configure("Token.Punctuation", foreground="#000000")

            # Fallback tags for regex highlighter
            text_widget.tag_configure("token_comment", foreground="#008000")
            text_widget.tag_configure("token_string", foreground="#A31515")
            text_widget.tag_configure("token_keyword", foreground="#0000FF")
            text_widget.tag_configure("token_number", foreground="#098658")
            text_widget.tag_configure("token_function", foreground="#795E26")
            text_widget.tag_configure("token_class", foreground="#267F99")

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
                display_text = f"{f} ({os.path.relpath(full_path, self.current_folder)})"
                tags = []


                self.file_tree.insert("", "end", full_path, text=display_text, tags=tuple(tags))

    def detect_language(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        mapping = {
            '.py': 'python', '.pyw': 'python',
            '.js': 'javascript', '.jsx': 'javascript', '.ts': 'javascript', '.tsx': 'javascript',
            '.html': 'html', '.htm': 'html',
            '.css': 'css',
            '.java': 'java',
            '.c': 'c', '.cpp': 'cpp', '.h': 'cpp',
            '.json': 'json',
            '.md': 'markdown',
            '.sql': 'sql',
            '.sh': 'bash', '.bat': 'batch'
        }
        return mapping.get(ext, 'text')

    def apply_highlighting(self, text_widget, content, language):
        # Clear old tags
        for tag in text_widget.tag_names():
            if tag.startswith("token_") or tag.startswith("Token."):
                text_widget.tag_remove(tag, "1.0", tk.END)

        if not content: return

        if PYGMENTS_AVAILABLE:
            try:
                if self.selected_file:
                    try:
                        lexer = get_lexer_for_filename(self.selected_file)
                    except:
                        lexer = get_lexer_by_name(language)
                else:
                    lexer = get_lexer_by_name(language)

                tokens = lex(content, lexer)
                self.mark_tokens(text_widget, tokens)
                return
            except Exception as e:
                print(f"Pygments error: {e}. Falling back to regex.")

        # Fallback Regex Highlighting
        if language == 'text': return

        def apply_regex(pattern, tag):
            for match in re.finditer(pattern, content):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                text_widget.tag_add(tag, start, end)

        if language == 'python':
            apply_regex(r'(?m)#.*$', "token_comment")
            apply_regex(r'(?s)"{3}.*?"{3}|\'{3}.*?\'{3}|"[^"\n]*"|\'[^\'\n]*\'', "token_string")
            apply_regex(r'\b(def|class|return|if|else|elif|while|for|in|import|from|try|except|with|as|pass|break|continue|lambda|yield|async|await|global|nonlocal|assert|del|raise)\b', "token_keyword")
            apply_regex(r'\b(True|False|None)\b', "token_keyword")
            apply_regex(r'\b\d+\b', "token_number")
            apply_regex(r'@[\w.]+', "token_function")
            apply_regex(r'(?<=class\s)\w+', "token_class")
            apply_regex(r'(?<=def\s)\w+', "token_function")

        elif language in ['javascript', 'java', 'cpp', 'c']:
            apply_regex(r'//.*', "token_comment")
            apply_regex(r'"[^"\n]*"|\'[^\'\n]*\'', "token_string")
            apply_regex(r'\b(function|return|if|else|for|while|do|switch|case|break|continue|var|let|const|class|new|this|import|export|public|private|protected|static|void|int|float|double|char|bool)\b', "token_keyword")
            apply_regex(r'\b\d+\b', "token_number")

        elif language == 'json':
             apply_regex(r'"[^"]*"(?=\s*:)', "token_keyword")
             apply_regex(r'(?<=:)\s*"[^"]*"', "token_string")
             apply_regex(r'\b\d+\b', "token_number")
             apply_regex(r'\b(true|false|null)\b', "token_keyword")

    def mark_tokens(self, text_widget, tokens):
        index = "1.0"
        for token, value in tokens:
            token_type = str(token)
            end_index = f"{index}+{len(value)}c"
            text_widget.tag_add(token_type, index, end_index)
            index = end_index

    def on_file_select(self, event):
        selected = self.file_tree.selection()
        if not selected: return
        filepath = selected[0]
        self.selected_file = filepath

        # Reset view state on new file selection
        self.is_diff_view = False
        self.diff_view_btn.config(text="Show Diff")
        self.apply_btn.config(state=tk.NORMAL)
        self.prev_change_btn.config(state=tk.DISABLED)
        self.next_change_btn.config(state=tk.DISABLED)
        self.diff_hunks = []
        self.current_hunk_index = -1

        # Detect Language
        language = self.detect_language(filepath)
        self.lang_label.config(text=f"Language: {language.capitalize()}")

        if os.path.isfile(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.orig_text.delete("1.0", tk.END)
                self.orig_text.insert(tk.END, content)
                self.apply_highlighting(self.orig_text, content, language)

                # Check if we have pending changes for this file
                if filepath in self.file_changes:
                    self.ai_text.delete("1.0", tk.END)
                    ai_content = self.file_changes[filepath]
                    self.ai_text.insert(tk.END, ai_content)
                    self.apply_highlighting(self.ai_text, ai_content, language)
                    self.status_label.config(text="Viewing pending changes.")
                else:
                    self.ai_text.delete("1.0", tk.END)
                    self.status_label.config(text="Viewing original file.")
            except Exception as e:
                self.orig_text.delete("1.0", tk.END)
                self.orig_text.insert(tk.END, f"Error reading file: {e}")

    def toggle_diff_view(self):
        if not self.selected_file or self.selected_file not in self.file_changes:
            messagebox.showinfo("Info", "No AI-generated changes available for this file to create a diff.", parent=self)
            return

        self.is_diff_view = not self.is_diff_view

        if self.is_diff_view:
            # Show the diff
            self.diff_view_btn.config(text="Show Code")
            self.apply_btn.config(state=tk.DISABLED)

            original_content = self.orig_text.get("1.0", "end-1c")
            new_content = self.file_changes[self.selected_file]
            self.display_side_by_side_diff(original_content, new_content)

            if self.diff_hunks:
                self.current_hunk_index = 0
                self._go_to_hunk(self.current_hunk_index)
                self._update_navigation_buttons()
        else:
            # Show the full code
            self.diff_view_btn.config(text="Show Diff")
            self.apply_btn.config(state=tk.NORMAL)
            self.prev_change_btn.config(state=tk.DISABLED)
            self.next_change_btn.config(state=tk.DISABLED)
            self.diff_hunks = []
            self.current_hunk_index = -1

            self.ai_text.config(state=tk.NORMAL)
            self.ai_text.delete("1.0", tk.END)
            new_content = self.file_changes[self.selected_file]
            self.ai_text.insert(tk.END, new_content)
            self.apply_highlighting(self.ai_text, new_content, self.detect_language(self.selected_file))

            # Reset Original text tags
            for tag in ["diff_removed", "diff_added", "diff_changed"]:
                self.orig_text.tag_remove(tag, "1.0", tk.END)

            self._unbind_sync_scroll()

    def display_side_by_side_diff(self, original_content, new_content):
        # Configure tags
        self.orig_text.tag_config("diff_removed", background="#ffcccc", foreground="black")
        self.orig_text.tag_config("diff_changed", background="#fff5cc", foreground="black")

        self.ai_text.tag_config("diff_added", background="#ccffcc", foreground="black")
        self.ai_text.tag_config("diff_changed", background="#fff5cc", foreground="black")

        # Update AI text
        self.ai_text.config(state=tk.NORMAL)
        self.ai_text.delete("1.0", tk.END)
        self.ai_text.insert(tk.END, new_content)
        self.apply_highlighting(self.ai_text, new_content, self.detect_language(self.selected_file))

        # Calculate diff
        orig_lines = original_content.splitlines()
        new_lines = new_content.splitlines()

        self.diff_hunks = []

        matcher = difflib.SequenceMatcher(None, orig_lines, new_lines)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                self.orig_text.tag_add("diff_changed", f"{i1+1}.0", f"{i2}.end")
                self.ai_text.tag_add("diff_changed", f"{j1+1}.0", f"{j2}.end")
                self.diff_hunks.append((i1, i2, j1, j2))
            elif tag == 'delete':
                self.orig_text.tag_add("diff_removed", f"{i1+1}.0", f"{i2}.end")
                self.diff_hunks.append((i1, i2, j1, j1)) # j1, j1 for no change in AI side
            elif tag == 'insert':
                self.ai_text.tag_add("diff_added", f"{j1+1}.0", f"{j2}.end")
                self.diff_hunks.append((i1, i1, j1, j2)) # i1, i1 for no change in original side

        self._bind_sync_scroll()

    def _go_to_hunk(self, index):
        if not self.diff_hunks or not (0 <= index < len(self.diff_hunks)):
            return

        orig_start, orig_end, ai_start, ai_end = self.diff_hunks[index]

        # Scroll both text widgets to the start of the hunk
        self.orig_text.see(f"{orig_start+1}.0")
        self.ai_text.see(f"{ai_start+1}.0")

        # Flash the hunk to draw attention
        self._flash_hunk(self.orig_text, f"{orig_start+1}.0", f"{orig_end}.end")
        self._flash_hunk(self.ai_text, f"{ai_start+1}.0", f"{ai_end}.end")

    def _flash_hunk(self, text_widget, start_index, end_index):
        original_bg = text_widget.tag_cget("flash_tag", "background") or text_widget.cget("bg")
        text_widget.tag_configure("flash_tag", background="yellow", foreground="black")
        text_widget.tag_add("flash_tag", start_index, end_index)
        self.after(300, lambda: text_widget.tag_configure("flash_tag", background=original_bg, foreground="black"))
        self.after(600, lambda: text_widget.tag_configure("flash_tag", background="yellow", foreground="black"))
        self.after(900, lambda: text_widget.tag_configure("flash_tag", background=original_bg, foreground="black"))

    def _go_to_next_change(self):
        if not self.diff_hunks: return
        self.current_hunk_index = (self.current_hunk_index + 1) % len(self.diff_hunks)
        self._go_to_hunk(self.current_hunk_index)
        self._update_navigation_buttons()

    def _go_to_prev_change(self):
        if not self.diff_hunks: return
        self.current_hunk_index = (self.current_hunk_index - 1 + len(self.diff_hunks)) % len(self.diff_hunks)
        self._go_to_hunk(self.current_hunk_index)
        self._update_navigation_buttons()

    def _update_navigation_buttons(self):
        if self.is_diff_view and self.diff_hunks:
            self.prev_change_btn.config(state=tk.NORMAL)
            self.next_change_btn.config(state=tk.NORMAL)
        else:
            self.prev_change_btn.config(state=tk.DISABLED)
            self.next_change_btn.config(state=tk.DISABLED)

    def _bind_sync_scroll(self):
        self.orig_editor.vsb.config(command=self._on_scroll_orig)
        self.ai_editor.vsb.config(command=self._on_scroll_ai)
        self.orig_text.bind("<MouseWheel>", self._on_wheel)
        self.ai_text.bind("<MouseWheel>", self._on_wheel)

    def _unbind_sync_scroll(self):
        self.orig_editor.vsb.config(command=self.orig_text.yview)
        self.ai_editor.vsb.config(command=self.ai_text.yview)
        self.orig_text.unbind("<MouseWheel>")
        self.ai_text.unbind("<MouseWheel>")

    def _on_scroll_orig(self, *args):
        self.orig_text.yview(*args)
        self.ai_text.yview(*args)

    def _on_scroll_ai(self, *args):
        self.orig_text.yview(*args)
        self.ai_text.yview(*args)

    def _on_wheel(self, event):
        self.orig_text.yview_scroll(int(-1*(event.delta/120)), "units")
        self.ai_text.yview_scroll(int(-1*(event.delta/120)), "units")
        return "break"

    def find_text(self, event=None):
        """Search text in the active code editor"""
        target = self.orig_text
        if self.is_diff_view:
            target = self.ai_text

        search_str = simpledialog.askstring("Find", "Enter text to search:", parent=self)
        if not search_str: return

        # Clear previous tags
        target.tag_remove('search_match', '1.0', tk.END)

        start = '1.0'
        count = 0
        while True:
            pos = target.search(search_str, start, stopindex=tk.END, nocase=True)
            if not pos: break

            end = f"{pos}+{len(search_str)}c"
            target.tag_add('search_match', pos, end)
            if count == 0:
                target.see(pos)
            start = end
            count += 1

        target.tag_config('search_match', background='yellow', foreground='black')
        if count > 0:
            self.status_label.config(text=f"Found {count} matches.")
        else:
            messagebox.showinfo("Find", "No matches found.", parent=self)

    def send_message(self):
        prompt = self.chat_input.get("1.0", tk.END).strip()
        if not prompt: return

        context = ""
        language = "text"
        if self.selected_file and os.path.isfile(self.selected_file):
            context = self.orig_text.get("1.0", tk.END)
            language = self.detect_language(self.selected_file)

        full_prompt = f"""You are a coding assistant in an IDE.
User Request: {prompt}

Current File Context ({self.selected_file}) [Language: {language}]:
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

        # Update Chat History
        self.chat_history.config(state=tk.NORMAL)
        self.chat_history.insert(tk.END, f"\nYou: {prompt}\n", "user")
        self.chat_history.insert(tk.END, "AI is thinking...\n", "system")
        self.chat_history.config(state=tk.DISABLED)
        self.chat_history.see(tk.END)

        self.thinking_start_time = time.time()
        self.update_thinking_timer()
        self.progress.start(10)
        self.send_btn.config(state=tk.DISABLED)
        self.chat_input.delete("1.0", tk.END)
        threading.Thread(target=self._process_ai_request, args=(full_prompt,), daemon=True).start()

    def _process_ai_request(self, prompt):
        try:
            response = self.chat_client.ask_gemini(prompt)
            self.after(0, self.handle_ai_response, response)
        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Error", str(e)))

    def handle_ai_response(self, response):
        self.thinking_start_time = 0 # Stop timer
        self.progress.stop()
        self.status_label.config(text="Response received.")
        self.send_btn.config(state=tk.NORMAL)

        # Update Chat History (Remove "Thinking..." and add response)
        self.chat_history.config(state=tk.NORMAL)
        # Simple hack: delete last line (Thinking...)
        self.chat_history.delete("end-2l", "end-1c")
        self.chat_history.insert(tk.END, f"AI: {response}\n", "ai")
        self.chat_history.insert(tk.END, "-"*40 + "\n", "system")
        self.chat_history.config(state=tk.DISABLED)
        self.chat_history.see(tk.END)

        # Reset to code view when new response arrives
        self.is_diff_view = False
        self.diff_view_btn.config(text="Show Diff")
        self.apply_btn.config(state=tk.NORMAL)
        self._update_navigation_buttons() # Disable nav buttons if not in diff view

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

            # Automatically show the first changed file if available
            if count > 0 and self.selected_file in self.file_changes:
                self.on_file_select(None)
                messagebox.showinfo("Changes Generated", f"AI suggested changes for {count} file(s).\nReviewing {os.path.basename(self.selected_file)}.")
            elif count > 0:
                messagebox.showinfo("Changes Generated", f"AI suggested changes for {count} file(s).\nSelect red files in the list to review.")


    def update_thinking_timer(self):
        if self.thinking_start_time > 0:
            elapsed = time.time() - self.thinking_start_time
            self.status_label.config(text=f"AI Thinking... ({elapsed:.1f}s)")
            self.after(100, self.update_thinking_timer)

    def apply_current_change(self):
        if not self.selected_file: return

        # Get content from AI text box (allows manual edits)
        new_content = self.ai_text.get("1.0", tk.END).strip()
        if not new_content: return

        self.file_changes[self.selected_file] = new_content

        # Update tree tag to show it's modified in memory
        if self.file_tree.exists(self.selected_file):
            self.file_tree.item(self.selected_file, tags=("changed",))

        messagebox.showinfo("Applied", "Changes staged in memory. Click 'Save All Changes' to write to disk.")

    def revert_current_file(self):
        if self.selected_file and self.selected_file in self.file_changes:
            del self.file_changes[self.selected_file]
            self.file_tree.item(self.selected_file, tags=())
            self.on_file_select(None) # Refresh
            messagebox.showinfo("Reverted", "Changes for this file discarded.")

    def save_all_changes(self):
        if not self.file_changes:
            messagebox.showinfo("Info", "No changes to save.")
            return

        if messagebox.askyesno("Save All", f"Write changes to {len(self.file_changes)} files?"):
            try:
                for filepath, content in self.file_changes.items():
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.file_tree.item(filepath, tags=()) # Remove tag

                self.file_changes.clear()
                self.on_file_select(None) # Refresh view
                messagebox.showinfo("Success", "All files updated.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def reset_all_changes(self):
        if messagebox.askyesno("Reset", "Discard all pending changes?"):
            self.file_changes.clear()
            for item in self.file_tree.get_children():
                self.file_tree.item(item, tags=())
            self.on_file_select(None)

    def format_code(self):
        if not self.selected_file:
            return

        content = self.orig_text.get("1.0", tk.END).strip()
        if not content: return

        ext = os.path.splitext(self.selected_file)[1].lower()
        formatted = None
        error = None

        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            if ext in ['.py', '.pyw']:
                cmd = ['black', '-', '-q']
                res = subprocess.run(cmd, input=content, capture_output=True, text=True, encoding='utf-8', startupinfo=startupinfo)
                if res.returncode == 0: formatted = res.stdout
                else: error = res.stderr
            elif ext in ['.js', '.ts', '.jsx', '.tsx', '.json', '.html', '.css']:
                cmd = ['npx.cmd' if os.name == 'nt' else 'npx', 'prettier', '--stdin-filepath', self.selected_file]
                res = subprocess.run(cmd, input=content, capture_output=True, text=True, encoding='utf-8', startupinfo=startupinfo)
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
