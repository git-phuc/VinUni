"""Pytest bootstrap: load .env before test modules are collected.

`test_graph_smoke.py` evaluates `pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), ...)`
at import time, so the API key must be in the environment *before* collection. conftest.py is
imported by pytest before any test module, making this the correct place to load .env.
"""

from __future__ import annotations

try:
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
except ImportError:
    pass
