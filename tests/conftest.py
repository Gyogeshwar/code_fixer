"""Pytest configuration for code-fixer tests."""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def tmp_path():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)
