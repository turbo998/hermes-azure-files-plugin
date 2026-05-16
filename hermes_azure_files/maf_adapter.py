"""Microsoft Agent Framework (MAF) adapter for hermes-azure-files-plugin.

This is an *additive* layer: it wraps the existing handler functions in
`mount.py` / `blob.py` as MAF `FunctionTool` instances suitable for passing
to `agent_framework.ChatAgent(tools=...)`.

Usage::

    from hermes_azure_files.maf_adapter import get_maf_tools
    from agent_framework import ChatAgent

    agent = ChatAgent(chat_client=..., tools=get_maf_tools())

The optional dependency `agent-framework-core>=1.4.0` must be installed::

    pip install hermes-azure-files-plugin[maf]
"""
from __future__ import annotations

import json
from typing import Any, Optional

try:  # pragma: no cover - import guard
    import agent_framework as af  # type: ignore
    _MAF_AVAILABLE = True
    _MAF_IMPORT_ERROR: Optional[BaseException] = None
except Exception as _exc:  # pragma: no cover
    af = None  # type: ignore
    _MAF_AVAILABLE = False
    _MAF_IMPORT_ERROR = _exc


def _parse(result: Any) -> dict:
    """Underlying handlers return JSON strings; convert to dict for MAF."""
    if isinstance(result, dict):
        return result
    if isinstance(result, (str, bytes, bytearray)):
        try:
            return json.loads(result)
        except Exception:
            return {"raw": result if isinstance(result, str) else result.decode("utf-8", "replace")}
    return {"result": result}


