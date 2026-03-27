"""Vercel serverless entry point — wraps the FastAPI app."""
import sys
import os

# Add backend directory to Python path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend')
sys.path.insert(0, backend_dir)

# Signal to database.py to use /tmp for SQLite
os.environ.setdefault('VERCEL', '1')

from main import app  # noqa: E402, F401
