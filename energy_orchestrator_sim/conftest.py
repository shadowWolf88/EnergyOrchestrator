"""
Pytest configuration and fixtures.
"""

import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

import pytest
import logging

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)


@pytest.fixture(scope="session")
def temp_dir(tmp_path_factory):
    """Provide temporary directory for test outputs."""
    return tmp_path_factory.mktemp("outputs")
