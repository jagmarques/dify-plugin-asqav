"""Smoke tests for the Asqav Dify plugin provider.

Scope: import safety, credential validation paths, and HTTP error mapping.
Out of scope: any real Dify runtime behavior or live Asqav API calls.
"""

from __future__ import annotations

from typing import Any

import pytest
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from provider.asqav import AsqavProvider


def test_provider_module_imports() -> None:
    """The provider module loads and exposes the expected class."""
    from provider import asqav as provider_module

    assert hasattr(provider_module, "AsqavProvider")
    assert issubclass(provider_module.AsqavProvider, object)


def test_provider_accepts_well_formed_credentials(
    mocker, valid_credentials: dict[str, Any], fake_response_factory
) -> None:
    """A well-formed sk_ API key + agent_ ID should pass validation when the
    cloud returns 200."""
    mocker.patch(
        "provider.asqav.httpx.get",
        return_value=fake_response_factory(status_code=200, json_data={"id": "agent_test_abc123"}),
    )

    provider = AsqavProvider()
    # Should not raise.
    provider._validate_credentials(valid_credentials)


def test_provider_rejects_missing_api_key() -> None:
    """An empty API key is rejected before any HTTP call is attempted."""
    provider = AsqavProvider()
    with pytest.raises(ToolProviderCredentialValidationError, match="API key"):
        provider._validate_credentials({"asqav_api_key": "", "asqav_agent_id": "agent_x"})


def test_provider_rejects_missing_agent_id() -> None:
    """An empty agent ID is rejected before any HTTP call is attempted."""
    provider = AsqavProvider()
    with pytest.raises(ToolProviderCredentialValidationError, match="Agent ID"):
        provider._validate_credentials({"asqav_api_key": "sk_test_x", "asqav_agent_id": ""})


def test_provider_rejects_invalid_api_key_via_401(
    mocker, valid_credentials: dict[str, Any], fake_response_factory
) -> None:
    """A 401 from the cloud surfaces as Invalid API key."""
    mocker.patch(
        "provider.asqav.httpx.get",
        return_value=fake_response_factory(status_code=401),
    )

    provider = AsqavProvider()
    with pytest.raises(ToolProviderCredentialValidationError, match="Invalid API key"):
        provider._validate_credentials(valid_credentials)


def test_provider_rejects_unknown_agent_via_404(
    mocker, valid_credentials: dict[str, Any], fake_response_factory
) -> None:
    """A 404 from the cloud surfaces as Agent not found."""
    mocker.patch(
        "provider.asqav.httpx.get",
        return_value=fake_response_factory(status_code=404),
    )

    provider = AsqavProvider()
    with pytest.raises(ToolProviderCredentialValidationError, match="Agent not found"):
        provider._validate_credentials(valid_credentials)


def test_provider_wraps_network_failure(mocker, valid_credentials: dict[str, Any]) -> None:
    """Arbitrary transport failures are wrapped in the Dify credential error
    type so the UI can render them properly."""
    import httpx

    mocker.patch(
        "provider.asqav.httpx.get",
        side_effect=httpx.ConnectError("connection refused"),
    )

    provider = AsqavProvider()
    with pytest.raises(ToolProviderCredentialValidationError, match="Failed to validate"):
        provider._validate_credentials(valid_credentials)
