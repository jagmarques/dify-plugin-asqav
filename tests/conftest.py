"""Shared test fixtures for the Asqav Dify plugin smoke tests.

These tests exercise the plugin's pure Python surface (credential validation,
request body construction, error mapping) without booting the full Dify runtime.
Network calls into the Asqav cloud are always mocked.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

# Make the repo root importable so `provider.asqav` and `tools.*` resolve
# the same way they would inside the Dify runner.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def valid_credentials() -> dict[str, Any]:
    return {
        "asqav_api_key": "sk_test_1234567890abcdef",
        "asqav_agent_id": "agent_test_abc123",
    }


class _FakeResponse:
    """Minimal httpx.Response stand-in for smoke tests."""

    def __init__(self, status_code: int = 200, json_data: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._json = json_data or {}

    def json(self) -> dict[str, Any]:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=None,  # type: ignore[arg-type]
                response=None,  # type: ignore[arg-type]
            )


@pytest.fixture
def fake_response_factory():
    """Return a factory that builds fake httpx.Response objects."""

    def _make(status_code: int = 200, json_data: dict[str, Any] | None = None) -> _FakeResponse:
        return _FakeResponse(status_code=status_code, json_data=json_data)

    return _make