def get_maf_tools() -> list:
    """Return all 7 Azure-files tools as MAF `FunctionTool` instances.

    Raises:
        RuntimeError: if `agent-framework-core` is not installed. Install via
            ``pip install hermes-azure-files-plugin[maf]``.
    """
    if not _MAF_AVAILABLE:
        raise RuntimeError(
            "agent-framework is not installed. Install with: "
            "pip install hermes-azure-files-plugin[maf]"
        ) from _MAF_IMPORT_ERROR

    # ── mount ────────────────────────────────────────────────────────────
    @af.tool(
        name="azurefiles_mount",
        description=(
            "Mount an Azure Blob container or Azure Files share as a local "
            "directory via BlobFuse2 (default) or NFS v4.1."
        ),
    )
    def azurefiles_mount(
        account_name: str,
        container_name: str,
        mount_path: Optional[str] = None,
        mode: str = "blobfuse2",
        auth: str = "managed_identity",
    ) -> dict:
        """Mount an Azure Blob container / Files share locally.

        Args:
            account_name: Azure storage account name (e.g. 'mystorageacct').
            container_name: Blob container or file share name.
            mount_path: Local mount path. Defaults to
                /mnt/azurefiles/<account>/<container>.
            mode: Mount driver: 'blobfuse2' (default), 'nfs', or 'smb'.
            auth: Auth mode. Only 'managed_identity' supported.
        """
        from .mount import azurefiles_mount_handler
        args = {
            "account_name": account_name,
            "container_name": container_name,
            "mode": mode,
            "auth": auth,
        }
        if mount_path is not None:
            args["mount_path"] = mount_path
        return _parse(azurefiles_mount_handler(args))

    @af.tool(
        name="azurefiles_unmount",
        description="Unmount an Azure Files / BlobFuse2 mount point.",
    )
    def azurefiles_unmount(mount_path: str) -> dict:
        """Unmount the given local mount path.

        Args:
            mount_path: The local mount path to unmount.
        """
        from .mount import azurefiles_unmount_handler
        return _parse(azurefiles_unmount_handler({"mount_path": mount_path}))

    @af.tool(
        name="azurefiles_status",
        description="List currently mounted Azure-files / BlobFuse2 mounts.",
    )
    def azurefiles_status() -> dict:
        """Return information about all currently mounted Azure-files mounts."""
        from .mount import azurefiles_status_handler
        return _parse(azurefiles_status_handler({}))

    @af.tool(
        name="azurefiles_setup",
        description=(
            "Verify (and install if missing) prerequisites for Azure Files "
            "mounts: az CLI, BlobFuse2, and the default mount directory."
        ),
    )
    def azurefiles_setup() -> dict:
        """Verify and install prerequisites for mounting Azure storage."""
        from .mount import azurefiles_setup_handler
        return _parse(azurefiles_setup_handler({}))

    # ── blob ─────────────────────────────────────────────────────────────
    @af.tool(
        name="azurefiles_blob_upload",
        description="Upload a local file to an Azure Blob container.",
    )
    def azurefiles_blob_upload(
        account_name: str,
        container_name: str,
        local_path: str,
        blob_name: Optional[str] = None,
        overwrite: bool = False,
        auth: str = "default",
        api_key: Optional[str] = None,
    ) -> dict:
        """Upload a local file to Azure Blob Storage.

        Args:
            account_name: Azure storage account name.
            container_name: Target blob container.
            local_path: Path to local file to upload.
            blob_name: Destination blob name (default: basename of local_path).
            overwrite: Whether to overwrite an existing blob.
            auth: 'default' (DefaultAzureCredential) or 'key' (with api_key).
            api_key: Storage account access key (when auth='key').
        """
        from .blob import blob_upload_handler
        args: dict[str, Any] = {
            "account_name": account_name,
            "container_name": container_name,
            "local_path": local_path,
            "overwrite": overwrite,
            "auth": auth,
        }
        if blob_name is not None:
            args["blob_name"] = blob_name
        if api_key is not None:
            args["api_key"] = api_key
        return _parse(blob_upload_handler(args))

    @af.tool(
        name="azurefiles_blob_download",
        description="Download a blob from an Azure Blob container to a local file.",
    )
    def azurefiles_blob_download(
        account_name: str,
        container_name: str,
        blob_name: str,
        local_path: str,
        auth: str = "default",
        api_key: Optional[str] = None,
    ) -> dict:
        """Download a blob to a local file path.

        Args:
            account_name: Azure storage account name.
            container_name: Source blob container.
            blob_name: Name of the blob to download.
            local_path: Local destination path.
            auth: 'default' or 'key'.
            api_key: Storage account access key (when auth='key').
        """
        from .blob import blob_download_handler
        args: dict[str, Any] = {
            "account_name": account_name,
            "container_name": container_name,
            "blob_name": blob_name,
            "local_path": local_path,
            "auth": auth,
        }
        if api_key is not None:
            args["api_key"] = api_key
        return _parse(blob_download_handler(args))

    @af.tool(
        name="azurefiles_blob_list",
        description="List blobs in an Azure Blob container (optionally by prefix).",
    )
    def azurefiles_blob_list(
        account_name: str,
        container_name: str,
        prefix: Optional[str] = None,
        max_results: int = 100,
        auth: str = "default",
        api_key: Optional[str] = None,
    ) -> dict:
        """List blobs in a container.

        Args:
            account_name: Azure storage account name.
            container_name: Container to list.
            prefix: Optional prefix filter.
            max_results: Max blobs to return (1-1000, default 100).
            auth: 'default' or 'key'.
            api_key: Storage account access key (when auth='key').
        """
        from .blob import blob_list_handler
        args: dict[str, Any] = {
            "account_name": account_name,
            "container_name": container_name,
            "max_results": max_results,
            "auth": auth,
        }
        if prefix is not None:
            args["prefix"] = prefix
        if api_key is not None:
            args["api_key"] = api_key
        return _parse(blob_list_handler(args))

    return [
        azurefiles_mount,
        azurefiles_unmount,
        azurefiles_status,
        azurefiles_setup,
        azurefiles_blob_upload,
        azurefiles_blob_download,
        azurefiles_blob_list,
    ]


__all__ = ["get_maf_tools"]
