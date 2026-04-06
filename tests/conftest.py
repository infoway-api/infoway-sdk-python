import pytest

API_KEY = "test-api-key-for-unit-tests"

@pytest.fixture
def api_key():
    return API_KEY
