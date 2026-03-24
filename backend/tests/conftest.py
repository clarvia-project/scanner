"""Pytest configuration for Clarvia backend tests."""

import os
import sys
from pathlib import Path

# Ensure the backend package is importable
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Override env vars for testing
os.environ.setdefault("SCANNER_PORT", "8099")
os.environ.setdefault("SCANNER_SUPABASE_URL", "")
os.environ.setdefault("SCANNER_SUPABASE_ANON_KEY", "")
os.environ.setdefault("SCANNER_STRIPE_SECRET_KEY", "")
