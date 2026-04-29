# conftest.py — root level
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "cars: Tests for Cars master data")
    config.addinivalue_line("markers", "slow: Slow integration tests")
