import os
import sys

# Ensure backend directory is in python search path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
backend_dir = os.path.join(project_dir, "backend")

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from database import DB_PATH, init_db
from seed_data import seed_database

# Auto-seed database if running on a fresh cloud container / /tmp
if not os.path.exists(DB_PATH):
    try:
        seed_database()
    except Exception as e:
        print(f"Cloud initialization note: {e}")

from app import app
