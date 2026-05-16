"""Offline quickstart demo for hermes-azure-files.

This is a fully offline demo:
- It calls get_credential() to show what credential type would be used.
- It then patches blob.get_blob_service_client with a MagicMock so that
  blob_list_handler runs without any real Azure account, and prints the
  fake JSON response.

No network access or real Azure credentials are required.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

# Allow running directly from a source checkout without `pip install -e .`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hermes_azure_files.auth import get_credential
from hermes_azure_files import blob


def demo_credential() -> None:
    print("=== get_credential() ===")
    try:
        cred = get_credential()
        print(f"credential type: {type(cred).__name__}")
    except Exception as exc:  # noqa: BLE001
        print(f"credential unavailable (expected offline): {exc}")


def demo_blob_list() -> None:
    print("\n=== blob_list (mocked) ===")

    fake_blob = MagicMock()
    fake_blob.name = "hello.txt"
    fake_blob.size = 1234
    fake_blob.last_modified = datetime(2025, 1, 1, 12, 0, 0)

    fake_container = MagicMock()
    fake_container.list_blobs.return_value = iter([fake_blob])

    fake_service = MagicMock()
    fake_service.get_container_client.return_value = fake_container

    with patch.object(blob, "get_blob_service_client", return_value=fake_service):
        result = blob.blob_list_handler(
            {"account_name": "demoacct", "container_name": "demo"}
        )

    print(json.dumps(json.loads(result), indent=2))


def main() -> None:
    demo_credential()
    demo_blob_list()


if __name__ == "__main__":
    main()
