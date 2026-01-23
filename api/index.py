import os
import sys

# Add the project root to sys.path so we can import backend.py
# This assumes api/index.py is one level deep from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import app

# This is the entry point for Vercel Serverless Functions
