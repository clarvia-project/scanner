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

# Store admin API key for tests that need authenticated write access
# pydantic-settings reads from .env file, not just os.environ
from app.config import settings as _settings
TEST_ADMIN_API_KEY = _settings.admin_api_key


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests that load large data files (deselect with -m 'not slow')")
