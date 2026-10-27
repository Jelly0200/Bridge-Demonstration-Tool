# config/settings.py
import os

# Project root directory.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Default database path.
DB_PATH = os.path.join(BASE_DIR, "bridge_tool.db")