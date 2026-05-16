"""Tests for hermes_azure_files.auth.get_credential."""
from __future__ import annotations

import pytest
from azure.identity import DefaultAzureCredential

from hermes_azure_files.auth import get_credential


def test_default_mode_returns_default_azure_credential():
    cred = get_credential(mode="default")
    assert isinstance(cred, DefaultAzureCredential)


def test_key_mode_returns_account_and_key_tuple():
    cred = get_credential(mode="key", account="myacct", api_key="secret123")
    assert cred == ("myacct", "secret123")


def test_key_mode_missing_args_raises_value_error():
    with pytest.raises(ValueError):
        get_credential(mode="key", account="only-account")
    with pytest.raises(ValueError):
        get_credential(mode="key", api_key="only-key")
    with pytest.raises(ValueError):
        get_credential(mode="key")
