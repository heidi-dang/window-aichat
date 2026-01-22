"""
Basic markdown renderer for chat display.
Supports common markdown features like bold, italic, code blocks, etc.
"""
import re
import logging
import tkinter as tk

logger = logging.getLogger('ui.markdown_renderer')


class MarkdownRenderer:
    """Renders markdown text in Tkinter Text widgets."""
    
    def __init__(self, text_widget: tk.Text):
        self.text_widget = text_widget
        self._setup_tags()
    
    def _setup_tags(self):
        """Setup text tags for markdown formatting."""
        # Bold text
        self.text_widget.tag_config("bold", font=("Segoe UI", 10, "bold"))
        
        # Italic text
        self.text_widget.tag_config("italic", font=("Segoe UI", 10, "italic"))
        
        # Code inline
        self.text_widget.tag_config("code_inline", 
                                   background="#2a2a2a", 
                                   foreground="#a8d8ff",
                                   font=("Consolas", 9))
        
        # Code block
        self.text_widget.tag_config("code_block",
                                   background="#1a1a1a",
                                   foreground="#a8d8ff",
                                   font=("Consolas", 9),
                                   lmargin1=20,
                                   lmargin2=20,
                                   rmargin=20)
        
        # Links (styled but not clickable in basic implementation)
        self.text_widget.tag_config("link", foreground="#4a9eff", underline=True)
        
        # Headers
        self.text_widget.tag_config("h1", font=("Segoe UI", 14, "bold"))
        self.text_widget.tag_config("h2", font=("Segoe UI", 12, "bold"))
        self.text_widget.tag_config("h3", font=("Segoe UI", 11, "bold"))
        
        # Lists
        self.text_widget.tag_config("list_item", lmargin1=20, lmargin2=30)
    
    def render(self, markdown_text: str, start_index: str = "1.0", base_tag: str = None):
        """Render markdown text into the text widget."""
        # Split by code blocks first (they need special handling)
        parts = re.split(r'(```[\s\S]*?```)', markdown_text)
        
        current_pos = start_index
        
        for part in parts:
            if part.startswith('```'):
                # Code block
                code_content = part[3:-3].strip()  # Remove ``` markers
                lang_match = re.match(r'^(\w+)\n', code_content)
                if lang_match:
                    code_content = code_content[len(lang_match.group(0)):]
                
                # Insert code block (combine with base tag if provided)
                tags = ["code_block"]
                if base_tag:
                    tags.append(base_tag)
                self.text_widget.insert(current_pos, code_content, tuple(tags))
                self.text_widget.insert(current_pos, "\n")
                current_pos = self.text_widget.index(f"{current_pos}+1c")
            else:
                # Regular markdown text
                current_pos = self._render_inline_markdown(part, current_pos, base_tag)
    
    def _render_inline_markdown(self, text: str, start_pos: str, base_tag: str = None) -> str:
        """Render inline markdown (bold, italic, code, links)."""
        # Process code spans first (to avoid conflicts with other patterns)
        text_parts = re.split(r'(`[^`]+`)', text)
        current_pos = start_pos
        
        for part in text_parts:
            if part.startswith('`') and part.endswith('`'):
                # Inline code
                code_text = part[1:-1]
                tags = ["code_inline"]
                if base_tag:
                    tags.append(base_tag)
                self.text_widget.insert(current_pos, code_text, tuple(tags))
                current_pos = self.text_widget.index(f"{current_pos}+{len(code_text)}c")
            else:
                # Process other markdown in this part
                current_pos = self._render_text_with_formatting(part, current_pos, base_tag)
        
        return current_pos
    
    def _render_text_with_formatting(self, text: str, start_pos: str, base_tag: str = None) -> str:
        """Render text with bold, italic, and links."""
        # Pattern to match markdown: **bold**, *italic*, [link](url), # headers, - lists
        # We'll process in order: headers, lists, bold, italic, links
        
        # Headers
        if text.strip().startswith('#'):
            header_match = re.match(r'^(#{1,3})\s+(.+)$', text.strip())
            if header_match:
                level = len(header_match.group(1))
                content = header_match.group(2)
                tags = [f"h{level}"]
                if base_tag:
                    tags.append(base_tag)
                self.text_widget.insert(start_pos, content, tuple(tags))
                self.text_widget.insert(start_pos, "\n")
                return self.text_widget.index(f"{start_pos}+1c")
        
        # Lists
        if text.strip().startswith('- ') or text.strip().startswith('* '):
            content = text.strip()[2:]
            tags = ["list_item"]
            if base_tag:
                tags.append(base_tag)
            self.text_widget.insert(start_pos, "• ", tuple(tags))
            if base_tag:
                self.text_widget.insert(start_pos, content, base_tag)
            else:
                self.text_widget.insert(start_pos, content)
            self.text_widget.insert(start_pos, "\n")
            return self.text_widget.index(f"{start_pos}+1c")
        
        # Process bold and italic (simplified - doesn't handle nested)
        # Split by **bold** and *italic*
        parts = re.split(r'(\*\*[^*]+\*\*|\*[^*]+\*)', text)
        current_pos = start_pos
        
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                # Bold
                bold_text = part[2:-2]
                tags = ["bold"]
                if base_tag:
                    tags.append(base_tag)
                self.text_widget.insert(current_pos, bold_text, tuple(tags))
                current_pos = self.text_widget.index(f"{current_pos}+{len(bold_text)}c")
            elif part.startswith('*') and part.endswith('*') and len(part) > 2:
                # Italic
                italic_text = part[1:-1]
                tags = ["italic"]
                if base_tag:
                    tags.append(base_tag)
                self.text_widget.insert(current_pos, italic_text, tuple(tags))
                current_pos = self.text_widget.index(f"{current_pos}+{len(italic_text)}c")
            else:
                # Regular text - also check for links
                link_parts = re.split(r'(\[[^\]]+\]\([^\)]+\))', part)
                for link_part in link_parts:
                    link_match = re.match(r'\[([^\]]+)\]\(([^\)]+)\)', link_part)
                    if link_match:
                        link_text = link_match.group(1)
                        link_url = link_match.group(2)
                        tags = ["link"]
                        if base_tag:
                            tags.append(base_tag)
                        self.text_widget.insert(current_pos, link_text, tuple(tags))
                        current_pos = self.text_widget.index(f"{current_pos}+{len(link_text)}c")
                    else:
                        if base_tag:
                            self.text_widget.insert(current_pos, link_part, base_tag)
                        else:
                            self.text_widget.insert(current_pos, link_part)
                        current_pos = self.text_widget.index(f"{current_pos}+{len(link_part)}c")
        
        return current_pos
