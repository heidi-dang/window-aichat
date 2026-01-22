"""
Centralized theme management for the application.
Provides a consistent way to manage and apply themes across the UI.
"""
import tkinter as tk
from typing import Dict, Optional
import logging

logger = logging.getLogger('ui.theme_manager')


class ThemeManager:
    """Manages application themes with support for multiple theme presets."""
    
    THEMES = {
        "Dark": {
            "bg": "#161616",
            "sidebar": "#1E1E1E",
            "chat_bg": "#000000",
            "input_bg": "#2C2C2C",
            "fg": "#EEEEEE",
            "fg_dim": "#9E9E9E",
            "accent": "#6210CC",
            "accent_hover": "#7B2FDD",
            "user_bubble": "#6210CC",
            "ai_bubble": "#2C2C2C",
            "border": "#333333"
        },
        "Light": {
            "bg": "#f0f0f0",
            "sidebar": "#e0e0e0",
            "chat_bg": "#ffffff",
            "input_bg": "#ffffff",
            "fg": "#000000",
            "fg_dim": "#7f8c8d",
            "accent": "#3498db",
            "accent_hover": "#2980b9",
            "user_bubble": "#3498db",
            "ai_bubble": "#ecf0f1",
            "border": "#bdc3c7"
        },
        "Blue": {
            "bg": "#2c3e50",
            "sidebar": "#34495e",
            "chat_bg": "#ecf0f1",
            "input_bg": "#ffffff",
            "fg": "#2c3e50",
            "fg_dim": "#95a5a6",
            "accent": "#e74c3c",
            "accent_hover": "#c0392b",
            "user_bubble": "#e74c3c",
            "ai_bubble": "#bdc3c7",
            "border": "#7f8c8d"
        },
        "Green": {
            "bg": "#1a1a1a",
            "sidebar": "#2a2a2a",
            "chat_bg": "#0a0a0a",
            "input_bg": "#3a3a3a",
            "fg": "#e0e0e0",
            "fg_dim": "#888888",
            "accent": "#27ae60",
            "accent_hover": "#2ecc71",
            "user_bubble": "#27ae60",
            "ai_bubble": "#2a2a2a",
            "border": "#444444"
        }
    }
    
    def __init__(self, default_theme: str = "Dark"):
        self.current_theme = default_theme
        self.colors = self.THEMES.get(default_theme, self.THEMES["Dark"]).copy()
        logger.info(f"ThemeManager initialized with theme: {default_theme}")
    
    def get_theme(self, theme_name: str) -> Optional[Dict[str, str]]:
        """Get a theme by name."""
        return self.THEMES.get(theme_name.capitalize())
    
    def list_themes(self) -> list:
        """List all available theme names."""
        return list(self.THEMES.keys())
    
    def set_theme(self, theme_name: str) -> bool:
        """Set the current theme."""
        theme = self.get_theme(theme_name)
        if theme:
            self.current_theme = theme_name.capitalize()
            self.colors = theme.copy()
            logger.info(f"Theme changed to: {self.current_theme}")
            return True
        logger.warning(f"Theme not found: {theme_name}")
        return False
    
    def get_color(self, color_key: str) -> str:
        """Get a color value by key."""
        return self.colors.get(color_key, "#000000")
    
    def apply_ttk_styles(self, style: tk.ttk.Style):
        """Apply the current theme to ttk styles."""
        try:
            style.theme_use('clam')
        except:
            pass
        
        # Configure TTK styles
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("Sidebar.TFrame", background=self.colors["sidebar"])
        
        style.configure("TLabel", 
                       background=self.colors["bg"], 
                       foreground=self.colors["fg"], 
                       font=("Segoe UI", 10))
        style.configure("Sidebar.TLabel", 
                       background=self.colors["sidebar"], 
                       foreground=self.colors["fg"])
        style.configure("Header.TLabel", 
                       background=self.colors["sidebar"], 
                       foreground=self.colors["fg"], 
                       font=("Segoe UI", 12, "bold"))
        
        style.configure("TButton", 
            background=self.colors["accent"], 
            foreground="white", 
            borderwidth=0, 
            font=("Segoe UI", 9, "bold"),
            padding=5
        )
        style.map("TButton", 
            background=[("active", self.colors["accent_hover"])],
            foreground=[("active", "white")]
        )
        
        style.configure("Secondary.TButton",
            background=self.colors["input_bg"],
            foreground=self.colors["fg"],
            borderwidth=0,
            font=("Segoe UI", 9),
            padding=5
        )
        style.map("Secondary.TButton",
            background=[("active", "#3D3D3D" if self.current_theme == "Dark" else "#e0e0e0")]
        )

        style.configure("Treeview", 
            background=self.colors["input_bg"], 
            foreground=self.colors["fg"], 
            fieldbackground=self.colors["input_bg"], 
            borderwidth=0,
            font=("Segoe UI", 9)
        )
        style.map("Treeview", background=[("selected", self.colors["accent"])])
        
        style.configure("TCombobox", 
            fieldbackground=self.colors["input_bg"], 
            background=self.colors["sidebar"], 
            foreground=self.colors["fg"], 
            arrowcolor=self.colors["fg"],
            borderwidth=0
        )
        
        style.configure("TPanedwindow", background=self.colors["bg"])
        style.configure("Sash", background=self.colors["border"], sashthickness=2)
        
        style.configure("Horizontal.TProgressbar", 
                       background=self.colors["accent"], 
                       troughcolor=self.colors["input_bg"], 
                       borderwidth=0)
