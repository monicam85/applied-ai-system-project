import pytest


@pytest.fixture(autouse=True)
def no_live_api_key(monkeypatch):
    """Tests must be offline and deterministic: a developer's real ANTHROPIC_API_KEY must never reach them."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
