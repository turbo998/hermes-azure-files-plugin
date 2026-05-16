"""Azure Blob Storage tool handlers for hermes-azure-files-plugin.

Provides three tool handlers (upload / download / list) backed by
``azure-storage-blob``. All handlers accept a single ``args`` dict and
return a JSON string with either a success payload or ``{error, hint}``.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def get_blob_service_client(
    account_name: str,
    auth: str = "default",
    api_key: Optional[str] = None,
) -> BlobServiceClient:
    """Return a :class:`BlobServiceClient` for ``account_name``.

    Tests typically monkeypatch this function to inject a ``MagicMock``.
    """
    account_url = f"https://{account_name}.blob.core.windows.net"
    if auth == "default":
        return BlobServiceClient(account_url, credential=DefaultAzureCredential())
    if auth == "account_key":
        if not api_key:
            raise ValueError("auth='account_key' requires api_key")
        return BlobServiceClient(account_url, credential=api_key)
    raise ValueError(f"unknown auth: {auth!r} (expected 'default' or 'account_key')")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _err(error: str, hint: str = "") -> str:
    return json.dumps({"error": error, "hint": hint})


def _require(args: Dict[str, Any], *keys: str) -> Optional[str]:
    missing = [k for k in keys if not args.get(k)]
    if missing:
        return f"missing required argument(s): {', '.join(missing)}"
    return None


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
def blob_upload_handler(args: Dict[str, Any], **kwargs: Any) -> str:
    err = _require(args, "account_name", "container_name", "local_path")
    if err:
        return _err(err, "provide account_name, container_name and local_path")

    account_name = args["account_name"]
    container_name = args["container_name"]
    local_path = args["local_path"]
    blob_name = args.get("blob_name") or os.path.basename(local_path)
    overwrite = bool(args.get("overwrite", False))
    auth = args.get("auth", "default")
    api_key = args.get("api_key")

    if not os.path.isfile(local_path):
        return _err(
            f"local file not found: {local_path}",
            "verify local_path exists and is readable",
        )

    try:
        service = get_blob_service_client(account_name, auth=auth, api_key=api_key)
        container = service.get_container_client(container_name)
        size = os.path.getsize(local_path)
        with open(local_path, "rb") as fh:
            container.upload_blob(name=blob_name, data=fh, overwrite=overwrite)
    except Exception as exc:  # noqa: BLE001 — surface to caller
        return _err(
            f"upload failed: {exc}",
            "check container exists, credentials, and overwrite flag",
        )

    return json.dumps(
        {
            "success": True,
            "message": f"uploaded {local_path} -> {container_name}/{blob_name}",
            "account": account_name,
            "container": container_name,
            "blob": blob_name,
            "size_bytes": size,
        }
    )


def blob_download_handler(args: Dict[str, Any], **kwargs: Any) -> str:
    err = _require(args, "account_name", "container_name", "blob_name", "local_path")
    if err:
        return _err(err, "provide account_name, container_name, blob_name, local_path")

    account_name = args["account_name"]
    container_name = args["container_name"]
    blob_name = args["blob_name"]
    local_path = args["local_path"]
    auth = args.get("auth", "default")
    api_key = args.get("api_key")

    try:
        service = get_blob_service_client(account_name, auth=auth, api_key=api_key)
        container = service.get_container_client(container_name)
        downloader = container.download_blob(blob_name)
        data = downloader.readall()
        parent = os.path.dirname(os.path.abspath(local_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(local_path, "wb") as fh:
            fh.write(data)
    except Exception as exc:  # noqa: BLE001
        return _err(
            f"download failed: {exc}",
            "check blob exists and credentials are valid",
        )

    return json.dumps(
        {
            "success": True,
            "message": f"downloaded {container_name}/{blob_name} -> {local_path}",
            "local_path": local_path,
            "size_bytes": len(data),
        }
    )


def blob_list_handler(args: Dict[str, Any], **kwargs: Any) -> str:
    err = _require(args, "account_name", "container_name")
    if err:
        return _err(err, "provide account_name and container_name")

    account_name = args["account_name"]
    container_name = args["container_name"]
    prefix = args.get("prefix")
    try:
        max_results = int(args.get("max_results", 100))
    except (TypeError, ValueError):
        max_results = 100
    max_results = max(1, min(1000, max_results))

    auth = args.get("auth", "default")
    api_key = args.get("api_key")

    try:
        service = get_blob_service_client(account_name, auth=auth, api_key=api_key)
        container = service.get_container_client(container_name)
        iterator = container.list_blobs(
            name_starts_with=prefix, results_per_page=max_results
        )
        collected = []
        has_more = False
        for i, item in enumerate(iterator):
            if i >= max_results:
                has_more = True
                break
            lm = getattr(item, "last_modified", None)
            collected.append(
                {
                    "name": getattr(item, "name", None),
                    "size": getattr(item, "size", None),
                    "last_modified": lm.isoformat() if hasattr(lm, "isoformat") else lm,
                }
            )
    except Exception as exc:  # noqa: BLE001
        return _err(
            f"list failed: {exc}",
            "check container exists and credentials are valid",
        )

    return json.dumps(
        {
            "success": True,
            "blobs": collected,
            "count": len(collected),
            "has_more": has_more,
        }
    )


# ---------------------------------------------------------------------------
# OpenAI function schemas
# ---------------------------------------------------------------------------
BLOB_UPLOAD_SCHEMA = {
    "type": "function",
    "function": {
        "name": "blob_upload",
        "description": "Upload a local file to an Azure Blob Storage container.",
        "parameters": {
            "type": "object",
            "properties": {
                "account_name": {"type": "string", "description": "Storage account name."},
                "container_name": {"type": "string", "description": "Target container name."},
                "local_path": {"type": "string", "description": "Path to the local file to upload."},
                "blob_name": {
                    "type": "string",
                    "description": "Destination blob name. Defaults to basename(local_path).",
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "Overwrite an existing blob with the same name.",
                    "default": False,
                },
                "auth": {
                    "type": "string",
                    "enum": ["default", "account_key"],
                    "default": "default",
                },
                "api_key": {
                    "type": "string",
                    "description": "Storage account key (required when auth='account_key').",
                },
            },
            "required": ["account_name", "container_name", "local_path"],
        },
    },
}

BLOB_DOWNLOAD_SCHEMA = {
    "type": "function",
    "function": {
        "name": "blob_download",
        "description": "Download a blob from Azure Blob Storage to a local file path.",
        "parameters": {
            "type": "object",
            "properties": {
                "account_name": {"type": "string"},
                "container_name": {"type": "string"},
                "blob_name": {"type": "string"},
                "local_path": {
                    "type": "string",
                    "description": "Destination file path; parent directories will be created.",
                },
                "auth": {
                    "type": "string",
                    "enum": ["default", "account_key"],
                    "default": "default",
                },
                "api_key": {"type": "string"},
            },
            "required": ["account_name", "container_name", "blob_name", "local_path"],
        },
    },
}

BLOB_LIST_SCHEMA = {
    "type": "function",
    "function": {
        "name": "blob_list",
        "description": "List blobs in an Azure Blob Storage container.",
        "parameters": {
            "type": "object",
            "properties": {
                "account_name": {"type": "string"},
                "container_name": {"type": "string"},
                "prefix": {
                    "type": "string",
                    "description": "Only return blobs whose names start with this prefix.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of blobs to return (1-1000, default 100).",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000,
                },
                "auth": {
                    "type": "string",
                    "enum": ["default", "account_key"],
                    "default": "default",
                },
                "api_key": {"type": "string"},
            },
            "required": ["account_name", "container_name"],
        },
    },
}
