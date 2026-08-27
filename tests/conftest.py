"""Pytest shared fixtures and test environment isolation."""

from __future__ import annotations

import os
from collections.abc import Generator
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def isolate_test_environment() -> Generator[None, None, None]:
    """Ensure test suite runs in deterministic, isolated offline mode by default."""
    test_env = {
        "TESTING": "1",
        "USE_LOCAL_SQLITE": "1",
        "OPENROUTER_API_KEY": "",
        "GEMINI_API_KEY": "",
        "GOOGLE_API_KEY": "",
        "OPENAI_API_KEY": "",
        "LLM_API_KEY": "",
    }
    with patch.dict(os.environ, test_env, clear=False):
        yield
