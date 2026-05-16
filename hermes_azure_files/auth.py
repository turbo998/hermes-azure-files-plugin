"""Azure authentication helpers for hermes-azure-files-plugin.

Two modes are supported:

* ``"default"`` — returns a :class:`azure.identity.DefaultAzureCredential`
  instance suitable for use with the Azure SDK clients. Picks up Managed
  Identity, ``az login``, env-var credentials, etc.
* ``"key"``    — returns a ``(account, account_key)`` tuple for use with
  shared-key auth (e.g. ``BlobServiceClient(account_url, credential=key)``).

Connection strings are intentionally not handled here to discourage embedding
secrets in config files.
"""
from __future__ import annotations

from typing import Optional, Tuple, Union

from azure.identity import DefaultAzureCredential


CredentialResult = Union[DefaultAzureCredential, Tuple[str, str]]


def get_credential(
    mode: str = "default",
    api_key: Optional[str] = None,
    account: Optional[str] = None,
) -> CredentialResult:
    """Return an Azure credential according to ``mode``.

    Parameters
    ----------
    mode:
        ``"default"`` (recommended) or ``"key"``.
    api_key:
        Storage account key. Required when ``mode == "key"``.
    account:
        Storage account name. Required when ``mode == "key"``.

    Returns
    -------
    DefaultAzureCredential | tuple[str, str]
        Either a credential object or an ``(account, api_key)`` tuple.

    Raises
    ------
    ValueError
        If an unknown mode is given, or if ``mode="key"`` is selected without
        both ``account`` and ``api_key``.
    """
    if mode == "default":
        return DefaultAzureCredential()

    if mode == "key":
        if not account or not api_key:
            raise ValueError(
                "mode='key' requires both 'account' and 'api_key' arguments"
            )
        return (account, api_key)

    raise ValueError(f"unknown auth mode: {mode!r} (expected 'default' or 'key')")
